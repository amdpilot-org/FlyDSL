# GEMM2/combine coverage on gfx950

## Result

The bounded GEMM2/combine investigation passed on one assigned AMD Instinct MI350X using the existing small `moe_gemm_2stage` FP8 reduce path. The new test covers:

- non-uniform top-k weights (`0.25` and `0.75`);
- duplicate expert routes in every token row;
- a ragged 7-token input with `tile_m=16`;
- 12 routing padding rows;
- output accumulation by summing the two per-slot reduce rows;
- an independent, directly dequantized Torch FP32 reference.

The unchanged numerical gate from the existing stage-2 tests remains `cosine similarity > 0.99`. The measured result was:

| Metric | Value |
|---|---:|
| Cosine similarity | 0.9999973177909851 |
| Relative L2 | 0.002321361331269145 |
| Maximum absolute error | 0.013124942779541016 |
| Mean absolute error | 0.0012168334797024727 |
| Reference L2 | 32.9512825012207 |
| Gate | PASS |

This is coverage of GEMM2/combine semantics only. It does not validate GEMM1 dispatch/sorting, persistent scheduling, multi-rank P2P transport, or the fused MegaMoE pipeline.

## Actual routing

The logical routing was:

```text
[[0, 0], [1, 1], [2, 2], [3, 3], [0, 0], [1, 1], [2, 2]]
```

Every row uses the same expert twice. Expert route counts were `[4, 4, 4, 2]`, for 14 logical routes. The sorted buffer capacity was 76 rows, `num_valid_ids` was 64, and 12 rows were padding. Slot weights were `[0.25, 0.75]` for every token. The complete sorted IDs, weights, expert block IDs, and padding state are in `gemm2_combine_results.json`.

## Kernel and dtype identities

The supported path used:

- source: `kernels/moe/moe_gemm_2stage/gemm2.py`;
- launcher: `launch_moe_gemm2`;
- GPU function: `moe_gemm2_0`;
- profiler: five launches, 24.635 µs total device time;
- cache artifact: `/tmp/flydsl-cache-j-f48f52cfae33/gemm2-report/launch_moe_gemm2_5646ea41a1580764e5a269b02f458c3c/b3c9c01d4fe59dac.pkl`;
- artifact SHA-256: `8f31fb799fb2dd31b48dfc7250b807cb179187175cfe3ffab3aee11f6db0491a`;
- LDS: 4096 bytes/CTA;
- VGPR/SGPR/AGPR: 34/26/0;
- VGPR/SGPR spills: 0/0;
- wavefront size: 64;
- max flat workgroup size: 256.

Dtype identities were:

| Operand | Dtype |
|---|---|
| Kernel input label | `fp8` |
| Activation payload | `torch.float8_e4m3fn` |
| Activation scale | `torch.float32` |
| Weight payload | `torch.float8_e4m3fn` |
| Weight scale | `torch.float32` |
| Kernel output | `torch.bfloat16` |
| Independent reference | `torch.float32` |

## Environment

- GPU: one AMD Instinct MI350X, `gfx950:sramecc+:xnack-`, 256 CUs, Torch UUID `35666234-3266-6639-3038-363630363065`.
- ROCm driver: `7.1.1.31500000`; GPU serial `692517020502`; unique ID `0x5fb42ff90866060e`.
- Image: operator-provided local image ID `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`. Container hostname was not used as image identity.
- Source: `/job/FlyDSL`, base commit `ed70142704e1a6d5563fb53e1607e3a4b85d7111`, branch `amdpilot/j-f48f52cfae33`.
- Python: `/opt/venv/bin/python`, Python 3.12.3.
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`; HIP `7.2.26015-fc0010cf6a`.
- Installed FlyDSL: version `0.2.4` at `/opt/venv/lib/python3.12/site-packages/flydsl`.
- Native modules are under `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs`; the full path list is recorded in `gemm2_combine_results.json`.
- Job-private caches: `/tmp/flydsl-cache-j-f48f52cfae33/gemm2-report` and `/tmp/flydsl-cache-j-f48f52cfae33/triton`.

No full model weights were downloaded, no node-wide state was changed, and no upstream issue, PR, or comment was posted or modified.

## Unsupported paths

The qualified image intentionally preserves its installed Torch/ROCm stack. Its FlyDSL `0.2.4` runtime predates two APIs used by current source:

1. The `moe_gemm_2stage` atomic epilogue fails during compilation with:

   ```text
   AttributeError: module 'flydsl.expr.rocdl' has no attribute 'get_buffer_rsrc'
   ```

2. The fused MegaMoE GEMM2/P2P combine path fails during compilation with:

   ```text
   AttributeError: module 'flydsl.expr.rocdl' has no attribute 'make_buffer_ptr'
   ```

No compatibility shim, package replacement, or fused-pipeline substitute was invented. The reduce path avoids those APIs and is the small supported GPU path used for coverage.

## Upstream context

- ROCm/FlyDSL issue 727, `[Feature]: Support Mega-Moe V1`, is open. Its description requests fused dispatch/sorting/GEMM1 and GEMM2/combine. Its three comments record combine optimization work, E2E imbalance observations, merging stage-1/stage-2 into one Mega op, and a GEMM1 interleave optimization.
- ROCm/FlyDSL PR 876, `MegaMoE on Gfx950`, is merged and introduced MegaMoEV2 with fused GEMM2/weighted P2P combine.
- ROCm/FlyDSL PR 947, `[MoE] Port moe_gemm_2stage (stage1+stage2) to the new fx.* pipeline`, is merged and provides the small supported reduce path exercised here.
- ROCm/FlyDSL PR 932, `fix(mega_moe): correct GEMM2 A-scale indexing for BM=16`, is closed and unmerged. Its head commit is `a59eca588a962373baede3fb4e63a4c1e9552b3c`. Current `main` still contains the old BM=16 A-scale indexing. The existing fix was not copied or duplicated; the fused path could not be compiled in this installed runtime, so no candidate result is claimed.

## Reproduction

```bash
export FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-f48f52cfae33/gemm2-report
export TRITON_CACHE_DIR=/tmp/flydsl-cache-j-f48f52cfae33/triton

/opt/venv/bin/python -m pytest \
  tests/kernels/test_moe_gemm_2stage.py::test_moe_gemm2_duplicate_routes_padded_reduce \
  -q --no-header

/opt/venv/bin/python \
  reports/j-f48f52cfae33/validate_gemm2_combine.py
```

The report harness writes `reports/j-f48f52cfae33/gemm2_combine_results.json`. It records the environment, complete routing buffers, dtype identities, profiler events, cache artifact resources, raw metrics, unchanged gate, and both unsupported-path exceptions.
