# Independent review of PR 619

Upstream issue: https://github.com/ROCm/FlyDSL/issues/400

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/622

Candidate: https://github.com/amdpilot-org/FlyDSL/pull/619 at
`af67c141fc79fab979c0446a0f2001e15211e468`

Recommendation: **accept as test-only hardening and an honest limitation
report**, not as a fix for the upstream issue.

The candidate changes only a synthetic test and its report. It has no FlyDSL
lowering, LLVM, Python implementation, or native C++ change. Consequently no
native rebuild was applicable. Python imports resolved to the prepared checkout
(`/job/repo/python/flydsl`), while the native MLIR bindings remained those from
the image's pinned wheel.

The exact candidate test was copied outside the checkout and run first on the
prepared base, then from the exact candidate commit. Both runs executed on the
assigned gfx950 GPU, matched the independent analytical reference exactly, and
produced the same compiler measurements: 32 `<4 x float>` phis, 160 MFMAs, 33
unique MFMA destination groups, 138 VGPRs, and zero spills. The generated LLVM
IR and final ISA were byte-identical between base and candidate. Thus the test
does not demonstrate a failing-before/passing-after fix.

The candidate's gfx942 compile-only path also produced 32 vector phis, 33
unique MFMA destinations, 138 VGPRs, and zero spills. This is cross-codegen
evidence only: the assigned GPU is gfx950, so gfx942 numerical execution and
runtime behavior were not tested.

The actual production MLA test could not be collected. The prepared aiter
package requires Triton 3.6 or newer for its Gluon kernels, while the pinned
environment contains `3.5.1+rocm7.2.0.gita272dfa8`. Torch, ROCm, packages, and
host configuration were left intact. Therefore the reported six branch
instances, their surrounding register pressure, the 71 destination groups / 170
spills, and production numerical output remain unverified.

The current pipeline still runs `fly-promote-regmem-to-vectorssa`, and the
candidate does not alter it. Mutable physical-register semantics for
`memref_alloca(Register)` are not implemented. The PR is useful because its
test retains both structural branches and its prose explicitly limits the
claim, but the original issue remains open.

Raw logs, dumps, hashes, the candidate diff, and the extracted test are retained
outside the checkout under `/job/review-evidence-j-fc636c0927a0`.
