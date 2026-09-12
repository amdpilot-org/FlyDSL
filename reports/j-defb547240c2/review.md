# Independent review of PR 623

Reviewed exact commit `bdd00893955ad9c5d33e3cca4891373456543860` against:

- Upstream issue: https://github.com/ROCm/FlyDSL/issues/453
- Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/625

Recommendation: **request changes**. The candidate is a meaningful partial fix, but it does not fully resolve the original helper-change contract.

The prepared base reproduced stale same-process wrapper reuse with `FLYDSL_RUNTIME_ENABLE_CACHE=0`. At the exact candidate, all six candidate regressions passed, the two PR 608 counterexamples independently passed, and the actual `compile_pa_decode_tile` factory observed a rebound `cdiv` sentinel on the first repeated-signature call.

Two independent cases still reused the identical cached wrapper:

1. Two closure-bearing helpers created from the same code object are referenced by one factory. `_dependency_refs` keys `visited_codes` only by code-object identity, so after traversing the first helper it skips the second helper's distinct closure cells.
2. A referenced helper's `__defaults__` is changed. `_snapshot` records callable identity and code bytes/constants but not `__defaults__` or `__kwdefaults__`.

These are retracing failures even where Python's live closure/default behavior makes the returned numerical value change; wrapper identity is the sentinel for whether a compile factory actually retraced.

No native source changed, so no native rebuild was applicable. Source imports used `/job/repo/python/flydsl`; native imports remained the prepared wheel at `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`. One assigned MI355X (`gfx950`) was available and passed a CPU-referenced Torch numerical sanity check, but the repository PA tests could not collect because prepared `aiter` requires Triton >=3.6.0 and the environment provides Triton 3.5.1. No PA numerical claim is made.

Raw evidence is preserved outside the checkout under `/job/review-evidence-j-defb547240c2/`.
