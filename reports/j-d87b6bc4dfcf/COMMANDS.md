# Command log

All commands were run from `/job` unless noted otherwise. Build and JIT caches were kept under `/job`.

```bash
git clone --filter=blob:none https://github.com/amdpilot-org/FlyDSL.git /job/FlyDSL
git -C /job/FlyDSL rev-parse HEAD
gh issue view 346 --repo amdpilot-org/FlyDSL --json number,title,state,body,comments,url
curl -L --retry 3 --max-time 30 -sS https://api.github.com/repos/ROCm/FlyDSL/issues/934
curl -L --retry 3 --max-time 30 -sS https://api.github.com/repos/ROCm/FlyDSL/issues/934/comments
rocminfo
rocm-smi --showproductname --showdriverversion --showmeminfo vram
```

Environment and source inspection used `rg`, `sed`, `find`, `git log`, `git diff`, `ldconfig`, `readelf`, and the Python `importlib.util` API. The substantive build and validation commands were:

```bash
cd /job/FlyDSL

export PIP_CACHE_DIR=/job/.pip-cache
export PIP_TARGET=/job/python-deps
/opt/venv/bin/python -m pip install 'nanobind==2.12.0'
/opt/venv/bin/python -m pip install 'cmake>=3.20'
/opt/venv/bin/python -m pip install patchelf

export LLVM_BUILD_PROFILE=amd-minimal
export LLVM_PACKAGE_INSTALL=1
export PIP_CACHE_DIR=/job/.pip-cache
export PIP_TARGET=/job/python-deps
export PYTHONPATH=/job/python-deps
export PATH=/job/python-deps/cmake/data/bin:/job/python-tools/bin:$PATH
bash scripts/build_llvm.sh -j32

export MLIR_PATH=/job/llvm-project/mlir_install
export FLY_BUILD_DIR=build-fly
bash scripts/build.sh -j32

export PYTHONPATH=/job/FlyDSL/build-fly/python_packages
export FLYDSL_RUNTIME_CACHE_DIR=/job/flydsl-cache6
export FLYDSL_DUMP_IR=1
export FLYDSL_DEBUG_DUMP_ASM=1
export FLYDSL_DUMP_DIR=/job/artifacts/isa6
/opt/venv/bin/python reports/j-d87b6bc4dfcf/validate_extrema.py \
  --output reports/j-d87b6bc4dfcf/results.json

export PYTHONPATH=/job/FlyDSL/build-fly/python_packages
/opt/venv/bin/python -m pytest tests/language/test_arithmetic_types.py \
  tests/unit/test_arith_ops.py -q

FLY_OPT=/job/FlyDSL/build-fly/bin/fly-opt
FILE_CHECK=/job/llvm-project/mlir_install/bin/FileCheck
$FLY_OPT tests/mlir/Conversion/fast_exp2.mlir \
  --pass-pipeline='builtin.module(gpu.module(convert-rocdl-fastmath-ops))' |
  $FILE_CHECK tests/mlir/Conversion/fast_exp2.mlir
$FLY_OPT tests/mlir/Conversion/fast_exp2.mlir \
  --pass-pipeline='builtin.module(gpu.module(convert-rocdl-fastmath-ops))' |
  $FILE_CHECK tests/mlir/Conversion/fast_exp2.mlir --check-prefix=VECTOR
$FLY_OPT tests/mlir/Conversion/fast_exp2.mlir --convert-fly-to-rocdl |
  $FILE_CHECK tests/mlir/Conversion/fast_exp2.mlir --check-prefix=FLY
```

Representative emitted-code inspection:

```bash
rg -n 'llvm\\.(maximum|minimum|maxnum|minnum)' \
  /job/artifacts/isa6/float_extrema_kernel_0/20_llvm_ir.ll
rg -n 'v_(maximum3|minimum3|max_f32|min_f32)' \
  /job/artifacts/isa6/float_extrema_kernel_0/21_final_isa.s
rg -n 's_(max|min)_u32' \
  /job/artifacts/isa6/int_extrema_kernel_0/21_final_isa.s
```
