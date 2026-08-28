#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors
#
# Benchmark: tiled GEMM via MFMA atoms on AMD Instinct (gfx950 / MI355X).
#
# Why this operation: FlyDSL is a layout IR + Python DSL whose defining operation is
# the *tiled matrix multiply-accumulate (GEMM) using MFMA hardware atoms* (see the
# repo's core examples `examples/03-tiledMma.py` and `examples/04-preshuffle_gemm.py`,
# the `fly.mma` / `FlyROCDL_MmaOpCDNA3_MFMA` dialect ops, and the production
# `kernels/gemm/gemm_a16w16_gfx950.py` which targets this exact GPU). The whole
# layout algebra exists to map tiles of a GEMM onto MFMA atoms and thread layouts.
#
# Substitution (stated plainly): the repository's own code cannot be imported
# without a from-source build of MLIR/LLVM (~30 min), which this task forbids.
# We therefore reimplement the *operation* — an MFMA-backed dense GEMM — faithfully
# in PyTorch via `torch.matmul`. On ROCm this dispatches to rocBLAS, which itself
# lowers to the gfx950 MFMA instructions that FlyDSL's generated kernels target.
# This measures the same MFMA-based GEMM *operation* on the same hardware, but NOT
# FlyDSL's layout-IR codegen/tiling path itself; rocBLAS is the codegen path here.
#
# Output: one row per (dtype, shape) with TFLOPS and the full run-to-run spread.

import argparse
import contextlib
import json
import os
import statistics
import subprocess
import sys
import time

import torch

# FP8 GEMM shapes from scripts/run_benchmark.sh (gfx950 preshuffle GEMM_SHAPES
# + FP8_GEMM_8WAVE_ROWSCALE_SHAPES). The repo's dominant gfx950 GEMM shapes are FP8;
# these exercise the CDNA4 mfma_scale (scaled MMA) path. M=16 GEMV-like shapes are
# excluded (pure launch/memory noise, not MFMA throughput).
FP8_SHAPES = [
    ("fp8", 8192, 8192, 8192),
    ("fp8", 5120, 5120, 8320),
    ("fp8", 9728, 8192, 8320),
    ("fp8", 512, 2112, 7168),
    ("fp8", 256, 2112, 7168),
]

@contextlib.contextmanager
def _silence_c_stderr():
    """Redirect the C-level stderr (fd 2) to /dev/null.

    rocBLAS floods stderr with "Latency not found ... (really slow)" heuristic
    warnings while searching FP8 (BFloat8Float8_fnuz) tile configs. They are pure
    autotuning noise and do not affect the executed kernel; hiding them keeps the
    results readable. Python tracebacks still print because fd 2 is restored on
    exit (including on exception).
    """
    saved = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, 2)
        yield
    finally:
        os.dup2(saved, 2)
        os.close(saved)
        os.close(devnull)


# ---------------------------------------------------------------------------
# Shapes.
# A) The repo's own gfx950 A16W16 benchmark shapes (scripts/run_benchmark.sh,
#    HGEMM_SHAPES_GFX950), so the measurement is directly comparable to what
#    FlyDSL cares about for this GPU.
# B) A square sweep to characterize compute-bound scaling and the spread.
# ---------------------------------------------------------------------------
REPO_SHAPES = [
    # (dtype, M, N, K)  -- mirrors HGEMM_SHAPES_GFX950 (a16w16, gfx950)
    ("fp16", 2048, 2048, 2048),
    ("bf16", 32, 384, 7168),
    ("bf16", 8192, 8192, 8192),
    # preshuffle bf16 GEMM shape also benchmarked for gfx950
    ("bf16", 5120, 5120, 8320),
]
SQUARE_SWEEP = [
    ("bf16", 1024, 1024, 1024),
    ("bf16", 2048, 2048, 2048),
    ("bf16", 4096, 4096, 4096),
    ("bf16", 8192, 8192, 8192),
    ("fp16", 4096, 4096, 4096),
    ("fp16", 8192, 8192, 8192),
]

DTYPE_MAP = {
    "fp16": torch.float16,
    "bf16": torch.bfloat16,
    "fp8": torch.float8_e4m3fn,  # E4M3, matches kernels/gemm/fp8_gemm_*.py (CDNA4 mfma_scale)
}


def sh(cmd):
    """Run a shell command, return stripped stdout or '' on failure."""
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True)
        return out.strip()
    except Exception:
        return ""


def collect_env():
    env = {}
    # torch / HIP (read from the running process, not assumed)
    env["torch_version"] = torch.__version__
    env["hip_version_torch"] = getattr(torch.version, "hip", None) or "unknown"
    env["cuda_available"] = torch.cuda.is_available()
    if torch.cuda.is_available():
        p = torch.cuda.get_device_properties(0)
        env["gpu_name_torch"] = p.name
        env["gcn_arch_name"] = getattr(p, "gcnArchName", "unknown")
        env["device_capability"] = f"{p.major}.{p.minor}"
        env["sm_count"] = getattr(p, "multi_processor_count", None)
    # HIP toolchain
    env["hipcc_version"] = sh("hipcc --version 2>/dev/null | grep -i 'HIP version' || true")
    # rocm-smi product
    env["rocm_smi_product"] = sh("rocm-smi --showproductname 2>/dev/null | grep -i 'Card Series' | head -1")
    env["gpu_gfx_version_smi"] = sh("rocm-smi --showproductname 2>/dev/null | grep -i 'GFX Version' | head -1")
    # clocks / power at measurement time
    env["amd_smi_top"] = sh("amd-smi monitor 2>/dev/null | head -2")
    # CU count: rocminfo lists one GPU agent for the whole MI355X chip with
    # Compute Unit = 256 (CPU agents are filtered out). torch's
    # multi_processor_count agrees (256). We parse rocminfo in Python to avoid
    # matching the host CPU's "Compute Unit" lines.
    cu_gpu = "<n/a>"
    try:
        import re
        txt = subprocess.check_output(["rocminfo"], stderr=subprocess.STDOUT, text=True)
        agents = re.findall(r"Agent \d+.*?(?=Agent \d+|\Z)", txt, re.S)
        for ag in agents:
            if "Device Type:" in ag and "GPU" in ag.split("Device Type:")[1].splitlines()[0]:
                m = re.search(r"Compute Unit:\s*(\d+)", ag)
                if m:
                    cu_gpu = m.group(1)
    except Exception:
        pass
    env["compute_units_gpu_rocminfo"] = cu_gpu
    # Machine-readable memory bandwidth / power ceiling from amd-smi static.
    env["max_memory_bandwidth_amdsmi"] = sh("amd-smi static 2>/dev/null | grep -i 'MAX_BANDWIDTH' | head -1")
    env["max_power_limit_amdsmi"] = sh("amd-smi static 2>/dev/null | grep -i 'MAX_POWER_LIMIT' | head -1")
    return env


def fmt_tflops(dtype, m, n, k, sec):
    flops = 2.0 * m * n * k
    return flops / sec / 1e12


def benchmark_scaled_mm(dtype, m, n, k, warmup, repeats):
    """FP8 GEMM via torch._scaled_mm -> rocBLAS scaled-MMA (CDNA4 mfma_scale).

    Layout: A is row-major (M,K); B is stored (N,K) so B.t() is column-major
    (K,N), which is the layout cuBLASLt/rocBLAS requires for scaled mm.
    Unit per-tensor scales are used: this measures MFMA throughput, not numerics.
    """
    dt = DTYPE_MAP[dtype]
    dev = "cuda"
    # fp8 has no randn kernel; build in fp32 then cast.
    a = torch.randn(m, k, device=dev).to(dt)
    b = torch.randn(n, k, device=dev).to(dt)  # -> b.t() is (K,N) col-major
    one = torch.ones(1, device=dev, dtype=torch.float32)
    out = torch.empty(m, n, dtype=torch.bfloat16, device=dev)

    def run():
        return torch._scaled_mm(a, b.t(), scale_a=one, scale_b=one, out_dtype=torch.bfloat16, out=out)

    with _silence_c_stderr():
        for _ in range(warmup):
            run()
        torch.cuda.synchronize()

        starts = [torch.cuda.Event(enable_timing=True) for _ in range(repeats)]
        ends = [torch.cuda.Event(enable_timing=True) for _ in range(repeats)]
        for i in range(repeats):
            starts[i].record()
            run()
            ends[i].record()
        torch.cuda.synchronize()

    times_ms = [s.elapsed_time(e) for s, e in zip(starts, ends)]
    arr = times_ms
    srt = sorted(arr)

    def pct(p):
        i = max(0, min(len(srt) - 1, int(round((p / 100.0) * (len(srt) - 1)))))
        return srt[i]

    return {
        "dtype": dtype, "M": m, "N": n, "K": k, "repeats": repeats,
        "time_ms_median": statistics.median(arr),
        "time_ms_mean": statistics.mean(arr),
        "time_ms_min": min(arr), "time_ms_max": max(arr),
        "time_ms_p90": pct(90), "time_ms_p99": pct(99),
        "time_ms_std": statistics.pstdev(arr) if len(arr) > 1 else 0.0,
        "tflops_median": fmt_tflops(dtype, m, n, k, statistics.median(arr) / 1e3),
        "tflops_best": fmt_tflops(dtype, m, n, k, min(arr) / 1e3),
        "samples_ms": arr,
    }


def benchmark_matmul(dtype, m, n, k, warmup, repeats):
    dt = DTYPE_MAP[dtype]
    dev = "cuda"
    # Column-major-ish via contiguous; rocBLAS picks the kernel. We use the
    # natural (M,K)x(K,N)->(M,N) layout that the FlyDSL a16w16 kernel assumes.
    a = torch.randn(m, k, dtype=dt, device=dev)
    b = torch.randn(k, n, dtype=dt, device=dev)
    c = torch.empty(m, n, dtype=dt, device=dev)

    # Warmup (let rocBLAS pick + cache the kernel; fill caches).
    for _ in range(warmup):
        torch.matmul(a, b, out=c)
    torch.cuda.synchronize()

    # Per-iteration timing with CUDA events -> real GPU time, real spread.
    starts = [torch.cuda.Event(enable_timing=True) for _ in range(repeats)]
    ends = [torch.cuda.Event(enable_timing=True) for _ in range(repeats)]
    for i in range(repeats):
        starts[i].record()
        torch.matmul(a, b, out=c)
        ends[i].record()
    torch.cuda.synchronize()

    times_ms = [s.elapsed_time(e) for s, e in zip(starts, ends)]  # ms per iter

    arr = times_ms
    sec_median = statistics.median(arr) / 1e3
    sec_min = min(arr) / 1e3
    sec_mean = statistics.mean(arr) / 1e3
    sec_max = max(arr) / 1e3
    stdev = statistics.pstdev(arr) if len(arr) > 1 else 0.0
    srt = sorted(arr)
    def pct(p):
        i = max(0, min(len(srt) - 1, int(round((p / 100.0) * (len(srt) - 1)))))
        return srt[i]
    return {
        "dtype": dtype, "M": m, "N": n, "K": k,
        "repeats": repeats,
        "time_ms_median": statistics.median(arr),
        "time_ms_mean": sec_mean * 1e3,
        "time_ms_min": min(arr),
        "time_ms_max": max(arr),
        "time_ms_p90": pct(90),
        "time_ms_p99": pct(99),
        "time_ms_std": stdev,
        "tflops_median": fmt_tflops(dtype, m, n, k, sec_median),
        "tflops_best": fmt_tflops(dtype, m, n, k, sec_min),  # from min time
        "samples_ms": arr,
    }


def self_check():
    """Correctness sanity: the operation must compute the right thing, not just fast.

    bf16/fp16: compare torch.matmul against a float64 reference, within dtype
        tolerance. fp8: with unit per-tensor scales the scaled_mm equals the
        plain matmul of the (dequantized-to-fp32) inputs; check the output is
        finite and close to a bf16 matmul of the same data.
    Runs once after all timing; a failure invalidates every number above it.
    """
    dev = "cuda"
    M = N = K = 512
    ref64 = torch.randn(M, K, dtype=torch.float64, device=dev)
    b64 = torch.randn(K, N, dtype=torch.float64, device=dev)
    expect = ref64 @ b64

    out_scale = expect.abs().max().item() + 1e-6
    for name, dt, tol in [("bf16", torch.bfloat16, 0.05), ("fp16", torch.float16, 0.05)]:
        a = ref64.to(dt); b = b64.to(dt)
        got = torch.matmul(a, b).to(torch.float64)
        rel_err = (got - expect).abs().max().item() / out_scale
        ok = rel_err < tol
        print(f"[self-check] {name} matmul rel_err={rel_err:.4e} (tol={tol:.0e}) -> {'PASS' if ok else 'FAIL'}")
        if not ok:
            raise RuntimeError(f"{name} matmul correctness check failed (rel_err={rel_err})")

    # fp8 e4m3 via _scaled_mm: with unit per-tensor scales the scaled_mm equals
    # the plain matmul of the (dequantized-to-fp32) inputs, accumulated to bf16.
    # Compare _scaled_mm against a reference computed from the SAME quantized
    # inputs (dequant->fp32 matmul), NOT against the unquantized fp64 result --
    # that isolates the scaled-MMA path's correctness from quantization loss.
    a32 = ref64.to(torch.float32); b32 = b64.to(torch.float32)
    a8 = a32.to(torch.float8_e4m3fn)
    b8 = b32.to(torch.float8_e4m3fn)  # (N,K); b8.t() is (K,N) col-major
    one = torch.ones(1, device=dev, dtype=torch.float32)
    got = torch._scaled_mm(a8, b8.t(), scale_a=one, scale_b=one, out_dtype=torch.bfloat16)
    ref_quant = (a8.to(torch.float32) @ b8.to(torch.float32).t()).to(torch.bfloat16)
    fin = torch.isfinite(got).all().item()
    scale = ref_quant.abs().max().item() + 1e-6
    rel_err = (got.to(torch.float32) - ref_quant.to(torch.float32)).abs().max().item() / scale
    ok = fin and rel_err < 0.02
    print(f"[self-check] fp8 _scaled_mm finite={fin} rel_err_vs_quantized_ref={rel_err:.4e} (tol=2e-2) -> {'PASS' if ok else 'FAIL'}")
    if not ok:
        raise RuntimeError("fp8 scaled_mm correctness check failed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--warmup", type=int, default=20)
    ap.add_argument("--repeats", type=int, default=100)
    ap.add_argument("--json", type=str, default="")
    args = ap.parse_args()

    print("=" * 78)
    print("FlyDSL operation benchmark: tiled GEMM via MFMA atoms (rocBLAS path)")
    print("=" * 78)

    env = collect_env()
    print("\n## Environment (read from the machine)")
    for k in [
        "gpu_name_torch", "gcn_arch_name", "device_capability", "sm_count",
        "torch_version", "hip_version_torch", "hipcc_version",
        "rocm_smi_product", "gpu_gfx_version_smi",
        "compute_units_gpu_rocminfo", "max_memory_bandwidth_amdsmi",
        "max_power_limit_amdsmi", "amd_smi_top",
    ]:
        v = env.get(k)
        if v is None:
            v = "<n/a>"
        print(f"  {k:28s}: {v}")

    if not torch.cuda.is_available():
        print("\nNo CUDA/HIP device available. Aborting.", file=sys.stderr)
        sys.exit(2)

    print(f"\n## Method: warmup={args.warmup} iters, repeats={args.repeats} iters, "
          f"per-iter CUDA-event timing. torch.matmul -> rocBLAS -> MFMA.")
    print(f"   dtype: fp16=torch.float16, bf16=torch.bfloat16 "
          f"(match kernels/gemm/gemm_a16w16_gfx950.py A16W16 dtypes)\n")

    results = []
    sections = [
        ("A) Repo gfx950 A16W16 / preshuffle GEMM shapes (bf16/fp16 via matmul)", REPO_SHAPES, "matmul"),
        ("B) Square compute-bound sweep (bf16/fp16 via matmul)", SQUARE_SWEEP, "matmul"),
        ("C) Repo gfx950 FP8 GEMM shapes (fp8 e4m3 via _scaled_mm / mfma_scale)", FP8_SHAPES, "scaled_mm"),
    ]
    for title, shapes, mode in sections:
        print(f"--- {title} ---")
        hdr = f"{'dtype':5s} {'M':>6s} {'N':>6s} {'K':>6s} | {'med ms':>8s} {'min ms':>8s} {'max ms':>8s} {'std ms':>7s} {'p90 ms':>7s} {'p99 ms':>7s} | {'TF/s med':>9s} {'TF/s best':>9s}"
        print(hdr)
        print("-" * len(hdr))
        for dtype, m, n, k in shapes:
            r = (benchmark_matmul if mode == "matmul" else benchmark_scaled_mm)(
                dtype, m, n, k, args.warmup, args.repeats)
            results.append(r)
            print(f"{r['dtype']:5s} {r['M']:6d} {r['N']:6d} {r['K']:6d} | "
                  f"{r['time_ms_median']:8.4f} {r['time_ms_min']:8.4f} {r['time_ms_max']:8.4f} "
                  f"{r['time_ms_std']:7.4f} {r['time_ms_p90']:7.4f} {r['time_ms_p99']:7.4f} | "
                  f"{r['tflops_median']:9.1f} {r['tflops_best']:9.1f}")
        print()

    if args.json:
        out = {"environment": env, "config": {"warmup": args.warmup, "repeats": args.repeats}, "results": results}
        with open(args.json, "w") as f:
            json.dump(out, f, indent=2)
        print(f"Wrote JSON results -> {args.json}")

    # Correctness self-check runs AFTER all timing so its allocations cannot
    # perturb rocBLAS kernel selection for the benchmarked shapes.
    print()
    self_check()


if __name__ == "__main__":
    main()
