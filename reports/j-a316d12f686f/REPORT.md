# FlyDSL operation benchmark — tiled GEMM via MFMA atoms on AMD Instinct MI355X

A from-scratch, self-contained measurement of the one operation FlyDSL is built
around — a **tiled matrix multiply-accumulate (GEMM) using MFMA hardware atoms** —
run on the GPU in this environment. The script, raw run output, and JSON are
shipped alongside this report in the same directory.

## The operation (and why it is representative)

FlyDSL is a *layout IR* + Python DSL whose defining operation is the **tiled GEMM
mapped onto MFMA atoms**. The whole layout algebra (`!fly.layout`,
`partition`/`divide`/`compose`, thread-value layouts) exists to express how tiles
of a GEMM land on the MFMA units and on threads. Evidence from the repo itself:

- Core examples: `examples/03-tiledMma.py` (tiled GEMM with `make_mma_atom(MFMA(16,16,4,…))`)
  and `examples/04-preshuffle_gemm.py` (preshuffle GEMM, `M=N=K=4096`, fp16).
- Dialect ops: `FlyROCDL_MmaOpCDNA3_MFMA` (`cdna3.mfma`) and
  `FlyROCDL_MmaOpCDNA4_MFMAScale` (`cdna4.mfma_scale`) in `include/flydsl/.../MmaAtom.td`.
- Production kernels for *this exact GPU*: `kernels/gemm/gemm_a16w16_gfx950.py`
  (bf16/fp16 A16W16 GEMM) and `kernels/gemm/fp8_gemm_{4,8}wave.py` (fp8 scaled MMA),
  with MFMA atoms `MFMA(16,16,16,bf16/f16)`, `MFMA(32,32,16,bf16)`,
  `MFMA(16,16,32,fp8)`.
- The repo's own benchmark harness (`scripts/run_benchmark.sh`) is dominated by GEMM
  shapes (`GEMM_SHAPES`, `HGEMM_SHAPES_GFX950`, `FP8_GEMM_8WAVE_ROWSCALE_SHAPES`).

So "tiled GEMM via MFMA" is the operation; the shapes below are taken verbatim from
that harness so the numbers are directly comparable to what FlyDSL tracks.

## Substitution (stated plainly)

The repository's own code **cannot be imported without a from-source build** of
MLIR/LLVM (`scripts/build_llvm.sh`, ~30 min) plus the C++ dialect build, which this
task forbids ("DO NOT try to build this repository from source"). I therefore
**reimplemented the *operation* — an MFMA-backed dense GEMM — faithfully in
PyTorch**:

- bf16/fp16: `torch.matmul` → rocBLAS → gfx950 MFMA (`cdna3.mfma`) path.
- fp8 e4m3: `torch._scaled_mm` → rocBLAS scaled-MMA → gfx950 `cdna4.mfma_scale` path
  (the same scaled-MMA op the repo's `fp8_gemm_*` kernels use).

This measures the **same MFMA GEMM operation on the same hardware and the same
shapes** FlyDSL targets. It does **not** measure FlyDSL's layout-IR codegen / tiling
path itself — rocBLAS is the codegen path here. That is the central gap; see
"Gaps" below.

## Environment (read from the machine, not assumed)

| Field | Value |
|---|---|
| GPU | AMD Instinct MI355X |
| GFX arch | `gfx950:sramecc+:xnack-` |
| Compute units | 256 (rocminfo GPU agent; torch `multi_processor_count` agrees) |
| Max memory BW (amd-smi) | 7782 GB/s |
| Max power limit (amd-smi) | 1400 W |
| torch | 2.9.1+rocm7.2.0.git7e1940d4 |
| HIP (torch.version.hip) | 7.2.26015-fc0010cf6a |
| hipcc --version | HIP 7.2.26015-fc0010cf6a |
| ROCm SMI product | AMD Instinct MI355X, gfx950 |
| VRAM (idle snapshot) | 0.3 / 288.0 GB |

Host: AMD EPYC 9575F (CPU agents show 128 "Compute Unit" lines in rocminfo — those
are SMT threads, not GPU CUs; the GPU agent is the one with 256).

## Method

- `warmup=30` iterations then `repeats=100` measured iterations, each bracketed by
  its own pair of CUDA timing events (real GPU time, not wall-clock/Python overhead).
- TFLOPS = `2·M·N·K / time`. Reported as **median** (typical) and **best** (from min
  time, least noise). Spread columns: min, max, population std, p90, p99.
- bf16/fp16 use `torch.matmul(..., out=)`; fp8 e4m3 uses `torch._scaled_mm` with
  unit per-tensor scales (measures MFMA throughput, not numerics) and bf16 output.
- rocBLAS prints thousands of "Latency not found … (really slow)" heuristic warnings
  while searching fp8 tile configs; these are autotuning noise that do not affect the
  executed kernel, so the script silences C-level stderr (fd 2) only during the fp8
  calls (restored on exit, so Python tracebacks still surface).

## Results

### A) Repo gfx950 A16W16 / preshuffle GEMM shapes (bf16/fp16, `torch.matmul`)

| dtype | M | N | K | med ms | min ms | max ms | std ms | p90 ms | p99 ms | TF/s med | TF/s best |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| fp16 | 2048 | 2048 | 2048 | 0.0286 | 0.0268 | 0.0397 | 0.0015 | 0.0291 | 0.0335 | 599.9 | 640.1 |
| bf16 | 32 | 384 | 7168 | 0.0160 | 0.0112 | 0.0771 | 0.0063 | 0.0184 | 0.0224 | 11.0 | 15.7 |
| bf16 | 8192 | 8192 | 8192 | 0.7793 | 0.7711 | 0.7942 | 0.0030 | 0.7820 | 0.7850 | 1410.8 | 1425.8 |
| bf16 | 5120 | 5120 | 8320 | 0.3718 | 0.3671 | 0.3830 | 0.0024 | 0.3741 | 0.3819 | 1173.3 | 1188.3 |

### B) Square compute-bound sweep (bf16/fp16, `torch.matmul`)

| dtype | M | N | K | med ms | min ms | max ms | std ms | p90 ms | p99 ms | TF/s med | TF/s best |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| bf16 | 1024 | 1024 | 1024 | 0.0121 | 0.0108 | 0.0418 | 0.0032 | 0.0144 | 0.0206 | 177.2 | 198.8 |
| bf16 | 2048 | 2048 | 2048 | 0.0252 | 0.0250 | 0.0365 | 0.0013 | 0.0260 | 0.0307 | 681.7 | 688.3 |
| bf16 | 4096 | 4096 | 4096 | 0.1047 | 0.1025 | 0.1130 | 0.0016 | 0.1054 | 0.1112 | 1312.4 | 1341.1 |
| bf16 | 8192 | 8192 | 8192 | 0.7767 | 0.7701 | 0.7834 | 0.0025 | 0.7801 | 0.7819 | 1415.6 | 1427.7 |
| fp16 | 4096 | 4096 | 4096 | 0.1173 | 0.1169 | 0.1248 | 0.0011 | 0.1178 | 0.1219 | 1171.5 | 1175.9 |
| fp16 | 8192 | 8192 | 8192 | 0.8771 | 0.8692 | 0.8876 | 0.0031 | 0.8807 | 0.8868 | 1253.6 | 1264.9 |

### C) Repo gfx950 FP8 GEMM shapes (fp8 e4m3, `torch._scaled_mm` / `cdna4.mfma_scale`)

| dtype | M | N | K | med ms | min ms | max ms | std ms | p90 ms | p99 ms | TF/s med | TF/s best |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| fp8 | 8192 | 8192 | 8192 | 0.3521 | 0.3485 | 0.3870 | 0.0047 | 0.3558 | 0.3707 | 3122.5 | 3155.1 |
| fp8 | 5120 | 5120 | 8320 | 0.2050 | 0.1934 | 0.3019 | 0.0139 | 0.2274 | 0.2342 | 2127.4 | 2255.9 |
| fp8 | 9728 | 8192 | 8320 | 0.4358 | 0.4286 | 0.4451 | 0.0026 | 0.4386 | 0.4408 | 3043.1 | 3093.6 |
| fp8 | 512 | 2112 | 7168 | 0.0203 | 0.0202 | 0.0366 | 0.0017 | 0.0205 | 0.0248 | 762.9 | 769.0 |
| fp8 | 256 | 2112 | 7168 | 0.0166 | 0.0164 | 0.0452 | 0.0032 | 0.0173 | 0.0299 | 465.8 | 472.6 |

**Headline number:** bf16 8192³ GEMM ≈ **1411 TFLOPS** (median, ±0.4% std); fp8
8192³ GEMM ≈ **3123 TFLOPS** (median). The fp8/bf16 throughput ratio is ~2.2×,
consistent with gfx950 fp8 MFMA having ~2× the bf16 MFMA rate. The large compute-bound
shapes are extremely tight (relative std ≈ 0.3–0.4%); small/skinny shapes are
launch/memory-bound and noisy (e.g. bf16 32×384×7168 swings 0.011–0.077 ms).

## How to reproduce

Exact command (run from the repo root with a ROCm build of torch on PATH):

```sh
python reports/j-a316d12f686f/bench_flydsl_gemm.py --warmup 30 --repeats 100 \
    --json reports/j-a316d12f686f/results.json
```

A quick variant (≈10 s) for a sanity check: `--warmup 5 --repeats 20`.
Raw console output is in `run_output.txt`; full per-sample data in `results.json`.

## Gaps / what I did not do

- **Did not build FlyDSL.** Per the task constraint, I did not run
  `scripts/build_llvm.sh`/`scripts/build.sh`. Therefore this measures the **MFMA GEMM
  operation** via rocBLAS, **not** FlyDSL's layout-IR-generated kernel, its tiling
  choices, its preshuffle/SwizzleAtom data-movement path, or its autotuner. rocBLAS
  is a strong baseline but a different codegen path — do not read these numbers as
  FlyDSL kernel throughput.
- **No peak/utilization asserted.** I report achieved TFLOPS and the machine-readable
  CU count / BW / power, but I did not compute a theoretical MFMA peak; the per-CU
  MFMA throughput-per-cycle for gfx950 is not trivially machine-readable and I will
  not guess it. (For orientation only, the bf16 best-case ~1428 TF and fp8 ~3155 TF
  are the achievable rocBLAS numbers on this part.)
- **fp8 via `_scaled_mm`, not FlyDSL's preshuffle fp8 kernel.** `torch.matmul` does
  not support fp8 (`addmm` not implemented for `Float8_e4m3fn`), so fp8 uses
  `torch._scaled_mm` (rocBLAS scaled-MMA). Unit per-tensor scales are used, so this
  is a throughput measurement, not a numerics/correctness one. The repo's M=16 fp8
  GEMV-like shapes (`16,40960,5120`, `16,77824,5120`) are excluded as pure
  launch/memory noise rather than MFMA throughput.
- **Single GPU, single run series.** No multi-GPU collectives, no persistence across
  reboots, no thermal soak beyond the warmup. GPU was idle before the run (GFX_CLK
  showed 155 MHz at rest; it ramps under load).
