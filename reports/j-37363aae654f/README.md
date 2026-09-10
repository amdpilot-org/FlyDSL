# Fused-add/residual RMSNorm gfx950 validation

## Scope

This report extends downstream-contract evidence to FlyDSL fused-add/residual RMSNorm backward. It deliberately does not add Quack integration or download model weights.

Read-only context from ROCm/FlyDSL issue 749 says PR 800 added fused-add/residual backward and PR 884 added mixed-weight support. Both are already present in the tested `main` commit, so this change adds validation rather than duplicating a kernel fix.

## Environment

- Repository: `https://github.com/amdpilot-org/FlyDSL.git`
- PR base: `main` at `ed70142704e1a6d5563fb53e1607e3a4b85d7111`
- Worktree: `/job/FlyDSL`
- Image: `amdpilotv2/open-job:gbt350-20260909`, expected local ID `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`
- GPU: one AMD Instinct MI350X, gfx950, unique ID `0xfa55ca8c650dfefb`, serial `692517020458`
- Python: `/opt/venv/bin/python`
- Torch: `2.9.1+rocm7.2.0.git7e1940d4` at `/opt/venv/lib/python3.12/site-packages/torch/__init__.py`
- Triton: `3.5.1+rocm7.2.0.gita272dfa8` at `/opt/venv/lib/python3.12/site-packages/triton/__init__.py`
- FlyDSL wheel: `0.2.4` at `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`
- Native FlyDSL modules include `_mlirDialectsFlyROCDL`, `_mlirDialectsFlyGPU`, `_mlirDialectsLLVM`, `_mlirExecutionEngine`, `libFlyPythonCAPI`, and `libfly_jit_runtime` under `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/`

The installed 0.2.4 wheel predates the checkout's `get_warp_size` API. The first exact test therefore failed collection with `ImportError`; a one-function compatibility shim supplied that API while preserving the installed Torch/ROCm/FlyDSL stack. This installed-source baseline is not proof for later checkout changes.

## Commands

The job-private cache was `/tmp/flydsl-cache-j-37363aae654f`. The shim directory contained:

```python
import flydsl.runtime.device as _device
if not hasattr(_device, "get_warp_size"):
    def _get_warp_size(arch=None):
        arch = arch or _device.get_rocm_arch()
        return 32 if str(arch).startswith(("gfx10", "gfx11", "gfx12")) else 64
    _device.get_warp_size = _get_warp_size
```

Focused new-case command:

```bash
cd /job/FlyDSL
PYTHONPATH=/tmp/flydsl-shim:/job/FlyDSL \
FLYDSL_CACHE_DIR=/tmp/flydsl-cache-j-37363aae654f \
/opt/venv/bin/python -m pytest -q \
  tests/kernels/test_rmsnorm.py::test_fused_add_rmsnorm_adversarial_autograd
```

Complete affected-case command:

```bash
cd /job/FlyDSL
PYTHONPATH=/tmp/flydsl-shim:/job/FlyDSL \
FLYDSL_CACHE_DIR=/tmp/flydsl-cache-j-37363aae654f \
/opt/venv/bin/python -m pytest -q \
  tests/kernels/test_rmsnorm.py::test_fused_add_rmsnorm \
  tests/kernels/test_rmsnorm.py::test_fused_add_rmsnorm_backward \
  tests/kernels/test_rmsnorm.py::test_fused_add_rmsnorm_autograd \
  tests/kernels/test_rmsnorm.py::test_fused_add_rmsnorm_adversarial_autograd
```

## Numerical gates

Existing gates were unchanged:

- Forward output and residual output absolute tolerance: FP32 `1e-4`, FP16 `1e-2`, BF16 `2e-2`.
- Backward `rstd` absolute tolerance: `1e-3`.
- Backward input/residual gradient absolute tolerance: FP32 `1e-3`, FP16 `3e-2`, BF16 `2e-1`.
- Backward weight-gradient tolerance: FP32 `rtol=1e-4, atol=1e-2`; FP16 `rtol=3e-2, atol=1e-1`; BF16 `rtol=1e-1, atol=5e-1`.
- Public autograd output/input/residual tolerance: FP32 `1e-3`, FP16 `3e-2`, BF16 `2e-1`; weight tolerance: FP32 `1e-2`, FP16 `2e-1`, BF16 `1.0`.

The new adversarial test uses independent FP32 Torch autograd and checks output, residual output, input gradient, residual gradient, and weight gradient. It also checks activation/output/gradient dtypes, finite inputs, unchanged source tensors, and that `residual_out` owns new storage rather than aliasing either input.

## Raw results

- First exact installed-source attempt: exit `4`, wall `2.955988 s`, unsupported because installed FlyDSL lacked `get_warp_size`.
- Supported neighboring control (`examples/01-vectorAdd.py`): `PASS`, wall `2.620896 s`.
- Installed-source fused-add backward with compatibility shim: all 10 existing configs passed, wall `10.553060 s`.
- New adversarial test: `4 passed in 4.38 s`, command wall `7.244077 s`.
- Complete affected set: `7 passed in 8.75 s`, command wall `12.085001 s`.

The new cases cover FP32/FP16 aligned hidden sizes and BF16/FP32 tail hidden sizes, including atomic and two-stage backward paths. No synthetic GPU burn, unbounded loops, sleep loops, or repeated work were used.

## Left undone

No Quack integration, full-model download, mixed-architecture claim, or performance regression threshold was attempted. `black` and `ruff` are not installed in this image; `git diff --check` and the 120-column limit were used instead.
