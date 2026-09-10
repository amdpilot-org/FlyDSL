# Conv3d layout edge validation on gfx950

## Scope

This report records a bounded, single-GPU validation of `conv3d_implicit` layout contracts and operator edge semantics. It is intentionally distinct from NDHWC two-layer chaining and tile-performance tuning.

Reference context: ROCm/FlyDSL issue 993, read-only. The issue requests explicit `input_layout` and `output_layout` support so chained convolutions can avoid per-layer layout round-trips. The current mirror `main` already implements that support, so this change adds focused edge-case coverage rather than duplicating an existing fix.

## Environment

- GPU: AMD Instinct MI350X, `gfx950`, CUDA capability `(9, 5)`.
- Image: `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.
- Python: `/opt/venv/bin/python`.
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`, module `/opt/venv/lib/python3.12/site-packages/torch/__init__.py`.
- Installed FlyDSL wheel: `0.2.4`, module `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`.
- Job-private FlyDSL wheel used for the checkout: `0.3.2`, module `/tmp/flydsl-wheel-0.3.2-j-7c64c1e67e18/flydsl/__init__.py`.
- Checkout kernel: `/job/FlyDSL/kernels/conv/conv3d_implicit.py`.
- Checkout tests: `/job/FlyDSL/tests/kernels/test_conv3d_implicit.py`.
- Runtime cache: `/tmp/flydsl-cache-j-7c64c1e67e18/runtime`.
- Autotune cache: `/tmp/flydsl-cache-j-7c64c1e67e18/autotune`.

The installed-source baseline is saved outside the repository at `/job/baseline-first.json`. It is an environment-context baseline and is not proof for later checkout changes.

## Layout contracts

`conv3d_implicit` accepts:

- Input layout `NCDHW` or `NDHWC`.
- Weight layout `OIDHW`.
- Output layout `NCDHW` or `NDHWC`.

The GEMM itself is channels-last. An `NDHWC` input skips the pre-transpose, and an `NDHWC` output is the raw row-major `(npq, K)` epilogue result.

## Validated edge cases

The new tests cover:

- Odd input channels (`C = 3`) and odd output channels (`K = 5`).
- Spatial tails (`D = 5`, `H = 5`, `W = 3`).
- Bias.
- Asymmetric supported padding through `padding="same"` with an even kernel.
- Admitted dilation, including `(1, 2, 1)` and `(2, 1, 1)`.
- All four input/output layout combinations.
- Precise rejection of an unsupported input layout, followed by a working `NCDHW` control.
- Precise rejection of an inadmissible dilated footprint, followed by a working neighboring control.

All comparisons use independent `torch.nn.functional.conv3d` references with the existing numerical gate:

```python
torch.allclose(actual, expected, rtol=2e-2, atol=2e-2)
```

## Results

- New focused tests: 14 passed.
- Full `tests/kernels/test_conv3d_implicit.py`: 71 passed.
- Full-suite runtime: 220.21 seconds.
- Maximum absolute error across the four layout-contract benchmark cases: `0.125`.
- Mean absolute error across those cases: `0.009412434883415699`.
- All four layout-contract cases passed the unchanged `rtol=2e-2, atol=2e-2` gate.

Raw benchmark results are in `conv3d-layout-edge-results.json`.

## Timings

All timings use five iterations after one warmup and CUDA events.

| Contract | Mean kernel time |
|---|---:|
| `NCDHW -> NCDHW` | `0.06851279735565186 ms` |
| `NCDHW -> NDHWC` | `0.06160060167312622 ms` |
| `NDHWC -> NCDHW` | `0.04000039994716644 ms` |
| `NDHWC -> NDHWC` | `0.043776598572731015 ms` |

Layout conversion timings:

| Conversion | Mean time |
|---|---:|
| Internal `NCDHW -> NDHWC` | `0.011368200182914734 ms` |
| Torch `NDHWC -> NCDHW` permute | `0.007040199637413025 ms` |

Independent Torch reference timing for the same case: `0.03179219961166382 ms` mean.

## Commands

Focused new tests:

```bash
export PYTHONPATH=/tmp/flydsl-wheel-0.3.2-j-7c64c1e67e18:/job/FlyDSL
export FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-7c64c1e67e18/runtime
export FLYDSL_AUTOTUNE_CACHE_DIR=/tmp/flydsl-cache-j-7c64c1e67e18/autotune
/opt/venv/bin/python -m pytest -q tests/kernels/test_conv3d_implicit.py \
  -k 'layout_edge_cases or invalid_layout or unsupported_dilation'
```

Full conv3d test file:

```bash
export PYTHONPATH=/tmp/flydsl-wheel-0.3.2-j-7c64c1e67e18:/job/FlyDSL
export FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-7c64c1e67e18/runtime
export FLYDSL_AUTOTUNE_CACHE_DIR=/tmp/flydsl-cache-j-7c64c1e67e18/autotune
/opt/venv/bin/python -m pytest -q tests/kernels/test_conv3d_implicit.py
```

## Notes

- The installed FlyDSL 0.2.4 wheel does not provide `flydsl.expr.rocdl.make_buffer_ptr`, which current `main` requires. A job-private FlyDSL 0.3.2 wheel was used to run the checkout without modifying the qualified Torch/ROCm stack.
- No upstream issue, pull request, or comment was posted or modified.
