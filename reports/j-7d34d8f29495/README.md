# FlyDSL GPU qualification: j-7d34d8f29495

This bounded report supplies real FlyDSL work for the AMDPilot PR-receipt recovery context in [amdpilotv2#438](https://github.com/amdpilot-org/amdpilotv2/pull/438). It is not an upstream FlyDSL fix and does not claim that platform receipt recovery succeeded.

Source revision: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f` (`amdpilot-org/FlyDSL` `main`). The prepared source was `/job/repo/python/flydsl`; the loaded native extension resolved through `/job/repo/python/flydsl/_mlir` to `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`.

## Measurements

- Device: one AMD Instinct MI355X, `gfx950:sramecc+:xnack-`.
- Stack: Torch `2.9.1+rocm7.2.0.git7e1940d4`, HIP `7.2.26015-fc0010cf6a`; neither was changed.
- Prepared test: `python -m pytest -rA -vv -s tests/unit/test_pointer_argument_vec_add.py` using the recorded interpreter. Exit 0; one test passed in 0.90 seconds.
- Independent control: deterministic 1,031-element float32 raw-pointer vector add with a CPU-built expected result. Exit 0; all outputs finite and maximum absolute error `0.0`.

Exact interpreter-qualified commands, paths, exit codes, and structured measurements are in `result.json`. Complete command outputs and separate exit-code files are preserved under `raw/`; `numerical_control.py` is the reproducible control source.

## Limitations

The observations cover one raw-pointer float32 vector-add workload and one independent numerical input on a single assigned GPU. They do not qualify other kernels, types, shapes, devices, or broader FlyDSL behavior. No source/native compiler changes were made, so no native rebuild was needed. The external harness introduces its receipt-loss fault only after this real work completes; that behavior was neither exercised nor compensated for here.
