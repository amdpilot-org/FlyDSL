# Independent review of PR 496 for issue 453

- Upstream issue: https://github.com/ROCm/FlyDSL/issues/453
- Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/516
- Candidate: https://github.com/amdpilot-org/FlyDSL/pull/496
- Prepared base: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`
- Exact candidate head: `e1da223932da0393754cc3f60469506c834455d6`
- Required interpreter: `/tmp/amdpilot-repo-j-ecfd23473a74/venv/bin/python`
- Checkout used for imports: `/job/repo`
- Raw evidence and standalone repro sources: `/job/review-evidence-j-ecfd23473a74`

## Conclusion and recommendation

The candidate fixes the exact stale-reuse mechanism for the current paged-attention compile factory when a directly referenced global helper is rebound. On the prepared base, the same static signature returned the identical cached `compile_pa_decode_tile` wrapper after its `cdiv` helper was replaced; the sentinel appeared only after `cache_clear()`. At the exact candidate head, the first same-signature call after the helper replacement observed the sentinel, proving that the factory was retraced rather than reusing the old wrapper.

This is nevertheless only a subset of the candidate's stated general dependency behavior. Independent boundary tests showed that the new decorator does not invalidate when a helper is reached through an object/module attribute (`helpers.fn`) or captured in a closure cell. Both cases retained the identical cached wrapper after helper rebinding. In a real JIT wrapper, retaining that wrapper is the stale-artifact failure even though the lightweight Python test body's later dynamic call can see the new value.

Recommendation: **request changes before accepting this as a general fix**. Either track attribute and closure dependencies (and add regressions), or narrow the decorator documentation and PR claim explicitly to supported direct-global dependencies. For the exact direct-global pattern reported in issue 453 and used by the converted current PA factories, the candidate is effective.

## Source and change inspection

The historical `compile_pa_decode_ps` / `_load_q_fragments` pair from the issue snapshot is no longer present at the prepared base. The current `kernels.attention.pa_decode_fp8` path delegates to cached factories in `pa_decode_tile.py`, `pa_decode_swa.py`, and `pa_metadata.py`. The review therefore exercised the same original failure mode on the actual checked-out `compile_pa_decode_tile` implementation by rebinding its directly referenced `cdiv` helper.

The candidate adds a Python-only `flyc.dependency_lru_cache`, converts the current PA tile/SWA/metadata factories, adds one direct-global nested-body regression, and updates authoring documentation. It changes no C++ or LLVM source, so the prepared native rebuild command was not applicable. The loaded native extension remained the pinned image extension at `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`; Python imports were explicitly confirmed from `/job/repo/python/flydsl` at both revisions.

## Commands and results

All commands used `PYTHONPATH=/job/repo/python:/job/repo`, `FLYDSL_RUNTIME_ENABLE_CACHE=0`, and the private runtime cache `/job/private-cache-j-ecfd23473a74` where applicable.

1. Base same-process reproduction (exit 0):

   ```bash
   /tmp/amdpilot-repo-j-ecfd23473a74/venv/bin/python \
     /job/review-evidence-j-ecfd23473a74/repro_issue453.py --expect stale
   ```

   Result: `baseline_wrapper_id` and `second_wrapper_id` were identical; `same_signature_sentinel=not_observed`; after `compile_pa_decode_tile.cache_clear()`, `after_manual_cache_clear_sentinel=observed`.

2. Exact candidate checkout and import verification (exit 0):

   ```bash
   git fetch origin e1da223932da0393754cc3f60469506c834455d6
   git checkout --detach e1da223932da0393754cc3f60469506c834455d6
   /tmp/amdpilot-repo-j-ecfd23473a74/venv/bin/python -c \
     'import flydsl, flydsl.compiler as c; print(flydsl.__file__); print(c.__file__); print(c.dependency_lru_cache)'
   ```

   Result: HEAD exactly matched the requested SHA; imports resolved to `/job/repo/python/flydsl/...` and exposed the candidate decorator.

3. Candidate regression suite (exit 0):

   ```bash
   /tmp/amdpilot-repo-j-ecfd23473a74/venv/bin/python -m pytest \
     tests/unit/test_dependency_cache.py tests/unit/test_jit_cache_key_completeness.py -q
   ```

   Result: 16 passed.

4. Candidate same-process PA reproduction (exit 0):

   ```bash
   /tmp/amdpilot-repo-j-ecfd23473a74/venv/bin/python \
     /job/review-evidence-j-ecfd23473a74/repro_issue453.py --expect invalidated
   ```

   Result: `same_signature_sentinel=observed` on the first repeated signature after rebinding; no manual clear was needed.

5. Adversarial dependency forms (exit 1, expected review failure):

   ```bash
   /tmp/amdpilot-repo-j-ecfd23473a74/venv/bin/python \
     /job/review-evidence-j-ecfd23473a74/adversarial_dependency_cache.py
   ```

   Result: direct global rebinding invalidated correctly. Module/object-attribute rebinding and closure-cell rebinding both reported `same_wrapper=True`, producing two assertion failures.

6. Independent GPU numerical reference, run on both base and candidate (exit 0 at each revision):

   ```bash
   /tmp/amdpilot-repo-j-ecfd23473a74/venv/bin/python \
     /job/review-evidence-j-ecfd23473a74/gpu_pa_reference.py
   ```

   Result at each revision: real BF16 `pa_decode_tile` execution on one AMD Instinct MI350X, `gfx950:sramecc+:xnack-`; finite output; `max_abs_diff=0.0009765625` against an independent float32 PyTorch softmax/attention reference; unchanged `rtol=0.005`, `atol=0.005` passed.

7. Repository PA test collection (exit 0 with module skipped):

   ```bash
   /tmp/amdpilot-repo-j-ecfd23473a74/venv/bin/python -m pytest \
     tests/kernels/test_pa.py --collect-only -q -rs
   ```

   Result: the module was skipped because `aiter` requires Triton >= 3.6.0 while the prepared interpreter has `3.5.1+rocm7.2.0.gita272dfa8`. Torch/ROCm were not modified. The standalone direct-kernel numerical check above covers the current tile path, but aiter-dependent PS entrypoints remain unverified.

## Raw evidence

The complete terminal transcripts are retained outside the checkout so revision switches could not overwrite them:

- `base-repro.log` (SHA-256 `d22629c3ea4646049f68d4b1eaa63003bae9f6cadbcd949004f784b116004606`)
- `candidate-repro.log` (SHA-256 `864381699ec415fd43520982cd8e9416fbd935489a8db7b2976dbf0572428163`)
- `candidate-unit-tests.log` (SHA-256 `78ff2323e604dfd9343bd52c34052abdeabc7b9484a547537199b3e0592866a4`)
- `candidate-adversarial.log` (SHA-256 `4aff7a497fb2300baaaaa411ff308e2572341790690a3ef56517b6d224107841`)
- `base-gpu-pa.log` (SHA-256 `4885212ab6b14e6852b694bb4f5486030274f1645a813e8b8cb2a8eddb51f9de`)
- `candidate-gpu-pa.log` (SHA-256 `68c0a02bf9ca935a1e21c78d7b027819553d79a28f1ae76d22e10553b929ca2a`)
- `gpu-environment.log` (SHA-256 `824b35245bd27fab8a68a7e5feb5b77af67ccae12f0683631ba669338e59b63d`)
- `pa-test-collection.log` (SHA-256 `f4e5783449ce952c985ffb1cdbd521646fb9e2bf2a39c89cae0fb91226701549`)

No candidate files were copied into the delivery branch, and the candidate PR was neither modified nor merged.
