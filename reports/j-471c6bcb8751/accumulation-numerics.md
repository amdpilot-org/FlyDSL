# GFX950 A16W16 accumulation numerics evidence

## Scope

This records a bounded accumulation-numerics probe for the gfx950 A16W16 GEMM. It is intentionally separate from issue 821's FP8 register-pressure and `BufferCopy*` legalization findings. Upstream issue 821 remains open; merged PR 824 is an unrelated MXFP4 launcher change and is not treated as a fix for this work.

## Environment

- Image: `amdpilotv2/open-job:gbt350-20260909`, local image ID `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.
- GPU: one AMD Instinct MI350X, gfx950, node ID 3, unique ID `0x9c60d586afa84d50`, serial `692517020709`.
- Interpreter: `/opt/venv/bin/python` (resolves to `/usr/bin/python3.12`).
- Torch: `2.9.1+rocm7.2.0.git7e1940d4` at `/opt/venv/lib/python3.12/site-packages/torch/__init__.py`.
- Triton: `3.5.1+rocm7.2.0.gita272dfa8` at `/opt/venv/lib/python3.12/site-packages/triton/__init__.py`.
- Installed FlyDSL: `0.2.4` at `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`.
- Installed native bindings include `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/_mlirDialectsFlyROCDL.cpython-312-x86_64-linux-gnu.so` and `libfly_jit_runtime.so`.
- Delivery base: mirror `main` commit `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.
- Installed-compatible control commit: `145a87651be9b278ea05a701c14b049eecae7db3` (FlyDSL `0.2.4`).

## First installed-source GPU baseline

Command:

```bash
cd /job/FlyDSL
FLYDSL_RUNTIME_ENABLE_CACHE=0 timeout 300 /opt/venv/bin/python examples/03-tiledMma.py
```

The installed FlyDSL package ran the repository's FP32 tiled-MMA example. It compared against `A @ B.T` with `torch.allclose(..., atol=1e-5, rtol=1e-5)` and printed `Result correct: True`. One process, including import, JIT, execution, synchronization, and reference comparison, took `3.711658139` seconds. This installed-source baseline is not proof for later checkout changes.

The initially selected AITER split-K HGEMM test was unsupported in this image. It spent 18.2 seconds building `module_aiter_core`, then failed with `ModuleNotFoundError: No module named 'aiter.jit.module_aiter_core'`. The FlyDSL example above was used as the meaningful supported neighboring control.

## Added numerical cases

The new test covers three input patterns for both BF16 and FP16:

- `finite_cancellation`: equal positive and negative unit products cancel exactly.
- `mixed_magnitude`: input terms span powers of two from `1` through `2^-9`.
- `small_residual`: alternating `1` and `-(1 - 2^-7)` products leave a small residual after cancellation.

Each case uses a 64x64x768 GEMM, FP32 output, and an independent CPU float64 matmul reference. Overflow is checked first and reported separately as explicit inf and NaN counts. Closeness then uses the existing A16W16 tolerance formula without relaxation:

- BF16: `atol = 0.2 * sqrt(k / 8192) * split_k * k_waves`, `rtol = 0.2`.
- FP16: `atol = 0.05 * sqrt(k / 8192) * split_k * k_waves`, `rtol = 0.05`.

For this no-bias, split-K=1, k-waves=1 case, that is BF16 `atol=0.0612372436`, `rtol=0.2` and FP16 `atol=0.0153093109`, `rtol=0.05`.

## Real-GPU control results

The current image's FlyDSL 0.2.4 native bindings predate the current `main` A16W16 implementation. The same six numerical patterns were therefore adapted to the supported split-K HGEMM API at exact installed-compatible commit `145a876`. The control used the existing `atol=0.1`, `rtol=0.1` gate from that commit's HGEMM test and an independent CPU float64 reference.

Command:

```bash
cd /tmp/flydsl-cache-j-471c6bcb8751/flydsl-0.2.4
FLYDSL_RUNTIME_ENABLE_CACHE=0 timeout 600 /opt/venv/bin/python -m pytest -q tests/kernels/test_accumulation_numerics_installed.py -s
```

Raw results:

| Case | Input | Max abs diff | Overflow | Result |
|---|---|---:|---|---|
| finite cancellation | BF16 | 0 | 0 inf, 0 NaN | pass |
| mixed magnitude | BF16 | 0 | 0 inf, 0 NaN | pass |
| small residual | BF16 | 0 | 0 inf, 0 NaN | pass |
| finite cancellation | FP16 | 0 | 0 inf, 0 NaN | pass |
| mixed magnitude | FP16 | 0 | 0 inf, 0 NaN | pass |
| small residual | FP16 | 0 | 0 inf, 0 NaN | pass |

All six tests passed in 3.43 seconds; the bounded pytest process took 6 seconds.

## Current-main local limitation

Command:

```bash
cd /job/FlyDSL
FLYDSL_RUNTIME_ENABLE_CACHE=0 timeout 300 /opt/venv/bin/python -m pytest -q 'tests/kernels/test_gemm_a16w16_gfx950.py::test_gemm_a16w16_accumulation_numerics[dtype0-finite_cancellation]' -s
```

The current-`main` test collects successfully but cannot execute in this image because the installed FlyDSL 0.2.4 bindings lack `flydsl.expr.rocdl.cdna4.BufferLoadAsyncLDS128b`:

```text
AttributeError: module 'flydsl.expr.rocdl.cdna4' has no attribute 'BufferLoadAsyncLDS128b'
```

The failure occurs during JIT compilation before kernel execution. The image has no reusable MLIR development install, so rebuilding current FlyDSL was not a bounded operation for this job. CI with the matching current FlyDSL build is required to execute the added test on current `main`.
