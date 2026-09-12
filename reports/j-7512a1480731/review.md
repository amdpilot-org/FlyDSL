# Independent review of candidate PR 501

Upstream issue: https://github.com/ROCm/FlyDSL/issues/688

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/526

Candidate: https://github.com/amdpilot-org/FlyDSL/pull/501

## Verdict

Candidate commit `135c348c82288d8362df74d859a56e9c8862ab1a` is verified for the concrete dynamic `for ... else` defect it identifies. On prepared base `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`, the candidate's unchanged GPU regression failed for both zero-trip and three-trip loops because the `else` suite was dropped. At the exact candidate head, those cases and seven independent adversarial cases passed with exact integer comparisons.

Recommendation: accept the candidate as a correct fix for this subset. Do not treat it as exhaustive closure of the broadly worded source issue: unsupported `break`/`continue` behavior and other unenumerated AST-rewriter risks were not verified by this patch or review.

## Checkout and import verification

- Prepared delivery branch and base: `amdpilot/j-7512a1480731` at `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`.
- Candidate fetched from `refs/pull/501/head`; fetched and checked-out SHA matched `135c348c82288d8362df74d859a56e9c8862ab1a`.
- Python imports resolved to `/job/repo/python/flydsl` and `/job/repo/python/flydsl/compiler/ast_rewriter.py` while each revision was checked out.
- `python/flydsl/_mlir` resolved to the prepared pinned native library at `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`.
- No native rebuild was needed: the candidate changes only Python AST rewriting and tests, with no C++ or native compiler source changes.

## Tests and evidence

All commands used `/tmp/amdpilot-repo-j-7512a1480731/venv/bin/python` and one assigned device via `ROCR_VISIBLE_DEVICES=0 HIP_VISIBLE_DEVICES=0 CUDA_VISIBLE_DEVICES=0`.

1. Base reproduction, running the candidate regression unchanged from outside the checkout:

   `FLYDSL_RUNTIME_ENABLE_CACHE=0 FLYDSL_RUNTIME_CACHE_DIR=/tmp/amdpilot-repo-j-7512a1480731/cache-base python -m pytest -q -s /job/review-evidence-j-7512a1480731/candidate_regression.py`

   Exit 1: 3 passed and 2 failed. Both `for ... else` cases produced stale scalar/vector values for `n=0` and `n=3`. Raw output: `/job/review-evidence-j-7512a1480731/base-candidate-regression.txt`.

2. Exact candidate regression plus independent adversarial cases:

   `FLYDSL_RUNTIME_ENABLE_CACHE=0 FLYDSL_RUNTIME_CACHE_DIR=/tmp/amdpilot-repo-j-7512a1480731/cache-candidate python -m pytest -q -s /job/review-evidence-j-7512a1480731/candidate_regression.py /job/review-evidence-j-7512a1480731/adversarial_for_else.py`

   Exit 0: 12 passed. The seven added cases cover negative, zero, one, and four trip bounds; a value defined only in the `else` suite; a direct output side effect; dependence on the final loop-carried value; and nested dynamic `for ... else` with zero and nonzero inner/outer trip counts. Expected values were independently calculated and checked with `rtol=0, atol=0`. Raw output: `/job/review-evidence-j-7512a1480731/candidate-regression-adversarial.txt`.

3. Focused control-flow suite plus adversarial cases:

   `python -m pytest -q -s tests/system/test_control_flow_independent_refs_e2e.py tests/system/test_if_liveout_minimal.py tests/system/test_for_vector_carry_shape_e2e.py tests/system/test_control_flow_compile.py tests/system/test_for_auto_iter_args_e2e.py tests/unit/test_for_dispatch_paths.py tests/unit/test_for_auto_iter_args.py tests/unit/test_while_dispatch_paths.py /job/review-evidence-j-7512a1480731/adversarial_for_else.py`

   Exit 0: 45 passed. Raw output: `/job/review-evidence-j-7512a1480731/candidate-focused-suite.txt`.

4. Compiler and ISA evidence from a nested nonzero-trip adversarial case:

   `FLYDSL_DUMP_IR=1 FLYDSL_DUMP_DIR=/job/review-evidence-j-7512a1480731/ir-final python -m pytest -q -s '/job/review-evidence-j-7512a1480731/adversarial_for_else.py::test_nested_for_else_observes_each_final_carried_value[2-3-24]'`

   Exit 0: 1 passed on an AMD Instinct MI355X (`gfx950`). `00_origin.mlir` contains two nested `scf.for` operations with loop-carried `i32` iter args and `scf.yield`; `21_final_isa.s` targets `amdgcn-amd-amdhsa-unknown-gfx950` and contains scalar arithmetic plus `global_store_dword`. Artifacts: `/job/review-evidence-j-7512a1480731/ir-final/_nested_kernel_0/`.

5. `git diff --check acf7e67b7d22847e345938ca54fcc137bd7b2a1f..135c348c82288d8362df74d859a56e9c8862ab1a` and Python `compileall` both exited 0.

## Limitations

Testing covered the available `gfx950` architecture only. Dynamic loop `break`/`continue` is outside the supported transformation described by the candidate and was not verified. The issue provides no specific reproducer beyond a broad request to discover AST-rewriter risks; consequently this review verifies the demonstrated `for ... else` defect and relevant boundaries, not every possible internal control-flow mutation.
