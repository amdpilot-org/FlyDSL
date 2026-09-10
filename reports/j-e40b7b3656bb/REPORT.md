# MoE GEMM1 persistent-mode investigation on gfx950

## Result

FlyDSL already has one supported persistent GEMM1 candidate: the standalone MegaMoE GEMM1 in `kernels/mega_moe/gemm1.py`. Its grid-stride loop can launch one work tile per CTA (ordinary) or cap the grid at 1024 CTAs on the assigned 256-CU MI350X (persistent).

On small synthetic expert-grouped A8W4 inputs, both schedules produced identical correctness metrics and passed the unchanged existing stage-1 gate, `relative L2 < 0.10`. Persistent scheduling was slower in all four bounded comparisons:

| Distribution | Tile N | Schedule | Grid CTAs | Mean warm time | Torch relL2 | Gate |
|---|---:|---|---:|---:|---:|---|
| uniform | 128 | ordinary | 4096 | 24.968 us | 0.026478 | PASS |
| uniform | 128 | persistent | 1024 | 27.564 us | 0.026478 | PASS |
| uniform | 256 | ordinary | 2048 | 22.362 us | 0.026478 | PASS |
| uniform | 256 | persistent | 1024 | 23.554 us | 0.026478 | PASS |
| skewed | 128 | ordinary | 4080 | 24.990 us | 0.026480 | PASS |
| skewed | 128 | persistent | 1024 | 27.456 us | 0.026480 | PASS |
| skewed | 256 | ordinary | 2040 | 22.046 us | 0.026480 | PASS |
| skewed | 256 | persistent | 1024 | 23.103 us | 0.026480 | PASS |

Persistent/ordinary ratios were 1.104 and 1.053 for uniform tile-N 128 and 256, and 1.099 and 1.048 for skewed tile-N 128 and 256. This is a negative performance result for the tested small shapes, not evidence that persistent GEMM1 is generally unsuitable.

## Upstream context

- ROCm/FlyDSL issue 726, `[Feature]: moe gemm1 support persistent mode`, is open. Its current description is only `moe gemm1 support persistent mode`; it has no comments and no linked branch or pull request on the issue page.
- ROCm/FlyDSL PR 282, `feat(moe): enable FP4 A-scale and persist_m support for MoE GEMM kernels`, is a closed draft. Its `persist_m` loop is in GEMM2, not GEMM1, and its old monolithic source does not apply cleanly to current main. It was not adopted or duplicated.
- Current `mxfp_moe` and `moe_2stage_a16wmix` GEMM1 launchers are flattened non-persistent grids. Their GEMM2 paths contain persistent worklists, but those are different primitives. No new scheduler was built.

## Experiment

- GPU: one AMD Instinct MI350X, `gfx950:sramecc+:xnack-`, serial `692517020434`, 256 CUs, 258032 MiB reported by Torch.
- Image: local image ID `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7` (operator-provided identity; hostname was not used as image identity).
- Source: `/job/FlyDSL`, base commit `ed70142704e1a6d5563fb53e1607e3a4b85d7111`, branch `amdpilot/j-e40b7b3656bb`.
- Python: `/opt/venv/bin/python`, Python 3.12.3.
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`; HIP `7.2.26015-fc0010cf6a`.
- FlyDSL package: `/opt/venv/lib/python3.12/site-packages/flydsl`.
- Native runtime examples: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/libfly_jit_runtime.so`, `_mlirDialectsFlyROCDL.cpython-312-x86_64-linux-gnu.so`, `_mlirDialectsFly.cpython-312-x86_64-linux-gnu.so`, and `libMLIRPythonSupport-mlir.so`.
- Job-private caches: `/tmp/flydsl-cache-j-e40b7b3656bb/runtime` and `/tmp/flydsl-cache-j-e40b7b3656bb/triton`.

The installed FlyDSL package lacks the current source's `fx.max` wrapper. The harness adds the compatibility alias `fx.max = fx.maxnumf` before importing the kernel. No numerical gate or kernel implementation was changed.

### Inputs and oracle

- `model_dim=256`, `inter_dim=512`, 8 experts, `sort_block_m=32`, `tile_k=256`, 4 waves, 256 threads/CTA.
- A8W4: MXFP8 activations and MXFP4 gate/up weights; MXFP8 stage-1 output.
- Uniform counts: `[2048] * 8` (16384 rows).
- Skewed counts: `[8192, 4096, 2048, 1024, 512, 256, 128, 64]` (16320 rows). Every count is a multiple of 32, so grouped source and compact output rows coincide.
- Tile-N candidates: 128 and 256. Ordinary scheduling uses `grid_x=total_work`; persistent uses `grid_x=min(total_work, 256*4)=1024`.
- Torch reference dequantizes MXFP8 A and MXFP4 W, computes gate and up matmuls per expert, applies `silu(gate) * up`, and dequantizes the kernel's MXFP8 output with its E8M0 scale.
- The unchanged gate is `relative L2 < 0.10`, matching the existing non-A4W4 MegaMoE stage-1 floor. No tolerance was widened.
- Timing uses 10 warmup launches followed by 50 timed launches with CUDA events. A separate five-launch Torch profiler window observed five CUDA kernel events, confirming one kernel launch per call.

### Resource usage

The compiled gfx950 artifacts report:

| Tile N | LDS bytes/CTA | VGPRs | SGPRs | AGPRs | VGPR/SGPR spills | Private bytes | Max flat WG |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 16640 | 72 | 54 | 0 | 0 / 0 | 0 | 256 |
| 256 | 16640 | 108 | 57 | 0 | 0 / 0 | 0 | 256 |

Both artifacts use 64-thread wavefronts. Torch reported about 162 MiB allocated and 291–294 MiB reserved during the runs. `rocm-smi` reported 1407254528 bytes total VRAM in use on the GPU at the report snapshot; that is device-wide usage, not attribution to this process alone.

## Reproduction

From `/job/FlyDSL`:

```bash
export PYTHONPATH=/job/FlyDSL
export FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-e40b7b3656bb/runtime
export TRITON_CACHE_DIR=/tmp/flydsl-cache-j-e40b7b3656bb/triton
mkdir -p "$FLYDSL_RUNTIME_CACHE_DIR" "$TRITON_CACHE_DIR"
/opt/venv/bin/python reports/j-e40b7b3656bb/bench_persistent_gemm1.py \
  --output reports/j-e40b7b3656bb/persistent_gemm1_results.json
```

The command is bounded to eight measured cases, two compiled tile variants, 10 warmup and 50 timed launches per case, and a five-launch profiler window. It does not download weights or modify node-wide state.

## Limitations

- This is a small synthetic microbenchmark, not a full MoE model or production-shape sweep.
- Only MegaMoE standalone GEMM1 was tested as the supported persistent GEMM1 candidate. The other current GEMM1 families do not expose a persistent primitive, and no new scheduler was built.
- The timing comparison uses the same compiled kernel and changes only `grid_x`; this isolates the existing grid-stride loop but does not test a fused dispatch producer or cross-XCD placement policy.
- The installed FlyDSL/source API mismatch required the documented `fx.maxnumf` compatibility alias. A source-matched FlyDSL build could remove that uncertainty.
- Raw results are retained in `persistent_gemm1_results.json`; timings are single-run means and should not be treated as a production tuning conclusion.
