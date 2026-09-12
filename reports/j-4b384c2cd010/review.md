# Independent review of PR 652

Candidate: https://github.com/amdpilot-org/FlyDSL/pull/652

Exact commit: `84e026797bbce124b3a207b1c5736c3cea256073`

Upstream issue: https://github.com/ROCm/FlyDSL/issues/453

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/655

## Recommendation

Request changes. The candidate is a substantive partial fix, not test-only
hardening: it fixes the original paged-attention helper-rebinding path and the
three concrete failures inherited from the PR 640 review. It does not fully
satisfy the more general helper-change contract stated by the original issue.

## Findings

1. Mutable state reached through a helper's default object is reduced to object
   identity and remains stale. `_snapshot` recursively snapshots built-in
   containers, but its fallback for a custom object is `(type(value),
   id(value))`. In the independent reproducer, a helper defaulted to
   `SimpleNamespace(value="v1")`; changing that visible value to `"v2"` left
   the dependency snapshot unchanged. The factory returned the identical old
   wrapper and its captured result remained `"v1"`.

2. Callable helper instances are not traversed through `__call__` and their
   state is also reduced to identity. In the independent reproducer, changing
   `helper.value` from `"v1"` to `"v2"` left both the callable snapshot and
   dependency graph unchanged. The identical old wrapper was returned with
   the old captured result.

These are not failures of unrelated disk caching: every cache test used
`FLYDSL_RUNTIME_ENABLE_CACHE=0`, ran in one process, and asserted wrapper
identity plus the captured result.

## Verified behavior

- The recorded base commit reproduces stale in-process reuse in the current
  paged-attention factory. Rebinding `pa_decode_tile.exp2_f32_fast` returns the
  identical `compile_pa_decode_tile` wrapper; explicit `cache_clear()` returns
  a new wrapper.
- At the exact candidate, the same paged-attention helper rebind automatically
  returns a new wrapper.
- The candidate passes its nine dependency-cache regressions.
- Independent checks pass for ordinary helper rebinding, two helpers sharing
  one code object but distinct closure cells, `__defaults__` replacement, and
  `__kwdefaults__` mutation.
- The focused cache suites pass (24 tests), and the full unit suite passes
  (1,107 passed, 17 skipped).

## Environment and limitations

Python sources were imported from `/job/repo/python` and the paged-attention
modules from `/job/repo/kernels`. The native extension loaded from
`/job/repo/python/flydsl/_mlir/_mlir_libs/_mlir.cpython-312-x86_64-linux-gnu.so`.
The candidate changes no C++/LLVM source, so a native rebuild was not
applicable.

One assigned AMD Instinct MI350X (`gfx950`) executed a Torch matrix multiply;
comparison against a CPU float64 reference produced
`max_abs_diff=1.1444091796875e-05`. This confirms the GPU environment only and
is not used as proof of the Python cache behavior. The exact issue-era
`compile_pa_decode_ps` symbol and supplied script are absent from the recorded
base, so the repository-level reproduction used its current replacement,
`compile_pa_decode_tile`. It validates compile-factory wrapper invalidation but
does not claim an end-to-end PA numerical launch.

Raw commands and output are retained outside the revision-switching checkout
at `/job/review-evidence-j-4b384c2cd010/`.
