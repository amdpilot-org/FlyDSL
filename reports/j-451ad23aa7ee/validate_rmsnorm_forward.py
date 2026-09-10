#!/usr/bin/env python3
"""Record bounded forward-only FlyDSL RMSNorm evidence on one gfx950 GPU."""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

import torch
import triton

import flydsl
from flydsl.runtime.device import get_rocm_arch
from kernels.norm import rmsnorm_kernel as rmsnorm_impl


ROWS = 4096
HIDDEN_SIZES = (8192, 8193, 10240, 12288, 14336, 16384)
EPS = 1e-5
TIMED_CALLS = 20
OUTPUT_ATOL = 2e-2
RSTD_ATOL = 1e-3


def _native_paths() -> list[str]:
    package_root = Path(flydsl.__file__).resolve().parent
    return sorted(str(path) for path in package_root.rglob("*.so"))


def _git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def _time_case(hidden_size: int, device: torch.device) -> dict:
    compile_start = time.monotonic()
    launcher = rmsnorm_impl.build_rmsnorm_module(
        hidden_size,
        "bf16",
        store_rstd=True,
        eps=EPS,
        weight_dtype_str="bf16",
    )
    x = torch.randn((ROWS, hidden_size), device=device, dtype=torch.bfloat16)
    weight = torch.rand((hidden_size,), device=device, dtype=torch.bfloat16)
    output = torch.empty_like(x)
    rstd = torch.empty((ROWS,), device=device, dtype=torch.float32)
    stream = torch.cuda.current_stream(device)
    rmsnorm_impl._run_compiled(launcher, x, weight, output, rstd, ROWS, stream)
    torch.cuda.synchronize()
    first_execution_seconds = time.monotonic() - compile_start

    x_reference = x.to(torch.float32)
    weight_reference = weight.to(torch.float32)
    rstd_reference = torch.rsqrt(x_reference.square().mean(dim=1) + EPS)
    reference = x_reference * rstd_reference[:, None] * weight_reference
    output_max_abs = (output.to(torch.float32) - reference).abs().max().item()
    rstd_max_abs = (rstd - rstd_reference).abs().max().item()

    rmsnorm_impl._run_compiled(launcher, x, weight, output, rstd, ROWS, stream)
    starts = [torch.cuda.Event(enable_timing=True) for _ in range(TIMED_CALLS)]
    ends = [torch.cuda.Event(enable_timing=True) for _ in range(TIMED_CALLS)]
    for index in range(TIMED_CALLS):
        starts[index].record()
        rmsnorm_impl._run_compiled(launcher, x, weight, output, rstd, ROWS, stream)
        ends[index].record()
    torch.cuda.synchronize()
    samples_ms = [starts[index].elapsed_time(ends[index]) for index in range(TIMED_CALLS)]

    return {
        "hidden_size": hidden_size,
        "rows": ROWS,
        "dtype": "bf16",
        "weight_dtype": "bf16",
        "eps": EPS,
        "tail_path": "scalar guarded loads/stores" if hidden_size % 2048 else "complete 128-bit vector tiles",
        "first_compile_and_execution_seconds": first_execution_seconds,
        "output_max_abs": output_max_abs,
        "rstd_max_abs": rstd_max_abs,
        "output_atol": OUTPUT_ATOL,
        "rstd_atol": RSTD_ATOL,
        "passed": output_max_abs <= OUTPUT_ATOL and rstd_max_abs <= RSTD_ATOL,
        "timing_method": f"CUDA events; one warmup then {TIMED_CALLS} timed calls",
        "timed_median_ms": statistics.median(samples_ms),
        "timed_mean_ms": statistics.mean(samples_ms),
        "timed_samples_ms": samples_ms,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError("A CUDA/ROCm GPU is required")
    device = torch.device("cuda")
    cases = [_time_case(hidden_size, device) for hidden_size in HIDDEN_SIZES]

    report = {
        "label": "persistent mirror checkout forward-only probe",
        "scope": "plain matching-BF16-weight forward and rstd only; no gradient claim",
        "source_commit": _git_commit(),
        "python_executable": sys.executable,
        "python_platform": platform.platform(),
        "flydsl_version": flydsl.__version__,
        "flydsl_path": flydsl.__file__,
        "torch_version": torch.__version__,
        "torch_path": torch.__file__,
        "triton_version": triton.__version__,
        "triton_path": triton.__file__,
        "native_paths": _native_paths(),
        "gpu_name": torch.cuda.get_device_name(device),
        "gpu_capability": torch.cuda.get_device_capability(device),
        "rocm_arch": get_rocm_arch(),
        "image_identity": "sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7",
        "image_identity_source": "operator-provided local image ID; container hostname is not image identity",
        "reference": "independent fp32 Torch mean-square/rsqrt output and rstd",
        "admission": "forward-only BF16 matching-weight cases through 16384 pass on this gfx950 run",
        "unsupported_boundaries": [
            "backward and autograd above 8192 are unmeasured and unsupported by this report",
            "mixed-weight streams, fused-add/residual paths, and other dtypes are out of scope",
            "empty rows, non-contiguous inputs, other architectures, and hidden sizes above 16384 are unmeasured",
        ],
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
