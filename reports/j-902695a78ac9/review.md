# Independent review of PR 572 for issue 453

- Upstream issue: https://github.com/ROCm/FlyDSL/issues/453
- Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/589
- Candidate: https://github.com/amdpilot-org/FlyDSL/pull/572
- Exact candidate commit: `8e565f0acdfded2ad7aa918e9cd072f909f12cb8`
- Prepared base: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`
- Recommendation: **request changes**
- Full original-issue resolution: **no**

## Conclusion

The candidate is a meaningful partial fix. It resolves the prepared-base stale reuse for the current `compile_pa_decode_tile` factory when its directly referenced `cdiv` helper is rebound. It also passes its focused regressions for direct globals, direct object/module attributes, and direct closure cells.

It does not implement general dependency-aware invalidation as claimed. Independent compile-artifact simulations found two stale-wrapper counterexamples:

1. For `container.fn()`, dependency discovery records the attribute path but does not traverse the function stored at that path. If that function keeps its identity and bytecode while one of its closure cells changes, the factory returns the old wrapper and old compiled value.
2. Dependency references are computed once when the decorator is created. Rebinding a root helper invalidates once, but if the replacement helper introduces a new dependency, later changes to that dependency are invisible and reuse the old wrapper.

These are tied directly to iterative helper editing and the original contract, not an unrelated smoke. The candidate should therefore be described as a partial fix and should not be accepted as fully resolving the original issue until the dependency graph is traversed through attribute targets and refreshed after dependency rebinding, with regressions for both cases.

## Reproduction and validation

On the prepared base, `/job/review-evidence-j-902695a78ac9/repro_pa_factory.py --expect stale` showed that the same static PA signature returned the identical cached wrapper after `cdiv` was replaced. The sentinel appeared only after `compile_pa_decode_tile.cache_clear()`.

At exact commit `8e565f0acdfded2ad7aa918e9cd072f909f12cb8`, the same reproducer with `--expect invalidated` observed the sentinel on the first repeated-signature call. The submitted focused suite passed 19 tests, and the complete unit suite passed 1102 tests with 17 skipped.

The independent adversarial script exited 1 as expected for review evidence. Its direct attribute-rebinding control passed, while both remaining counterexamples returned `same_wrapper=True` and the old captured value.

## Environment and native/GPU scope

Source imports were confirmed from `/job/repo/python/flydsl`; the native extension remained the pinned `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`. The candidate changes no C++ or LLVM source, so the prescribed native rebuild was not applicable.

One AMD Instinct MI350X was visible through Torch/ROCm 7.2. The repository PA module could not collect because `aiter` requires Triton >=3.6.0 while the prepared interpreter provides `3.5.1+rocm7.2.0.gita272dfa8`. No independent numerical GPU result is claimed by this review. The actual PA compile factory was still used for the failing-before/passing-candidate cache behavior.

Raw logs, scripts, import paths, revision records, and checksums are preserved outside the checkout under `/job/review-evidence-j-902695a78ac9`.
