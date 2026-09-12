# Independent review of PR 618

Reviewed candidate: https://github.com/amdpilot-org/FlyDSL/pull/618

Exact commit: `2582321e975d839edb5f0fd01450e78e72bec065`

Upstream issue: https://github.com/ROCm/FlyDSL/issues/1016

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/621

## Verdict

Recommendation: **accept** as a scoped documentation and regression-test
hardening contribution. It does **not** fully resolve the broad original issue.

The prepared base already contained the BlockScan implementation and passed its
62 existing GPU tests plus the stream-compaction example. The base did not have
the public `docs/extension/coop_scan.md` on-ramp. At the exact candidate commit,
the new documentation correctly puts `fx.barrier()` between consecutive
collectives that reuse shared storage, explicitly says the contribution is not
a complete collective library, and the focused suite grows to 64 passing tests.

Independent adversarial validation used three 128-thread blocks, signed
non-monotonic int32 inputs, both inclusive and exclusive forms in the same
kernel, the same shared storage with the documented intervening barrier, and
host `torch.cumsum` references. This passed and exercised both sides of wave64
boundaries and block-local restart behavior. The full cooperative suite (326
tests) and the real GPU stream-compaction example also passed.

The candidate changes no FlyDSL implementation or native C++ code, so it is
best classified as test-only/documentation hardening of an already-present
scoped BlockScan contribution. A native rebuild was therefore not applicable.
Python source imports resolved from `/job/repo/python`; the prepared native
extension remained the pinned wheel.

## Limitations and remaining counterexamples

- The upstream proposal asks for a broad library of common GPU building blocks.
  This candidate only documents and strengthens validation of block-wide prefix
  scan, so the original issue remains open beyond that scope.
- Only the assigned AMD Instinct MI355X (`gfx950:sramecc+:xnack-`, wave64) was
  available. Wave32 and other listed architectures remain unverified.
- BlockScan still has its documented power-of-two block-size,
  full-participation, `WARP_SCANS`, and ADD/MUL/MIN/MAX limitations.
- PR 618's historical body and committed reports refer to mirror issue 604,
  whereas this independent review is assigned mirror issue 621. This is a
  provenance mismatch, not evidence of a GPU correctness defect.
- Raw command output and the external adversarial harness were preserved under
  `/job/review-evidence/` while revisions were switched.
