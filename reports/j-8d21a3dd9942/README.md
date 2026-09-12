# Independent review of PR 671

Candidate: https://github.com/amdpilot-org/FlyDSL/pull/671 at
`716219a9b7bd7b2b9632123f95433a0745e3045a`

Upstream issue: https://github.com/ROCm/FlyDSL/issues/515

Candidate mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/669

Review mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/673

## Finding

Request changes. The candidate is an honest partial implementation of the
six-part feature request: it adds a useful final-ISA reporting API/CLI but does
not implement register pinning, stronger scheduling control, the requested
instruction helpers, exact low-level buffer forms, or an option-sweep example.

The prepared base reproduces the absence of the proposed analyzer. On the exact
candidate, its 31 focused tests pass (29 passed, 2 skipped), its retained gfx950
ISA produces the checked-in report, and two GPU tests pass on one MI350X/gfx950.
The import logs confirm both revisions used `/job/repo/python/flydsl`, not the
installed wheel. No C++/MLIR native source changed, so a native rebuild was not
applicable.

Independent adversarial cases expose correctness bugs in the new analyzer:

- instruction-looking text on interior lines of a valid multiline `/* ... */`
  comment is counted as real ISA, including MFMA and store family counts;
- a valid instruction on the same line as a label (`entry: s_nop 0`) is omitted.

These contradict the documentation's "exact opcode counts" statement. The
candidate therefore needs parser fixes and regression tests before acceptance,
and it must continue to be described as a partial contribution rather than a
full resolution of the original issue.

## Environment and limits

Testing used Python `/tmp/amdpilot-repo-j-8d21a3dd9942/venv/bin/python`, Torch
2.9.1 with ROCm 7.2, and one AMD Instinct MI350X (`gfx950`). No other CDNA or
RDNA architecture was available. Static assembly counts do not establish cycle
timing, dependency correctness, occupancy, register pinning, scheduling
preservation, or the claimed 1000-1160+ TFLOPS performance comparison.

Raw command output and import paths are retained under `raw/`.
