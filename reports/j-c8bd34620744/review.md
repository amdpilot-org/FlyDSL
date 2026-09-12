# Independent review of candidate PR 510

- Upstream issue: https://github.com/ROCm/FlyDSL/issues/813
- Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/530
- Prepared base: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`
- Candidate head: `08c66ccee87802d8fcbd123d18e0ec9115cab634`
- Recommendation: do not accept this candidate as a complete resolution of issue 813. The ROCm SDK-free runtime portion is verified, but backend autodetection and the proposed `rocdl;nvvm` dual-backend wheel are not implemented. It is suitable only as a partial patch if its scope is stated accordingly.

## Findings

The prepared base reproduced the reported build-time ROCm SDK dependency. Configuring with `-DCMAKE_DISABLE_FIND_PACKAGE_hip=TRUE` failed at `lib/Runtime/ROCm/CMakeLists.txt:8`, where `find_package(hip REQUIRED)` could not be disabled.

At the exact candidate head, the same fresh configure succeeded and `FlyJitRuntime` built using the pinned LLVM/MLIR toolchain. ELF inspection found no `DT_NEEDED` entry for `libamdhip64` and no undefined HIP symbols. Loading the resulting library in a fresh Python process did not map `libamdhip64`; the runtime was loaded only when a HIP operation was requested.

The required native rebuild passed and redirected the native package to `/tmp/amdpilot-repo-j-c8bd34620744/native-build/python_packages/flydsl/_mlir`. Its GPU smoke ran on one AMD Instinct MI355X (`gfx950`). A separate uncached pointer-vector-add test compared GPU output with the independent PyTorch `a + b` reference at the existing `1e-5` tolerance and passed. Emitted ISA identifies `amdgcn-amd-amdhsa-unknown-gfx950` and contains two `global_load_dword` instructions, `v_add_f32_e32`, and `global_store_dword`.

Adversarial runtime-boundary checks exercised odd element counts for 32-bit and 16-bit device memset (17 and 19), a one-byte allocation/free, and stream/event create-record-synchronize-destroy. All results matched exact PyTorch references. These checks cover several manually declared HIP ABI signatures beyond the candidate's startup smoke.

The original RFC is broader than this change. Current main still permits only `rocdl` in `cmake/FlyDSLBackends.cmake`, defaults unconditionally to it, and has no `nvvm` backend descriptor. The candidate changes only the ROCm JIT runtime and a source-text guard test. It therefore verifies a useful subset—building the ROCm JIT runtime without HIP development headers or link libraries—but does not deliver backend autodetection or a dual-backend wheel.

## Commands and results

All Python commands used `/tmp/amdpilot-repo-j-c8bd34620744/venv/bin/python`. Raw logs and generated ISA are retained outside the checkout under `/job/`.

```text
# Base reproduction (exit 1 as expected)
cmake -S /job/repo -B /tmp/amdpilot-repo-j-c8bd34620744/base-sdkfree-config-review -G Ninja \
  -DMLIR_DIR=/opt/amdpilot/llvm-project/mlir_install/lib/cmake/mlir \
  -DPython3_EXECUTABLE=/tmp/amdpilot-repo-j-c8bd34620744/venv/bin/python \
  -Dnanobind_DIR=/opt/venv/lib/python3.12/site-packages/nanobind/cmake \
  -DCMAKE_DISABLE_FIND_PACKAGE_hip=TRUE
# CMake Error: REQUIRED hip package cannot be disabled.

git checkout --detach 08c66ccee87802d8fcbd123d18e0ec9115cab634

# Native rebuild (exit 0)
/tmp/amdpilot-repo-j-c8bd34620744/venv/bin/python /opt/amdpilot/rebuild-native.py /job
# PASS; AMD Instinct MI355X, gfx950; vector_add 100x1000.

# Candidate SDK-free configure/build (both exit 0)
cmake -S /job/repo -B /tmp/amdpilot-repo-j-c8bd34620744/candidate-sdkfree-config-review -G Ninja \
  -DMLIR_DIR=/opt/amdpilot/llvm-project/mlir_install/lib/cmake/mlir \
  -DPython3_EXECUTABLE=/tmp/amdpilot-repo-j-c8bd34620744/venv/bin/python \
  -Dnanobind_DIR=/opt/venv/lib/python3.12/site-packages/nanobind/cmake \
  -DCMAKE_DISABLE_FIND_PACKAGE_hip=TRUE
cmake --build /tmp/amdpilot-repo-j-c8bd34620744/candidate-sdkfree-config-review --target FlyJitRuntime -j2

# Candidate regression (exit 0)
/tmp/amdpilot-repo-j-c8bd34620744/venv/bin/python -m pytest -q tests/unit/test_backend_cmake_defaults.py
# 5 passed

# Independent GPU regression with fresh private cache and ISA dump (exit 0)
FLYDSL_DUMP_IR=1 FLYDSL_DUMP_DIR=/job/candidate-isa \
FLYDSL_RUNTIME_CACHE_DIR=/tmp/amdpilot-repo-j-c8bd34620744/review-cache \
/tmp/amdpilot-repo-j-c8bd34620744/venv/bin/python -m pytest -q -s tests/unit/test_pointer_argument_vec_add.py
# 1 passed; maximum error stayed below the unchanged 1e-5 assertion.

readelf -d .../libfly_jit_runtime.so
nm -D --undefined-only .../libfly_jit_runtime.so
# No HIP DT_NEEDED entry and no undefined HIP symbols.
```

Additional ctypes checks and their exact outputs are in `/job/candidate-lazy-load.log` and `/job/candidate-adversarial-runtime-2.log`. Other evidence includes `/job/base-sdkfree-config.log`, `/job/candidate-sdkfree-config.log`, `/job/candidate-sdkfree-build.log`, `/job/candidate-native-rebuild.log`, `/job/candidate-pointer-vec-add.log`, `/job/candidate-readelf-dynamic.log`, `/job/candidate-nm-undefined.log`, and `/job/candidate-isa/`.

## Limitations

The review host has ROCm 7.2 installed, so a physically SDK-free host was not available. Disabling CMake HIP package discovery, building the actual target, inspecting ELF dependencies, and checking lazy loading provide strong evidence for the build boundary, but do not replace testing a produced wheel on a machine with no SDK files. Only the available `gfx950` AMD architecture was exercised. CUDA/NVVM, NVIDIA hardware, dual-backend packaging, backend autodetection, and cluster-launch behavior were not verified.
