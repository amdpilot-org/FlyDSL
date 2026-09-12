# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""AITER/FlyDSL downstream tensor and stream integration regression.

This file is also an executable so the SGLang nightly can run it inside the
same container in which it installs AITER and the FlyDSL wheel under test.
"""

from __future__ import annotations

import importlib

import torch


def _run_aiter_flydsl_hgemm() -> dict[str, object]:
    aiter = importlib.import_module("aiter")
    flydsl = importlib.import_module("flydsl")
    flydsl_ops = importlib.import_module("aiter.ops.flydsl")

    if not torch.cuda.is_available():
        raise RuntimeError("AITER/FlyDSL integration requires a ROCm GPU")

    device = torch.device("cuda", 0)
    arch = torch.cuda.get_device_properties(device).gcnArchName.split(":", 1)[0]
    dtype = torch.bfloat16
    m = n = k = 64

    # Build the numerical reference independently on the CPU in fp32.  Moving
    # the inputs and launching HGEMM on a non-default stream also verifies that
    # AITER forwards the Torch stream through fx.Stream to the FlyDSL launcher.
    generator = torch.Generator(device="cpu").manual_seed(603)
    a_cpu = torch.randn((m, k), generator=generator, dtype=torch.float32)
    b_cpu = torch.randn((n, k), generator=generator, dtype=torch.float32)
    reference = torch.mm(a_cpu.to(dtype).float(), b_cpu.to(dtype).float().t()).to(dtype)

    stream = torch.cuda.Stream(device=device)
    with torch.cuda.stream(stream):
        a = a_cpu.to(device=device, dtype=dtype)
        b = b_cpu.to(device=device, dtype=dtype)
        output = flydsl_ops.flydsl_hgemm(
            a,
            b,
            tile_m=64,
            tile_n=64,
            tile_k=64,
            block_m_warps=1,
            block_n_warps=1,
            block_k_warps=1,
            # AITER derives this setting from the active architecture.  Pass it
            # explicitly because gfx942 uses synchronous copies while gfx950
            # and the other supported CDNA targets use async copies.
            async_copy=arch != "gfx942",
            stream=stream,
        )
        completion = torch.cuda.Event()
        completion.record(stream)

    torch.cuda.current_stream(device).wait_event(completion)
    actual = output.cpu()
    max_abs_error = (actual.float() - reference.float()).abs().max().item()
    torch.testing.assert_close(actual, reference, atol=0.5, rtol=0.03)

    evidence = {
        "aiter_path": aiter.__file__,
        "flydsl_path": flydsl.__file__,
        "gpu_arch": arch,
        "input_shape": [m, k],
        "weight_shape": [n, k],
        "output_shape": list(actual.shape),
        "stream": int(stream.cuda_stream),
        "max_abs_error": max_abs_error,
    }
    print(f"AITER_FLYDSL_HGEMM_OK {evidence}")
    return evidence


def test_aiter_flydsl_hgemm_tensor_and_stream_boundary() -> None:
    import pytest

    pytest.importorskip("aiter", reason="requires the downstream amd-aiter package")
    _run_aiter_flydsl_hgemm()


if __name__ == "__main__":
    _run_aiter_flydsl_hgemm()
