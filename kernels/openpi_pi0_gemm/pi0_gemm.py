# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

"""OpenPI PI0 LIBERO bf16 GEMM kernel (FlyDSL).

Target: M=11, N=1024, K=2048, bf16.
Layout: A row-major (M,K), B stored row-major (N,K), used as B^T.
C = A @ B.T

This module builds a FlyDSL preshuffle GEMM pipeline tuned for the small-batch
decode shape that dominates the pi0 policy-inference trace (rank-1 GEMM hotspot).
"""

from typing import Optional, Tuple
import torch
import flydsl.compiler as flyc
from kernels.preshuffle_gemm import compile_preshuffle_gemm_a8
from tests.utils import shuffle_weight

# Target shape constants
PI0_M: int = 11
PI0_N: int = 1024
PI0_K: int = 2048
_PI0_TILE_M: int = 16
_PI0_TILE_N: int = 64
_PI0_TILE_K: int = 256
_PI0_LDS_STAGE: int = 2

# Cached compiled state
_compile_cache: dict = {}


def build_pi0_gemm_module(
    M: int = PI0_M,
    N: int = PI0_N,
    K: int = PI0_K,
    tile_m: int = _PI0_TILE_M,
    tile_n: int = _PI0_TILE_N,
    tile_k: int = _PI0_TILE_K,
    lds_stage: int = _PI0_LDS_STAGE,
):
    """Compile the FlyDSL bf16 GEMM kernel for the pi0 target shape.

    Returns a JitFunction ready for flyc.compile(...).
    """
    cache_key = (M, N, K, tile_m, tile_n, tile_k, lds_stage)
    if cache_key not in _compile_cache:
        launch_fn = compile_preshuffle_gemm_a8(
            M=M,
            N=N,
            K=K,
            tile_m=tile_m,
            tile_n=tile_n,
            tile_k=tile_k,
            in_dtype="bf16",
            out_dtype="bf16",
            lds_stage=lds_stage,
        )
        _compile_cache[cache_key] = launch_fn
    return _compile_cache[cache_key]


def _prepare_args(
    a: torch.Tensor,
    b: torch.Tensor,
    c: Optional[torch.Tensor] = None,
    stream=None,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, Tuple]:
    """Flatten tensors and construct kernel args.

    *a* is (M, K) row-major bf16.
    *b* is (N, K) row-major bf16; will be shuffled internally.
    *c* is optional (M, N) output buffer.
    """
    if a.dtype != torch.bfloat16:
        raise TypeError(f"pi0_gemm expects bf16 input A, got {a.dtype}")
    if b.dtype != torch.bfloat16:
        raise TypeError(f"pi0_gemm expects bf16 input B, got {b.dtype}")
    M, K = a.shape
    N, K2 = b.shape
    if K != K2:
        raise ValueError(f"K mismatch: A has {K}, B has {K2}")

    if c is None:
        c = torch.empty((M, N), dtype=torch.bfloat16, device=a.device)

    # One-time preshuffle of B weight matrix.
    b_shuffled = shuffle_weight(b, layout=(16, 16))

    sa = torch.empty((0,), device=a.device, dtype=torch.float32)
    sb = torch.empty((0,), device=a.device, dtype=torch.float32)
    dummy_bias = torch.empty(0, dtype=torch.bfloat16, device=a.device)

    stream = stream or torch.cuda.current_stream()
    return a, b_shuffled, c, (c.contiguous().view(-1),
                              a.contiguous().view(-1),
                              b_shuffled.contiguous().view(-1),
                              sa, sb, dummy_bias,
                              M, N, stream)


def pi0_gemm_dispatch(
    a: torch.Tensor,
    b: torch.Tensor,
    c: Optional[torch.Tensor] = None,
    stream=None,
) -> torch.Tensor:
    """Dispatch the pi0 FlyDSL bf16 GEMM kernel.

    Args:
        a: (M, K) bf16, row-major.
        b: (N, K) bf16, row-major (will be used as B^T).
        c: optional (M, N) bf16 output buffer.
        stream: optional CUDA/HIP stream.

    Returns:
        c: (M, N) bf16 result tensor.
    """
    a, b_shuffled, c, args = _prepare_args(a, b, c, stream)
    launch_fn = build_pi0_gemm_module(M=a.shape[0], N=b.shape[0], K=a.shape[1])
    compiled = flyc.compile(launch_fn, *args)
    compiled(*args)
    return c


def benchmark_pi0_gemm(
    warmup: int = 20,
    iters: int = 100,
    M: int = PI0_M,
    N: int = PI0_N,
    K: int = PI0_K,
) -> dict:
    """Benchmark the pi0 GEMM kernel against torch.mm baseline.

    Returns a dict with timing metrics. If no GPU is available, returns a
    stub result indicating the benchmark was skipped (so import-time and
    smoke-test verification on CPU-only machines do not fail).
    """
    import statistics
    import time

    if not torch.cuda.is_available():
        return {
            "M": M,
            "N": N,
            "K": K,
            "dtype": "bf16",
            "layout": "rowmajor_storage_transposed",
            "skipped": True,
            "reason": "no CUDA/HIP GPU available",
        }

    device = torch.device("cuda")
    torch.manual_seed(123)
    a = torch.randn((M, K), device=device, dtype=torch.bfloat16)
    b = torch.randn((N, K), device=device, dtype=torch.bfloat16)

    # --- FlyDSL path ---
    a_in, b_shuffled, c_out, args = _prepare_args(a, b)
    launch_fn = build_pi0_gemm_module(M=M, N=N, K=K)
    compiled = flyc.compile(launch_fn, *args)

    for _ in range(warmup):
        c_out.zero_()
        compiled(*args)
    torch.cuda.synchronize()

    times = []
    for _ in range(iters):
        c_out.zero_()
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        compiled(*args)
        torch.cuda.synchronize()
        times.append((time.perf_counter() - t0) * 1000.0)
    flydsl_med = statistics.median(times)
    flydsl_mean = statistics.mean(times)

    # --- torch.mm baseline ---
    b_t = b.t()
    for _ in range(warmup):
        c_ref = torch.mm(a, b_t)
    torch.cuda.synchronize()
    times_ref = []
    for _ in range(iters):
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        c_ref = torch.mm(a, b_t)
        torch.cuda.synchronize()
        times_ref.append((time.perf_counter() - t0) * 1000.0)
    torch_med = statistics.median(times_ref)
    torch_mean = statistics.mean(times_ref)

    # correctness sanity
    c_ref_f32 = torch.mm(a.float(), b_t.float()).to(torch.bfloat16)
    max_abs_vs_ref = (c_out - c_ref_f32).abs().max().item()

    tflops = (2 * M * N * K) / (flydsl_med / 1000.0) / 1e12
    return {
        "M": M,
        "N": N,
        "K": K,
        "dtype": "bf16",
        "layout": "rowmajor_storage_transposed",
        "bf16_torch_mm_median_ms": torch_med,
        "bf16_flydsl_gemm_median_ms": flydsl_med,
        "bf16_flydsl_gemm_mean_ms": flydsl_mean,
        "speedup_vs_torch_mm": torch_med / flydsl_med,
        "tflops_median": tflops,
        "max_abs_vs_fp32_ref_bf16": max_abs_vs_ref,
    }


if __name__ == "__main__":
    import json
    result = benchmark_pi0_gemm()
    print(json.dumps(result, indent=2))
