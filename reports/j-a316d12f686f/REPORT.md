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
- **Correctness self-check:** after all timing, the script verifies the operation is
  actually correct — bf16/fp16 `matmul` against a float64 reference (relative error
  < 5%), fp8 `_scaled_mm` against a reference computed from the same quantized inputs
  (relative error < 2%). This runs *after* timing so its allocations cannot perturb
  rocBLAS kernel selection for the benchmarked shapes. A PASS is printed at the end
  of every run; a failure raises and invalidates every number above it.
- rocBLAS prints thousands of "Latency not found … (really slow)" heuristic warnings
  while searching fp8 tile configs; these are autotuning noise that do not affect the
  executed kernel, so the script silences C-level stderr (fd 2) only during the fp8
  calls (restored on exit, so Python tracebacks still surface).

## Results

### A) Repo gfx950 A16W16 / preshuffle GEMM shapes (bf16/fp16, `torch.matmul`)

| dtype | M | N | K | med ms | min ms | max ms | std ms | p90 ms | p99 ms | TF/s med | TF/s best |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| fp16 | 2048 | 2048 | 2048 | 0.0280 | 0.0268 | 0.0446 | 0.0020 | 0.0292 | 0.0339 | 612.7 | 640.1 |
| bf16 | 32 | 384 | 7168 | 0.0153 | 0.0112 | 0.1122 | 0.0098 | 0.0183 | 0.0278 | 11.5 | 15.8 |
| bf16 | 8192 | 8192 | 8192 | 0.7798 | 0.7729 | 0.7893 | 0.0029 | 0.7824 | 0.7873 | 1410.0 | 1422.6 |
| bf16 | 5120 | 5120 | 8320 | 0.3719 | 0.3676 | 0.3879 | 0.0031 | 0.3750 | 0.3840 | 1172.8 | 1186.8 |

### B) Square compute-bound sweep (bf16/fp16, `torch.matmul`)

| dtype | M | N | K | med ms | min ms | max ms | std ms | p90 ms | p99 ms | TF/s med | TF/s best |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| bf16 | 1024 | 1024 | 1024 | 0.0135 | 0.0106 | 0.0366 | 0.0030 | 0.0148 | 0.0192 | 158.8 | 203.4 |
| bf16 | 2048 | 2048 | 2048 | 0.0252 | 0.0249 | 0.0348 | 0.0012 | 0.0256 | 0.0305 | 682.8 | 690.5 |
| bf16 | 4096 | 4096 | 4096 | 0.1046 | 0.1028 | 0.1130 | 0.0012 | 0.1054 | 0.1094 | 1313.4 | 1336.9 |
| bf16 | 8192 | 8192 | 8192 | 0.7766 | 0.7678 | 0.7841 | 0.0028 | 0.7799 | 0.7834 | 1415.8 | 1432.0 |
| fp16 | 4096 | 4096 | 4096 | 0.1172 | 0.1160 | 0.1255 | 0.0012 | 0.1181 | 0.1216 | 1173.1 | 1184.4 |
| fp16 | 8192 | 8192 | 8192 | 0.8762 | 0.8703 | 0.8848 | 0.0027 | 0.8802 | 0.8822 | 1254.9 | 1263.4 |

### C) Repo gfx950 FP8 GEMM shapes (fp8 e4m3, `torch._scaled_mm` / `cdna4.mfma_scale`)

| dtype | M | N | K | med ms | min ms | max ms | std ms | p90 ms | p99 ms | TF/s med | TF/s best |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| fp8 | 8192 | 8192 | 8192 | 0.3542 | 0.3493 | 0.3885 | 0.0044 | 0.3566 | 0.3685 | 3104.0 | 3147.9 |
| fp8 | 5120 | 5120 | 8320 | 0.2052 | 0.1948 | 0.2549 | 0.0106 | 0.2208 | 0.2303 | 2126.0 | 2239.2 |
| fp8 | 9728 | 8192 | 8320 | 0.4351 | 0.4300 | 0.4545 | 0.0030 | 0.4377 | 0.4439 | 3047.7 | 3083.6 |
| fp8 | 512 | 2112 | 7168 | 0.0201 | 0.0199 | 0.0356 | 0.0018 | 0.0205 | 0.0252 | 770.5 | 779.8 |
| fp8 | 256 | 2112 | 7168 | 0.0166 | 0.0164 | 0.0576 | 0.0044 | 0.0174 | 0.0319 | 466.9 | 473.8 |

**Headline number:** bf16 8192³ GEMM ≈ **1410 TFLOPS** (median, ±0.37% std); fp8
8192³ GEMM ≈ **3104 TFLOPS** (median). The fp8/bf16 throughput ratio is ~2.20×,
consistent with gfx950 fp8 MFMA having ~2× the bf16 MFMA rate. The large compute-bound
shapes are extremely tight (relative std ≈ 0.3–0.4%); small/skinny shapes are
launch/memory-bound and noisy (e.g. bf16 32×384×7168 swings 0.011–0.112 ms).

## How to reproduce

Exact command (run from the repo root with a ROCm build of torch on PATH):

```sh
python reports/j-a316d12f686f/bench_flydsl_gemm.py --warmup 30 --repeats 100 \
    --json reports/j-a316d12f686f/results.json
```

A quick variant (≈10 s) for a sanity check: `--warmup 5 --repeats 20`.
Raw console output is in `run_output.txt`; full per-sample data in `results.json`.
The correctness self-check prints three `PASS` lines at the end of every run.

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
  not guess it. (For orientation only, the bf16 best-case ~1432 TF and fp8 ~3148 TF
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
