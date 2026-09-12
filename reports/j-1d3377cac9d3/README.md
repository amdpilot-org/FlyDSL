# Independent review of ROCm linker discovery candidate

Upstream issue: https://github.com/ROCm/FlyDSL/issues/946

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/645

Candidate PR: https://github.com/amdpilot-org/FlyDSL/pull/644

Candidate commit: `cace24273ede0742f57b4ef6d716485384721a9b`

Recorded base: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`

## Recommendation

Request changes. The candidate is a real partial fix: it resolves the reported
space-containing alternate-toolkit counterexample and adds deterministic
discovery and useful explicit-root diagnostics. It does not fully satisfy its
broader path-handling claim in the actual compiler path.

On the recorded base, setting `ROCM_PATH` to a private incomplete root caused
the real vector-add compilation to fail in `gpu-module-to-binary` with only
`lld invocation failed` (exit 1). On the exact candidate, a valid private ROCm
root containing a space compiled and executed vector add on gfx950, with maximum
error `0.00e+00` against the test's independent Torch `a + b` reference. The
same run exercised ISA dumping; the 4,227-byte ISA names gfx950 and
`vecAddKernel_0` and contains `s_endpgm` and AMDHSA kernel metadata.

The candidate's unit test only proves that quote- and backslash-containing
values parse as textual pass options. Independent real-compilation tests used
otherwise valid private toolkit roots (symlinks to the real linker and device
libraries) and found that a root containing a double quote fails with
`lld invocation failed`; a root containing a backslash fails identically. Thus
the parser-only assertions are not proof that these paths reach `ld.lld`
correctly.

An additional process-local `PATH` case placed a working `ld.lld` symlink in an
arbitrary private bin directory. `shutil.which` found that linker, but candidate
discovery ignored it because it was not lexically under `llvm/bin` and selected
`/opt/rocm` instead. The candidate supports a private PATH layout only when it
already has the exact `<toolkit>/llvm/bin/ld.lld` shape.

## Validation performed

- Base reproduction: `ROCM_PATH=/tmp/amdpilot-repo-j-1d3377cac9d3/fixtures/missing-root FLYDSL_RUNTIME_CACHE_DIR=/tmp/amdpilot-repo-j-1d3377cac9d3/base-cache /tmp/amdpilot-repo-j-1d3377cac9d3/venv/bin/python -m pytest 'tests/kernels/test_vec_add.py::test_benchmark_vector_add[4]' -q -s --tb=short` — exit 1, actual serializer failure `lld invocation failed`.
- Candidate focused tests: `/tmp/amdpilot-repo-j-1d3377cac9d3/venv/bin/python -m pytest tests/unit/test_rocm_toolkit_discovery.py tests/unit/test_external_llvm_codegen.py -q` — 19 passed.
- Candidate space-path GPU test: `FLYDSL_ROCM_TOOLKIT_PATH='<private valid toolkit with space>' FLYDSL_DUMP_IR=1 ... python -m pytest 'tests/kernels/test_vec_add.py::test_benchmark_vector_add[4]' -q -s --tb=short` — exit 0, max error `0.00e+00`, gfx950 ISA emitted.
- Candidate quote-path GPU test using a valid private root — exit 1, `lld invocation failed`.
- Candidate backslash-path GPU test using a valid private root — exit 1, `lld invocation failed`.
- Candidate discovery checks — explicit-root precedence, MLIR-layout PATH discovery, missing-linker diagnostic, and nonexecutable-linker diagnostic passed; arbitrary private-bin PATH linker was found by `shutil.which` but ignored in favor of `/opt/rocm`.
- Candidate full unit suite: `/tmp/amdpilot-repo-j-1d3377cac9d3/venv/bin/python -m pytest tests/unit -q` — 1,106 passed, 17 skipped.

Complete raw command output is retained outside the revision-switched checkout
at `/job/review-evidence-j-1d3377cac9d3/`. Compiler dumps are retained at
`/tmp/amdpilot-repo-j-1d3377cac9d3/candidate-space-dump-v2/`.

## Environment and limitations

Repository Python sources loaded from `/job/repo/python/flydsl`. The native
extension resolved to the prepared pinned-wheel artifact at
`/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/_mlir.cpython-312-x86_64-linux-gnu.so`
through the prepared repository import path. The candidate changes Python only,
so no native rebuild was required.

GPU execution used one AMD Instinct MI350X (`gfx950`) with Torch
`2.9.1+rocm7.2.0.git7e1940d4` and HIP/ROCm 7.2. The issue's gfx1250/ROCm 6
environment is unavailable, so execution and exact layout compatibility there
remain unverified. This limitation is not treated as evidence for or against a
source change.
