# Correction review for PR 671

Candidate: https://github.com/amdpilot-org/FlyDSL/pull/671 at
`716219a9b7bd7b2b9632123f95433a0745e3045a`

Independent review: https://github.com/amdpilot-org/FlyDSL/pull/675

Upstream issue: https://github.com/ROCm/FlyDSL/issues/515

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/676

## Result

The two concrete parser counterexamples from the independent review reproduced
against the exact candidate. Interior lines of a valid multiline block comment
were counted as instructions, including false MFMA and VMEM-store family
counts. An instruction following a label on the same line was omitted.

This correction preserves the candidate's final-ISA analysis feature and makes
comment removal stateful across lines. It also recognizes instructions after
ordinary, assembler-local, and numeric labels. Regression tests cover both
counterexamples and code adjacent to block comments.

The candidate remains a partial implementation of the original six-part
feature request. Physical register pinning or named register reservation,
exact scheduling-region preservation and MFMA co-execute assertions, the
requested first-class instruction helpers, exact low-level buffer forms, and a
compiler-option sweep example remain unimplemented. Those are API/backend
features, not justified parser corrections. Static ISA analysis does not prove
cycle scheduling, performance parity, or register-placement control.

## Reproduction

The exact commands, resolved source path, and output are retained in `raw/`.
The focused suite passed with 31 tests and 2 environment-dependent skips. Two
GPU tests passed on one assigned MI350X/gfx950, including comparison with the
portable GPU implementation. No native rebuild was needed because no C++ or
MLIR-native source changed. No architecture other than gfx950 was available.
