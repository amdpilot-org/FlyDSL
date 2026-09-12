# Independent review of PR 686

Upstream issue: https://github.com/ROCm/FlyDSL/issues/515

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/687

Candidate: https://github.com/amdpilot-org/FlyDSL/pull/686 at exact commit
`576bdb4f4ecf6ca0bcd2c966d8f4615e6cba7f51`.

## Recommendation

Accept the candidate as a correct, scoped correction to the final-ISA analyzer,
not as a complete resolution of the original six-part feature request.

On the recorded base `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`,
`flydsl.tools.isa_analyzer` is absent. On parent candidate
`b0d6d33d6256a013e0a5ba4a4f0a5308998ee954`, the retained compiler-emitted
gfx950 assembly reproduces the reported failure: 35 instructions instead of
28, with `global_buffer` (2), `by_value` (2), `kernel_0`, `kernel_0.kd`, and
`false` incorrectly accepted as opcodes. The exact reviewed commit reports 28
and excludes all seven YAML values.

The candidate's six unit tests pass. Independent adversarial checks also pass
for multiple metadata blocks, indented/annotated delimiters, commented-out
delimiters, and instruction-family-looking YAML values. The broader focused
suite passes with 32 tests and 2 environment-dependent skips. Two live GPU
tests pass, including optimized output agreement with a portable GPU reference
and compiler-emitted final-ISA assertions.

Python sources resolved from `/job/repo/python/flydsl`; the `_mlir` link
resolved to the pinned `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`.
No native rebuild was performed because the candidate changes no C++ or native
MLIR source.

## Scope and limitations

The available accelerator was an AMD Instinct MI350X (`gfx950`). No other CDNA
or RDNA architecture was available. Direct upstream issue API access was
blocked by the ROCm organization's fine-grained-token lifetime policy, so the
provided issue snapshot, mirror material, repository history, exact candidate,
and retained compiler output were used.

The candidate implements only the final-ISA analysis workflow. Physical
VGPR/SGPR pinning or named reservation, exact hand-scheduled-region preservation
and MFMA co-execute-window assertions, requested first-class AMD instruction
helpers, exact low-level buffer load/store APIs, and a compiler-option sweep
example remain unimplemented. Static analysis also does not establish cycle
timing, dependency correctness, occupancy, physical placement, or performance
parity with handwritten ISA.

Raw outputs are retained in `raw/`.
