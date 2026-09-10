# RMSNorm numerical-range validation on gfx950

## Scope

This change adds focused forward RMSNorm validation for zero, tiny, and finite-outlier rows. It checks all supported activation/weight dtype pairs against an independent 50-digit `decimal` reference and verifies the documented epsilon/scale relationship. It intentionally does not add input-layout, large-hidden-size, or residual-backward cases.

## Environment

- GPU: one AMD Instinct MI350X, `gfx950`.
- Image: `amdpilotv2/open-job:gbt350-20260909`, local image ID `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.
- Interpreter: `/opt/venv/bin/python` (Python 3.12.3).
- Torch: `/opt/venv/lib/python3.12/site-packages/torch/__init__.py`, version `2.9.1+rocm7.2.0.git7e1940d4`.
- Triton: `/opt/venv/lib/python3.12/site-packages/triton/__init__.py`, version `3.5.1+rocm7.2.0.gita272dfa8`.
- Installed FlyDSL source: `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`, version `0.2.4`.
- Installed FlyDSL native module: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/_mlirDialectsFlyROCDL.cpython-312-x86_64-linux-gnu.so`.
- Checkout: `/job/FlyDSL`, base commit `ed70142704e1a6d5563fb53e1607e3e4b85d7111`.
- Job-private runtime used for checkout tests: `/tmp/flydsl-wheel-0.3.2/flydsl/__init__.py`, version `0.3.2`.
- Job-private native module used for checkout tests: `/tmp/flydsl-wheel-0.3.2/flydsl/_mlir/_mlir_libs/_mlirDialectsFlyROCDL.cpython-312-x86_64-linux-gnu.so`.

The local checkout reports source version `0.3.3`, but its generated `_mlir` bindings are not present and no MLIR CMake installation is available in the image. Tests therefore use checkout kernels/tests with the published, compatible `0.3.2` wheel installed only under `/tmp`. This preserves the qualified Torch/ROCm stack and avoids a full LLVM rebuild.

## Installed-source baseline

The current checkout RMSNorm test could not import against installed FlyDSL `0.2.4`:

```text
ImportError: cannot import name 'get_warp_size' from 'flydsl.runtime.device'
(/opt/venv/lib/python3.12/site-packages/flydsl/runtime/device.py)
```

Command:

```bash
PYTHONPATH=/tmp/flydsl-installed-baseline \
ROCDSL_RMSNORM_SHAPES='4,128,f32' \
timeout 300 /opt/venv/bin/python -m pytest -q \
  /job/FlyDSL/tests/kernels/test_rmsnorm.py -k test_rmsnorm_eps_honored
```

Raw timing: status `2`, elapsed `2.955593 s`, no GPU execution. This is an installed-source compatibility baseline only and is not proof for later checkout changes.

Supported neighboring control:

```bash
timeout 300 /opt/venv/bin/python -m pytest -q \
  /job/FlyDSL/tests/unit/test_pointer_argument_vec_add.py::test_pointer_argument_vector_add
```

Raw result: `1 passed`, status `0`, elapsed `3.356695 s`, including GPU execution and synchronization.

## Checkout reproduction

Existing epsilon gate before edits:

```bash
PYTHONPATH=/tmp/flydsl-wheel-0.3.2:/job/FlyDSL \
timeout 600 /opt/venv/bin/python -m pytest -q \
  /job/FlyDSL/tests/kernels/test_rmsnorm.py -k test_rmsnorm_eps_honored
```

Raw result: `1 passed`, status `0`, elapsed `5.109881 s`.

New focused gate after edits:

```bash
PYTHONPATH=/tmp/flydsl-wheel-0.3.2:/job/FlyDSL \
timeout 600 /opt/venv/bin/python -m pytest -q \
  /job/FlyDSL/tests/kernels/test_rmsnorm.py \
  -k test_rmsnorm_finite_range_and_epsilon_scale
```

Raw result: `5 passed`, status `0`, elapsed `5.115969 s`.

Combined unchanged and new gates:

```bash
PYTHONPATH=/tmp/flydsl-wheel-0.3.2:/job/FlyDSL \
timeout 600 /opt/venv/bin/python -m pytest -q \
  /job/FlyDSL/tests/kernels/test_rmsnorm.py \
  -k 'test_rmsnorm_eps_honored or test_rmsnorm_finite_range_and_epsilon_scale'
```

Raw result: `6 passed`, status `0`, elapsed `4.571518 s`.

Timing uses `date +%s%N` immediately before and after each bounded pytest command. No synthetic burn, sleep loop, unbounded loop, or repeated GPU work was used.

## Numerical design

The independent reference computes each row in a 50-digit `decimal` context:

```text
mean_square = sum(x_i^2) / N
scale = 1 / sqrt(mean_square + eps)
expected_i = x_i * scale * weight_i
```

The expected values are quantized only at the final comparison to the supported output dtype. The test covers:

- `f32/f32`
- `f16/f16`
- `f16/f32`
- `bf16/bf16`
- `bf16/f32`

Rows are exactly zero, tiny (`1e-6` through `8e-6`), and finite dtype-safe outliers. The test asserts all outputs remain finite, matches the independent reference, and checks that tiny-row output scales by approximately `sqrt(1e-2 / 1e-6) = 100` when epsilon changes from `1e-2` to `1e-6`.

## Issue context

Read-only context is ROCm/FlyDSL issue 749, “[RFC] FlyDSL kernels in downstream libraries.” Its current description and comments state that forward `rstd`, plain backward, fused-add backward, staged backward, and mixed FP16/BF16 activation with FP32 weight support have already landed through related changes. This change therefore adds missing numerical-range validation and does not duplicate an existing fix.

## Limitations

- The checkout compiler/runtime was not rebuilt from source because the image has neither CMake nor an MLIR installation; the compatible published `0.3.2` wheel was used instead.
- Validation is limited to the assigned single `gfx950` GPU.
- Input layout, hidden sizes above the existing gates, residual backward, autograd, and multi-GPU behavior are intentionally outside this change.
