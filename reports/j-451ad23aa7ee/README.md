# FlyDSL plain RMSNorm larger-hidden-size evidence

This report addresses the larger-hidden-size limitation named in ROCm/FlyDSL
issue 749. It is distinct from mixed-weight streams and fused-add/residual
backward work already present in the tested commit.

Issue 749 currently states that larger hidden sizes remain unsupported until
tested. The related changes already present in the tested base are PRs 795
(`rstd` and plain backward), 800 (fused-add backward), 855 (staged backward
reduction), 884 (mixed-weight support), and 902 (kernel-style alignment). This
report does not duplicate those changes or broaden their claims.

## Scope and admission

- Forward-only plain RMSNorm with matching BF16 activations and weights.
- Independent FP32 Torch output and `rstd` references.
- Hidden sizes `8192`, `8193`, `10240`, `12288`, `14336`, and `16384`.
- `4096` rows, `eps=1e-5`, one assigned MI350X (`gfx950`).
- Output tolerance `atol=2e-2`; `rstd` tolerance `atol=1e-3`.
- `8193` exercises the scalar guarded tail path; multiples of 2048 exercise
  complete 128-bit vector tiles.

This run admits only the tested forward-only matching-BF16 cases through
`16384`. It does **not** claim backward, autograd, mixed-weight, fused-add,
other-dtype, non-contiguous, empty-row, other-architecture, or larger-size
support. Backward dispatch above `8192` remains on the atomic path and was not
measured here.

## Reproduction

Use the qualified image interpreter and keep caches outside the delivery
checkout:

```bash
cd /job/FlyDSL
export FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-451ad23aa7ee
export FLYDSL_GPU_ARCH=gfx950
export PYTHONPATH=/tmp/flydsl-wheel-j-451ad23aa7ee:/job/FlyDSL
/opt/venv/bin/python reports/j-451ad23aa7ee/validate_rmsnorm_forward.py \
  reports/j-451ad23aa7ee/results.json
```

The job-private FlyDSL 0.3.2 wheel supplies the compiler/runtime API expected
by this checkout while preserving the image's Torch 2.9.1+rocm7.2 and Triton
3.5.1+rocm7.2 stack. The installed 0.2.4 wheel cannot import the current
checkout because `get_warp_size` is absent from its runtime module.

The focused regression test is:

```bash
cd /job/FlyDSL
PYTHONPATH=/tmp/flydsl-wheel-j-451ad23aa7ee:/job/FlyDSL \
FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-451ad23aa7ee \
FLYDSL_GPU_ARCH=gfx950 \
/opt/venv/bin/pytest tests/kernels/test_rmsnorm.py \
  -k test_rmsnorm_forward_large_hidden_sizes
```

## Evidence

- Tested mirror base commit: `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.
- Qualified image: `amdpilotv2/open-job:gbt350-20260909`, local image ID
  `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.
- Raw machine-readable results: `reports/j-451ad23aa7ee/results.json`.
- Timing is bounded with CUDA events: one warmup followed by 20 timed calls.
- No synthetic burn, unbounded loop, sleep loop, model-weight download, or
  repeated GPU work is used.
