# Numeric extrema and vector reduction investigation

Upstream issue: https://github.com/ROCm/FlyDSL/issues/934

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/630

Base: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`

## Findings

The latent `Numeric.minimumf` failure reported in upstream child issue 938 is
already fixed on this base. `Numeric.minimumf` delegates to
`ArithValue.minimumf`, which exists in `python/flydsl/expr/utils/arith.py` and
emits `arith.minimumf`. The existing compile-tier regression is retained, and
the new GPU regression executes this method with NaN, signed zero, infinity,
and finite-boundary operands.

The vector discrepancy from upstream child issue 939 was still present:
`Vector.reduce("max")` selected `MAXNUMF`, while `Vector.reduce("min")` selected
`MINIMUMF`. The failing-before output records the mismatched emitted IR. The
dispatch now selects `MAXIMUMF`, matching `MINIMUMF` and the documented
NaN-propagating `fx.max` / `fx.min` contract.

The separate number-style operations remain unchanged. `fx.maxnumf` and
`fx.minnumf` return the numeric operand when exactly one operand is NaN, as
specified by LLVM's `maxnum`/`minnum` contract. The GPU regression checks this
directly alongside the propagating operations.

References:

- MLIR `arith.maximumf`: https://mlir.llvm.org/docs/Dialects/ArithOps/#arithmaximumf-arithmaximumfop
- MLIR `arith.minimumf`: https://mlir.llvm.org/docs/Dialects/ArithOps/#arithminimumf-arithminimumfop
- LLVM `maxnum`: https://llvm.org/docs/LangRef.html#llvm-maxnum-intrinsic
- LLVM `minnum`: https://llvm.org/docs/LangRef.html#llvm-minnum-intrinsic

## Evidence

- `raw/failing-before.txt`: four focused IR regressions fail on the base and
  show `vector.reduction <maxnumf>`.
- `raw/emitted-ir.txt`: fixed source IR contains paired `maximumf` and
  `minimumf` vector reductions.
- `raw/gpu-regression.txt`: real gfx950 output for scalar propagating,
  scalar number-style, and vector reduction paths.
- `raw/full-focused-suite.txt`: 534 focused tests pass.
- `raw/import-paths.txt`: confirms the Python implementation was imported from
  `/job/repo/python/flydsl`.

No kernel-family migration or broad arithmetic cleanup was performed.
