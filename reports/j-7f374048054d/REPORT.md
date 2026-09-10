# MXFP4 MoE GEMM2 large-token investigation

## Scope and conclusion

This is the GEMM2 large-token throughput investigation for campaign `repo-e2e-20260909`, distinct from the earlier small-token stage-latency work. No production kernel was changed, no compiler was rebuilt, no full sweep was run, and no model weights were downloaded.

The supported installed AITER/FlyDSL A16WFP4 GEMM2 path passed the unchanged numerical gate at 512, 1024, and 2048 tokens. At the 2048-token bottleneck, four existing tile/pipeline candidates all passed the same independent dequantized-reference gate. The persistent `tile_m=64, tile_n=128, tile_k=128` candidate was fastest in this bounded run:

| Candidate | Mean | Median | Stdev | CV | TFLOPS | Correctness |
|---|---:|---:|---:|---:|---:|---|
| `tm32_tn128_tk256_default` | 43.086 us | 42.241 us | 4.390 us | 10.189% | 49.842 | pass |
| `tm64_tn128_tk256_default` | 46.292 us | 46.181 us | 1.068 us | 2.307% | 46.390 | pass |
| `tm128_tn128_tk256_default` | 52.186 us | 51.901 us | 1.977 us | 3.789% | 41.151 | pass |
| `tm64_tn128_tk128_persistent` | 40.147 us | 39.700 us | 1.774 us | 4.418% | 53.490 | pass |

The result is a bounded observation, not a proposed dispatch change. Shared-GPU timing variance is reported as the coefficient of variation over 60 CUDA-event samples per candidate. The baseline candidate had one large outlier (`73.921us`), which explains its higher CV; the other candidates ranged from 2.307% to 4.418%.

## Environment

- GPU: one AMD Instinct MI350X, `gfx950`, UUID `GPU-5e94f9cc641f4027`.
- Qualified image: `amdpilotv2/open-job:gbt350-20260909`, local image ID `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.
- Interpreter: `/opt/venv/bin/python`.
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`, HIP `7.2.26015-fc0010cf6a`.
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`.
- Installed FlyDSL Python: `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`, version `0.2.4`.
- Installed AITER source: `/opt/aiter`, commit `d9e5ef7ce08ee7045d583aed768cff41aa9210fe`.
- Mirror checkout: `/job/FlyDSL`, base `main` at `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.
- Job-private caches: `/tmp/flydsl-cache-j-7f374048054d` and `/tmp/flydsl-overlay-j-7f374048054d`.

## First GPU execution

The first installed-source attempt was:

```bash
/opt/venv/bin/python /opt/aiter/op_tests/flydsl_tests/test_flydsl_moe_a16wfp4.py \
  --stage stage2 -t 16 --mode atomic
```

It failed in 10.233 seconds with `ModuleNotFoundError: No module named 'aiter.jit.module_aiter_core'`. Setting `AITER_JIT_DIR=/job/.aiter/jit` exposed a second concrete blocker: AITER's gluon import requires Triton 3.6.0, while the qualified stack has 3.5.1.

The meaningful supported control was:

```bash
AITER_USE_SYSTEM_TRITON=1 \
AITER_JIT_DIR=/tmp/flydsl-cache-j-7f374048054d/aiter \
/opt/venv/bin/python /opt/aiter/op_tests/flydsl_tests/test_flydsl_moe_a16wfp4.py \
  --stage stage2 -t 16 --mode atomic
```

This passed in 47.820 seconds with cosine `0.99999`, relative L2 `0.0035`, max delta `0.0005`, and 100% element-wise closeness. The complete first-execution record is in `/job/baseline-first.json`; it is explicitly an installed-source baseline and is not proof for later checkout changes.

## Correctness

The bounded large-token command was:

```bash
AITER_USE_SYSTEM_TRITON=1 \
AITER_JIT_DIR=/tmp/flydsl-cache-j-7f374048054d/aiter \
/opt/venv/bin/python /opt/aiter/op_tests/flydsl_tests/test_flydsl_moe_a16wfp4.py \
  --stage stage2 -t 512 1024 2048 --mode atomic
```

Shape: `model_dim=512`, `inter_dim=256`, `E=64`, `topk=4`, `block_m=32`, atomic mode. All three cases passed in 10.533 seconds with cosine `0.99999`, relative L2 `0.0035`, max delta `0.0010`, and 100% closeness.

The reference is `torch_moe_stage2`, which dequantizes MXFP4 weights and applies E8M0 block scales independently of the GPU kernel. The test preserves the production shuffle semantics: `shuffle_weight_a16w4(..., gate_up=False)` for GEMM2 weights and `e8m0_shuffle(...)` for GEMM2 scales.

## Throughput method

`reports/j-7f374048054d/bench_gemm2.py` measures the 2048-token GEMM2 bottleneck. It regenerates routing with `block_m == tile_m` for every candidate, checks the kernel once against the independent reference, performs five warmups, and records three rounds of 20 CUDA-event samples. The output zero-fill is outside the timed event. Total work is bounded to 65 launches per candidate.

The timing command was:

```bash
AITER_USE_SYSTEM_TRITON=1 \
AITER_JIT_DIR=/tmp/flydsl-cache-j-7f374048054d/aiter \
/opt/venv/bin/python reports/j-7f374048054d/bench_gemm2.py
```

It completed in 17.785 seconds. Raw per-sample results are in `/job/logs/gemm2-bench.json`; the human-readable run is in `/job/logs/gemm2-bench.log`.

## Issue and PR context

ROCm/FlyDSL issue 708, “MXFP4 MoE low MFU at large shapes and long latency at small tokens,” is open. It requests bounded tuning of MXFP4 MoE GEMM1/GEMM2 tiles and pipelines while preserving AITER shuffle compatibility.

The issue links PR 736, “MXFP4 MoE tuning harness: legality filter, measurement, ledger + validated baseline.” That PR is closed and unmerged. It added tuning infrastructure only, with no production kernel logic change, so this report does not duplicate it as a working fix. No upstream issue, PR, or comment was posted or modified.

## Limitations

- The installed AITER source and the mirror checkout are different revisions. Real GPU correctness and throughput used the installed, supported AITER/FlyDSL stack.
- The mirror checkout's current `a16w4` kernel reaches compilation but its Python API is ahead of the installed native MLIR bindings (`make_buffer_ptr` and CDNA4 bindings are missing from FlyDSL 0.2.4). Rebuilding the compiler was out of scope.
- The benchmark uses manageable `512x256` dimensions rather than a full DeepSeek/Kimi/GPT-OSS shape sweep.
- The first benchmark control changed `tile_m` without rebuilding routing at the same block size and failed numerically. The final benchmark regenerates matching routing for each candidate; only the corrected four-candidate results above are claimed.
- No dispatch or production kernel change is proposed from this single-shape result.
