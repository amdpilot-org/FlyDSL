# Review correction for the SSA phi investigation

Upstream issue: https://github.com/ROCm/FlyDSL/issues/400

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/603

Candidate: https://github.com/amdpilot-org/FlyDSL/pull/554 at
`383ee41aaa252f8f081d0b6a860f2c8f051f1cb0`

Independent review: https://github.com/amdpilot-org/FlyDSL/pull/587

Outcome: **candidate rejected** as a fix. The candidate's corrected runtime
predicate is useful characterization coverage, so that test is retained with
wording that does not claim to reproduce the production failure.

The review counterexamples reproduced independently. Running the exact
candidate test against both the untouched prepared base and the exact candidate
produced the same result on gfx950: exact numerical output, 32 `<4 x float>`
phis, 160 MFMAs, 33 unique MFMA destination groups, 138 VGPRs, and zero spills.
The generated gfx950 LLVM IR and final ISA were byte-identical. Cross-codegen
for gfx942 produced the same compiler metrics, but gfx942 was not executed.

The production MLA test could not be collected. Importing the prepared `aiter`
raises because its Gluon kernels require Triton 3.6 or newer, while the pinned
environment contains `3.5.1+rocm7.2.0.gita272dfa8`. No package, model, ROCm, or
host configuration was changed. Consequently the six-branch production
register pressure, reported 71 destination groups / 170 spills, and production
numerical output remain unverified.

No compiler change is justified by the available evidence. The current ROCm
pipeline explicitly runs `fly-promote-regmem-to-vectorssa`, and the captured
dump contains that pass, so this work does not claim that
`memref_alloca(Register)` implements mutable physical-register semantics.
Changing that behavior without a runnable production regression would be
speculative and could silently lower retained storage to scratch.

Raw logs and dumps are retained under `/job/evidence-j-20d874fecb6e`.

