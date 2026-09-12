# Correction review for issue 862

This correction preserves the valid source change from candidate
https://github.com/amdpilot-org/FlyDSL/pull/512 and incorporates the concrete
counterexamples from independent review
https://github.com/amdpilot-org/FlyDSL/pull/607.

The candidate removes one redundant source-IR serialization.  The focused
regression fails on base `acf7e67b7d22847e345938ca54fcc137bd7b2a1f` and the
candidate plus cache-identity suites pass.  Fresh-cache GPU runs preserve the
same source and compiled IR hashes and match independent Torch references.

The correction does not claim an end-to-end speedup or resolution of the broad
compile-time request.  In this independent reproduction both candidate cold
wall-clock observations were higher within run-to-run noise.  Most compiler
pipeline time remains after the narrow change.  The issue-linked RMSNorm code
still imports a removed `flydsl.expr.vector` module, and the assigned GPU was an
MI350X in the gfx950 family rather than the reported MI355.

Raw outputs are under `raw/`; `result.json` records exact commands and limits.
