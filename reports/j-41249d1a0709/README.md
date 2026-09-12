# Independent review of PR 679

Candidate: https://github.com/amdpilot-org/FlyDSL/pull/679 at
`b0d6d33d6256a013e0a5ba4a4f0a5308998ee954`

Upstream issue: https://github.com/ROCm/FlyDSL/issues/515

Candidate mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/676

Review mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/680

Parent candidate: https://github.com/amdpilot-org/FlyDSL/pull/671 at
`716219a9b7bd7b2b9632123f95433a0745e3045a`

Prior review: https://github.com/amdpilot-org/FlyDSL/pull/675

## Recommendation

Request changes. The exact candidate fixes both concrete parser regressions from
the prior review: multiline `/* ... */` comments no longer create false
instructions/family counts, and instructions following ordinary, local, or
numeric labels are counted. Those failures were independently reproduced at
the exact parent candidate and pass at the exact reviewed commit.

However, the analyzer still counts YAML AMDGPU metadata scalar values as
instructions in real compiler output. Running the exact candidate on its own
retained `gfx950-final-isa.s` reports 35 instructions instead of the 28 actual
instructions and invents these opcodes: `by_value` (2), `false` (1),
`global_buffer` (2), `kernel_0` (1), and `kernel_0.kd` (1). The parser ignores
directive keys because they begin with `.`, but accepts their alphabetic values
after the YAML colon. This violates the advertised exact opcode and instruction
counts on the primary final-ISA input format.

The candidate is also only a partial implementation of the original six-part
feature request. It adds a useful static ISA-analysis API and CLI, but does not
implement physical register pinning/reservation, exact scheduling-region and
MFMA co-execute-window preservation/assertions, the requested first-class AMD
instruction helpers, exact low-level buffer load/store APIs, or a compiler
option sweep example. It must not be represented as fully resolving the
original issue.

## Evidence

- The recorded base `acf7e67b7d22847e345938ca54fcc137bd7b2a1f` fails to
  import `flydsl.tools.isa_analyzer`; the feature did not exist.
- The prior candidate `716219a9b7bd7b2b9632123f95433a0745e3045a` independently
  reproduced both reported counterexamples (3 instructions instead of 1 for
  the block-comment case, and 0 instead of 1 for `entry: s_nop 0`).
- The candidate regression file passes all 5 tests, and independent adjacent
  comment/multiple-label, metadata-comment, hexadecimal-resource, and family
  counting cases pass.
- The focused compatibility suite passes 31 tests with 2 skips.
- Two GPU tests pass on the available gfx950 device, including comparison to
  the portable GPU reduction and final-ISA shape assertions.
- The real retained gfx950 assembly exposes the remaining YAML-metadata false
  positives described above.

Raw command output is retained in `raw/`.

## Environment and scope limitations

Python source loaded from `/job/repo/python/flydsl`. The native extension loaded
through `/job/repo/python/flydsl/_mlir/_mlir_libs/_mlir.cpython-312-x86_64-linux-gnu.so`,
which is the prepared pinned native payload. No C++ or native MLIR source changes
between the base and candidate, so rebuilding native code was not required and
would not validate the Python-only analyzer change.

Only one gfx950-class accelerator was available; no other CDNA or RDNA target
was tested. GPU execution establishes compatibility and real compiler output,
not performance parity, exact scheduling, occupancy, or register placement.
Direct inspection of the upstream issue through `gh` was blocked by the ROCm
organization's fine-grained-token lifetime policy. The supplied issue snapshot,
mirror issues, exact commits, repository history, and candidate files were used;
credentials and host configuration were not changed.
