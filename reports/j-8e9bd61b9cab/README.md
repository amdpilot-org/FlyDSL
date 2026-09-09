# `zipped_divide` lower-rank and `None` tiler validation

## Status

Complete. The working source fix is based on upstream read-only PR 746’s functional changes, with a focused FlyDSL regression and a reproducible gfx942 validation harness.

## Environment

- Working mirror: `amdpilot-org/FlyDSL`
- Base source-tree commit: `ed70142704e1a6d5563fb53e1607e3a4b85d7111` (`v0.3.2-30-ged70142`, source `__version__` 0.3.3)
- Working source path: `/job/FlyDSL`
- Source-native Python path: `/job/FlyDSL/build-fly/python_packages/flydsl`
- Source-native library path: `/job/FlyDSL/build-fly/python_packages/flydsl/_mlir/_mlir_libs`
- Installed wheel: FlyDSL 0.3.1 at `/opt/venv/lib/python3.10/site-packages/flydsl`
- Installed native path: `/opt/venv/lib/python3.10/site-packages/flydsl/_mlir/_mlir_libs`
- Python: `/opt/venv/bin/python` (3.10.12)
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`
- ROCm HIP runtime reported by Torch: `7.2.26015-fc0010cf6a`
- GPU: one assigned AMD Instinct MI300X, gfx942, serial `692440004359`, Torch device capability `(9, 4)`
- Operator-specified image: `amdpilotv2/open-job-mi300:jit-config-readable-260909-banff5`, local image ID `sha256:39fe745feda79ecf4c17f4d806d8ef12150bef720f2f07f5c63a20b3ccfd63f1`
- Container OS: Ubuntu 22.04.5 LTS; hostname is not used as image identity.

The installed wheel and working source tree are intentionally recorded separately; the installed 0.3.1 native module is not assumed to match the source-tree commit.

## Reproduction

The installed 0.3.1 wheel and a job-private 0.3.2 wheel both reproduced the assertion for `zipped_divide` with explicit `None` entries. The source tree at the base commit also lacked the unmerged PR 746 correction.

The source build used the bounded `LLVM_BUILD_PROFILE=amd-minimal` profile and a job-private MLIR prefix:

```bash
export PYTHONPATH=/job/build-deps
export LLVM_BUILD_PROFILE=amd-minimal
export LLVM_INSTALL_DIR=/job/llvm-project/mlir_install
bash scripts/build_llvm.sh -j64

export MLIR_PATH=/job/llvm-project/mlir_install
export FLY_BUILD_DIR=/job/FlyDSL/build-fly
bash scripts/build.sh -j64

export PYTHONPATH=/job/FlyDSL/build-fly/python_packages
export LD_LIBRARY_PATH=/job/FlyDSL/build-fly/python_packages/flydsl/_mlir/_mlir_libs
/opt/venv/bin/python reports/j-8e9bd61b9cab/validate_divides.py
/opt/venv/bin/python -m pytest -q tests/unit/test_layout_algebra.py
```

## Results

For layout `(64,50,80):(16000,160,1)`:

- `logical_divide` with `(32,)`, `(32,None,None)`, and `(32,None,40)` preserves the original index mapping.
- `zipped_divide` with `(32,)` groups the tile coordinate with `(2,50,80)`.
- Explicit `None` modes become `(1):(0)` placeholders in the first zipped group; omitted lower-rank modes do not.
- `zipped_divide` with `(32,None,None)` produces `((32,1,1),(2,50,80)):((16000,0,0),(512000,160,1))`.
- `zipped_divide` with `(32,None,40)` produces `((32,1,40),(2,50,2)):((16000,0,1),(512000,160,40))`.

The independent NumPy oracle recomputes each divided index from the original coordinates and tiler. The real gfx942 kernel performs one load and one store per element through `crd2idx` on the divided layout. It writes 256,000 unique indices into a buffer sized to the layout cosize `1,015,920`, followed by 1,024 sentinel elements. All six operation/tiler combinations reported zero mismatches, 256,000 unique writes, and 1,024 untouched out-of-range sentinels.

No existing numerical gate was changed. The focused regression passes, and the existing layout-algebra suite reports 32 passed and 1 skipped.

## Raw output

See `reports/j-8e9bd61b9cab/raw-results.txt`.

Using the installed 0.3.1 wheel and layout `(64,50,80):(16000,160,1)`:

- `logical_divide` with `(32,)`, `(32,None,None)`, and `(32,None,40)` completed.
- `zipped_divide` with `(32,)` completed.
- `zipped_divide` with `(32,None,None)` aborted with the assertion from upstream issue 739:
  `intTupleZip2By expects rank-2 tuple at terminal`.
- `zipped_divide` with `(32,None,40)` aborted with the same assertion.

Raw installed-wheel output is retained in the job log and will be summarized in the final report.

## Upstream context

Read-only investigation of upstream issue 739 found upstream pull request 746, which changes divide tile handling and adds layout-algebra coverage for these cases. PR 746 was not already present in the tested mirror source. This branch applies its functional correction, adds a focused regression, and adds the independent oracle plus gfx942 load/store validation. No upstream issue, pull request, or comment was modified.

## Notes

- The source-native build used the minimal MLIR profile rather than a full LLVM/Clang/lld build.
- PyPI 0.3.2 was tested as a bounded binary candidate and still reproduced the assertion; it is not the tested source-native result.
- The device harness intentionally uses the layout cosize rather than element count because the non-contiguous strides map up to index `1,015,919`.
