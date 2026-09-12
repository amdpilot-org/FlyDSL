# Independent review of candidate PR 492

- Upstream issue: https://github.com/ROCm/FlyDSL/issues/770
- Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/521
- Prepared base: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`
- Candidate head: `60273a666ee45369fd0b0548117c27afbb9daa9c`

## Recommendation

Accept the candidate as a correct fix for a real subset of the umbrella issue: selected post-search and winner-cache executions now apply `Config.pre_hook`, the tuner `pre_hook`, and the tuner `post_hook` in the same successful-call order as benchmark repetitions. Do not treat this candidate alone as completing issue 770: the source issue remains open and its offline-artifact, broad-CI opt-out, and documentation acceptance items are outside this patch.

No blocking defect was found in the candidate. The implementation is small and preserves accepted-artifact failure propagation: hook or kernel failures are not caught by `_run_config` and therefore cannot silently retry a default.

## Independent reproduction

The review used the prepared interpreter `/tmp/amdpilot-repo-j-ee0e81ef74d4/venv/bin/python`, set `PYTHONPATH=/job/repo/python`, and kept autotune caches under `/job/review-evidence-j-ee0e81ef74d4/`. Import evidence identified `flydsl` and `flydsl.autotune` under `/job/repo/python`. The assigned GPU was AMD Instinct MI355X, `gfx950:sramecc+:xnack-`.

On the prepared base:

```text
PYTHONPATH=/job/repo/python \
FLYDSL_AUTOTUNE_CACHE_DIR=/job/review-evidence-j-ee0e81ef74d4/base-cache-corrected \
/tmp/amdpilot-repo-j-ee0e81ef74d4/venv/bin/python -m pytest -q \
  /job/review-evidence-j-ee0e81ef74d4/test_candidate_hooks.py
```

Result: exit 1, 3 failed. The direct regression returned `1` rather than `13`; the reset/pre-hook boundary returned `64.0` rather than `71`; and a cached failing call recorded only `kernel`, proving its pre-hook was skipped.

At exact candidate head `60273a666ee45369fd0b0548117c27afbb9daa9c`, the same command with the candidate cache directory exited 0 with 3 passed. These independent cases cover forced search followed by selected execution, a non-searching winner-cache hit, reset-before-pre-hook ordering, return-value preservation, and failure propagation without a post-hook after an unsuccessful kernel call.

## Additional candidate validation

```text
/tmp/amdpilot-repo-j-ee0e81ef74d4/venv/bin/python -m pytest -q tests/unit/test_autotune.py
```

Result: exit 0, 56 passed.

```text
FLYDSL_AUTOTUNE=0 /tmp/amdpilot-repo-j-ee0e81ef74d4/venv/bin/python -m pytest \
  tests/unit/test_softmax_autotune.py \
  tests/kernels/test_softmax_autotune.py::test_workgroup_size_tracks_block_threads \
  tests/kernels/test_softmax_autotune.py::test_wrapper_matches_the_torch_reference \
  tests/kernels/test_softmax_autotune.py::test_default_serves_without_searching_on_the_current_stream \
  tests/kernels/test_softmax_autotune.py::test_compiled_cache_hit_bypasses_resolution_and_accepts_new_buffers_and_stream \
  tests/kernels/test_rmsnorm_autotune.py::test_rmsnorm_autotuned_default_uses_current_stream_and_skips_search -v
```

Result: exit 0, 52 passed. The device tests executed real Softmax and RMSNorm kernels on the assigned MI355X/gfx950 and included Torch-reference comparisons plus current-stream/cache behavior. No tolerance was changed.

## Native and architecture limits

The candidate modifies only `python/flydsl/autotune.py` and a Python test/report; it has no C++ or LLVM change, so the prepared native rebuild command was not applicable. The unchanged native compiler/runtime remained the image-pinned installation. GPU behavior was verified only on the assigned gfx950 device; other architectures were not available.

Raw outputs and the independent regression remain outside the checkout in `/job/review-evidence-j-ee0e81ef74d4/`.
