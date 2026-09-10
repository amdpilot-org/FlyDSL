# Conv3d structural impulse-response validation

## Result

Current `main` already implements the layout support requested by ROCm/FlyDSL issue 993. This change does not duplicate that fix; it adds a distinct structural oracle to `tests/kernels/test_conv3d_implicit.py`.

The oracle uses a `(2, 3, 5, 5, 5)` bfloat16 input and a `(4, 3, 3, 3, 3)` weight. Six impulses distinguish batch, input-channel, and spatial mapping. Four asymmetric nonzero taps distinguish output-channel and kernel orientation. It covers all four `input_layout`/`output_layout` combinations and two stride/padding cases:

- `stride=(1,1,1), padding=(1,1,1)`
- `stride=(2,1,2), padding=(1,0,1)`

The independent reference is Torch CPU float32 cross-correlation through `torch.nn.functional.conv3d`, cast to bfloat16. The existing numerical gate remains `torch.allclose(..., rtol=2e-2, atol=2e-2)`.

## Environment

- GPU: one AMD Instinct MI350X, `gfx950`, capability `(9,5)`, serial `692517019400`.
- Image: `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.
- Python: `/opt/venv/bin/python`.
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`, HIP `7.2.26015-fc0010cf6a`.
- Installed FlyDSL: `0.2.4` at `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`.
- Checkout runtime: FlyDSL `0.3.2` extracted to `/tmp/flydsl-cache-127556238a1c/wheel-0.3.2/flydsl/__init__.py`.
- Source: `/job/FlyDSL`, branch `amdpilot/j-127556238a1c`, base commit `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.

## Commands

```bash
export PYTHONPATH=/tmp/flydsl-cache-127556238a1c/wheel-0.3.2:/job/FlyDSL
export FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-127556238a1c/runtime
export FLYDSL_AUTOTUNE_CACHE_DIR=/tmp/flydsl-cache-127556238a1c/autotune

/opt/venv/bin/python -m pytest -q tests/kernels/test_conv3d_implicit.py \
  -k structural_impulse_response
/opt/venv/bin/python -m pytest -q tests/kernels/test_conv3d_implicit.py
```

## Raw results

- Focused impulse oracle: **8 passed**, 0 failed, final pytest duration **2.68 s**, surrounding wall time **4.901230379 s**. An earlier identical run before removing an unused local unpack took **4.57 s**.
- Full affected file: **65 passed**, 0 failed, pytest duration **221.24 s**, surrounding wall time **224.341410726 s**.
- Installed-source baseline: `/job/baseline-first.json`; first synchronized GPU execution **3.6251891599968076 s**, Torch CPU reference `allclose=true`, max absolute error `0.0`.
- Installed FlyDSL `0.2.4` control failed with `TypeError: s_waitcnt() got an unexpected keyword argument 'lgkmcnt'`; the matching FlyDSL `0.3.2` runtime passed the same existing GPU test.

Timing uses pytest's reported duration plus one surrounding `date +%s%N` wall measurement. There are no synthetic burn loops, unbounded loops, sleep loops, or repeated work.

## Scope and uncertainty

- ROCm/FlyDSL issue 993 and its comments were read only; no upstream issue, PR, or comment was posted or changed.
- Open mirror PRs 417 and 434 were inspected. Their random layout-edge and boundary coverage is distinct from this structural impulse oracle.
- No kernel implementation change was needed because current `main` already supports the requested layouts.
- The report does not claim the installed-source baseline validates later checkout changes.
