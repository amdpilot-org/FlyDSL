# FlyDSL cold/warm JIT measurement on gfx950

## Scope

This report measures one small supported preshuffle GEMM and one RMSNorm on one assigned AMD Instinct MI350X (gfx950). It does not change FlyDSL runtime code and does not rebuild the qualified Torch/ROCm stack.

Upstream context is ROCm/FlyDSL issue 862, "reduce Flydsl compile time". The issue had no comments when read. Its only timeline cross-reference was ROCm/FlyDSL PR 964, which defaults an unset CMake build type to RelWithDebInfo. That PR is merged upstream and present in this mirror's `main`, but it is absent from the image-matched `v0.2.4` source used for measurement.

## Environment

- Image: `amdpilotv2/open-job:gbt350-20260909`, local image ID `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.
- GPU: one AMD Instinct MI350X, gfx950, 256 CUs, about 270.6 GiB reported memory.
- Python: `/opt/venv/bin/python`.
- FlyDSL: 0.2.4 at `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`.
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`, HIP `7.2.26015-fc0010cf6a`.
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`.
- Native JIT runtime libraries:
  - `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/libfly_jit_runtime.so`
  - `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/libmlir_c_runner_utils.so`
- Kernel source: mirror tag `v0.2.4`, commit `145a87651be9b278ea05a701c14b049eecae7db3`, checked out at `/tmp/flydsl-v0.2.4`.
- Private cache: `/tmp/flydsl-cache-j-ce54fc8121f9`, outside `/job/FlyDSL`.

## Method

The benchmark uses FlyDSL 0.2.4's installed Python/native stack and the image-matched `v0.2.4` kernel source. It runs in two processes against the same private disk cache:

1. `cold`: empty cache, first JIT call, followed by an in-process warm call.
2. `warm`: fresh process, first disk-cache call, followed by another in-process warm call.

The script wraps these observable boundaries without changing their behavior:

- `MlirCompiler.compile`: combined frontend, lowering, and embedded code-object generation.
- `CompiledArtifact._ensure_engine`: code-object load and explicit GPU module load.
- `_build_call_state`: host call-state construction.
- Whole JIT call and subsequent `torch.cuda.synchronize()`.

FlyDSL 0.2.4 does not expose separate frontend, lowering, and code-object-generation timers, so those phases are reported as one measured combined interval. The residual total is reported as cache lookup/frontend plus host launch.

Inputs use fixed seed `20260910` and identical shapes in both processes. SHA-256 hashes of the raw tensor bytes are recorded in the JSON. The compiled artifact IR hash and each cache pickle SHA-256 are also recorded.

## Kernels and gates

- GEMM: `compile_preshuffle_gemm`, shape `16x64x64`, tiles `16x64x64`, bf16 input and output. Reference is `torch.mm(a.float(), b.t().float()).to(bfloat16)`. Existing gate is `atol=0.1`, `rtol=0.1`.
- RMSNorm: `build_rmsnorm_module`, shape `16x64`, bf16, epsilon `1e-6`. Reference computes in float32 and casts to bf16. Existing gate is maximum absolute error below `2e-2`.

Both kernels passed their unchanged gates with maximum absolute error `0.0` in cold and warm runs.

## Raw results

All timings are seconds on the CPU-side call path; GPU synchronization is reported separately.

| Kernel | Run | Total JIT call | Frontend/lowering/code object | Code-object load | Call state | GPU sync |
|---|---|---:|---:|---:|---:|---:|
| GEMM | cold | 0.238893 | 0.133640 | 0.022047 | 0.001219 | 0.000231 |
| GEMM | cold in-process warm | 0.000360 | 0 | 0 | 0 | 0.000023 |
| GEMM | warm process disk hit | 0.037367 | 0 | 0.025193 | 0.000820 | 0.000100 |
| GEMM | warm in-process | 0.000243 | 0 | 0 | 0 | 0.000026 |
| RMSNorm | cold | 0.140995 | 0.086580 | 0.019479 | 0.000736 | 0.000098 |
| RMSNorm | cold in-process warm | 0.000267 | 0 | 0 | 0 | 0.000025 |
| RMSNorm | warm process disk hit | 0.021242 | 0 | 0.018650 | 0.000613 | 0.000083 |
| RMSNorm | warm in-process | 0.000189 | 0 | 0 | 0 | 0.000024 |

The cold-to-warm-process first-call reduction was about 84.4% for GEMM and about 85.0% for RMSNorm. The cold-to-in-process-warm reduction was above 99.8% for both.

Artifact IR SHA-256 values were identical across cold and warm:

- GEMM: `0db727c3d52955858a10f8d05625d75f414cded1bb7673115d30860227b5624d`
- RMSNorm: `8b7b7133c225bd7e0994c6dea0a6e50623b0399c9b114e7c6df0457ec9c74d2e`

Cache pickle SHA-256 values were identical before and after the warm process:

- GEMM: `9676722f965c51574053f0d6fc1b882847722d640f543069d3199c711ea0267c` (56,663 bytes)
- RMSNorm: `117ff7f664fe1b8e064abc1ceae6f677e1755f7f5c8fa019831712da81b25d30` (44,150 bytes)

## Candidate decision

No compiler/cache candidate was run. The only issue-linked candidate, ROCm/FlyDSL PR 964, changes the default compiler build type. It does not target the measured runtime JIT frontend/lowering or code-object-load bottleneck, it is already merged upstream, and testing it would require a compiler rebuild, which this task explicitly excludes. The current mirror `main` already contains its CMake default.

## Reproduction

From a clean `v0.2.4` worktree, with the qualified image's `/opt/venv/bin/python` first on `PATH`:

```bash
mkdir -p /tmp/flydsl-cache-j-ce54fc8121f9 /tmp/flydsl-results-j-ce54fc8121f9

PYTHONPATH=/tmp/flydsl-v0.2.4 /opt/venv/bin/python \
  reports/j-ce54fc8121f9/benchmark.py \
  --mode cold \
  --cache-root /tmp/flydsl-cache-j-ce54fc8121f9 \
  --source-root /tmp/flydsl-v0.2.4 \
  --output /tmp/flydsl-results-j-ce54fc8121f9/cold.json

PYTHONPATH=/tmp/flydsl-v0.2.4 /opt/venv/bin/python \
  reports/j-ce54fc8121f9/benchmark.py \
  --mode warm \
  --cache-root /tmp/flydsl-cache-j-ce54fc8121f9 \
  --source-root /tmp/flydsl-v0.2.4 \
  --output /tmp/flydsl-results-j-ce54fc8121f9/warm.json
```

The complete raw JSON is in `results/cold.json` and `results/warm.json`.

## Limitations

- This is a single-run latency probe, not a statistical performance benchmark.
- The GPU reported a low-power state warning before launch; both kernels still executed and synchronized successfully.
- Frontend, lowering, and code-object generation are not separately observable in FlyDSL 0.2.4 without invasive instrumentation, so they are reported as one combined phase.
- No upstream issue, PR, or comment was posted or changed.
