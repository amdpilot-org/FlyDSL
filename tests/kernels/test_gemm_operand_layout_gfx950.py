#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""Validate FP8 fx.gemm operand storage layouts on gfx950.

The scale format is two per-tensor float32 scalars applied after the raw FP8
MFMA.  The independent reference dequantizes both FP8 operands to float32
before multiplying by those exact scalars.
"""

import os
import sys

import pytest
import torch

import flydsl.compiler as flyc
import flydsl.expr as fx

pytestmark = [pytest.mark.l2_device, pytest.mark.rocm_lower]

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

if not torch.cuda.is_available():
    pytest.skip("CUDA/ROCm not available. Skipping GPU tests.", allow_module_level=True)

from flydsl.runtime.device import get_rocm_arch  # noqa: E402

_ARCH = str(get_rocm_arch() or "")
if _ARCH != "gfx950":
    pytest.skip(
        f"FP8 operand-layout GEMM test requires gfx950, got {_ARCH}",
        allow_module_level=True,
    )


@flyc.kernel
def gemm_kernel(
    A: fx.Tensor,
    B: fx.Tensor,
    C: fx.Tensor,
    M: fx.Constexpr[int],
    N: fx.Constexpr[int],
    K: fx.Constexpr[int],
):
    tid = fx.thread_idx.x
    bid = fx.block_idx.x

    bA = fx.zipped_divide(A, (M, K))
    bB = fx.zipped_divide(B, (N, K))
    bC = fx.zipped_divide(C, (M, N))
    bA = fx.slice(bA, (None, bid))
    bB = fx.slice(bB, (None, bid))
    bC = fx.slice(bC, (None, bid))

    mma_atom = fx.make_mma_atom(fx.rocdl.MFMA(16, 16, 32, fx.Float8E4M3FN))
    tiled_mma = fx.make_tiled_mma(
        mma_atom,
        fx.make_layout((2, 2, 1), (1, 2, 0)),
    )
    thr_mma = tiled_mma.thr_slice(tid)

    copy_atom = fx.make_copy_atom(fx.UniversalCopy32b(), fx.Float8E4M3FN)
    tiled_copy_a = fx.make_tiled_copy_A(copy_atom, tiled_mma)
    tiled_copy_b = fx.make_tiled_copy_B(copy_atom, tiled_mma)
    tiled_copy_c = fx.make_tiled_copy_C(
        fx.make_copy_atom(fx.UniversalCopy32b(), fx.Float32),
        tiled_mma,
    )
    thr_copy_a = tiled_copy_a.get_slice(tid)
    thr_copy_b = tiled_copy_b.get_slice(tid)
    thr_copy_c = tiled_copy_c.get_slice(tid)

    frag_a = thr_mma.make_fragment_A(bA)
    frag_b = thr_mma.make_fragment_B(bB)
    frag_c = thr_mma.make_fragment_C(bC)

    fx.copy(
        copy_atom,
        thr_copy_a.partition_S(bA),
        thr_copy_a.retile(frag_a),
        pred=None,
    )
    fx.copy(
        copy_atom,
        thr_copy_b.partition_S(bB),
        thr_copy_b.retile(frag_b),
        pred=None,
    )
    frag_c.fill(0.0)
    fx.gemm(mma_atom, frag_c, frag_a, frag_b, frag_c)
    fx.copy(
        fx.make_copy_atom(fx.UniversalCopy32b(), fx.Float32),
        thr_copy_c.retile(frag_c),
        thr_copy_c.partition_D(bC),
        pred=None,
    )


@flyc.jit
def launch_gemm(
    A: fx.Tensor,
    B: fx.Tensor,
    C: fx.Tensor,
    M: fx.Constexpr[int],
    N: fx.Constexpr[int],
    K: fx.Constexpr[int],
    stream: fx.Stream = fx.Stream(None),
):
    gemm_kernel(A, B, C, M, N, K).launch(
        grid=(1, 1, 1),
        block=(256, 1, 1),
        stream=stream,
    )


def _timed(fn):
    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    torch.cuda.synchronize()
    start.record()
    result = fn()
    end.record()
    torch.cuda.synchronize()
    return result, start.elapsed_time(end) / 1000.0


def _layout_operand(tensor, layout_char):
    if layout_char == "n":
        return tensor, 0.0
    return _timed(lambda: tensor.t().contiguous().t())


@pytest.mark.parametrize(
    "M, N, K",
    [
        (64, 32, 32),
        (96, 64, 64),
    ],
    ids=["64x32x32", "96x64x64"],
)
@pytest.mark.parametrize(
    "layout",
    [
        pytest.param("nn", id="nn"),
        pytest.param(
            "nt",
            marks=pytest.mark.xfail(
                strict=True,
                reason="fx.gemm admits transposed B storage but changes values",
            ),
        ),
        pytest.param(
            "tn",
            marks=pytest.mark.xfail(
                strict=True,
                reason="fx.gemm admits transposed A storage but changes values",
            ),
        ),
        pytest.param(
            "tt",
            marks=pytest.mark.xfail(
                strict=True,
                reason="fx.gemm admits transposed A/B storage but changes values",
            ),
        ),
    ],
)
def test_fp8_gemm_operand_layout_parity(M, N, K, layout):
    device = torch.device("cuda")
    torch.manual_seed(821)
    a_fp32 = torch.randn(M, K, device=device, dtype=torch.float32).clamp_(-1, 1)
    b_fp32 = torch.randn(N, K, device=device, dtype=torch.float32).clamp_(-1, 1)
    a_fp8 = a_fp32.to(torch.float8_e4m3fn)
    b_fp8 = b_fp32.to(torch.float8_e4m3fn)
    scale_a = torch.tensor(0.017, device=device, dtype=torch.float32)
    scale_b = torch.tensor(0.019, device=device, dtype=torch.float32)

    a_operand, a_conversion = _layout_operand(a_fp8, layout[0])
    b_operand, b_conversion = _layout_operand(b_fp8, layout[1])
    output = torch.zeros(M, N, device=device, dtype=torch.float32)
    stream = torch.cuda.Stream()

    launch_gemm(a_operand, b_operand, output, M, N, K, stream=stream)
    torch.cuda.synchronize()

    raw_reference = a_operand.float() @ b_operand.float().t()
    reference = raw_reference * (scale_a * scale_b)
    scaled_output = output * (scale_a * scale_b)
    max_abs_error = (scaled_output - reference).abs().max().item()
    relative_error = max_abs_error / max(reference.abs().max().item(), 1e-12)

    for _ in range(2):
        launch_gemm(a_operand, b_operand, output, M, N, K, stream=stream)
    durations = []
    for _ in range(5):
        _, duration = _timed(
            lambda: launch_gemm(
                a_operand,
                b_operand,
                output,
                M,
                N,
                K,
                stream=stream,
            )
        )
        durations.append(duration)

    print(
        {
            "shape": [M, N, K],
            "layout": layout,
            "a_stride": list(a_operand.stride()),
            "b_stride": list(b_operand.stride()),
            "conversion_seconds": a_conversion + b_conversion,
            "kernel_seconds_mean": sum(durations) / len(durations),
            "kernel_seconds_min": min(durations),
            "kernel_seconds_max": max(durations),
            "max_abs_error": max_abs_error,
            "relative_to_reference_max": relative_error,
        },
        flush=True,
    )
    torch.testing.assert_close(
        scaled_output,
        reference,
        rtol=1e-4,
        atol=2e-5,
    )
