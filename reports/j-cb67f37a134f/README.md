# Independent review of candidate PR 491

Upstream issue: https://github.com/ROCm/FlyDSL/issues/353

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/517

Reviewed base `acf7e67b7d22847e345938ca54fcc137bd7b2a1f` and exact candidate head
`b43bcc55b50af4f5e1e40a585dc1852b7007bca9`.

## Recommendation

Accept the candidate as regression coverage and a logical-`not` diagnostic
improvement, but do not describe it as the change that fixes the reported
vector `~`/unary-`-` compiler crash. The candidate's four signed/unsigned GPU
regressions pass unchanged on the prepared base. The only candidate behavior
that fails before and passes after is that Python `not` on a `Vector` now raises
a clear `TypeError`; base silently accepts it because ordinary Python truth
semantics apply.

The literal issue script is no longer source-compatible because current
`make_tile` rejects the historical single-list spelling. With only that API
spelling adapted to the current equivalent, the original 8x24 tiled copy,
15-block launch, vector bitwise inversion, and exact Torch reference all pass
on base. Thus the historical assertion is not reproduced on the prepared
revision.

## Evidence

- Base literal reproduction: exit 1 before reaching unary compilation,
  `ValueError: make_tile: expected int, None, tuple, or Layout, got <class 'list'>`.
- Base current-API equivalent: exit 0, real GPU execution, `Result correct: True`.
- Candidate focused suite: 400 passed (all arithmetic conformance plus four
  GPU vector-unary cases).
- Candidate GPU regression copied unchanged and run on base: 4 passed.
- Candidate logical-`not` diagnostic copied unchanged and run on base: failed
  because no `TypeError` was raised; it passes at the candidate head.
- Candidate uncached IR/ISA run: 4 passed. Origin/lowered MLIR contains
  `arith.xori` and `arith.subi` on `vector<48xi32>`; gfx950 ISA contains
  `v_not_b32_e32` and `v_sub_u32_e32`.
- Independent numerical references are NumPy `invert`/`negative` with exact
  `array_equal`, including signed and unsigned 32-bit extrema and wraparound.

Raw logs, the adapted source reproduction, copied candidate tests, and complete
IR/ISA dumps are retained outside the checkout at
`/job/evidence-j-cb67f37a134f/`. Python imports resolved to
`/job/repo/python/flydsl`; native shared objects resolved under
`/job/repo/python/flydsl/_mlir/_mlir_libs/`, populated from the prepared pinned
wheel. No C++ files differ in the candidate, so the native rebuild command was
not applicable.

## Limitations

Execution used the assigned AMD Instinct MI350X, reported by Torch as gfx950
capability `(9, 5)`, with ROCm/HIP 7.2. The report named MI355 and ROCm 7.1;
that exact board/runtime combination was unavailable. This review therefore
verifies the same gfx950 ISA family, not the exact reported hardware/software
pair. It also cannot identify which historical pre-base change removed the
assertion, only that the prepared base already contains working vector unary
operators.
