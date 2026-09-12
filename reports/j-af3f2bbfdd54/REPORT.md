# FlyDSL qualification report: j-af3f2bbfdd54

This bounded run qualifies the prepared FlyDSL revision `acf7e67b7d22847e345938ca54fcc137bd7b2a1f` for the requested PR-receipt recovery exercise. It is a platform report, not an upstream FlyDSL fix. Platform context: https://github.com/amdpilot-org/amdpilotv2/pull/438.

## Results

- Device: one assigned `AMD Instinct MI355X` (`cuda:0`, `gfx950:sramecc+:xnack-`). Torch was `2.9.1+rocm7.2.0.git7e1940d4`; HIP was `7.2.26015-fc0010cf6a`.
- Prepared test: `tests/unit/test_pointer_argument_vec_add.py` passed, 1/1, with pytest reporting `1 passed in 0.90s`; command process exit code 0 and measured wall time 2.8335 seconds.
- Independent numerical control: a deterministic 16,387-element float32 affine operation ran on the GPU and was transferred back for comparison with a CPU reference. Maximum and mean absolute error were both 0.0; sums were both 32917.2578125; exit code 0 and measured wall time 1.0372 seconds.
- Source imports came from `/job/repo/python/flydsl`; the pinned native package was `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`. The prepared interpreter was `/tmp/amdpilot-repo-j-af3f2bbfdd54/venv/bin/python`.

Exact commands and unabridged captured output are under `raw/`; structured measurements are in `result.json`.

## Limitations

Only the requested focused test and one small independent GPU control were run. No FlyDSL source or native compiler code was changed, so no native rebuild was needed. This does not qualify other FlyDSL behavior or hardware. The external harness performs its receipt-loss fault after this work; these measurements do not compensate for that fault and do not claim platform recovery success.
