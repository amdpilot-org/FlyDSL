# gfx950 linker-discovery control report

## Scope

- Campaign: `repo-e2e-20260909`, continuous-feed batch `20260910`.
- Reference: ROCm/FlyDSL issue 946, `[Issue]: lld lookup failure in different docker images for gfx1250`.
- Issue 946 was open, had no comments at the time read, and reported gfx1250 with ROCm 6.
- **gfx1250 was not tested.** This run used only the assigned MI350X gfx950 as a distinct architecture/environment control.
- No upstream issue, pull request, or comment was posted or changed.

## Environment

- Image: `amdpilotv2/open-job:gbt350-20260909`, local image ID `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.
- GPU: one AMD Instinct MI350X, gfx950, unique ID `0xcb3b7f83d3aa787d`, serial `692517020513`, node ID 9, GUID 1779.
- Python: `/opt/venv/bin/python`.
- Torch: `2.9.1+rocm7.2.0.lw.git7e1940d4`, source `/opt/venv/lib/python3.12/site-packages/torch/__init__.py`.
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`, source `/opt/venv/lib/python3.12/site-packages/triton/__init__.py`.
- FlyDSL: `0.2.4`, source `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`.
- Native FlyDSL bindings: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/`.
- Delivery clone: `/job/j-0ee706f2c47c/FlyDSL`, base `main` commit `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.
- ROCm root: `/opt/rocm`, resolving to `/opt/rocm-7.2.0`.
- Exact linker: `/opt/rocm/llvm/bin/ld.lld`, resolving to `/opt/rocm-7.2.0/lib/llvm/bin/lld`.
- Linker version: AMD LLD 22.0.0, LLVM commit `7b800a19466229b8479a78de19143dc33c3ab9b5`.
- No `ld.lld` was present on the original process `PATH`; MLIR's bundled `gpu-module-to-binary` path used the ROCm root above.
- Job-private cache/source root: `/tmp/flydsl-cache-j-0ee706f2c47c`.

## Issue and candidate

- ROCm/FlyDSL issue 946 says different Docker images place `rocm_path` and `lld` differently, causing FlyDSL compilation to fail in `gpu-module-to-binary` for gfx1250.
- The only relevant upstream candidate found was ROCm/FlyDSL pull request 568, `Auto-discover MLIR ROCm toolkit from rocm-sdk Python wheels`.
- PR 568 was an open draft. Tested head commit: `1e7a7b99e4b1b7e08663f1ad16810a5516a6f490`.
- PR 568 adds `get_rocm_toolkit_path()` with preference `FLYDSL_ROCM_TOOLKIT_PATH`, then `ROCM_PATH`, then `/opt/rocm`, then a rocm-sdk wheel shim. It passes the discovered root as `toolkit=` to both `gpu-module-to-binary` invocations.
- This report does not duplicate or merge that fix. It records a control result only.

## Test

The tiny GPU kernel was the existing vector-add test:

```sh
/opt/venv/bin/python -m pytest \
  tests/kernels/test_vec_add.py::'test_benchmark_vector_add[4]' -q -s --tb=short
```

The existing numerical gate was unchanged: result correctness requires max error `< 1e-5`.

Baseline used the installed FlyDSL 0.2.4 package. The exact PR 568 source tree could not execute directly because its generated `_mlir` bindings were absent, and linking the image's newer native bindings into that older source produced an ABI mismatch before kernel compilation. To isolate the discovery change, the three PR 568 files were applied to a job-private copy of the installed FlyDSL 0.2.4 Python source, with the image's original `_mlir` tree linked unchanged. No host path or binary was changed or replaced.

### Baseline

- Default environment: pass.
- `ROCM_PATH=/opt/rocm`: pass.
- Invalid `ROCM_PATH=/tmp/flydsl-cache-j-0ee706f2c47c/invalid-rocm`: pass; current installed code ignored the invalid value and used `/opt/rocm`.
- Numerical gate: max error `0.00e+00`.

### PR 568 discovery behavior

All cases passed the same gfx950 vector-add kernel and numerical gate:

- Default: resolves `/opt/rocm`; pass.
- `FLYDSL_ROCM_TOOLKIT_PATH=/opt/rocm`: resolves `/opt/rocm`; pass.
- Invalid `FLYDSL_ROCM_TOOLKIT_PATH=/tmp/flydsl-cache-j-0ee706f2c47c/invalid-toolkit`: falls back to `/opt/rocm`; pass.
- `ROCM_PATH=/opt/rocm`: resolves `/opt/rocm`; pass.
- Invalid `ROCM_PATH=/tmp/flydsl-cache-j-0ee706f2c47c/invalid-rocm`: falls back to `/opt/rocm`; pass.

The candidate does not diagnose an invalid explicit path; it silently rejects it as not well-formed and continues discovery. That behavior is safe in this image but may hide a user typo.

### External toolchain diagnostic

The supported process-local external LLVM override was also exercised:

```sh
FLYDSL_COMPILE_LLVM_DIR=/tmp/flydsl-cache-j-0ee706f2c47c/invalid-llvm \
/opt/venv/bin/python -m pytest \
  tests/kernels/test_vec_add.py::'test_benchmark_vector_add[4]' -q --tb=short
```

It failed before execution with:

```text
ExternalLLVMError: External LLVM tool 'mlir-opt' not found. Tried:
/tmp/flydsl-cache-j-0ee706f2c47c/invalid-llvm/bin/mlir-opt
```

No valid external `mlir-opt` prefix was available in this image, so external-LLVM positive execution was not tested.

## Conclusion

- On this qualified gfx950 image, the existing `/opt/rocm` layout is well-formed and the exact linker is `/opt/rocm/llvm/bin/ld.lld`.
- Baseline FlyDSL compiles and executes successfully without changing host paths.
- PR 568's discovery logic also compiles and executes successfully when its change is isolated against the installed 0.2.4 source/native stack.
- Invalid explicit ROCm toolkit paths are ignored/fall back rather than diagnosed; the separate external LLVM override does provide a concrete missing-tool diagnostic.
- This result does not establish a gfx1250 fix or reproduce issue 946. gfx1250 remains untested.
