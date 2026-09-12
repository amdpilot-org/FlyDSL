# FlyDSL platform qualification: j-1db274d57e01

This report qualifies the prepared FlyDSL source checkout on the assigned AMD
GPU. It is a platform qualification record, not a claim that a FlyDSL issue has
been fixed.

## Prepared source and environment

- Source: `amdpilot-org/FlyDSL` at base commit
  `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`
- Branch: `amdpilot/j-1db274d57e01`
- Prepared checkout: `/job/repo`
- Prepared interpreter:
  `/tmp/amdpilot-repo-j-1db274d57e01/venv/bin/python`
- Prepared native module: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`
- GPU: AMD Instinct MI355X (one assigned device)
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`
- HIP: `7.2.26015-fc0010cf6a`

## Early GPU smoke

A simple Torch numerical operation on the assigned GPU passed:

```text
device=AMD Instinct MI355X
result=1576448.0 expected=1576448.0 match=True
```

This only establishes basic GPU execution.

## Native rebuild qualification

Command (exit code `0`):

```text
/tmp/amdpilot-repo-j-1db274d57e01/venv/bin/python /opt/amdpilot/rebuild-native.py /job
```

The rebuild passed in `46.745190432993695` seconds using the `amd-minimal`
profile and LLVM hash `e2a39f504fee836e4def9581bed817ecc327b9dc`.
The rebuilt native tree is:

```text
/tmp/amdpilot-repo-j-1db274d57e01/native-build/python_packages/flydsl/_mlir
```

The rebuild tool's real numerical GPU smoke also passed:

```text
operation=FlyDSL vector_add 100x1000 (predicated border blocks)
gpu=AMD Instinct MI355X
arch=gfx950
device_count=1
wall_s=1.2945506909163669
```

The complete rebuild record is retained at `/job/native-build.json` in the
job artifacts. After switching to the rebuild, resolved imports included:

```text
flydsl=/job/repo/python/flydsl/__init__.py
native=/job/repo/python/flydsl/_mlir/_mlir_libs/_mlir.cpython-312-x86_64-linux-gnu.so
torch=/opt/venv/lib/python3.12/site-packages/torch/__init__.py
```

The repository-side native paths are linked to the rebuilt native tree by the
prepared rebuild workflow.

## Focused unit suite

Command (exit code `0`):

```text
/tmp/amdpilot-repo-j-1db274d57e01/venv/bin/python -m pytest tests/unit
```

Measured result:

```text
1098 passed, 17 skipped, 2 warnings in 7.39s
```

## Limitations

- This qualification did not attempt the repository's broader test suites.
- Seventeen unit tests were skipped by their existing test conditions.
- Two warnings concerned Python `int` annotations in dynamic shared-memory
  tests; they did not fail the suite.
- No upstream repository was modified, and this PR is not evidence that the
  surrounding host receipt-delivery platform succeeded.

## Platform context

- https://github.com/amdpilot-org/amdpilotv2/pull/410
- https://github.com/amdpilot-org/amdpilotv2/pull/435
