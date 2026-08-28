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
- bf16/fp16 use `torch.matmul(..., out=)`; fp8 e4m3 uses `torch._scaled_mm(..., out=)`
  with unit per-tensor scales (measures MFMA throughput, not numerics) and bf16 output.
  All three paths use a pre-allocated output buffer so timing measures pure kernel
  execution, not allocation.
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
| fp16 | 2048 | 2048 | 2048 | 0.0273 | 0.0266 | 0.0417 | 0.0016 | 0.0282 | 0.0328 | 629.8 | 644.9 |
| bf16 | 32 | 384 | 7168 | 0.0155 | 0.0115 | 0.0980 | 0.0084 | 0.0184 | 0.0247 | 11.4 | 15.3 |
| bf16 | 8192 | 8192 | 8192 | 0.7786 | 0.7727 | 0.7849 | 0.0025 | 0.7809 | 0.7840 | 1412.2 | 1422.9 |
| bf16 | 5120 | 5120 | 8320 | 0.3721 | 0.3683 | 0.3779 | 0.0016 | 0.3735 | 0.3777 | 1172.2 | 1184.3 |

### B) Square compute-bound sweep (bf16/fp16, `torch.matmul`)

| dtype | M | N | K | med ms | min ms | max ms | std ms | p90 ms | p99 ms | TF/s med | TF/s best |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| bf16 | 1024 | 1024 | 1024 | 0.0118 | 0.0108 | 0.0322 | 0.0024 | 0.0141 | 0.0188 | 182.3 | 199.6 |
| bf16 | 2048 | 2048 | 2048 | 0.0251 | 0.0248 | 0.0332 | 0.0010 | 0.0259 | 0.0298 | 683.9 | 691.6 |
| bf16 | 4096 | 4096 | 4096 | 0.1046 | 0.1029 | 0.1127 | 0.0013 | 0.1058 | 0.1098 | 1313.9 | 1335.9 |
| bf16 | 8192 | 8192 | 8192 | 0.7766 | 0.7702 | 0.7878 | 0.0027 | 0.7803 | 0.7844 | 1415.8 | 1427.5 |
| fp16 | 4096 | 4096 | 4096 | 0.1173 | 0.1168 | 0.1248 | 0.0010 | 0.1182 | 0.1227 | 1171.5 | 1176.7 |
| fp16 | 8192 | 8192 | 8192 | 0.8772 | 0.8700 | 0.8879 | 0.0029 | 0.8813 | 0.8866 | 1253.4 | 1263.8 |

### C) Repo gfx950 FP8 GEMM shapes (fp8 e4m3, `torch._scaled_mm` / `cdna4.mfma_scale`)

| dtype | M | N | K | med ms | min ms | max ms | std ms | p90 ms | p99 ms | TF/s med | TF/s best |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| fp8 | 8192 | 8192 | 8192 | 0.3548 | 0.3514 | 0.3802 | 0.0032 | 0.3583 | 0.3618 | 3098.8 | 3128.6 |
| fp8 | 5120 | 5120 | 8320 | 0.2062 | 0.1935 | 0.2389 | 0.0078 | 0.2160 | 0.2269 | 2115.0 | 2254.5 |
| fp8 | 9728 | 8192 | 8320 | 0.4353 | 0.4298 | 0.4496 | 0.0026 | 0.4377 | 0.4394 | 3046.6 | 3085.3 |
| fp8 | 512 | 2112 | 7168 | 0.0201 | 0.0199 | 0.0309 | 0.0012 | 0.0206 | 0.0248 | 772.0 | 779.8 |
| fp8 | 256 | 2112 | 7168 | 0.0166 | 0.0163 | 0.0493 | 0.0035 | 0.0168 | 0.0290 | 468.1 | 476.1 |


**Headline number:** bf16 8192³ GEMM ≈ **1412 TFLOPS** (median, ±0.32% std); fp8
8192³ GEMM ≈ **3099 TFLOPS** (median). The fp8/bf16 throughput ratio is ~2.19×,
consistent with gfx950 fp8 MFMA having ~2× the bf16 MFMA rate. The large compute-bound
shapes are extremely tight (relative std ≈ 0.3–0.4%); small/skinny shapes are
launch/memory-bound and noisy (e.g. bf16 32×384×7168 swings 0.012–0.098 ms).

### Cross-run stability (3 independent runs, warmup=20, repeats=50)

| dtype | M | N | K | run1 TF/s | run2 TF/s | run3 TF/s | mean | std | rel std % |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| bf16 | 8192 | 8192 | 8192 | 1416.6 | 1414.9 | 1419.8 | 1417.1 | 2.0 | 0.14 |
| bf16 | 4096 | 4096 | 4096 | 1318.2 | 1313.2 | 1314.4 | 1315.3 | 2.1 | 0.16 |
| fp16 | 4096 | 4096 | 4096 | 1170.7 | 1170.7 | 1171.9 | 1171.1 | 0.6 | 0.05 |
| fp8 | 8192 | 8192 | 8192 | 3075.5 | 3098.1 | 3093.5 | 3089.0 | 9.7 | 0.32 |
| fp8 | 9728 | 8192 | 8320 | 3039.7 | 3041.0 | 3034.7 | 3038.5 | 2.7 | 0.09 |

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
  not guess it. (For orientation only, the bf16 best-case ~1423 TF and fp8 ~3129 TF
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
