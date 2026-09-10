# Signed integer division and remainder validation

## Scope and environment

- Campaign: `repo-e2e-20260909`.
- GPU: one AMD Instinct MI350X, `gfx950`, serial `692517020434`, unique ID `0x6e4208b780600d88`, ROCm driver `7.1.1.31500000`.
- Image: `amdpilotv2/open-job:gbt350-20260909`, local image ID `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.
- Interpreter: `/opt/venv/bin/python3`.
- Preserved stack: Torch `2.9.1+rocm7.2.0.git7e1940d4`, Triton `3.5.1+rocm7.2.0.gita272dfa8`.
- PR base: `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.
- Source path: `/job/FlyDSL/python/flydsl`.
- Job-private native wheel: `/tmp/flydsl-cache-j-4ef98015bc2b/extract/flydsl/_mlir` from FlyDSL `0.3.2`; the current source is `0.3.3`. No installed package or node-wide state was modified.
- Read-only issue context: ROCm/FlyDSL issue 934, “Expression-layer arithmetic cleanup.” It has no comments and does not describe division/remainder. A bounded upstream search found no existing fix for this mismatch.

## First installed-source GPU baseline

The baseline was recorded before cloning or editing and is saved at `/job/baseline-first.json`. It is evidence for the installed source only, not for this checkout.

Command:

```bash
cd /tmp
TIMEFORMAT='wall_seconds=%R'
time python3 flydsl_baseline.py
```

Paths:

- Python package: `/opt/venv/lib/python3.12/site-packages/flydsl`
- Native ROCDL bindings: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/_mlirDialectsFlyROCDL.cpython-312-x86_64-linux-gnu.so`
- JIT runtime: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/libfly_jit_runtime.so`

Timing used `time.perf_counter()` around the first JIT call and `torch.cuda.synchronize()`. First GPU execution took `0.350389272` seconds; process wall time was `2.546` seconds.

For operands `[7, -7, 7, -7, 123, -123, 1, -1]` and divisors `[3, 3, -3, -3, 17, 17, 5, 5]`:

- Floor quotient: `[2, -3, -3, 2, 7, -8, 0, -1]`, matched.
- Actual remainder: `[1, -1, 1, -1, 4, -4, 1, -1]`, mismatched.
- Independent floor remainder: `[1, 2, -2, -1, 4, 13, 1, 4]`.

The installed source therefore used truncating remainder semantics for Python `%`.

## Reproduction and validation

The source was tested through a job-private copy at `/tmp/flydsl-cache-j-4ef98015bc2b/python_packages_copy`, with the matching native `_mlir` tree linked from the extracted FlyDSL `0.3.2` wheel.

```bash
CACHE=/tmp/flydsl-cache-j-4ef98015bc2b
cd /job/FlyDSL
PYTHONPATH="$CACHE/python_packages_copy" python3 -m pytest \
  tests/unit/test_docs_api_guard.py \
  tests/language/test_arithmetic_types.py \
  tests/unit/test_vector.py \
  tests/unit/test_integer_division_remainder.py \
  -q --no-header --tb=short
```

Result: `517 passed in 4.69s`.

The same first-run int32 kernel after the change took `0.426492949` seconds and matched both independent references.

## Numerical gates

- Floor division `lhs // rhs` uses `arith.floordivsi` for widths through 64.
- Python `%` now starts from truncating `arith.remsi` and adds the divisor only when the remainder is nonzero and its sign disagrees with the divisor. This gives floor remainder without evaluating `lhs - quotient * rhs`, avoiding avoidable overflow.
- Direct documented truncation operations `fx.arith.divsi` and `fx.arith.remsi` are tested separately.
- GPU floor/truncation gates cover `Int8`, `Int16`, `Int32`, `Int64`, and `Int128`.
- IR gates cover all documented signed widths: `Int4`, `Int8`, `Int16`, `Int32`, `Int64`, and `Int128`.
- `docs/language/arithmetic_types.md` now states the floor and truncation semantics explicitly.
- Independent references use `torch.div(..., rounding_mode="floor")`, `torch.div(..., rounding_mode="trunc")`, and `lhs - quotient * rhs`; the int128 gate uses Python integer arithmetic and explicit little-endian byte packing.

For the shared signed operand set, expected values are:

- Floor quotient: `[2, -3, -3, 2, 7, -8, 0, -1]`
- Floor remainder: `[1, 2, -2, -1, 4, 13, 1, 4]`
- Truncating quotient: `[2, -2, -2, 2, 7, -7, 0, 0]`
- Truncating remainder: `[1, -1, 1, -1, 4, -4, 1, -1]`

## Wide-width finding

Before the change, an `Int128` GPU probe produced negative floor quotients as `2^64 - |q|` (for example, `18446744073709551613` instead of `-3`). Raw `i128` `divsi` and `remsi` were correct. IR inspection showed MLIR's `floordivsi` lowering materialized the adjustment constant as `18446744073709551615 : i128` (`2^64-1`) rather than all-ones `-1`.

The fix keeps native `floordivsi` for widths through 64 and lowers wider signed floor division with `divsi`, an exactness test, a sign test, and `arith_const(-1, type)`. The `Int128` GPU gate now passes.

## Excluded undefined operations

No divide-by-zero or signed overflow case was executed on the GPU. Compile-time zero divisors are covered and raise `ZeroDivisionError`. Signed overflow remains excluded because its machine result is undefined.

## Tooling note

`ruff` and `black` are not installed in the qualified image. `git diff --check` passes.
