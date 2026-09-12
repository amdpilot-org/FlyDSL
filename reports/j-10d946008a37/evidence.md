# Independent review of PR 490 for duplicate ROCDL targets

Upstream issue: https://github.com/ROCm/FlyDSL/issues/1054

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/513

Prepared base: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`

Candidate head: `6661f060ec2dc0656cf4e67023a826d0827eb7f9`

Python: `/tmp/amdpilot-repo-j-10d946008a37/venv/bin/python`

Python source import: `/job/repo/python/flydsl/__init__.py`

Native bindings: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`

Raw evidence: `/job/review-evidence-j-10d946008a37/`

## Recommendation

Approve the candidate for the reported defect. The base reproduced the issue,
and the exact candidate fixes it across default, fast-only, unsafe-only, and
combined compile-hint cases. It also passes real GPU execution and focused
neighboring tests. The candidate changes Python only, so rebuilding the native
C++ library was not required.

## Base reproduction

On the untouched prepared base:

```text
ARCH=gfx1201 COMPILE_ONLY=1 FLYDSL_RUNTIME_ENABLE_CACHE=0 \
REVIEW_FAST=1 REVIEW_UNSAFE=1 \
REVIEW_IR=/job/review-evidence-j-10d946008a37/base-gfx1201-both.mlir \
/tmp/amdpilot-repo-j-10d946008a37/venv/bin/python \
/job/review-evidence-j-10d946008a37/review_duplicate_targets.py
```

Exit code: `1` (the strict one-object regression failed).

```text
gpu_objects=2
explicit_handler=False
target[0]=#rocdl.target<chip = "gfx1201">
target[1]=#rocdl.target<chip = "gfx1201", flags = {fast, no_wave64, unsafe_math}>
review_expectation=FAIL
```

This directly reproduces the original report: a bare first object and a second
object carrying the requested compile hints, with no explicit handler.

## Exact candidate review

After `git switch --detach 6661f060ec2dc0656cf4e67023a826d0827eb7f9`,
imports still resolved to `/job/repo/python/flydsl`. The same strict script was
run for four adversarial `gfx1201` combinations. All exited zero and emitted
exactly one object:

| Hints | Sole target flags |
|---|---|
| neither | `no_wave64` |
| fast only | `fast, no_wave64` |
| unsafe only | `no_wave64, unsafe_math` |
| fast and unsafe | `fast, no_wave64, unsafe_math` |

The candidate regression itself passed:

```text
/tmp/amdpilot-repo-j-10d946008a37/venv/bin/python -m pytest -q \
tests/unit/test_compile_hints.py::TestCompileHintsPropagation::test_fp_math_reaches_the_only_serialized_gpu_object
```

Result: `1 passed`.

Focused neighboring coverage passed:

```text
/tmp/amdpilot-repo-j-10d946008a37/venv/bin/python -m pytest -q \
tests/unit/test_compile_hints.py tests/unit/test_external_llvm_codegen.py \
tests/unit/test_compile_backends.py tests/unit/test_pointer_argument_vec_add.py
```

Result: `30 passed, 2 skipped`. The skips are pre-existing marked tests in the
compile-hints suite.

## GPU and compiler evidence

An independently written vector-add test executed 4,103 FP32 elements on the
assigned AMD Instinct MI350X (`gfx950:sramecc+:xnack-`). Its CPU-side PyTorch
reference was compared with `rtol=0, atol=0`; maximum absolute error was `0.0`.
The final `gpu.binary` contained exactly one object with
`#rocdl.target<chip = "gfx950", flags = {fast, unsafe_math}>`.

The emitted ISA states
`.amdgcn_target "amdgcn-amd-amdhsa-unknown-gfx950"` and contains
`global_load_dword`, `v_add_f32_e32`, `global_store_dword`, and `s_endpgm`.
Raw pipeline IR, LLVM IR, ISA, and command output are retained under the raw
evidence directory.

## Limitations

The reported `gfx1201` architecture was validated compile-only because the
assigned device is `gfx950`; execution on `gfx1201` remains unverified. MLIR
canonicalizes default-valued target options out of printed attributes, so the
non-default hint flags and object count are directly visible while default
values such as `O=2`, `abi=600`, `correct-sqrt=true`, and `daz=false` are
verified from the unchanged backend pipeline construction. Public upstream
issue JSON was retained; authenticated `gh issue view` was blocked by the ROCm
organization's fine-grained-token lifetime policy.
