# Independent review of amdpilot-org/FlyDSL PR 632

Upstream issue: https://github.com/ROCm/FlyDSL/issues/934

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/633

Candidate: `697129d402848711037a0169f3bb09b0882257aa`

Prepared base: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`

## Recommendation

Accept. The candidate is a full fix for the approved, narrow original-issue
scope: the `Numeric.minimumf` defect is already fixed on the prepared base, and
the candidate fixes the remaining `Vector.reduce("max")` NaN-semantic
discrepancy. This does not claim to complete the umbrella issue's deferred
kernel migrations or broad arithmetic cleanup.

## Independent findings

On the prepared base, the candidate's real-GPU regression failed because
`Vector.reduce("max")` returned `+inf` for `[NaN, 1, -inf, +inf]`, while the
corresponding minimum reduction returned NaN. The scalar `Numeric.minimumf`
path already compiled and passed on that same base. The existing implementation
delegates through `Numeric.minimumf` to `ArithValue.minimumf`, which emits
`arith.minimumf`.

At the exact candidate commit, `Vector.reduce("max")` emits
`vector.reduction <maximumf>` instead of `<maxnumf>`. The candidate regression
passes on a real AMD Instinct MI355X (gfx950). An independent GPU kernel also
placed NaN in each of the four vector lanes in turn, exercised scalar NaN in
both operand orders, reversed signed-zero order, infinities, and both finite
`float32` extremes. All results matched the documented distinction:

- `maximumf`/`minimumf` and vector max/min propagate NaN.
- `maxnumf`/`minnumf` select the numeric operand when exactly one input is NaN.
- maximum selects `+0` and minimum selects `-0` for mixed signed zeros.

The focused 534-test suite passed at the candidate commit.

## Source, native code, and architecture

Python was imported from `/job/repo/python/flydsl`. The MLIR namespace was
resolved from `/job/repo/python/flydsl/_mlir`, extended by the pinned wheel's
native libraries under `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`.
The candidate changes only Python dispatch and tests; it changes no C++ or
native source, so the prepared native rebuild command was not applicable and
was not run.

GPU validation used ROCm 7.2 with Torch `2.9.1+rocm7.2.0.git7e1940d4` on one
AMD Instinct MI355X, reported as gfx950 / capability `(9, 5)`. Other GPU
architectures, multi-GPU execution, and CPU-only lowering were not tested.

## Evidence index

- `raw/base-reproduction.txt`: failing-before real-GPU output.
- `raw/candidate-gpu.txt`: candidate regression and independent adversarial output.
- `raw/focused-suite.txt`: 534 focused tests passing.
- `raw/environment.txt`: source/native paths and accelerator details.

No candidate code was copied, modified, or merged into this review branch.
