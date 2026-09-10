# FlyDSL plain RMSNorm gfx950 validation

This is GPU evidence for existing FlyDSL core behavior. It is not a Quack
repository integration and makes no `torch.compile` support claim.

## Result

- Custom mixed-weight matrix: **10/10 passed**.
- Existing mixed-weight autograd gate: **4/4 passed**.
- Existing forward/backward cache and non-default-stream gates: **3/3 passed**.
- No core defect was found and no core fix is duplicated.

The custom matrix covers BF16 and FP16 activations with FP32 weights, plain
forward output and saved `rstd`, `x` and `weight` gradients, `M=512`, and hidden
sizes `512`, `4096`, `4097`, `8191`, and `8192`. Every case selected the
two-stage backward path, ran on a non-default current stream, and reused warm
forward/backward launchers.

## Environment

- PR base: `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.
- Qualified image: `amdpilotv2/open-job:gbt350-20260909`, local image ID
  `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.
- GPU: one assigned AMD Instinct MI350X, `gfx950`, 256 CUs.
- Python: `/opt/venv/bin/python` (3.12.3).
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`, `/opt/venv/lib/python3.12/site-packages/torch/__init__.py`.
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`, `/opt/venv/lib/python3.12/site-packages/triton/__init__.py`.
- FlyDSL wheel: `0.2.4`, `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`.
- FlyDSL native modules:
  `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/`.
- Tested kernel source: `/job/FlyDSL/kernels/norm/rmsnorm_kernel.py`.
- Shared contract source: `/job/FlyDSL/kernels/norm/rmsnorm_common.py`.
- Existing test source: `/job/FlyDSL/tests/kernels/test_rmsnorm.py`.

The image wheel is 0.2.4 while this mirror source is 0.3.3. The wheel lacks the
newer `get_warp_size` helper used by the source kernel helpers. The validation
harness patches that helper in memory before importing the source kernels; it
does not install packages or alter the qualified Torch/ROCm stack.

## Reproduction

Run from the repository root with one assigned MI350X. All caches are kept
outside `/job/FlyDSL`:

```bash
export PYTHONPATH=/job/FlyDSL
export PYTHONDONTWRITEBYTECODE=1
export HOME=/tmp/flydsl-cache-j-65dd8f3726b1/home
export XDG_CACHE_HOME=/tmp/flydsl-cache-j-65dd8f3726b1/xdg
export FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-65dd8f3726b1/runtime
export FLYDSL_AUTOTUNE_CACHE_DIR=/tmp/flydsl-cache-j-65dd8f3726b1/autotune
export TRITON_CACHE_DIR=/tmp/flydsl-cache-j-65dd8f3726b1/triton
export TMPDIR=/tmp/flydsl-cache-j-65dd8f3726b1/tmp
mkdir -p "$HOME" "$XDG_CACHE_HOME" "$FLYDSL_RUNTIME_CACHE_DIR" \
  "$FLYDSL_AUTOTUNE_CACHE_DIR" "$TRITON_CACHE_DIR" "$TMPDIR"

/opt/venv/bin/python reports/j-65dd8f3726b1/validate_rmsnorm.py \
  reports/j-65dd8f3726b1/results.json
```

Focused existing gates:

```bash
/opt/venv/bin/python - <<'PY'
import flydsl.runtime.device as device

if not hasattr(device, "get_warp_size"):
    def get_warp_size(arch=None):
        if arch is None:
            arch = device.get_rocm_arch()
        return 32 if str(arch).lower().startswith(("gfx10", "gfx11", "gfx12")) else 64
    device.get_warp_size = get_warp_size

import pytest
raise SystemExit(pytest.main([
    "tests/kernels/test_rmsnorm.py",
    "-k", "rmsnorm_mixed_fp32_weight_autograd and not fused_add",
    "--tb=short", "-q",
]))
PY

/opt/venv/bin/python - <<'PY'
import flydsl.runtime.device as device

if not hasattr(device, "get_warp_size"):
    def get_warp_size(arch=None):
        if arch is None:
            arch = device.get_rocm_arch()
        return 32 if str(arch).lower().startswith(("gfx10", "gfx11", "gfx12")) else 64
    device.get_warp_size = get_warp_size

import pytest
raise SystemExit(pytest.main([
    "tests/kernels/test_rmsnorm.py",
    "-k",
    "(rmsnorm_fwd_cache_reuses_compiled_launcher and not fused_add) or "
    "(rmsnorm_bwd_two_stage_cache_reuse_across_m and not fused_add) or "
    "rmsnorm_bwd_two_stage_multistream_workspace",
    "--tb=short", "-q",
]))
PY
```

## Numerical gates

The custom harness uses independent FP32 Torch autograd references and the
existing dtype-specific tolerances:

- FP16 output and `x` gradient: `rtol=3e-2`, `atol=3e-2`.
- BF16 output and `x` gradient: `rtol=1e-1`, `atol=2e-1`.
- FP32 `weight` gradient: `rtol=5e-3`, `atol=5e-2`.
- `rstd`: `rtol=0`, `atol=1e-3`.

Raw per-case errors, stream identities, cache identities, source paths, native
paths, and environment metadata are in
`reports/j-65dd8f3726b1/results.json`.

## Context

- Upstream context: ROCm/FlyDSL issue 749.
- Existing fixes already present in the tested source include PRs 795, 800,
  855, and 884.
- No upstream issue, PR, or comment was posted or changed.
