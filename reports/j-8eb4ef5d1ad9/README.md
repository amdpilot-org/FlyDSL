# conv3d_implicit layout validation on MI300X

## Result

This is a truthful negative result for the assigned MI300X (`gfx942`). The tested candidate already implements the requested `conv3d_implicit(..., layout=..., out_layout=...)` API, but its bf16 implicit-GEMM kernel uses a CDNA4-only MFMA/LDS path. Direct execution on `gfx942` aborts in LLVM during code generation before either synthetic chain can produce a tensor. No numerical comparison or device timing is therefore possible on this GPU.

The candidate is reported as already-fixed rather than duplicated. Its implementation and tests are preserved verbatim in this branch; this directory adds only the gfx942 reproduction and raw evidence.

## Candidate and source

- Mirror: `https://github.com/amdpilot-org/FlyDSL.git`
- Delivery branch: `amdpilot/j-8eb4ef5d1ad9`, cut from `main` at `ed70142704e1a6d5563fb53e1607e3a4b85d7111`
- Tested candidate branch: `origin/amdpilot/j-d84b12979282`
- Tested candidate tip: `19f7acc4e61f06f99742ffcb326585be43fb685a`
- Candidate commits preserved by merge: `2ba80a8`, `34e3b56`, `13d0e06`, `b3a8377`, `9e5ea6d`, `11fd9dd`, `3499f64`, `0e80deb`, `2663643`, `2f91b55`, `19f7acc`
- Read-only context: ROCm/FlyDSL issue 993, “conv3d_implicit — accept and emit NDHWC so chained convs skip the layout round-trip”

The candidate exposes the exact source-facing names `layout` and `out_layout`, defaults `layout="NCDHW"`, and makes `out_layout=None` inherit `layout`. It also preserves the rank-specific `input_layout`/`output_layout` aliases with conflict checks.

## Environment

- Expected qualified image: `amdpilotv2/open-job-mi300:jit-config-readable-35122-260909`
- Operator-provided local image ID: `sha256:dfc9419089c338b5712da4841768b38b1ab79f3da41f8c58c3cd4dfcc1147ff1`
- Host: `banff-cyxtera-cx57-4`
- GPU: one AMD Instinct MI300X, serial `692440004420`, GFX `gfx942`, node ID 3
- Python: `/opt/venv/bin/python`, Python `3.10.12`
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`
- HIP: `7.2.26015-fc0010cf6a`
- `hipcc`: HIP `7.2.26015-fc0010cf6a`; AMD clang `22.0.0git`
- Installed FlyDSL: `0.3.1`, `/opt/venv/lib/python3.10/site-packages/flydsl/__init__.py`
- Working source: `/job/FlyDSL`, source version marker `0.3.3`, commit `5d4a1104172cdd241f69c6362e6abc2a8cf1defe`
- Working conv source: `/job/FlyDSL/kernels/conv/conv3d_implicit.py`
- Native JIT runtime: `/opt/venv/lib/python3.10/site-packages/flydsl/_mlir/_mlir_libs/libfly_jit_runtime.so`
- Native MLIR support: `/opt/venv/lib/python3.10/site-packages/flydsl/_mlir/_mlir_libs/libFlyPythonCAPI.so.24.0git`

The installed FlyDSL native stack is `0.3.1` while the working source reports `0.3.3`; this mismatch is recorded rather than hidden. No MLIR install with `lib/cmake/mlir` was available for a source-native rebuild, so no source C++ build was attempted. The working clone's Python/kernel code was used with the qualified image's installed native FlyDSL runtime. This kept the Torch/ROCm stack unchanged and avoided an unbounded LLVM build/download.

## Synthetic validation

`validate_conv3d_layout_gfx942.py` uses only local synthetic bf16 tensors:

- input `(1, 32, 4, 8, 8)`
- first weight `(64, 32, 3, 3, 3)`, second weight `(64, 64, 3, 3, 3)`
- fp32 bias with 64 outputs
- two chained `conv3d_implicit` calls
- stride `(1, 2, 1)`, padding `(1, 0, 1)`
- default mode: NCDHW input and output
- channels-last mode: contiguous NDHWC input and `out_layout="NDHWC"`
- independent reference: two `torch.nn.functional.conv3d` calls with the same bias, stride, and padding
- unchanged numerical gate: `torch.allclose(..., rtol=2e-2, atol=2e-2)`

Both modes abort during FlyDSL/LLVM code generation on `gfx942` before the first output is returned. The raw error is:

```text
LLVM ERROR: Do not know how to expand this operator's operand!
```

The failing instruction is an `llvm.amdgcn.raw.ptr.buffer.load.lds` with a 128-bit load and 8192-bit LDS store. The process exits with signal 6 (`SIGABRT`, shell status 134). Raw logs are in `gfx942_validation_raw.log` and `layout_trace_raw.log`.

The candidate's existing tests use the same unchanged `rtol=2e-2, atol=2e-2` gate. They include a three-layer channels-last chain, mixed layouts, bias dtype coverage, default output-layout inheritance, rank-specific aliases, unbatched NDHWC, and alias-conflict checks. On this GPU, the relevant 15 tests are all skipped by the existing CDNA4 gate:

```text
15 skipped, 57 deselected in 1.22s
```

That gate is correct: the kernel's `rocdl.mfma_f32_16x16x32_bf16` path is intended for CDNA4 `gfx95x`, not CDNA3 `gfx942`.

## Layout-copy measurement

Device profiling was not valid because code generation aborts before kernel execution. The bounded measurement is therefore a source-level call-path audit, recorded in `layout_static_audit_raw.log`.

For the general 3D path:

- NCDHW input reaches `_ncdhw_to_ndhwc(x, stream)` at `kernels/conv/conv3d_implicit.py:1147`.
- NDHWC input takes `x.contiguous()` instead; for an already-contiguous NDHWC tensor this is not a transpose/copy-producing layout round-trip.
- Split-K NCDHW output allocates NCDHW storage and executes `out.copy_(...permute(...))` at `kernels/conv/conv3d_implicit.py:1209`.
- Split-K NDHWC output returns the existing `(npq, K)` result as an NDHWC view at `kernels/conv/conv3d_implicit.py:1207`, skipping that copy/permute.
- Direct (`splitk == 1`) output allocation is already NDHWC when `out_ndhwc` is true at `kernels/conv/conv3d_implicit.py:1157`, so it also has no post-kernel output transpose.

Thus the candidate removes the unnecessary per-layer input transpose and output transpose for a channels-last chain. The only remaining copies in the tested ordinary zero-padding path are the existing weight preparation/cache path and any tensor that is not already contiguous. This is a static count, not a runtime timing, because `gfx942` cannot execute the CDNA4 kernel.

## Commands run

```bash
git clone https://github.com/amdpilot-org/FlyDSL.git /job/FlyDSL
cd /job/FlyDSL
git switch -c amdpilot/j-8eb4ef5d1ad9 main
git merge --no-edit 19f7acc4e61f06f99742ffcb326585be43fb685a

rocm-smi --showproduct --showserial
/opt/venv/bin/python --version
hipcc --version
/opt/venv/bin/python -c 'import torch; print(torch.__version__, torch.version.hip)'
/opt/venv/bin/python -c 'import flydsl; print(flydsl.__version__, flydsl.__file__)'

PYTHONPATH=/job/FlyDSL /opt/venv/bin/python \
  reports/j-8eb4ef5d1ad9/validate_conv3d_layout_gfx942.py --mode default
PYTHONPATH=/job/FlyDSL /opt/venv/bin/python \
  reports/j-8eb4ef5d1ad9/validate_conv3d_layout_gfx942.py --mode channels_last

PYTHONPATH=/job/FlyDSL /opt/venv/bin/python -m pytest -q \
  tests/kernels/test_conv3d_implicit.py -k 'layout or chain' --disable-warnings
/opt/venv/bin/python -m py_compile \
  kernels/conv/conv3d_implicit.py \
  tests/kernels/test_conv3d_implicit.py \
  tests/perf/bench_conv3d_layout.py

git diff main...HEAD > /job/recovery.patch
```

## Raw artifacts

- `environment_raw.log`: source/native paths and versions
- `gpu_identity_raw.log`: `rocm-smi` product, serial, node, and GFX version
- `gfx942_validation_raw.log`: direct default-mode abort
- `gfx942_channels_last_raw.log`: direct channels-last-mode abort
- `validation_exit_raw.log`: both reproduction exits are status 134 (`SIGABRT`)
- `layout_trace_raw.log`: channels-last trace reaches the same LLVM abort
- `layout_static_audit_raw.log`: transpose/permute/contiguous call-site count
- `pytest_layout_raw.log`: 15 relevant tests skipped by CDNA4 gate
- `static_checks_raw.log`: Python syntax compilation result
- `benchmark_help_raw.log`: candidate benchmark cases/options; not run because `gfx942` cannot execute the kernel

## Uncertainty and left undone

- No FlyDSL output tensor or numerical error was produced on `gfx942`; the LLVM abort is the concrete environment blocker.
- No valid CUDA event timing, Torch profiler kernel count, or generated-kernel runtime trace could be collected on `gfx942`.
- The candidate benchmark was not run because its cases target the CDNA4 kernel and would only repeat the same code-generation abort.
- A source-native rebuild was not attempted because no matching MLIR CMake installation was available in the image.
