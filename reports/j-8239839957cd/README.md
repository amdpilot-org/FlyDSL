# Large `scf.if` accumulator investigation

Source issue: https://github.com/ROCm/FlyDSL/issues/400

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/533

The original experimental kernel was ported to the prepared checkout. Its
`warp_id == 0` predicate was constant true because the launch contains one
64-thread wave, so the compiler removed the structurally different else arm.
The regression now branches on runtime block parity and asserts that both arms
remain (96 + 64 = 160 MFMAs).

Current pinned code generation does not reproduce the reported explosion:

| target | executed | vector phis | MFMAs | unique MFMA dst groups | VGPRs | spills |
|---|---:|---:|---:|---:|---:|---:|
| gfx942 | no (cross-compile) | 32 | 160 | 33 | 138 | 0 |
| gfx950 | yes | 32 | 160 | 33 | 138 | 0 |

The gfx950 output exactly matched an analytical Torch reference using all-one
inputs: each 16x16x16 MFMA contributes 16, producing 1536 in even blocks and
512 in odd blocks after summing 32 accumulators.

FlyDSL already lowers register-memory state through
`fly-promote-regmem-to-vectorssa`; its tests explicitly require `scf.if` to
carry the promoted vector. Avoiding that phi while retaining register storage
would need a late machine-level construct (or LLVM backend support), not an
opaque LLVM alloca that can silently become scratch. Since the pinned LLVM
coalesces the faithful reproducer to 33 groups with no spills, no such lowering
change is proposed here.

Raw artifacts are retained under `/job/artifacts/final-gfx942`,
`/job/artifacts/final-gfx950`, and `/job/artifacts/logs`.
