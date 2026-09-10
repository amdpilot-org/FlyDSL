#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

import os
import sys

import pytest
import torch

import flydsl.compiler as flyc

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

pytestmark = [pytest.mark.l2_device, pytest.mark.rocm_lower]

if not torch.cuda.is_available():
    pytest.skip("CUDA/ROCm not available. Skipping GPU tests.", allow_module_level=True)

from flydsl.runtime.device import get_rocm_arch  # noqa: E402
from kernels.gemm.preshuffle_gemm import compile_preshuffle_gemm  # noqa: E402
from tests.utils import shuffle_weight  # noqa: E402


def _run_boundary_case(m, n, k, tile_m=32, tile_n=64, tile_k=64):
    if get_rocm_arch() not in ("gfx942", "gfx950"):
        pytest.skip(f"v2 preshuffle GEMM requires gfx942/gfx950, got {get_rocm_arch()}")

    device = torch.device("cuda")
    dtype = torch.bfloat16
    sentinel = torch.tensor(-8192.0, dtype=dtype, device=device)
    a_alloc = torch.full(((m + 1) * k,), sentinel, dtype=dtype, device=device)
    b_alloc = torch.full(((n + 1) * k,), sentinel, dtype=dtype, device=device)
    c_alloc = torch.full((m * n + 16,), sentinel, dtype=dtype, device=device)
    a = a_alloc[: m * k].view(m, k)
    b = b_alloc[: n * k].view(n, k)
    c = c_alloc[: m * n].view(m, n)

    a.uniform_(-1, 1)
    b.uniform_(-1, 1)
    b_reference = b.clone()
    b_shuffled = shuffle_weight(b)
    b_alloc[: n * k].view(n, k).copy_(b_shuffled)

    launch_gemm = compile_preshuffle_gemm(
        N=n,
        K=k,
        tile_m=tile_m,
        tile_n=tile_n,
        tile_k=tile_k,
        in_dtype="bf16",
        out_dtype="bf16",
    )
    empty_f32 = torch.empty((0,), dtype=torch.float32, device=device)
    empty_bf16 = torch.empty((0,), dtype=dtype, device=device)
    args = (
        c.contiguous().view(-1),
        a.contiguous().view(-1),
        b_alloc[: n * k].view(-1),
        empty_f32,
        empty_f32,
        empty_bf16,
        m,
        n,
        torch.cuda.current_stream(),
    )
    compiled_gemm = flyc.compile(launch_gemm, *args)
    compiled_gemm(*args)
    torch.cuda.synchronize()

    reference = torch.mm(a.float(), b_reference.float().t())
    actual = c.float()
    torch.testing.assert_close(actual, reference, rtol=0.1, atol=0.1)

    a_guard = a_alloc[m * k :]
    b_guard = b_alloc[n * k :]
    c_guard = c_alloc[m * n :]
    assert torch.all(a_guard == sentinel)
    assert torch.all(b_guard == sentinel)
    assert torch.all(c_guard == sentinel)

    absolute_error = (actual - reference).abs()
    return {
        "max_abs_error": absolute_error.max().item(),
        "mean_abs_error": absolute_error.mean().item(),
        "a_guard_changes": int((a_guard != sentinel).sum().item()),
        "b_guard_changes": int((b_guard != sentinel).sum().item()),
        "c_guard_changes": int((c_guard != sentinel).sum().item()),
    }


@pytest.mark.parametrize(
    "m,n,k",
    [
        (32, 64, 64),
        (33, 64, 64),
    ],
)
def test_preshuffle_bf16_tail_boundaries(m, n, k):
    result = _run_boundary_case(m, n, k)
    print(result)


def test_preshuffle_bf16_rejects_n_tail():
    if get_rocm_arch() not in ("gfx942", "gfx950"):
        pytest.skip(f"v2 preshuffle GEMM requires gfx942/gfx950, got {get_rocm_arch()}")
    with pytest.raises(ValueError, match=r"tile_n must be a positive divisor of N"):
        compile_preshuffle_gemm(
            N=80,
            K=64,
            tile_m=32,
            tile_n=64,
            tile_k=64,
            in_dtype="bf16",
            out_dtype="bf16",
        )


def test_preshuffle_bf16_rejects_k_tail():
    if get_rocm_arch() not in ("gfx942", "gfx950"):
        pytest.skip(f"v2 preshuffle GEMM requires gfx942/gfx950, got {get_rocm_arch()}")
    with pytest.raises(ValueError, match=r"tile_k must be a positive divisor of K"):
        compile_preshuffle_gemm(
            N=64,
            K=65,
            tile_m=32,
            tile_n=64,
            tile_k=64,
            in_dtype="bf16",
            out_dtype="bf16",
        )
