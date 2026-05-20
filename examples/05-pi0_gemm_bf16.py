#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Benchmark FlyDSL bf16 GEMM for pi0 LIBERO hot shape (M=3072,N=3072,K=1536)."""

import torch
from aiter.ops.flydsl.gemm_kernels import flydsl_hgemm
from aiter.ops.shuffle import shuffle_weight


def bench_pi0_gemm():
    device = "cuda:0"
    M, N, K = 3072, 3072, 1536
    warmup = 3
    iters = 20

    a = torch.randn(M, K, dtype=torch.bfloat16, device=device)
    b = shuffle_weight(torch.randn(N, K, dtype=torch.bfloat16, device=device), layout=(16, 16))

    # Warmup / JIT compile
    for _ in range(warmup):
        flydsl_hgemm(
            a, b,
            tile_m=64, tile_n=256, tile_k=64,
            split_k=1, block_m_warps=1, block_n_warps=4,
            b_to_lds=False, b_preshuffle=True, auto_shuffle_b=False,
        )
    torch.cuda.synchronize()

    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    start.record()
    for _ in range(iters):
        flydsl_hgemm(
            a, b,
            tile_m=64, tile_n=256, tile_k=64,
            split_k=1, block_m_warps=1, block_n_warps=4,
            b_to_lds=False, b_preshuffle=True, auto_shuffle_b=False,
        )
    end.record()
    torch.cuda.synchronize()

    avg_ms = start.elapsed_time(end) / iters
    flops = 2 * M * N * K
    tflops = flops / (avg_ms * 1e-3) / 1e12
    print(f"pi0_gemm_bf16: {avg_ms:.4f} ms/iter -> {tflops:.2f} TFLOPS")
    print(f"iters_per_second: {1000.0 / avg_ms:.2f}")


if __name__ == "__main__":
    bench_pi0_gemm()
