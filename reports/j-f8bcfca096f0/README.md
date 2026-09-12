# Independent review of early-return control-flow check

Upstream issue: https://github.com/ROCm/FlyDSL/issues/687

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/524

Candidate reviewed: https://github.com/amdpilot-org/FlyDSL/pull/502 at
`bdbb5574cae5fb9e16febb6dc960c63a6e1bec0c`

Prepared base: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`

## Recommendation

Accept the candidate for the issue's requested safety check. On the prepared
base, an early `return` in a runtime `if` returned only from the outlined region:
an independent gfx950 GPU regression expected `[3]` but observed `[9]` after the
store following the apparent return executed. The same base also accepted
returns in runtime `if`, `for`, and `while` constructs without a diagnostic.

At the exact candidate commit, the independent regression instead received a
source-located `SyntaxError` before GPU launch, and adversarial checks confirmed
the diagnostic for runtime `if`, `for`, and `while`. Compile-time `const_expr`
returns and returns belonging to a nested Python function remained valid. The
candidate's own focused unit tests and GPU system tests passed, as did the full
unit suite.

This is a diagnostic fix, not an implementation of divergent function exit:
users must restructure runtime control flow. That limitation is consistent with
the feature request to prevent silently incorrect output or crashes.

## Environment and imports

- Python: `/tmp/amdpilot-repo-j-f8bcfca096f0/venv/bin/python`
- Python package: `/job/repo/python/flydsl/__init__.py`
- AST implementation: `/job/repo/python/flydsl/compiler/ast_rewriter.py`
- MLIR Python module: `/job/repo/python/flydsl/_mlir/ir.py`
- Native extension directory: `/job/repo/python/flydsl/_mlir/_mlir_libs`
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`; HIP: `7.2.26015-fc0010cf6a`
- GPU: AMD Instinct MI350X, `gfx950:sramecc+:xnack-`

No native rebuild was performed: the candidate modifies only
`python/flydsl/compiler/ast_rewriter.py` and tests/reports, with no C++ or native
extension changes.

## Commands and results

All commands were run from `/job/repo`, with raw logs retained under
`/job/review-evidence-j-f8bcfca096f0/`.

1. Base independent regression:

   ```text
   ROCR_VISIBLE_DEVICES=0 HIP_VISIBLE_DEVICES=0 FLYDSL_RUNTIME_ENABLE_CACHE=0 \
     /tmp/amdpilot-repo-j-f8bcfca096f0/venv/bin/python -m pytest -q -s \
     /job/review-evidence-j-f8bcfca096f0/test_independent_early_return.py
   ```

   Exit 1: 4 failed, 3 passed. GPU expected `[3]`, observed `[9]`; dynamic
   `if`/`for`/`while` returns produced no `SyntaxError`.

2. Candidate focused unit regression:

   ```text
   /tmp/amdpilot-repo-j-f8bcfca096f0/venv/bin/python -m pytest -q -s \
     tests/unit/test_early_return_control_flow.py
   ```

   Exit 0: 6 passed.

3. Candidate GPU system regression:

   ```text
   ROCR_VISIBLE_DEVICES=0 HIP_VISIBLE_DEVICES=0 FLYDSL_RUNTIME_ENABLE_CACHE=0 \
     /tmp/amdpilot-repo-j-f8bcfca096f0/venv/bin/python -m pytest -q -s \
     tests/system/test_early_return_control_flow_e2e.py
   ```

   Exit 0: 2 passed. Exact integer comparisons used `rtol=0, atol=0`.

4. Independent candidate regression and boundary cases:

   ```text
   ROCR_VISIBLE_DEVICES=0 HIP_VISIBLE_DEVICES=0 FLYDSL_RUNTIME_ENABLE_CACHE=0 \
     /tmp/amdpilot-repo-j-f8bcfca096f0/venv/bin/python -m pytest -q -s \
     /job/review-evidence-j-f8bcfca096f0/test_independent_early_return.py
   ```

   Exit 0: 7 passed. The original unsafe kernel was rejected during AST
   transformation, and runtime `if`/`for`/`while`, `const_expr`, nested-function,
   and checkout-import boundaries passed.

5. Candidate full unit suite:

   ```text
   /tmp/amdpilot-repo-j-f8bcfca096f0/venv/bin/python -m pytest -q tests/unit
   ```

   Exit 0: 1104 passed, 17 skipped.

6. Candidate GPU test with compiler artifacts:

   ```text
   ROCR_VISIBLE_DEVICES=0 HIP_VISIBLE_DEVICES=0 FLYDSL_RUNTIME_ENABLE_CACHE=0 \
     FLYDSL_DUMP_IR=1 \
     FLYDSL_DUMP_DIR=/job/review-evidence-j-f8bcfca096f0/candidate-ir \
     /tmp/amdpilot-repo-j-f8bcfca096f0/venv/bin/python -m pytest -q -s \
     tests/system/test_early_return_control_flow_e2e.py
   ```

   Exit 0: 2 passed. Dumps include origin MLIR, all lowering stages, LLVM IR,
   and final gfx950 ISA (`21_final_isa.s`) for both compiled kernels.

## Limitations

Only the assigned AMD Instinct MI350X/gfx950 architecture was tested. Other GPU
architectures and operating systems remain unverified. The issue asks for a
guard against invalid code; the candidate deliberately rejects runtime early
return rather than implementing its semantics.
