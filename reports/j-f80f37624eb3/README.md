# Independent review of candidate PR 498 for issue 510

Upstream issue: https://github.com/ROCm/FlyDSL/issues/510

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/518

Prepared base: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`

Candidate head: `f6910a2058dd6eea405d30ecd4f23acf3c7b8d34`

## Recommendation

Do not accept the candidate as a fix for the original issue. The candidate is a
report-only commit: its diff adds seven files under `reports/j-bf3c6b11071c/`
and changes no implementation or regression test. Base and candidate therefore
have identical PA SWA behavior.

The exact historical test named by the issue cannot be run from either revision:
`tests/kernels/test_pa_swa.py` and its `global_window_accuracy` node do not exist,
and the current PA SWA API has no `global_window` argument. This was verified on
the actual base before checking out the exact candidate head, where the same
pytest node exits 4 during collection.

The closest current implementation was tested on the assigned MI350X (`gfx950`)
with every reported numerical parameter except the unavailable
`global_window=3`. With the Gluon comparison disabled because the installed
Gluon/Triton combination fails compilation before FlyDSL runs, the FlyDSL GPU
kernel passed the independent Torch reference at the repository's unchanged
sliding-window tolerance (`atol=rtol=5e-2`). Four adversarial cases around the
1023/1024 sliding-window and physical-page boundaries also passed. These are
useful current-path checks, but they are not evidence that the historical
`ExtUIOp` failure is fixed: the current implementation uses a different pointer
addressing design and does not contain `_widen_nonnegative_i32_to_i64`.

No native rebuild was required or performed because candidate PR 498 has no C++
changes. The prepared pinned native library was used, and Python imports were
confirmed to come from `/job/repo` on both revisions. The extension module's
namespace package reports `__file__` as `None`; the prepared environment records
the native library at `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`.

## Commands and results

- Exact base regression node:
  `HIP_VISIBLE_DEVICES=0 FLYDSL_RUNTIME_ENABLE_CACHE=0 PYTHONPATH=/job/repo/python:/job/repo /tmp/amdpilot-repo-j-f80f37624eb3/venv/bin/python -m pytest -q 'tests/kernels/test_pa_swa.py::test_multi_case_set[global_window_accuracy]' -s`
  — exit 4, file not found.
- Exact candidate regression node: same command at candidate head — exit 4,
  file not found.
- Closest current GPU case: direct call to `run_pa_decode_ps_test` with FP8
  e4m3fn, per-token KV, transposed V, fixed KV length, partition 256, page 1024,
  heads `(12, 2)`, context 3000, batch 128, query length 4, head size 128, and
  sliding window 1023 — exit 0, `FlyDSL PS vs Torch PASSED`.
- Boundary matrix: `(context_length, sliding_window)` values `(3000, 1022)`,
  `(3000, 1024)`, `(1024, 1023)`, and `(1025, 1023)`, otherwise retaining the
  relevant FP8/layout/head/query settings and using batch 16 — exit 0, all four
  passed the Torch reference.
- Running the repository script without disabling Gluon — exit 1 in Gluon
  compilation with `invalid intrinsic shape`; this happened before the FlyDSL
  comparison and is retained as dependency evidence, not called a product
  failure.

Raw command output, import paths, GPU identification, source searches, and the
complete candidate diff are retained in `raw/`.
