# gfx942 `fx.gemm`, MFMA, and BufferCopy investigation

## Scope

This report reproduces the small synthetic matrix cases from FlyDSL issue 821 on one assigned MI300X. It uses local random or zero tensors only; no model weights were downloaded. The investigation is read-only with respect to upstream issues and pull requests.

The tested shape is `M=64`, `N=16`, `K=128`. The FP8 case uses `Float8E4M3FNUZ` with `fx.rocdl.MFMA(16, 16, 32, ...)` and the actual raw intrinsic name `fx.rocdl.mfma_f32_16x16x32_fp8_fp8`. The 16-bit controls use gfx942-supported `K=16` MFMA atoms: BF16 uses `mfma_f32_16x16x16bf16_1k`, and FP16 uses `mfma_f32_16x16x16f16`.

## Environment

| Item | Measurement |
| --- | --- |
| Image | `amdpilotv2/open-job-mi300:jit-config-readable-260909-banff5`, local image ID `sha256:39fe745feda79ecf4c17f4d806d8ef12150bef720f2f07f5c63a20b3ccfd63f1` |
| GPU | One AMD Instinct MI300X, gfx942, card model `0x74a1`, SKU `M3000108`, GUID `61795`, 206141652992 bytes |
| Python | `/opt/venv/bin/python`, Python 3.10.12 |
| Installed FlyDSL | 0.3.1, `/opt/venv/lib/python3.10/site-packages/flydsl/__init__.py` |
| Installed native modules | `/opt/venv/lib/python3.10/site-packages/flydsl/_mlir/_mlir_libs/libFlyPythonCAPI.so` and `libfly_jit_runtime.so` |
| Working source | `/job/FlyDSL`, branch `amdpilot/j-998971116868`, validation commit `2c12064fed5342d8af36bb72f6a4f583372a3aef` |
| Source Python package | `/job/flydsl-build-candidate/python_packages/flydsl/__init__.py`, version 0.3.3 |
| Source native modules | `/job/flydsl-build-candidate/python_packages/flydsl/_mlir/_mlir_libs/libFlyPythonCAPI.so.24.0git` and `libfly_jit_runtime.so` |
| Torch | 2.9.1+rocm7.2.0.git7e1940d4 |
| ROCm/HIP | HIP 7.2.26015-fc0010cf6a, runtime 1.18, driver 6.19.14.31400000 |
| `hipcc` | `/opt/rocm/bin/hipcc`, AMD clang 22.0.0git, roc-7.2.0 build 26014 |
| Other tools | `rocminfo` and `rocm-smi` available; `clang++`, `lld`, and `llvm-mc` are not on `PATH` |

The image identity is the operator-supplied qualified local image ID. It was not derivable from the container hostname and was not independently re-pulled.

## Commands

The source build used a job-private MLIR install and build directory:

```bash
cd /job/FlyDSL
export LLVM_BUILD_PROFILE=amd-minimal
export MLIR_PATH=/job/llvm-project/mlir_install
export FLY_BUILD_DIR=/job/flydsl-build-candidate
export PYTHONPATH=/job/python-deps
bash scripts/build_llvm.sh -j32
bash scripts/build.sh -j32
```

Focused tests and the measurement harness used:

```bash
export PYTHONPATH=/job/flydsl-build-candidate/python_packages:/job/python-deps
export FLYDSL_RUNTIME_ENABLE_CACHE=0
/opt/venv/bin/python -m pytest \
  tests/kernels/test_buffer_copy_gemm_gfx942.py \
  tests/kernels/test_buffer_copy_gemm_gfx942_dtypes.py \
  -q --disable-warnings

/opt/venv/bin/python reports/j-998971116868/validate_gfx942.py \
  --output reports/j-998971116868/candidate-results.json \
  --dump-root /job/flydsl-artifacts/validation-candidate \
  --image-identity 'amdpilotv2/open-job-mi300:jit-config-readable-260909-banff5 sha256:39fe745feda79ecf4c17f4d806d8ef12150bef720f2f07f5c63a20b3ccfd63f1'
```

The installed 0.3.1 baseline was measured with the same harness after unsetting `PYTHONPATH`, so it imported `/opt/venv/lib/python3.10/site-packages/flydsl` rather than the source build.

## FP8 results

All numerical comparisons use a CPU float32 Torch matmul of the same synthetic input tensors. `max_abs_error` is the maximum absolute elementwise difference.

| Case | Installed 0.3.1 | Candidate `2c12064` |
| --- | --- | --- |
| Raw MFMA, corrected epilogue | passed, error 0, 26 VGPRs | passed, error 0, 26 VGPRs |
| `fx.gemm` + `UniversalCopy32b` | passed, error 0, 28 VGPRs | passed, error 0, 28 VGPRs |
| `fx.gemm` + explicit buffer tensor + `BufferCopy32b` | passed, error 0, 26 VGPRs | passed, error 0, 26 VGPRs |
| `fx.gemm` + explicit buffer tensor + `BufferCopy64b` | passed, error 0, 26 VGPRs | passed, error 0, 26 VGPRs |
| Global pointer + `BufferCopy32b` | failed `fly.copy_atom_call_ssa` legalization | passed, error 0, 26 VGPRs |
| Global pointer + `BufferCopy64b` | failed `fly.copy_atom_call_ssa` legalization | passed, error 0, 26 VGPRs |
| Global pointer + `BufferCopy128b` | unsupported width combination | clean `DSLCompileError`: 128-bit atom does not match 64-bit register operand |

The explicit buffer-tensor cases call `fx.rocdl.make_buffer_tensor`. The failing baseline cases pass the original global tensor directly to the tiled-copy fragment path. This distinction explains why some `BufferCopy` uses already worked while the issue's global-pointer fragment path did not.

## BF16 and FP16 controls

| Case | Installed 0.3.1 | Candidate `2c12064` |
| --- | --- | --- |
| BF16 raw MFMA | passed, max error `3.814697265625e-06`, 34 VGPRs | passed, max error `3.814697265625e-06`, 34 VGPRs |
| BF16 `fx.gemm` + `UniversalCopy32b` | passed, max error `1.9073486328125e-06`, 40 VGPRs | passed, max error `1.9073486328125e-06`, 40 VGPRs |
| BF16 `fx.gemm` + global `BufferCopy64b` | failed legalization | passed, max error `1.9073486328125e-06`, 40 VGPRs |
| FP16 raw MFMA | passed, max error `3.814697265625e-06`, 34 VGPRs | passed, max error `3.814697265625e-06`, 34 VGPRs |
| FP16 `fx.gemm` + `UniversalCopy32b` | passed, max error `3.814697265625e-06`, 40 VGPRs | passed, max error `3.814697265625e-06`, 40 VGPRs |
| FP16 `fx.gemm` + global `BufferCopy64b` | failed legalization | passed, max error `3.814697265625e-06`, 40 VGPRs |

## Issue-attached VGPR reproducer

The exact script attached to upstream issue 821 reports raw MFMA at 24 VGPRs and `fx.gemm` at 26 VGPRs. On this qualified image and both the installed 0.3.1 package and source build, that exact script emits 24 VGPRs for raw MFMA and 28 VGPRs for `fx.gemm`.

More importantly, its raw-MFMA epilogue is not numerically equivalent to the stated GEMM. With seeded random FP8 inputs, its raw output has maximum absolute error `25.018585205078125` versus the Torch reference, while its `fx.gemm` output has error `0`. The corrected raw epilogue in the new test matches Torch exactly and uses 26 VGPRs. Therefore the attached script's 24-VGPR raw count is not a valid like-for-like compiler-overhead measurement.

With the corrected epilogue, the current measurements are:

- Raw MFMA: 26 VGPRs.
- `fx.gemm` + `UniversalCopy32b`: 28 VGPRs, a measured +2 difference.
- `fx.gemm` + `BufferCopy32b` or `BufferCopy64b`: 26 VGPRs, no measured overhead.

## Classification

- **Genuine compiler lowering gap, fixed by candidate:** CDNA3 `BufferCopy` did not lower a global-pointer source or destination in the `fx.gemm` fragment path. This affected FP8, BF16, and FP16 controls on installed FlyDSL 0.3.1. Candidate commit `15d41037d70f6d33ed76a0fd8a741da758026ea5` adds global buffer-resource construction and makes these cases compile and match Torch.
- **Unsupported combination, not a compiler bug:** `BufferCopy128b` with the FP8 fragment's `vector<8xi8>` register operand is a 128-bit atom paired with a 64-bit value. The candidate validates this and emits a clean width-mismatch error.
- **VGPR claim not confirmed as stated:** the issue's exact raw control has an invalid output epilogue. A corrected raw control measures 26 VGPRs. `UniversalCopy32b` still measures +2 VGPRs, but the relevant `BufferCopy32b` and `BufferCopy64b` paths measure no overhead after the candidate fix. No additional VGPR correction is made without a valid remaining defect.

The candidate was not duplicated. Mirror branch commit `15d41037d70f6d33ed76a0fd8a741da758026ea5` was tested, then cherry-picked onto `main` as `4f664861c3d66bef04bd76a29d03ba2479a09b1c`; validation additions are commit `2c12064fed5342d8af36bb72f6a4f583372a3aef`.

## Accuracy gates

No existing accuracy gate was changed. The original FP8 test tolerances remain `atol=1e-5` and `rtol=1e-5` against Torch and exact equality against raw MFMA. The new BF16/FP16 controls use `atol=5e-2` and `rtol=5e-2` against CPU float32 Torch and `atol=1e-5` and `rtol=1e-5` against raw MFMA.

## Raw artifacts

- `candidate-results.json`: source-build environment, statuses, errors, and VGPR counts.
- `installed-baseline-results.json`: installed 0.3.1 environment, statuses, errors, and VGPR counts.
- `upstream-repro-results.json`: exact issue-script numerical and VGPR findings.
- `validate_gfx942.py`: bounded synthetic measurement harness.

The complete job-local IR dumps and command logs are outside the repository under `/job/flydsl-artifacts/`.
