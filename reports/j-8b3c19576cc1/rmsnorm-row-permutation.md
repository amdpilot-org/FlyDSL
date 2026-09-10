# RMSNorm row-permutation validation

## Result

Permuting independent RMSNorm rows and restoring their order preserved every
output and `rstd` value exactly on MI350X/gfx950. The direct results also stayed
within the existing dtype gates against an independent CPU float64 reference.
This isolates unintended cross-row dependence without changing dtype, layout,
or epsilon semantics.

The checkout base was `ed70142704e1a6d5563fb53e1607e3a4b85d7111`. The test was
added in `tests/kernels/test_rmsnorm.py`; no production kernel behavior was
changed.

## Environment

- Interpreter: `/opt/venv/bin/python` (Python 3.12.3)
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`, `/opt/venv/lib/python3.12/site-packages/torch/__init__.py`
- Torch native: `/opt/venv/lib/python3.12/site-packages/torch/lib/libtorch_hip.so`
- FlyDSL runtime: published wheel `0.3.2`, loaded from `/tmp/flydsl-cache-j-8b3c19576cc1/wheel-0.3.2/flydsl/__init__.py`
- FlyDSL native:
  `/tmp/flydsl-cache-j-8b3c19576cc1/wheel-0.3.2/flydsl/_mlir/_mlir_libs/_mlirDialectsFlyROCDL.cpython-312-x86_64-linux-gnu.so`
- FlyDSL native runtime:
  `/tmp/flydsl-cache-j-8b3c19576cc1/wheel-0.3.2/flydsl/_mlir/_mlir_libs/libfly_jit_runtime.so`
- Checkout kernel: `/job/FlyDSL/kernels/norm/rmsnorm_kernel.py`
- GPU: one AMD Instinct MI350X, gfx950, device ID `0x75a0`, GUID `51966`
- Image: `amdpilotv2/open-job:gbt350-20260909`, local image ID `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`

The installed wheel remains FlyDSL `0.2.4`; `0.3.2` was downloaded to the
job-private cache and selected only through `PYTHONPATH`. No environment or
node-wide state was replaced.

## Commands

```bash
export PYTHONPATH=/tmp/flydsl-cache-j-8b3c19576cc1/wheel-0.3.2:/job/FlyDSL
export FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-8b3c19576cc1/runtime-cache
export FLYDSL_AUTOTUNE_CACHE_DIR=/tmp/flydsl-cache-j-8b3c19576cc1/autotune-cache
export XDG_CACHE_HOME=/tmp/flydsl-cache-j-8b3c19576cc1/xdg-cache
export TRITON_CACHE_DIR=/tmp/flydsl-cache-j-8b3c19576cc1/triton-cache

/opt/venv/bin/python -m pytest tests/kernels/test_rmsnorm.py \
  -k 'row_permutation or eps_honored' -vv -s --tb=short
```

## Cases and gates

Each case uses 16 rows, `eps=1e-6`, a deterministic permutation, and neighboring
row scales from `1e-6`, `1e-3`, `1`, `1e3`, and `1e6`. Sentinels require finite
values, positive `rstd`, output magnitude below `8`, and `rstd` magnitude below
`2e6`. Restored rows must be exactly equal with `torch.equal`.

The unchanged reference gates are:

- FP32 output: `rtol=1e-4`, `atol=1e-4`
- BF16 output: `rtol=2e-2`, `atol=2e-2`
- `rstd`: `rtol=1e-3`, `atol=1e-3`

| Path | N / activation / weight | Output max abs error | Rstd max abs error | Restored exact |
| --- | --- | ---: | ---: | --- |
| Small-N | 512 / FP32 / FP32 | `7.153e-07` | `6.104e-05` | Yes |
| Generic scalar | 3000 / FP32 / FP32 | `4.768e-07` | `5.960e-08` | Yes |
| Vec8 mixed weight | 4096 / BF16 / FP32 | `1.518e-02` | `1.192e-07` | Yes |

The existing epsilon control also passed on N=256 and N=3000 for `eps` values
`1e-5`, `1e-6`, and `1e-2`. Its maximum output errors were `2.384e-07` or
`4.768e-07`, and the `1e-2` versus `1e-6` output difference was nonzero.

## Installed-source baseline

Before cloning or editing, the qualified stack's native
`aten::_fused_rms_norm` control was run on the same GPU. The 16x4096 FP32 case
passed exact restored-row equality for both output and `rstd`; CPU float64
reference errors were `1.3793463124633678e-07` and `7.93400577296307e-08`.
The first CUDA-event timing was `4.046998977661133 ms`, with process wall time
to first GPU completion `1.5893001100048423 s`. The complete artifact is
`/job/baseline-first.json`.

This baseline is explicitly labeled installed-source evidence and is not proof
for later checkout changes. The checkout results above are the relevant evidence
for this patch.

## Context

Read-only context came from ROCm/FlyDSL issue 749 and its current description,
comments, and related changes. The relevant landed changes include plain
backward and forward `rstd` support, fused-add backward, staged dweight
reduction, and FP32 weights with FP16/BF16 activations. No upstream issue, PR,
or comment was posted or changed.
