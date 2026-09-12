# Persistent mode for standard MoE GEMM1

## Result

Implemented an opt-in persistent worklist in the existing
`kernels/moe/moe_gemm_2stage/gemm1.py` path. The design assumption is explicit:
`persistent=False` remains the default, keeps the existing call signature valid,
uses the existing 2-D launch shape, and preserves the mathematical operation. With
`persistent=True`, a 1-D grid capped at `device_CUs * persistent_grid_multiplier`
(default multiplier 1) grid-strides over exactly the same flattened
`(expert-block, channel-block)` tiles.

No C++ or native compiler source changed, so the pinned native rebuild was not
applicable. The prepared wheel's native compiler generated and executed gfx950
artifacts for both modes; their cache paths are recorded in
`compiler-artifacts.log` and remain under the job-private runtime directory.

## GPU correctness

The assigned device was one AMD Instinct MI350X (`gfx950:sramecc+:xnack-`, 256
CUs). The regression covers fp8, int8, int8smooth, and packed-int4 inputs, BF16
outputs, `tile_m` 16 and 64, and masked routing tails at 2051 and 8193 tokens.
Those cases create 522 and 520 logical tiles respectively, so the 256-CTA
persistent launch necessarily performs multiple worklist iterations.

All persistent outputs passed the independent Torch GEMM1 reference with cosine
similarity between 0.9999985 and 0.9999987. Persistent/default cosine similarity
was approximately 1.0 in every case. The focused suite, including the existing
default numeric and sentinel-tail regressions, passed 28/28 tests.

## Timing

Timing used identical tensors for each default/persistent pair, 20 warmups, then
seven batches of 100 GPU-event-timed launches. Values below are mean ± sample
standard deviation in microseconds. These measurements do not promise a speedup.

| Tokens / tile_m | dtype | default (us) | persistent (us) | persistent/default |
|---|---|---:|---:|---:|
| 2051 / 16 | fp8 | 8.332 ± 0.238 | 8.327 ± 0.351 | 0.999 |
| 2051 / 16 | int8 | 7.741 ± 0.486 | 7.974 ± 0.063 | 1.030 |
| 2051 / 16 | int8smooth | 7.217 ± 0.091 | 8.165 ± 0.063 | 1.131 |
| 2051 / 16 | int4 | 8.013 ± 0.067 | 10.380 ± 4.522 | 1.295 |
| 8193 / 64 | fp8 | 9.252 ± 0.087 | 11.603 ± 0.079 | 1.254 |
| 8193 / 64 | int8 | 9.482 ± 0.072 | 12.620 ± 0.137 | 1.331 |
| 8193 / 64 | int8smooth | 9.546 ± 0.097 | 12.602 ± 0.128 | 1.320 |
| 8193 / 64 | int4 | 9.582 ± 1.124 | 13.326 ± 0.125 | 1.391 |

The isolated feature is neutral within variability for the smaller fp8 case and
slower for the other measured cases. Selection is therefore deliberately opt-in;
production tuning and a broader shape sweep remain caller responsibilities.

## Reproduction and evidence

Run from the repository root with the prepared interpreter:

```bash
HIP_VISIBLE_DEVICES=0 PYTHONPATH=/job/repo \
FLYDSL_RUNTIME_CACHE_DIR=/tmp/amdpilot-repo-j-9870aaa06078/cache/final-tests \
TRITON_CACHE_DIR=/tmp/amdpilot-repo-j-9870aaa06078/cache/triton \
/tmp/amdpilot-repo-j-9870aaa06078/venv/bin/python -m pytest \
  tests/kernels/test_moe_gemm_2stage.py \
  -k 'test_moe_gemm1_numeric or test_moe_gemm1_persistent_numeric or test_moe_gemm1_sentinel_token0' -q -s

HIP_VISIBLE_DEVICES=0 PYTHONPATH=/job/repo \
FLYDSL_RUNTIME_CACHE_DIR=/tmp/amdpilot-repo-j-9870aaa06078/cache/validation \
TRITON_CACHE_DIR=/tmp/amdpilot-repo-j-9870aaa06078/cache/triton \
/tmp/amdpilot-repo-j-9870aaa06078/venv/bin/python \
  reports/j-9870aaa06078/validate_persistent_gemm1.py
```

Raw logs and structured measurements are retained beside this report. Ruff was
not installed in the prepared interpreter; `py_compile` and `git diff --check`
both passed.

## Limitations

- Measurements cover two synthetic but real kernel shapes on gfx950, not a full
  production model or every legal shape.
- Persistent mode is not auto-selected because the observed performance varies
  by dtype and was usually slower in this bounded sample.
- No native source changed; consequently this result does not claim a native
  compiler change or rebuild.
