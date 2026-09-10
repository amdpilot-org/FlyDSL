# Fused Stage1 Mapping Slice

## Result

The bounded mapping slice passed on one assigned MI350X (`gfx950`). No token/expert mapping or sentinel-bound defect was demonstrated, so no kernel correction was made.

Issue 725 remains open as a feature request for `fused_stage1(dispatch+sorting+swizzle+gemm1)`. Its comments identify upstream PR 876 as the MegaMoE merge. This investigation preserved and tested exact merge commit `dc8e1539b24fb8e06357c6385139a8f5307173cc`; it did not duplicate that already-working change.

## Environment

- Image: `amdpilotv2/open-job:gbt350-20260909`, ID `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.
- GPU: one AMD Instinct MI350X, GFX version `gfx950`, serial `692517020475`, unique ID `0x593d46f1dbb5dce5`, 256 CUs.
- Python: `/opt/venv/bin/python3` (3.12.3).
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`; Triton: `3.5.1+rocm7.2.0.gita272dfa8`.
- Installed FlyDSL: `0.2.4`, Python `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`, native `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`.
- Mapping kernel source: `/job/FlyDSL-dc8e153/kernels/moe/moe_sorting_kernel.py` at commit `dc8e1539b24fb8e06357c6385139a8f5307173cc`.
- Current-main GEMM1 source: `/job/FlyDSL/kernels/moe/moe_gemm_2stage/gemm1.py` at base `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.
- Job-private caches: `/tmp/flydsl-cache-j-f48e2e4d7ec1`; no model weights or framework stack were downloaded.

## Mapping Probe

`stage1_mapping_probe.py` compares the GPU sorting output with an independent CPU/Torch reference. It checks exact packed token IDs, weights, compacted expert IDs, both `num_valid_ids` entries, valid/block bounds, tail sentinels, zero tail weights, and inactive expert tails.

The routes cover a repeated hot expert across tokens, inactive experts through an expert mask, 8- and 48-expert geometries, topk 2 and 8, and token counts 1, 3, 7, 15, 16, 17, 31, 32, and 33. Counts through 16 use the oneshot path; 17 and above use the multiphase path.

All 11 cases passed. Raw values are in `stage1_mapping_results.json`; the compact results are:

| Case | Tokens | Valid IDs | Valid blocks | Sentinel |
|---|---:|---:|---:|---:|
| hot_inactive_tail_1 | 1 | 32 | 1 | `0x02000001` |
| hot_inactive_tail_3 | 3 | 32 | 1 | `0x02000003` |
| hot_inactive_tail_7 | 7 | 32 | 1 | `0x02000007` |
| hot_inactive_tail_15 | 15 | 32 | 1 | `0x0200000f` |
| hot_inactive_tail_16 | 16 | 32 | 1 | `0x02000010` |
| hot_inactive_tail_17 | 17 | 32 | 1 | `0x02000011` |
| hot_inactive_tail_31 | 31 | 32 | 1 | `0x0200001f` |
| hot_inactive_tail_32 | 32 | 32 | 1 | `0x02000020` |
| hot_inactive_tail_33 | 33 | 64 | 2 | `0x02000021` |
| spread_inactive_48_tail_1 | 1 | 128 | 4 | `0x08000001` |
| spread_inactive_48_tail_17 | 17 | 128 | 4 | `0x08000011` |

## GEMM1 Control

One small supported current-main GEMM1 control passed:

```text
pytest -q 'tests/kernels/test_moe_gemm_2stage.py::test_moe_gemm1_numeric[16-8-bf16-fp8]'
1 passed
```

The unchanged numerical gate is cosine similarity greater than `0.99`. The result is recorded in `gemm1_control_result.json`.

## Limitations

- The image's installed FlyDSL `0.2.4` lacks `flydsl.expr.coop` and the newer CDNA4 async-copy MLIR symbol required by current-main `moe_sorting_kernel.py`. The mapping probe therefore used the preserved PR 876 source with the image's existing native bindings through a job-private source overlay.
- `MegaMoEV2` fused dispatch could not be launched in this image: importing `kernels.mega_moe.mega_moe` fails because the `mori` Python package is absent. The task also assigned one GPU, while the fused dispatch path is designed around eight ranks. No substitute framework was installed.
- No upstream issue, PR, or comment was posted or changed.

## Reproduction

The exact mapping run used a detached worktree at `dc8e153`, a job-private source overlay, and the image's existing native `_mlir`:

```bash
git worktree add --detach ../FlyDSL-dc8e153 dc8e153
CACHE=/tmp/flydsl-cache-j-f48e2e4d7ec1
mkdir -p "$CACHE/src-overlay-dc8e153/python"
cp -a ../FlyDSL-dc8e153/python/flydsl "$CACHE/src-overlay-dc8e153/python/"
ln -s /opt/venv/lib/python3.12/site-packages/flydsl/_mlir \
  "$CACHE/src-overlay-dc8e153/python/flydsl/_mlir"
export PYTHONPATH="$CACHE/src-overlay-dc8e153/python:$(pwd)/../FlyDSL-dc8e153"
export FLYDSL_RUNTIME_CACHE_DIR="$CACHE/runtime-dc8e153"
export FLYDSL_AUTOTUNE_CACHE_DIR="$CACHE/autotune-dc8e153"
cd ../FlyDSL-dc8e153
python ../FlyDSL/reports/j-f48e2e4d7ec1/stage1_mapping_probe.py
```

The GEMM1 control used current main with a job-private `sitecustomize.py` that only supplied the missing `get_warp_size` compatibility helper to installed FlyDSL `0.2.4`:

```bash
export PYTHONPATH=/tmp/flydsl-cache-j-f48e2e4d7ec1:/job/FlyDSL
export FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-f48e2e4d7ec1/runtime-current
export FLYDSL_AUTOTUNE_CACHE_DIR=/tmp/flydsl-cache-j-f48e2e4d7ec1/autotune-current
pytest -q 'tests/kernels/test_moe_gemm_2stage.py::test_moe_gemm1_numeric[16-8-bf16-fp8]'
```
