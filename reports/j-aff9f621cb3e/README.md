# Correction generation 2: AMD ISA analyzer metadata parsing

Upstream issue: https://github.com/ROCm/FlyDSL/issues/515

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/685

Candidate parent PR: https://github.com/amdpilot-org/FlyDSL/pull/679

Independent review parent PR: https://github.com/amdpilot-org/FlyDSL/pull/683

The exact candidate commit `b0d6d33d6256a013e0a5ba4a4f0a5308998ee954`
was checked out separately and run against its retained compiler-emitted gfx950
assembly. It reported 35 instructions because seven YAML metadata scalar values
were accepted as opcodes. The corrected parser tracks the
`.amdgpu_metadata`/`.end_amdgpu_metadata` region and reports the actual 28
instructions.

The candidate's valid multiline-comment and same-line-label fixes are retained.
The new adversarial unit case also places an instruction-looking MFMA value in
the YAML block to prevent family-count inflation.

No native rebuild was performed because no C++ or native MLIR source changed.
The GPU checks ran on the assigned MI355X/gfx950 and include agreement with a
portable GPU reference plus final-ISA generation/assertions.

The original request remains only partially implemented. Physical register
pinning/reservation, exact scheduling-region and MFMA-window guarantees,
first-class AMD instruction helpers, exact low-level buffer APIs, and the
compiler-option sweep example remain unavailable.
