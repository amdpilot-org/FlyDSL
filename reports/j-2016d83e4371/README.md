# Bounded small-token MXFP4 MoE latency report

## Scope and upstream context

This report addresses the small-token part of ROCm/FlyDSL issue 708. It is not a
generic `fx.gemm` fragment test, a full production token sweep, or a large-shape
MFU study.

Read-only context review:

- ROCm/FlyDSL issue 708 asks for MXFP4 MoE tuning on gfx950, including
  small-token latency and separate GEMM1/GEMM2 treatment.
- ROCm/FlyDSL pull request 736 was read as related context. It is closed and
  unmerged, describes tuning infrastructure only, and contains no production
  kernel-logic change or performance win. This work therefore does not duplicate
  it. Its head commit inspected was `1e0ccf0e7f979d5530211b8cacfb054fe04fb2dc`.
- The measured mirror `main` commit is
  `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.

## Environment

- Image: `amdpilotv2/open-job:gbt350-20260909`
- Operator-provided local image ID:
  `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`
- Source: `/job/flydsl`
- Python: `/opt/venv/bin/python`
- FlyDSL Python package: `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`
- Torch: `/opt/venv/lib/python3.12/site-packages/torch/__init__.py`
- Triton: `/opt/venv/lib/python3.12/site-packages/triton/__init__.py`
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`
- ROCm arch: `gfx950`
- GPU: one visible AMD Instinct MI350X, 256 CUs, 270,566,162,432 bytes VRAM
- Job-private caches: `/tmp/flydsl-cache-j-2016d83e4371/{runtime,triton,aiter-jit}`

## Method

Synthetic shape: `model_dim=1024`, `inter_dim=256`, `experts=8`, `topk=2`,
seed `20260910`. Tokens were bounded to `1, 8, 32, 128`.

Four supported latency-oriented configurations were measured:

1. `bm16_inline_atomic`: GEMM1 BM16 inline quant, GEMM2 BM16 atomic
2. `bm32_prequant_atomic`: GEMM1 BM32 prequant, GEMM2 BM32 atomic
3. `bm64_prequant_atomic`: GEMM1 BM64 prequant, GEMM2 BM64 atomic
4. `bm128_prequant_nonatomic`: GEMM1 BM128 prequant, GEMM2 BM128 nonatomic

The existing per-1x32 E8M0 scale shuffle and FP4 weight shuffle were preserved.
Host enqueue latency used `perf_counter_ns` around the Python host call. Device
duration used CUDA events around each synchronized launch. Each case used 10
warmup launches and 50 timed launches. SiLU and FP4 re-quantization are fused
into GEMM1, so activation is reported as a zero-latency fused stage rather than
inventing a separate launch.

Validation reconstructed the BM-dependent GEMM1 output-scale layout, dequantized
the actual stage-1 FP4 output, and compared it with an independently dequantized
and re-quantized SiLU reference. Stage 2 was validated by dequantizing the actual
stage-1 intermediate and MXFP4 W2, then performing an independent weighted
down-projection. The existing numerical gate was unchanged:
`rtol=2e-3`, `atol=2e-3`, `logits_diff_threshold=2e-3`, with the existing
5-percent allclose early-pass rule.

For the inline-quant reference, the input was first rounded to BF16 because that
is what the inline GEMM1 path consumes. The harness over-allocates only the
stage-1 scale output buffer so the BM16 layout has sufficient writable storage;
it does not change the scale layout or kernel contract.

## Results

All times below are microseconds. `host` is enqueue latency and `device` is
event-measured duration. Each value is `median/p95`.

| tokens | config | GEMM1 host | GEMM1 device | GEMM2 host | GEMM2 device | gates |
|---:|---|---:|---:|---:|---:|---|
| 1 | bm16_inline_atomic | 10.11/11.00 | 12.64/16.08 | 10.61/11.58 | 13.32/16.06 | pass/pass |
| 1 | bm32_prequant_atomic | 10.48/11.98 | 13.68/19.58 | 10.53/11.52 | 13.20/17.50 | pass/pass |
| 1 | bm64_prequant_atomic | 10.30/11.85 | 15.20/19.84 | 10.54/11.25 | 13.16/16.71 | pass/pass |
| 1 | bm128_prequant_nonatomic | 10.28/10.88 | 18.14/22.91 | 10.62/11.03 | 15.26/17.37 | pass/pass |
| 8 | bm16_inline_atomic | 10.25/11.13 | 13.88/15.62 | 10.55/11.05 | 13.16/15.84 | pass/pass |
| 8 | bm32_prequant_atomic | 10.45/12.33 | 14.56/28.21 | 10.60/11.33 | 13.34/17.59 | pass/pass |
| 8 | bm64_prequant_atomic | 10.33/11.47 | 16.20/27.10 | 10.54/11.13 | 13.12/17.58 | pass/pass |
| 8 | bm128_prequant_nonatomic | 10.15/10.93 | 19.12/24.74 | 10.60/11.11 | 15.54/17.45 | pass/pass |
| 32 | bm16_inline_atomic | 10.26/12.90 | 13.80/19.77 | 10.51/10.92 | 13.20/14.78 | pass/pass |
| 32 | bm32_prequant_atomic | 10.53/13.13 | 14.62/21.25 | 10.53/11.00 | 13.12/15.27 | pass/pass |
| 32 | bm64_prequant_atomic | 10.29/12.73 | 16.16/18.38 | 10.54/11.09 | 13.16/15.06 | pass/pass |
| 32 | bm128_prequant_nonatomic | 10.14/11.49 | 19.20/22.66 | 10.56/10.90 | 15.42/17.72 | pass/pass |
| 128 | bm16_inline_atomic | 10.13/13.70 | 14.68/26.55 | 10.56/14.44 | 13.30/17.65 | pass/pass |
| 128 | bm32_prequant_atomic | 10.23/31.79 | 14.18/40.02 | 10.48/10.95 | 13.52/17.00 | pass/pass |
| 128 | bm64_prequant_atomic | 10.29/11.88 | 16.16/20.86 | 10.53/12.09 | 13.54/16.78 | pass/pass |
| 128 | bm128_prequant_nonatomic | 10.09/11.30 | 19.08/20.80 | 10.48/11.18 | 15.40/19.25 | pass/pass |

Validation maxima across all 16 cases:

- Stage 1: all gates passed; maximum exceed fraction `0.00732421875`,
  logits diff `0.0008359304`, max absolute error `1.0`, RMSE `0.04384755`.
- Stage 2: all gates passed; maximum exceed fraction `0.00006103515625`,
  logits diff `0.00000348484`, max absolute error `0.00363326`, RMSE `0.000372375`.

By median device duration, BM16 inline was fastest at tokens 1, 8, and 32.
At token 128, BM32 was nominally fastest by about `0.12 us` over BM16, which is
within shared-hardware noise. Host enqueue was approximately `10-11 us` for
both stages and is a substantial part of total small-token stage latency.

## Shared-hardware timing limits

- Only one assigned MI350X was visible, but the host node is shared; no exclusive
  GPU lock was acquired.
- Clocks were not pinned. `rocm-smi` reported a low-power warning before the run.
- P95 shows substantial interference, for example BM32/token128 host enqueue
  `31.79 us` versus a `10.23 us` median and device `40.02 us` versus a
  `14.18 us` median.
- CUDA event timing includes event/launch overhead and synchronized per-sample
  measurement; it is not a profiler-isolated kernel duration.
- Medians from 50 samples are more robust than individual samples, but the
  sub-microsecond differences between BM16 and BM32 at token 128 should not be
  treated as a stable ranking.

## Reproduction

```bash
cd /job/flydsl
export PYTHONPATH=/job/flydsl
export FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-2016d83e4371/runtime
export TRITON_CACHE_DIR=/tmp/flydsl-cache-j-2016d83e4371/triton
export AITER_JIT_DIR=/tmp/flydsl-cache-j-2016d83e4371/aiter-jit
/opt/venv/bin/python reports/j-2016d83e4371/benchmark_small_token_mxfp4.py \
  --output reports/j-2016d83e4371/results.json
```

Raw artifacts:

- `results.json`: complete environment, configuration, validation, and per-sample
  timing data.
- `benchmark.log`: final run summary.
- `gpu_identity.txt`: read-only `rocm-smi` product, memory, driver, and process
  output.

## Left undone

- No production kernel or dispatch logic was changed.
- No full token sweep, large-shape MFU measurement, or model-weight download
  was performed.
- No AITER end-to-end workload was run; this report measures the FlyDSL stages
  directly.
- The BM16 stage-1 scale-output allocation hazard is documented here but not
  fixed in production code.
