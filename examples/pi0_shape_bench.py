# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors
#
# Profiling probe for pi0 LIBERO hot shape: M=3072, N=3072, K=1536, bf16.
# Compares eager torch.mm, torch.compile, and a minimal FlyDSL tiled MMA.

import torch
import statistics
import json

M, N, K = 3072, 3072, 1536
WARMUP = 5
ITERS = 200

def bench_eager(a, b):
    for _ in range(WARMUP):
        c = torch.mm(a, b)
    torch.cuda.synchronize()

    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    start.record()
    for _ in range(ITERS):
        c = torch.mm(a, b)
    end.record()
    torch.cuda.synchronize()
    return start.elapsed_time(end) / ITERS, c

def bench_compile(a, b):
    @torch.compile(mode="max-autotune", fullgraph=True)
    def mm_fn(x, y):
        return x @ y

    for _ in range(WARMUP):
        c = mm_fn(a, b)
    torch.cuda.synchronize()

    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    start.record()
    for _ in range(ITERS):
        c = mm_fn(a, b)
    end.record()
    torch.cuda.synchronize()
    return start.elapsed_time(end) / ITERS, c

def bench_flydsl(a, b):
    import flydsl.compiler as flyc
    import flydsl.expr as fx

    block_m = 64
    block_n = 64
    block_k = 8

    @flyc.kernel
    def gemm_kernel(A: fx.Tensor, B: fx.Tensor, C: fx.Tensor):
        tid = fx.thread_idx.x
        bid = fx.block_idx.x

        A = fx.rocdl.make_buffer_tensor(A)
        B = fx.rocdl.make_buffer_tensor(B)
        C = fx.rocdl.make_buffer_tensor(C)

        bA = fx.zipped_divide(A, (block_m, block_k))
        bB = fx.zipped_divide(B, (block_n, block_k))
        bC = fx.zipped_divide(C, (block_m, block_n))

        bA = fx.slice(bA, (None, bid))
        bB = fx.slice(bB, (None, bid))
        bC = fx.slice(bC, (None, bid))

        mma_atom = fx.make_mma_atom(fx.rocdl.MFMA(16, 16, 4, fx.Float32))
        tiled_mma = fx.make_tiled_mma(mma_atom, fx.make_layout((2, 2, 1), (1, 2, 0)))
        thr_mma = tiled_mma.thr_slice(tid)

        copy_atom = fx.make_copy_atom(fx.rocdl.BufferCopy32b(), fx.Float32)
        tiled_copy_A = fx.make_tiled_copy_A(copy_atom, tiled_mma)
        tiled_copy_B = fx.make_tiled_copy_B(copy_atom, tiled_mma)
        tiled_copy_C = fx.make_tiled_copy_C(copy_atom, tiled_mma)

        thr_copy_A = tiled_copy_A.get_slice(tid)
        thr_copy_B = tiled_copy_B.get_slice(tid)
        thr_copy_C = tiled_copy_C.get_slice(tid)

        copy_src_A = thr_copy_A.partition_S(bA)
        copy_src_B = thr_copy_B.partition_S(bB)
        copy_dst_C = thr_copy_C.partition_S(bC)

        frag_A = thr_mma.make_fragment_A(bA)
        frag_B = thr_mma.make_fragment_B(bB)
        frag_C = thr_mma.make_fragment_C(bC)

        copy_frag_A = thr_copy_A.retile(frag_A)
        copy_frag_B = thr_copy_B.retile(frag_B)
        copy_frag_C = thr_copy_C.retile(frag_C)

        fx.copy(copy_atom, copy_src_A, copy_frag_A, pred=None)
        fx.copy(copy_atom, copy_src_B, copy_frag_B, pred=None)

        frag_C.fill(0)
        fx.gemm(mma_atom, frag_C, frag_A, frag_B, frag_C)

        fx.copy(copy_atom, copy_frag_C, copy_dst_C, pred=None)

    @flyc.jit
    def tiledMma(A: fx.Tensor, B: fx.Tensor, C: fx.Tensor, stream: fx.Stream = fx.Stream(None)):
        gemm_kernel(A, B, C).launch(grid=(1, 1, 1), block=(256, 1, 1), stream=stream)

    C = torch.zeros(M, N, dtype=torch.bfloat16, device="cuda")
    # FlyDSL example uses f32 and specific layouts; this is just a probe, may not match shape exactly.
    # We launch for a single tile only since the 03-tiledMma example is designed for M=N=K=blocksize.
    tiledMma(a[:block_m, :block_k], b[:block_n, :block_k], C[:block_m, :block_n], stream=torch.cuda.current_stream())
    torch.cuda.synchronize()
    return None, C  # timing not meaningful for partial probe

def main():
    torch.manual_seed(123)
    a = torch.randn((M, K), device="cuda", dtype=torch.bfloat16)
    b = torch.randn((K, N), device="cuda", dtype=torch.bfloat16)

    results = {}

    ms_eager, c_eager = bench_eager(a, b)
    tflops_eager = (2 * M * N * K) / (ms_eager / 1000.0) / 1e12
    results["eager"] = {"ms": ms_eager, "tflops": tflops_eager}

    ms_compile, c_compile = bench_compile(a, b)
    tflops_compile = (2 * M * N * K) / (ms_compile / 1000.0) / 1e12
    results["compile"] = {"ms": ms_compile, "tflops": tflops_compile}

    # correctness sanity
    ref = torch.mm(a[:64, :].float(), b[:, :64].float()).to(torch.bfloat16)
    max_abs_eager = (c_eager[:64, :64] - ref).abs().max().item()
    max_abs_compile = (c_compile[:64, :64] - ref).abs().max().item()

    results["max_abs_eager"] = max_abs_eager
    results["max_abs_compile"] = max_abs_compile

    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
