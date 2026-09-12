#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

"""Cross-process AOT cache coverage for runtime scalar arguments."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest
import torch

pytestmark = [pytest.mark.l2_device, pytest.mark.rocm_lower]

if not torch.cuda.is_available():
    pytest.skip("CUDA/ROCm not available", allow_module_level=True)

import flydsl.compiler as flyc  # noqa: E402
import flydsl.expr as fx  # noqa: E402


@flyc.kernel
def _scalar_kernel(Out: fx.Tensor, value: fx.Int32):
    Out[0] = value * value + fx.Int32(3)


@flyc.jit
def _scalar_launch(Out: fx.Tensor, value: fx.Int32, stream: fx.Stream = fx.Stream(None)):
    _scalar_kernel(Out, value).launch(grid=(1, 1, 1), block=(1, 1, 1), stream=stream.value)


def _tensor(dtype=torch.int32):
    output = torch.zeros(1, device="cuda", dtype=dtype)
    return output, flyc.from_torch_tensor(output).mark_layout_dynamic(leading_dim=0, divisibility=1)


def _artifact_paths(cache_root: Path) -> list[Path]:
    return sorted(path for path in cache_root.rglob("*") if path.is_file() and path.suffix != ".lock")


def _worker(mode: str, cache_root: Path) -> None:
    print(f"mode={mode}")
    print(f"gpu={torch.cuda.get_device_name(0)}")
    print(f"cache_root={cache_root.resolve()}")

    if mode == "export":
        _, output_arg = _tensor()
        _scalar_launch(output_arg, 0)
        artifacts = _artifact_paths(cache_root)
        assert artifacts, f"no AOT artifact written below {cache_root}"
        for artifact in artifacts:
            print(f"artifact={artifact.resolve()}")
        print("native_artifact=embedded in serialized CompiledArtifact")
        return

    if mode == "reload":
        cases = (-7, 11)
        for value in cases:
            output, output_arg = _tensor()
            _scalar_launch(output_arg, value)
            torch.cuda.synchronize()
            # Compute the reference independently with Torch tensor operations.
            reference = torch.tensor(value, device="cuda", dtype=torch.int32).square().add(3)
            torch.testing.assert_close(output[0], reference, rtol=0, atol=0)
            print(f"scalar={value} actual={output.item()} torch_reference={reference.item()} comparison=exact")

        _, wrong_schema = _tensor(torch.float32)
        with pytest.raises(RuntimeError, match="no usable AOT cache") as exc_info:
            _scalar_launch(wrong_schema, cases[0])
        print(f"invalid_schema=torch.float32 rejection={exc_info.value}")
        return

    raise ValueError(f"unknown worker mode: {mode}")


def test_aot_runtime_scalar_roundtrip(tmp_path):
    """Export once, then reload for two scalar values without allowing JIT fallback."""
    cache_root = tmp_path / "aot-cache"
    base_env = os.environ.copy()
    base_env["FLYDSL_RUNTIME_CACHE_DIR"] = str(cache_root)
    base_env["PYTHONUNBUFFERED"] = "1"

    commands = []
    outputs = []
    for mode, setting in (("export", ("COMPILE_ONLY", "1")), ("reload", ("FLYDSL_RUNTIME_RUN_ONLY", "1"))):
        env = base_env.copy()
        env[setting[0]] = setting[1]
        command = [sys.executable, str(Path(__file__).resolve()), "--worker", mode, str(cache_root)]
        commands.append(command)
        result = subprocess.run(command, env=env, text=True, capture_output=True, check=False)
        outputs.append(result.stdout + result.stderr)
        assert result.returncode == 0, outputs[-1]

    print("\n".join(f"command={' '.join(command)}" for command in commands))
    print("".join(outputs))


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] != "--worker":
        raise SystemExit(f"usage: {sys.argv[0]} --worker export|reload CACHE_ROOT")
    _worker(sys.argv[2], Path(sys.argv[3]))
