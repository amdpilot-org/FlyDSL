# MI350X gfx950 expression extrema validation

## Result

**No lowering defect found.** The synthetic GPU harness passed all 44 cases on one assigned AMD Instinct MI350X (gfx950). No source fix was needed, so product code is unchanged.

- Float cases: 36/36 passed (`fx.max`, `fx.min`, `fx.maxnumf`, `fx.minnumf`, `fx.maximumf`, `fx.minimumf`).
- Integer cases: 8/8 passed (`fx.max`, `fx.min`).
- Raw per-case inputs, expected values, actual values, and pass flags: `results.json`.
- Reproduction harness: `validate_extrema.py`.

## Contracts verified

The source API maps operations as follows:

- `fx.max` and `fx.min` on floats use NaN-propagating `arith.maximumf` and `arith.minimumf`.
- `fx.max` and `fx.min` on signed integers use `arith.maxsi` and `arith.minsi`.
- `fx.max` and `fx.min` on unsigned integers use `arith.maxui` and `arith.minui`.
- `fx.maxnumf` and `fx.minnumf` implement libm `fmax`/`fmin` semantics: one NaN returns the other operand; both NaNs return NaN; mixed zero may return either zero.
- `fx.maximumf` and `fx.minimumf` propagate NaN and treat `-0.0` as less than `+0.0`. Therefore mixed-zero maximum is `+0.0` and mixed-zero minimum is `-0.0`.

The independent oracle implements these rules directly from Python bit patterns and signed/unsigned interpretations; it does not call the FlyDSL operations under test.

## Case matrix

- Float32 finite values in both operand orders: `(-3.0, 4.0)` and `(4.0, -3.0)`.
- Float32 NaN in both operand orders: `(NaN, 7.0)` and `(7.0, NaN)`.
- Float32 signed zero in both orders: `(-0.0, +0.0)` and `(+0.0, -0.0)`.
- Int32 signed values in both orders: `(-1, 1)` and `(1, -1)`.
- Uint32 unsigned values in both orders: `(0xffffffff, 1)` and `(1, 0xffffffff)`.

## Environment

- Qualified image: `amdpilotv2/open-job:gbt350-20260909`, specified local image ID `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`. Docker image metadata was not inspectable from inside the job container, so this ID is recorded from the task specification rather than measured from a registry.
- GPU: AMD Instinct MI350X, gfx950, capability `(9, 5)`, device model `0x75a0`, node ID 5, GUID 42642.
- Python: `/opt/venv/bin/python`, Python 3.12.3.
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`, HIP `7.2.26015-fc0010cf6a`.
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`.
- AITER: package `amd-aiter` version `0+gd9e5ef7ce08ee7045d583aed768cff41aa9210fe`, source `/opt/aiter`, commit `d9e5ef7ce08ee7045d583aed768cff41aa9210fe`.
- ROCm driver: `7.1.1.31500000`; Torch ROCm userspace reports `7.2.26015-fc0010cf6a`.
- Native libraries: `libamdhip64.so.7.2.70200` (SONAME `libamdhip64.so.7`), `libhsa-runtime64.so.1.18.70200` (SONAME `libhsa-runtime64.so.1`), `librccl.so.1.0.70200` (SONAME `librccl.so.1`).
- Working clone: `/job/FlyDSL`, commit `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.
- Preinstalled FlyDSL package: `/opt/venv/lib/python3.12/site-packages/flydsl`, version 0.2.4. It is a different, older layout and was not used for validation.
- Validated FlyDSL Python/native package: `/job/FlyDSL/build-fly/python_packages`.
- Matching LLVM/MLIR source commit: `e2a39f504fee836e4def9581bed817ecc327b9dc`; install prefix `/job/llvm-project/mlir_install`.

The preinstalled native FlyDSL runtime lacked the clone's `convert-rocdl-fastmath-ops` pass. A bounded `amd-minimal` LLVM/MLIR build (MLIR, X86 and AMDGPU targets only) and the clone's native layer were therefore built in job-private paths before GPU validation.

## Emitted code

No GPU output differed from its oracle, so no mismatch-specific disassembly was required. Representative final ISA from the passing run:

- `llvm.maximum.f32` lowers to `v_maximum3_f32`.
- `llvm.minimum.f32` lowers to `v_minimum3_f32`.
- `llvm.maxnum.f32` lowers to a NaN-check sequence using `v_max_f32_e32`.
- `llvm.minnum.f32` lowers to a NaN-check sequence using `v_min_f32_e32`.
- Unsigned integer extrema lower to `s_max_u32` and `s_min_u32`.

Full final ISA, LLVM IR, and all MLIR stages are retained outside the repository in `/job/artifacts/isa6`.

## Existing gates

Unchanged numerical/type gates were run after the final GPU validation:

- `pytest tests/language/test_arithmetic_types.py tests/unit/test_arith_ops.py -q`: **413 passed**.
- `tests/mlir/Conversion/fast_exp2.mlir` FileCheck runs for scalar, vector, and Fly conversion prefixes: **all passed**.

## Notes and limitations

- The first harness draft loaded unsigned integers through raw `fx.Pointer` values. MLIR pointer element integers are signless, so pointer loads decay to `Int32`; this was a harness issue, not an expression-lowering defect. The final harness passes explicitly typed `fx.Int32` and `fx.Uint32` expression operands.
- An initial oracle draft incorrectly expected mixed-zero `maximumf` to return `-0.0`. The MLIR contract says `-0.0 < +0.0`, so the correct mixed-zero maximum is `+0.0`. The oracle was corrected and the final 44-case run passes.
- AITER import previously attempted a JIT build and reported `ModuleNotFoundError: No module named 'aiter.jit.module_aiter_core'`. AITER version and commit were therefore recorded from installed package metadata and source repository, without modifying the image stack.
