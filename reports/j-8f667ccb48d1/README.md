# FP32 expression extrema GPU regression report

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/470

Upstream issue: https://github.com/ROCm/FlyDSL/issues/934

## Result

No FlyDSL implementation defect was reproduced. The added regression executes
real FP32 kernels for `fx.max`, `fx.min`, `fx.maxnumf`, `fx.minnumf`,
`fx.maximumf`, and `fx.minimumf` through the job-private rebuilt native
compiler. It covers representative finite values, a NaN in either operand,
two NaNs, and both signed-zero operand orders.

The references are independent of FlyDSL: the NaN-propagating operations use
explicit IEEE maximum/minimum rules, while the number operations use explicit
libm `fmax`/`fmin` rules. Values, NaN masks, and zero sign bits are checked.

This is focused regression coverage and does not claim completion of the full
upstream cleanup issue.

## Prepared environment

- Source checkout: `/job/repo`
- Base revision: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`
- Python: `/tmp/amdpilot-repo-j-8f667ccb48d1/venv/bin/python`
- Rebuilt native package: `/tmp/amdpilot-repo-j-8f667ccb48d1/native-build/python_packages/flydsl/_mlir`
- GPU: AMD Instinct MI350X (`gfx950`)

## Commands

Native rebuild (the helper invokes `scripts/build.sh -j16`):

```text
/tmp/amdpilot-repo-j-8f667ccb48d1/venv/bin/python /opt/amdpilot/rebuild-native.py /job
```

Focused GPU regression:

```text
/tmp/amdpilot-repo-j-8f667ccb48d1/venv/bin/python -m pytest -q -s tests/unit/test_expr_float_extrema_gpu.py
```

Related expression API tests:

```text
/tmp/amdpilot-repo-j-8f667ccb48d1/venv/bin/python -m pytest -q tests/unit/test_typed_arith_ops.py tests/unit/test_arith_ops.py
```

Raw final outputs are preserved alongside this report in
`native-rebuild.stdout.log`, `expr-float-extrema-gpu.stdout.log`, and
`related-expression-tests.stdout.log`. The machine-readable native receipt is
preserved at `/job/native-build.json`.

## Prepared-image notes

The initial rebuild exposed two image-only packaging problems before the native
compiler could be validated: `patchelf` was absent although the copied MLIR
libraries already had the requested `$ORIGIN` RUNPATH, and the job virtualenv's
path hook overrode the build's native-package-first `PYTHONPATH`. Job-private
environment shims corrected those two conditions without changing repository
sources, LLVM/MLIR, Torch, ROCm, or compiler wheels. The final rebuild and GPU
smoke then passed.
