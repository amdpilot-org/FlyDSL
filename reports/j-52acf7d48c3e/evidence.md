# Qualification command evidence

## Before rebuild

```text
$ patchelf --version
patchelf 0.17.2

$ git submodule status --recursive
 84d107bf416c6bab9ae68ad285876600d230490d thirdparty/dlpack (v1.3)
 ed067c17b259774f4ddc23ba7de937a90642bbb1 thirdparty/tvm-ffi (v0.1.8-13-ged067c1)
 84d107bf416c6bab9ae68ad285876600d230490d thirdparty/tvm-ffi/3rdparty/dlpack (v1.3)
 793921876c981ce49759114d7bb89bb89b2d3a2d thirdparty/tvm-ffi/3rdparty/libbacktrace (7939218)

$ /tmp/amdpilot-repo-j-52acf7d48c3e/venv/bin/python -c 'from pathlib import Path; import flydsl.expr as e; import flydsl._mlir as m; print("source_import=" + str(Path(e.__file__).resolve())); print("native_import=" + str(Path(next(iter(m.__path__))).resolve()))'
source_import=/job/repo/python/flydsl/expr/__init__.py
native_import=/opt/venv/lib/python3.12/site-packages/flydsl/_mlir

$ find /job/native-build-attempts -mindepth 1 -maxdepth 2 -type f -print
/job/native-build-attempts: absent

$ find /tmp/amdpilot-repo-j-52acf7d48c3e/native-build -type f -o -type l
/tmp/amdpilot-repo-j-52acf7d48c3e/native-build: absent

$ cat /job/repository-smoke.json
{
  "passed": true,
  "operation": "FlyDSL vector_add 100x1000 (predicated border blocks)",
  "gpu": "AMD Instinct MI350X",
  "arch": "gfx950",
  "device_count": 1,
  "wall_s": 1.4202069751918316,
  "torch": "2.9.1+rocm7.2.0.git7e1940d4",
  "hip": "7.2.26015-fc0010cf6a"
}
```

## Single rebuild invocation

The build subprocess's complete output is in `native-build.log`.

```text
$ /tmp/amdpilot-repo-j-52acf7d48c3e/venv/bin/python /opt/amdpilot/rebuild-native.py /job
PASS
{
  "attempt": "/job/native-build-attempts/1789178146737361701",
  "passed": true,
  "state": "passed",
  "toolchain": {
    "llvm_hash": "e2a39f504fee836e4def9581bed817ecc327b9dc",
    "patch_sha256": "082cca2b52291b122bd69e17126739ece7337f37c30b3676ba3dd446f9b4fca4",
    "source_revision": "acf7e67b7d22847e345938ca54fcc137bd7b2a1f",
    "build_profile": "amd-minimal",
    "parallel_jobs": 32
  },
  "native": "/tmp/amdpilot-repo-j-52acf7d48c3e/native-build/python_packages/flydsl/_mlir",
  "working_tree_sha256": "e766acdc4a4a5012943b7877f88e1121e5e62c686986a4b2327be1f5b3a81759",
  "wall_s": 62.75802497845143,
  "smoke": {
    "passed": true,
    "operation": "FlyDSL vector_add 100x1000 (predicated border blocks)",
    "gpu": "AMD Instinct MI350X",
    "arch": "gfx950",
    "device_count": 1,
    "wall_s": 2.462609068490565,
    "torch": "2.9.1+rocm7.2.0.git7e1940d4",
    "hip": "7.2.26015-fc0010cf6a"
  }
}
```

## After rebuild

```text
$ patchelf --version
patchelf 0.17.2

$ git submodule status --recursive
 84d107bf416c6bab9ae68ad285876600d230490d thirdparty/dlpack (v1.3)
 ed067c17b259774f4ddc23ba7de937a90642bbb1 thirdparty/tvm-ffi (v0.1.8-13-ged067c1)
 84d107bf416c6bab9ae68ad285876600d230490d thirdparty/tvm-ffi/3rdparty/dlpack (v1.3)
 793921876c981ce49759114d7bb89bb89b2d3a2d thirdparty/tvm-ffi/3rdparty/libbacktrace (7939218)

$ /tmp/amdpilot-repo-j-52acf7d48c3e/venv/bin/python -c 'from pathlib import Path; import flydsl.expr as e; import flydsl._mlir as m; print("source_import=" + str(Path(e.__file__).resolve())); print("native_import=" + str(Path(next(iter(m.__path__))).resolve()))'
source_import=/job/repo/python/flydsl/expr/__init__.py
native_import=/tmp/amdpilot-repo-j-52acf7d48c3e/native-build/python_packages/flydsl/_mlir

$ find /job/native-build-attempts -mindepth 1 -maxdepth 2 -type f -print
/job/native-build-attempts/1789178146737361701/build.log
/job/native-build-attempts/1789178146737361701/result.json

$ find /tmp/amdpilot-repo-j-52acf7d48c3e/native-build/python_packages/flydsl/_mlir/_mlir_libs -maxdepth 1 -type f -o -type l
/tmp/amdpilot-repo-j-52acf7d48c3e/native-build/python_packages/flydsl/_mlir/_mlir_libs/_mlir.cpython-312-x86_64-linux-gnu.so
/tmp/amdpilot-repo-j-52acf7d48c3e/native-build/python_packages/flydsl/_mlir/_mlir_libs/_mlirDialectsFly.cpython-312-x86_64-linux-gnu.so
/tmp/amdpilot-repo-j-52acf7d48c3e/native-build/python_packages/flydsl/_mlir/_mlir_libs/_mlirDialectsFlyROCDL.cpython-312-x86_64-linux-gnu.so
/tmp/amdpilot-repo-j-52acf7d48c3e/native-build/python_packages/flydsl/_mlir/_mlir_libs/libFlyPythonCAPI.so.24.0git
/tmp/amdpilot-repo-j-52acf7d48c3e/native-build/python_packages/flydsl/_mlir/_mlir_libs/libfly_jit_runtime.so

$ cat /job/native-verification/repository-smoke.json
{
  "passed": true,
  "operation": "FlyDSL vector_add 100x1000 (predicated border blocks)",
  "gpu": "AMD Instinct MI350X",
  "arch": "gfx950",
  "device_count": 1,
  "wall_s": 2.462609068490565,
  "torch": "2.9.1+rocm7.2.0.git7e1940d4",
  "hip": "7.2.26015-fc0010cf6a"
}
```

The complete single-attempt record is preserved in `native-attempt-result.json` and `native-build.json`.

## Required expression tests

```text
$ . /tmp/amdpilot-repo-j-52acf7d48c3e/environment.sh
$ /tmp/amdpilot-repo-j-52acf7d48c3e/venv/bin/python -m pytest -q tests/unit/test_typed_arith_ops.py tests/unit/test_arith_ops.py
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0
rootdir: /job/repo/tests
configfile: pytest.ini
plugins: hypothesis-6.150.2, anyio-4.14.2
collected 53 items

tests/unit/test_typed_arith_ops.py ...................................   [ 66%]
tests/unit/test_arith_ops.py ..................                          [100%]

============================== 53 passed in 0.89s ==============================
```
