# Retile diagnostics for UniversalCopy128b plus UniversalAtomicAdd

## Conclusion

The reported kernel has two invalid user layouts and one isolated compiler diagnostic defect:

- Passing the un-retiled `UniversalCopy128b` fragment to `UniversalAtomicAdd` is invalid. The atomic atom is scalar-sized, while the load fragment is vectorized. Upstream pull request 918, commit `933e351992d2ff71b5c66561b73bb8ff74a5cf3c`, already provides the correct clear diagnostic; this change preserves that exact commit.
- Calling `retile` after indexing away both tile modes is also an invalid user layout. The fragment must retain one value mode plus the tiled-copy tile modes. FlyDSL `0.3.1` aborts on an `IntTupleUtils.h` assertion instead of diagnosing this, which is the isolated compiler defect fixed here.
- The supported pattern is to create and load the full-rank fragment, retile it, and only then index tile modes for the scalar atomic stores.

## Valid layouts

The actual atom definitions in `lib/Dialect/Fly/IR/FlyUniversalOps.cpp` are:

- `UniversalCopy128b` with `Float32`: one thread and a 128-bit value, equivalent to eight contiguous `f32` values.
- `UniversalAtomicAdd(Float32)`: one thread and one 32-bit `f32` value.

For the issue's `(32, 64)` tile, 256-thread layout, and `(64, 64)` input, the API produces:

```text
load partition:  Tensor<f32, global,  ((4,2),2,1):((1,4),?{i64 div=32},0)>
load fragment:  Tensor<f32, register, ((4,2),2,1):((1,4),8,0)>
retile result:  Tensor<f32, register, ((1,8),2,1):((0,1),8,0)>
retiled tile:   Tensor<f32, register, (1,8):(0,1)>

broadcast B:    Tensor<f32, global, (64,64):(0,0)>
store partition: Tensor<f32, global, ((1,8),2,1):((0,0),0,0)>
store tile:      Tensor<f32, global, (1,8):(0,0)>
```

The broadcast must cover the full `(tileM, tileN)` logical tile with zero strides. The store fragment must be scalar-valued (`(1,8):(0,1)` after tile indexing), not the load fragment's vector-valued `(4,2):(1,4)` layout.

## Environment

- Campaign: `repo-e2e-20260909`
- Mirror issue: `amdpilot-org/FlyDSL` issue number 318
- Upstream reference: `ROCm/FlyDSL` issue number 732, read only
- Working clone: `/job/FlyDSL`
- Delivery branch: `amdpilot/j-ad5464a877dd`
- PR base: `main` at `ed70142704e1a6d5563fb53e1607e3a4b85d7111`
- Source version: FlyDSL `0.3.3`
- Installed runtime: FlyDSL `0.3.1`
- Installed Python module: `/opt/venv/lib/python3.10/site-packages/flydsl/__init__.py`
- Installed native modules: `/opt/venv/lib/python3.10/site-packages/flydsl/_mlir/_mlir_libs/_mlirDialectsFly.cpython-310-x86_64-linux-gnu.so` and `/opt/venv/lib/python3.10/site-packages/flydsl/_mlir/_mlir_libs/libfly_jit_runtime.so`
- Source-build Python package: `/job/.cache/flydsl-build/python_packages/flydsl`
- Source-build native module: `/job/.cache/flydsl-build/python_packages/flydsl/_mlir/_mlir_libs/_mlirDialectsFly.cpython-310-x86_64-linux-gnu.so`
- Source-build compiler tool: `/job/.cache/flydsl-build/bin/fly-opt`
- Source-build MLIR prefix: `/job/llvm-project/mlir_install`
- Python: `/opt/venv/bin/python`, Python `3.10.12`
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`
- HIP: `7.2.26015-fc0010cf6a`
- ROCm SMI: `4.0.0+fc0010cf6a`; driver `6.19.14.31400000`
- `hipcc`: `/opt/rocm/bin/hipcc`, AMD clang `22.0.0git`
- Toolchain availability: `/opt/venv/bin/python`, `/opt/rocm/bin/rocminfo`, `/opt/rocm/bin/rocm-smi`, `/opt/rocm/bin/hipcc`, `/opt/venv/bin/cmake`, `/opt/venv/bin/ninja`, `/usr/bin/git`, and `/usr/local/bin/gh`
- `clang` is not on `PATH`; `hipcc` reports AMD clang `22.0.0git` from `/opt/rocm-7.2.0/lib/llvm/bin`
- GPU: one AMD Instinct MI300X, `gfx942`, serial `692440004420`, unique ID `0x2e2f615a49e61496`, node ID 3
- Image: operator-qualified `amdpilotv2/open-job-mi300:jit-config-readable-35122-260909`, local image ID `sha256:dfc9419089c338b5712da4841768b38b1ab79f3da41f8c58c3cd4dfcc1147ff1`. The container exposes no Docker socket or image metadata, so the image identity is the operator-provided local ID rather than a hostname-derived value.

## Commands

The working clone was created with bounded retry logic:

```bash
git clone --depth 50 https://github.com/amdpilot-org/FlyDSL.git /job/FlyDSL
```

Issue and candidate data were read through public GitHub APIs or `gh` against the mirror only. No upstream issue, pull request, or comment was modified.

Installed-runtime reproduction:

```bash
/opt/venv/bin/python /job/artifacts/repro_issue_732.py 3
/opt/venv/bin/python /job/artifacts/repro_issue_732.py 1
/opt/venv/bin/python /job/artifacts/repro_issue_732.py 2
/opt/venv/bin/python /job/artifacts/repro_issue_732.py 4
```

Source build, with caches outside the repository. The LLVM script was started at 16 jobs, interrupted cleanly at target `2056/5803`, and resumed at a bounded 32 jobs:

```bash
LLVM_BUILD_PROFILE=amd-minimal \
PIP_TARGET=/job/.cache/flydsl-python-deps \
PYTHONPATH=/job/.cache/flydsl-python-deps \
bash scripts/build_llvm.sh -j16

cmake --build /job/llvm-project/build-flydsl -j32
cmake --install /job/llvm-project/build-flydsl --prefix /job/llvm-project/mlir_install

MLIR_PATH=/job/llvm-project/mlir_install \
FLY_BUILD_DIR=/job/.cache/flydsl-build \
PYTHONPATH=/job/.cache/flydsl-python-deps \
bash scripts/build.sh -j32
```

Source validation:

```bash
PYTHONPATH=/job/.cache/flydsl-build/python_packages \
/opt/venv/bin/python -m pytest tests/unit/test_derived.py

PYTHONPATH=/job/.cache/flydsl-build/python_packages \
/opt/venv/bin/python -m pytest tests/unit/test_universal_atomic.py

PYTHONPATH=/job/.cache/flydsl-build/python_packages \
/opt/venv/bin/python examples/06-universal_copy_atomic_sum.py
```

## Raw results

### Installed FlyDSL 0.3.1

Case 3, the issue's hard-coded scalar view, passed:

```text
expected=-64.268074
actual=-64.2680817
absolute_error=7.62939453e-06
relative_error=1.18712045e-07
```

Case 1, the un-retiled vector fragment passed to the scalar atomic, emitted:

```text
error: unsupported atomicrmw fadd: target supports atomics up to 8 bytes, but this atomic accesses 16 bytes
actual=0
```

This is an invalid user layout. The existing upstream candidate turns the low-level backend error into a clear frontend diagnostic.

Case 2, retile after tile indexing, aborted with status 134:

```text
IntTupleUtils.h:887:
Assertion `tRank >= guideRank && "Mismatched ranks in intTupleZip2By"' failed.
```

The user layout is invalid, but the assertion is a compiler diagnostic defect.

Case 4, the supported full-rank retile pattern, passed:

```text
expected=-64.268074
actual=-64.2680893
absolute_error=1.52587891e-05
relative_error=2.37424089e-07
```

A second run produced `-64.2680664`, with absolute error `7.62939453e-06` and relative error `1.18712045e-07`. The variation is expected from nondeterministic floating-point atomic-add ordering.

### Source build

The source build completed successfully. It imported FlyDSL `0.3.3` from `/job/.cache/flydsl-build/python_packages/flydsl`, while retaining Torch `2.9.1+rocm7.2.0.git7e1940d4` and HIP `7.2.26015-fc0010cf6a`.

Focused retile tests:

```text
tests/unit/test_derived.py: 11 passed in 0.66s
```

Existing universal atomic tests, with their unchanged `1e-3` absolute gate:

```text
tests/unit/test_universal_atomic.py: 6 passed in 2.49s
```

Supported gfx942 sum example:

```text
expected=-64.268074
actual=-64.2680817
absolute_error=7.62939453e-06
relative_error=1.18712046e-07
```

The patched source rejects the invalid vector atomic with status 1 and:

```text
DSLCompileError: Failure while executing pass pipeline:
error: "-":35:7: vectorized atomic ops are unsupported, need a scalar-sized copy atom
```

It also rejects the invalid rank-2 retile input with:

```text
MLIRError
Operation creation failed:
error: unknown: TiledCopyRetileOp: expected input rank at least 3 (one value mode plus 2 tile modes), got 2
```

## Changes

- Preserved upstream PR 918 commit `933e351992d2ff71b5c66561b73bb8ff74a5cf3c`, which rejects vector operands in universal atomic copy atoms.
- Added a `TiledCopyRetileOp` rank check that reports the required value and tile modes before the layout utility can assert.
- Added a unit test for the invalid rank-2 retile input.
- Added `examples/06-universal_copy_atomic_sum.py`, a supported 64-by-64 sum using `UniversalCopy128b`, full-rank retile, zero-stride broadcast, and scalar `UniversalAtomicAdd`.
- Updated the README example inventory.

The existing numerical gate in `tests/unit/test_universal_atomic.py` remains `abs(actual - expected) < 1e-3`. No existing gate was changed.

## Constraints

- Only the one assigned MI300X (`gfx942`) was used.
- No model weights or alternate framework stacks were downloaded.
- Build dependencies were installed into `/job/.cache/flydsl-python-deps`; the installed Torch/ROCm stack was not replaced.
- LLVM, FlyDSL, and Python build outputs remain under `/job/llvm-project` and `/job/.cache`.
- The upstream issue and pull request were read only; nothing was posted or changed upstream.
