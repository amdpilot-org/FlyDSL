#!/usr/bin/env python3
"""Benchmark script for pi0 LIBERO hot-shape bf16 GEMM on MI300X.

Target: M=3072, N=3072, K=1536 via hgemm_splitk (gfx942).
"""
import os
import sys
import time
import statistics

_FLYDSL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _FLYDSL_ROOT not in sys.path:
    sys.path.insert(0, _FLYDSL_ROOT)

import torch
from kernels.hgemm_splitk import hgemm_splitk_

M, N, K = 3072, 3072, 1536
DTYPE = torch.bfloat16
DEVICE = torch.device("cuda")
WARMUP = 20
ITERS = 100


def main():
    if not torch.cuda.is_available():
        print("ERROR: CUDA/ROCm not available")
        return 1

    torch.manual_seed(42)
    a = torch.randn((M, K), device=DEVICE, dtype=DTYPE)
    b = torch.randn((N, K), device=DEVICE, dtype=DTYPE)
    c = torch.zeros((M, N), device=DEVICE, dtype=DTYPE)

    tile_kwargs = {
        "TILE_M": 128,
        "TILE_N": 128,
        "TILE_K": 64,
        "SPLIT_K": 1,
        "BLOCK_M_WARPS": 2,
        "BLOCK_N_WARPS": 2,
        "BLOCK_K_WARPS": 1,
    }

    for _ in range(WARMUP):
        c.zero_()
        hgemm_splitk_(c, a, b, hgemm_kwargs=tile_kwargs)
    torch.cuda.synchronize()

    times = []
    for _ in range(ITERS):
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        hgemm_splitk_(c, a, b, hgemm_kwargs=tile_kwargs)
        torch.cuda.synchronize()
        times.append((time.perf_counter() - t0) * 1000.0)

    median_ms = statistics.median(times)
    mean_ms = statistics.mean(times)
    min_ms = min(times)
    max_ms = max(times)

    flops = 2.0 * M * N * K
    tflops = flops / (median_ms / 1000.0) / 1e12
    iters_per_second = 1000.0 / median_ms

    c_ref = torch.mm(a, b.T)
    max_err = (c - c_ref).abs().max().item()

    print(f"M={M} N={N} K={K} dtype={DTYPE}")
    print(f"median_ms: {median_ms:.4f}")
    print(f"mean_ms: {mean_ms:.4f}")
    print(f"min_ms: {min_ms:.4f}")
    print(f"max_ms: {max_ms:.4f}")
    print(f"tflops: {tflops:.2f}")
    print(f"iters_per_second: {iters_per_second:.2f}")
    print(f"max_abs_err: {max_err:.4f}")
    print(f"\nFINAL iters_per_second: {iters_per_second:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
