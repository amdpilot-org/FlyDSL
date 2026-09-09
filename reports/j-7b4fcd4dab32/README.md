# gfx942 typed extrema validation

## Result

The public `fx.max` and `fx.min` implementation already contains upstream PR 995
(mirror commit `92ca7ece48f820aedb5ef0ae6375409e62a48883`). Real `gfx942` kernels
confirmed the documented semantics:

- Signed `Int32` extrema use signed ordering, including `INT32_MIN` and `INT32_MAX`.
- Unsigned `Uint32` extrema use unsigned ordering, including `0xFFFFFFFB` and `0xFFFFFFFF`.
- `fx.max` and `fx.min` propagate NaN and order `-0.0 < +0.0`.
- `fx.maxnumf` and `fx.minnumf` return the non-NaN operand when exactly one input is NaN.

No production fix or kernel call-site migration was needed. The new device test uses
scalar kernel arguments and explicit hand-computed expected values.

## Environment

- Operator-qualified image: `amdpilotv2/open-job-mi300:jit-config-readable-260909-banff5`
- Operator-qualified local image ID: `sha256:39fe745feda79ecf4c17f4d806d8ef12150bef720f2f07f5c63a20b3ccfd63f1`
- Source: `/job/flydsl` at `ed70142704e1a6d5563fb53e1607e3a4b85d7111`
- Working Python: `/opt/venv/bin/python`
- Working FlyDSL source version: `0.3.3`
- Preinstalled FlyDSL wheel: `0.3.1` at `/opt/venv/lib/python3.10/site-packages/flydsl`
- Matching native wheel used for source execution: FlyDSL `0.3.2`, extracted to `/tmp/flydsl-0.3.2-wheel`
- Working native path: `/tmp/flydsl-source-run/flydsl/_mlir` linked to `/tmp/flydsl-0.3.2-wheel/flydsl/_mlir`
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`
- HIP: `7.2.26015-fc0010cf6a`
- AMD clang: `22.0.0git` (`roc-7.2.0 26014`)
- ROCm driver: `6.19.14.31400000`
- GPU: one AMD Instinct MI300X, `gfx942`, UUID `GPU-6e8448eb6f49db1d`

The source Python layer was run from a temporary copy with its `_mlir` package linked to
the matching `0.3.2` native wheel. This kept all downloads, builds, caches, and logs
job-private and avoided rebuilding LLVM.

## Reproduction

Environment inventory used `rocminfo`, `rocm-smi --showproductname --showdriverversion`,
`hipcc --version`, `amdclang --version`, and `/opt/venv/bin/python`.

```bash
cd /job/flydsl
export PYTHONPATH=/tmp/flydsl-source-run
export FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-runtime-cache
export FLYDSL_AUTOTUNE_CACHE_DIR=/tmp/flydsl-autotune-cache
export FLYDSL_RUNTIME_ENABLE_CACHE=0
/opt/venv/bin/python -m pytest tests/unit/test_typed_arith_device.py -q
```

The numerical gates are unchanged: integer results are compared exactly, finite float
results and signed-zero bit patterns are compared exactly, and NaN results are checked
with `math.isnan`.

## Raw observations

```text
int -5 3 -> max 3, min -5
int 3 -5 -> max 3, min -5
int -2147483648 2147483647 -> max 2147483647, min -2147483648
uint 4294967291 3 -> max 4294967291, min 3
uint 3 4294967291 -> max 4294967291, min 3
uint 0 4294967295 -> max 4294967295, min 0
float -1.25 2.5 -> max 2.5, min -1.25, maxnum 2.5, minnum -1.25
float 2.5 -1.25 -> max 2.5, min -1.25, maxnum 2.5, minnum -1.25
float nan 7 -> max nan, min nan, maxnum 7, minnum 7
float 7 nan -> max nan, min nan, maxnum 7, minnum 7
float -0 +0 -> max +0 (bits 0), min -0 (bits -2147483648)
float +0 -0 -> max +0 (bits 0), min -0 (bits -2147483648)
float -0 -0 -> max -0 (bits -2147483648), min -0 (bits -2147483648)
float +0 +0 -> max +0 (bits 0), min +0 (bits 0)
```

## Unrelated observation

An exploratory pointer-buffer kernel showed that `flyc.from_c_void_p(fx.Uint32, ...)`
loads as `Int32` after JIT reconstruction because MLIR integer types are signless. That
caused `fx.max(0xFFFFFFFB, 3)` to use `maxsi` through that pointer path. The expression
API itself emits `maxui` correctly when operands have explicit `Uint32` DSL types. This
pointer signedness issue is outside the expression-arithmetic slice and was not changed.
