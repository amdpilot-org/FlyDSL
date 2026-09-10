# FlyDSL plain RMSNorm gfx950 validation

This is GPU evidence for existing FlyDSL core behavior. It is not a Quack
repository integration and makes no `torch.compile` support claim.

## Scope

- BF16 and FP16 activations with FP32 weights.
- Plain forward, saved `rstd`, and `x`/`weight` gradients.
- Hidden sizes `512`, `4096`, `4097`, `8191`, and `8192`.
- Non-default current-stream execution and warm in-memory cache reuse.
- Independent FP32 Torch autograd references.
- Existing dtype-specific tolerances, unchanged by this report.

## Reproduction

Use the image's existing `/opt/venv/bin/python` interpreter and one assigned
MI350X. Keep all caches outside the delivery workdir:

```bash
cd /job/FlyDSL
export HOME=/tmp/flydsl-cache-j-65dd8f3726b1/home
export XDG_CACHE_HOME=/tmp/flydsl-cache-j-65dd8f3726b1/xdg
export FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-65dd8f3726b1/runtime
export FLYDSL_AUTOTUNE_CACHE_DIR=/tmp/flydsl-cache-j-65dd8f3726b1/autotune
export TRITON_CACHE_DIR=/tmp/flydsl-cache-j-65dd8f3726b1/triton
mkdir -p "$HOME" "$XDG_CACHE_HOME" "$FLYDSL_RUNTIME_CACHE_DIR" "$FLYDSL_AUTOTUNE_CACHE_DIR" "$TRITON_CACHE_DIR"

/opt/venv/bin/python reports/j-65dd8f3726b1/validate_rmsnorm.py \
  reports/j-65dd8f3726b1/results.json
```

The focused upstream tests can be run with:

```bash
/opt/venv/bin/pytest tests/kernels/test_rmsnorm.py \
  -k 'rmsnorm_mixed_fp32_weight_autograd and not fused_add'
/opt/venv/bin/pytest tests/kernels/test_rmsnorm.py \
  -k 'rmsnorm_fwd_cache_reuses_compiled_launcher or rmsnorm_bwd_two_stage_cache_reuse_across_m and not fused_add or rmsnorm_bwd_two_stage_multistream_workspace'
```

## Evidence

- Tested mirror commit: `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.
- Upstream context: ROCm/FlyDSL issue 749.
- Existing upstream fixes already present in the tested commit include PRs
  795, 800, 855, and 884; this report does not duplicate them.
- Qualified image: `amdpilotv2/open-job:gbt350-20260909`, local image ID
  `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.
- Raw machine-readable results: `reports/j-65dd8f3726b1/results.json`.
