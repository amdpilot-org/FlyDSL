# MI350X gfx950 FP8 `fx.gemm` investigation

## Status

This is a completed, bounded synthetic-operator investigation. It is a negative result for the `BufferCopy` atom path and does not propose a product fix.

On one assigned MI350X (`gfx950`), the FP8 M64/N16/K128 `fx.gemm` path using `UniversalCopy32b` matches the Torch reference. A corrected row-major raw-MFMA control also matches Torch and emits the same 26 VGPR count as `fx.gemm`. The issue 821 raw store emits 24 VGPR, but that store misroutes the MFMA accumulator and fails the unchanged numerical gate.

All tested `BufferCopy` widths fail MLIR legalization for both FP8 and BF16. This means the failure is not specific to FP8 on this image and shape.

## Environment

- Date: 2026-09-09 UTC.
- GPU: one AMD Instinct MI350X, Device ID `0x75a0`, GUID `42642`, GFX `gfx950`, capability `(9, 5)`.
- Qualified image: `amdpilotv2/open-job:gbt350-20260909`, local image ID `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`. The task supplied this local ID; it is not a pullable registry digest. The shell is inside container ID `9c6e3333717ded2ac43b9a9dc4579cd3ecebcf6a0f5d1e373c4bf8a3f21e5863`.
- Python: `/opt/venv/bin/python`, Python 3.12.3.
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`, `/opt/venv/lib/python3.12/site-packages/torch/__init__.py`.
- Torch HIP: `7.2.26015-fc0010cf6a`.
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`, `/opt/venv/lib/python3.12/site-packages/triton/__init__.py`.
- FlyDSL runtime: `0.2.4`, `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`.
- FlyDSL compiler: `/opt/venv/lib/python3.12/site-packages/flydsl/compiler/__init__.py`.
- FlyDSL expression API: `/opt/venv/lib/python3.12/site-packages/flydsl/expr/__init__.py`.
- Embedded MLIR: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/ir.py`.
- AITER distribution metadata: `amd-aiter 0+gd9e5ef7ce08ee7045d583aed768cff41aa9210fe`. `import aiter` triggers a build and then fails with `ModuleNotFoundError: No module named 'aiter.jit.module_aiter_core'`; no other AITER operation was used.
- ROCm native paths: `/opt/rocm-7.2.0/lib/libamdhip64.so.7`, `/opt/rocm-7.2.0/lib/libhipblas.so.3`, and `/opt/rocm-7.2.0/lib/libhipblaslt.so.1`.
- Torch native path: `/opt/venv/lib/python3.12/site-packages/torch/lib`, including `libtorch_hip.so`.
- Working clone: `https://github.com/amdpilot-org/FlyDSL.git`, `main` commit `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.

### Runtime/source limitation

The clone is current `main` (`0.3.3`), but the image's importable FlyDSL package is `0.2.4`. Loading the checkout against the image's older embedded MLIR bindings fails because current `main` imports `CopyOpCDNA4BufferLoadAsyncLDSType`, which the installed bindings do not export. The image has no MLIR development install (`MLIRConfig.cmake`) and no container runtime command, so rebuilding current `main` would require a full LLVM/MLIR build. Therefore, all GPU results here are for the image's actual FlyDSL `0.2.4` stack, not for current `main`. This limitation is not hidden by reusing a MI300 result.

## Issue 821 context

Read-only upstream context came from public GitHub API access to ROCm/FlyDSL issue 821. The mirror has no issue 821, and the authenticated `gh` token was rejected by the upstream organization's fine-grained-token lifetime policy.

The issue reports two MI300 (`gfx942`) findings for FP8 M64/N16/K128:

1. `fx.gemm` used 26 VGPR versus 24 for a raw MFMA microbenchmark.
2. `BufferCopy32b`, `BufferCopy64b`, and `BufferCopy128b` failed with the `fx.gemm` fragment/copy path; only `UniversalCopy32b` compiled.

The issue comment re-verified the VGPR result at upstream `41b8f90a`, including #824. It also reports that #784 changed the 128b failure from a C++ assertion to a catchable MLIR legalization failure, while 32b/64b continued to fail legalization.

The MI300 repro uses `Float8E4M3FNUZ`. FlyDSL's current `gfx950` paths use OCP `Float8E4M3FN`, so this investigation uses `Float8E4M3FN` and `torch.float8_e4m3fn`. Reusing the MI300 FNUZ result as proof would be invalid.

## Method

The harness is `gemm_gfx950_compare.py`. It uses deterministic synthetic tensors with seed `20260909`, one CUDA/ROCm device, one block of 256 threads, and no model weights.

Compiler/runtime options actually used:

- Backend: `rocm`.
- Runtime kind: `rocm`.
- Optimization level: `2`.
- Disk cache: disabled (`FLYDSL_RUNTIME_ENABLE_CACHE=0`).
- IR dump: enabled.
- Final ISA dump: enabled.
- Verifier: enabled.
- Debug info: disabled.
- Actual backend target: `gfx950`, warp size 64.

The command set `FLYDSL_COMPILE_ARCH=gfx950`, but FlyDSL 0.2.4's environment manager reported an empty override field. The backend independently detected and emitted `gfx950`; the final ISA header confirms `amdgcn-amd-amdhsa--gfx950`.

### Numerical gates

The gates were not loosened:

- FP8: `atol=0.1`, `rtol=0.1`.
- BF16: `atol=0.1`, `rtol=0.1`.

The harness records mismatch count, maximum absolute error, mean absolute error, SHA256 of the full output and reference tensors, and the first 16 values of each. Full raw JSON is in `results.json`.

## Results

| Case | Status | Mismatches | Max abs error | VGPR | SGPR | LDS | Scratch |
|---|---:|---:|---:|---:|---:|---:|---:|
| FP8 raw MFMA, issue store | ran but failed gate | 918 | 44.596458435058594 | 24 | 10 | 0 | 0 |
| FP8 raw MFMA, corrected row-major store | passed | 0 | 0.00079345703125 | 26 | 10 | 0 | 0 |
| FP8 `fx.gemm` + `UniversalCopy32b` | passed | 0 | 0.00079345703125 | 26 | 28 | 0 | 0 |
| FP8 `fx.gemm` + `BufferCopy32b` | compile failed | n/a | n/a | n/a | n/a | n/a | n/a |
| FP8 `fx.gemm` + `BufferCopy64b` | compile failed | n/a | n/a | n/a | n/a | n/a | n/a |
| FP8 `fx.gemm` + `BufferCopy128b` | compile failed | n/a | n/a | n/a | n/a | n/a | n/a |
| BF16 raw MFMA | passed | 0 | 0.000003814697265625 | 34 | 10 | 0 | 0 |
| BF16 `fx.gemm` + `UniversalCopy64b` | passed | 0 | 0.00000762939453125 | 40 | 28 | 0 | 0 |
| BF16 `fx.gemm` + `BufferCopy32b` | compile failed | n/a | n/a | n/a | n/a | n/a | n/a |
| BF16 `fx.gemm` + `BufferCopy64b` | compile failed | n/a | n/a | n/a | n/a | n/a | n/a |
| BF16 `fx.gemm` + `BufferCopy128b` | compile failed | n/a | n/a | n/a | n/a | n/a | n/a |

### FP8 interpretation

- The issue-style raw store emits 24 VGPR, but it writes the 16x16 MFMA accumulator transposed within each tile. It fails 918/1024 gate checks and is not a valid correctness control.
- The corrected raw store uses `row = warp * 16 + rgroup * 4 + r`, `col = lane16`, passes the gate, and emits 26 VGPR.
- `fx.gemm` also passes and emits 26 VGPR. On this `gfx950` image stack, there is no 24-vs-26 VGPR overhead once the raw path produces the correct row-major output.
- Both passing FP8 paths have identical maximum absolute error (`0.00079345703125`) and identical full-output SHA256 (`dcfd453b455a067e8589498c415cbe061b60bf7def60919fa08fe9f517cd3304`).

### BufferCopy interpretation

Every FP8 and BF16 `BufferCopy` case fails before ISA emission with `DSLCompileError`:

```text
failed to legalize operation 'fly.copy_atom_call_ssa' that was explicitly marked illegal
```

The FP8 failures show these atom/result combinations:

- 32b: `buffer_copy<32>` with `vector<4xi8>`.
- 64b: `buffer_copy<64>` with `vector<8xi8>`.
- 128b: `buffer_copy<128>` with `vector<8xi8>`.

The BF16 failures show the same class:

- 32b: `buffer_copy<32>` with `vector<2xbf16>`.
- 64b: `buffer_copy<64>` with `vector<4xbf16>`.
- 128b: `buffer_copy<128>` with `vector<4xbf16>`.

Thus, on this image and shape, the `BufferCopy` legalization failure is not FP8-specific.

## Reproduction

From the repository root:

```bash
FLYDSL_COMPILE_ARCH=gfx950 \
/opt/venv/bin/python reports/j-e53e86456ec4/gemm_gfx950_compare.py \
  fp8_gemm_universal32 --dump-root /job/artifacts/dumps
```

Replace `fp8_gemm_universal32` with any case listed in `commands.txt`. Each case runs in its own process so a compile failure cannot contaminate later measurements. `results.json` contains the raw result objects.

## Left undone

- No current-`main` GPU run: the image lacks a matching MLIR development install, and its installed bindings are too old for the checkout.
- No performance timing or occupancy sweep: the task requested correctness and emitted resources, not throughput.
- No model weights or external frameworks were downloaded or installed.
- No upstream issue, PR, comment, or review was posted or modified.
