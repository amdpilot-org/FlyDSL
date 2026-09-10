# gfx950 expression shift/cast validation

## Scope

- Read-only upstream context: ROCm/FlyDSL issue 934, "Expression-layer arithmetic cleanup".
- Issue 934 has no comments. Its completed children are issues 937, 938, 939, 940, 941, and 994.
- This validation covers public expression integer right shifts and explicit integer casts. It does not change Pointer/Tensor signedness reconstruction, shuffle width, or vector-reduce NaN semantics.

## Environment

- Image: `amdpilotv2/open-job:gbt350-20260909`, local ID `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.
- Python: `/opt/venv/bin/python` (Python 3.12).
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`.
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`.
- Installed FlyDSL: version 0.2.4 at `/opt/venv/lib/python3.12/site-packages/flydsl`.
- Mirror source: `/job/FlyDSL`, base commit `ed70142` before this branch.
- Native MLIR bindings used for source-overlay execution: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`.
- GPU: one AMD Instinct MI350X, gfx950, unique ID `0x6e4208b780600d88`, serial `692517020434`.

## Early installed-source baseline

`/job/baseline-first.json` records the first GPU execution attempt and a supported neighboring control.

- The packaged FlyDSL test `/opt/aiter/op_tests/flydsl_tests/test_silu_and_mul_fq.py` could not collect because its installed Aiter import path requires Triton 3.6.0, while the image has 3.5.1. The bounded attempt took 23.731 seconds.
- A direct installed-Triton integer control executed on the assigned GPU in 0.283195 seconds on its first launch. A CUDA-event timing of one warm launch reported 0.082681 ms.
- That control's signed and unsigned 32/64-bit shift comparisons passed. Its unsigned cast comparisons were mixed; this installed-source control is not evidence about the mirror checkout.

## Real gfx950 expression results

The new test constructs explicitly typed `fx.Vector` values in-kernel, applies public shift/cast expressions, and stores already-typed results. This avoids using pointer loads as inputs, which would conflate the separate Pointer signedness issue with expression semantics.

- Signed and unsigned 32/64-bit values: zero, one, positive maximum, high bit, and all ones.
- Shift counts: 0, 1, and width minus one (31 or 63).
- Explicit conversion widths: 8, 16, 32, and 64 bits.
- All 12 real-GPU expression cases passed on the mirror source. The bounded 12-case runner took 1.013508 seconds after compilation.
- Existing unsupported-operation checks passed: 33 selected tests covering float shifts, mixed integer/float shifts, and invalid rounding-mode casts.

The installed 0.2.4 control passed the same signed and unsigned32 cases but failed all three unsigned64 cases while constructing high-bit constants with `RuntimeError: std::bad_cast`. The mirror already contains upstream PR 973, merged as commit `f83759e953db4b9b0d1e0304f9c3634443a3bf3b`, which implements integer wrap-around and wide unsigned constants. This branch therefore adds regression coverage rather than duplicating that fix.

## Reproduction

The image's native bindings predate the mirror's unrelated `convert-rocdl-fastmath-ops` pass. For this integer-only validation, the source overlay was run with that pass removed from the parsed pipeline; no fastmath operation was exercised. A normal current FlyDSL build does not need this workaround.

```bash
export PYTHONPATH=/job/FlyDSL/python
export FLYDSL_CACHE_DIR=/tmp/flydsl-cache-j-75fda9878c24

# Real expression cases (12 passed in the source-overlay runner).
/opt/venv/bin/python /tmp/run_current_integer_gpu.py

# Existing shift/cast and unsupported-operation coverage.
/opt/venv/bin/python -m pytest -q FlyDSL/tests/language/test_arithmetic_types.py \
  -k 'shift or ToConversion or RoundingMode'
```

The source-overlay runner imports `FlyDSL/tests/unit/test_expression_integer_gpu.py`, monkeypatches the missing unrelated fastmath pass out of the pipeline, and invokes its four test functions for all listed shift counts.

## Result

No expression shift or cast mismatch remains on the tested mirror source. The installed-source unsigned64 constant failure is already fixed by PR 973. This branch adds focused real-GPU regression coverage for that behavior and for signed/unsigned shift/cast semantics.
