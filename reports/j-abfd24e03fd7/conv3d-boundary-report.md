# conv3d batch/kernel boundary report

## Scope and conclusion

- Upstream context: ROCm/FlyDSL issue 993 requested NCDHW/NDHWC input and output layout support for `conv3d_implicit`.
- Tested mirror base: `ed70142704e1a6d5563fb53e1607e3a4b85d7111` (`main`).
- The layout implementation is already present on this base, so this work does not duplicate it. The change adds boundary regressions for small batch counts, odd supported kernels/spatial extents, bias/layout contracts, and empty-output rejection.
- All 23 focused boundary cases pass against independent `torch.nn.functional.conv3d` references. The complete existing `tests/kernels/test_conv3d_implicit.py` suite also passes: 80/80.

## Environment

- Image: `amdpilotv2/open-job:gbt350-20260909`, local image ID `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.
- GPU: one AMD Instinct MI350X, `gfx950`, unique ID `0x5e94f9cc641f4027`, serial `692517020474`.
- Interpreter: `/opt/venv/bin/python` (Python 3.12).
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`, `/opt/venv/lib/python3.12/site-packages/torch/__init__.py`.
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`, `/opt/venv/lib/python3.12/site-packages/triton/__init__.py`.
- Installed FlyDSL baseline: `0.2.4`, `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`.
- Checkout runtime used for GPU cases: FlyDSL `0.3.2`, installed with `--no-deps --target` at `/tmp/flydsl-cache-j-abfd24e03fd7/flydsl-0.3.2/flydsl/__init__.py`. Torch, Triton, and ROCm remain the installed image versions.
- Checkout kernel source: `/job/FlyDSL/kernels/conv/conv3d_implicit.py`.
- Runtime native modules include `/tmp/flydsl-cache-j-abfd24e03fd7/flydsl-0.3.2/flydsl/_mlir/_mlir_libs/_mlirDialectsFly.cpython-312-x86_64-linux-gnu.so`, `_mlirDialectsFlyROCDL.cpython-312-x86_64-linux-gnu.so`, `_mlirDialectsGPU.cpython-312-x86_64-linux-gnu.so`, `_mlirDialectsLLVM.cpython-312-x86_64-linux-gnu.so`, `_mlirExecutionEngine.cpython-312-x86_64-linux-gnu.so`, and `libfly_jit_runtime.so` in the same directory.
- Native ROCm libraries include `/opt/rocm-7.2.0/lib/libamdhip64.so.7`, `/opt/rocm-7.2.0/lib/librccl.so.1`, and `/opt/rocm-7.2.0/lib/libhipblas.so.3`.
- Job-private cache: `/tmp/flydsl-cache-j-abfd24e03fd7`.

The installed FlyDSL 0.2.4 wheel cannot execute this checkout: its Python API rejects `s_waitcnt(lgkmcnt=0)`, and its native dialects lack `CopyOpCDNA4BufferLoadAsyncLDSType`. The published 0.3.2 runtime is compatible with the checkout kernel and was used without modifying the qualified Torch/ROCm stack.

## Installed-source baseline

The early baseline is saved outside the repository at `/job/baseline-first.json`. The installed AITER FlyDSL neighboring control at `/opt/aiter/op_tests/flydsl_tests/test_silu_and_mul_fq.py` failed collection after an 18.4-second JIT build because `aiter.jit.module_aiter_core` was not importable. The supported control, `/job/FlyDSL/examples/01-vectorAdd.py`, passed `torch.allclose(A + B, C)` on MI350X in 2.663469 seconds. This installed-source baseline is not evidence for later checkout changes.

## Reproduction

```bash
export PYTHONPATH=/tmp/flydsl-cache-j-abfd24e03fd7/flydsl-0.3.2:$PWD
export FLYDSL_CACHE_DIR=/tmp/flydsl-cache-j-abfd24e03fd7
/opt/venv/bin/python -m pytest tests/kernels/test_conv3d_implicit.py -q \
  -k 'small_batches or odd_kernels or empty_spatial'
/opt/venv/bin/python -m pytest tests/kernels/test_conv3d_implicit.py -q
```

The focused command reports 23 passed. The full command reports 80 passed in 223.84 seconds on this run.

## Numerical gate

The existing gate is unchanged: bf16 outputs are compared with `torch.allclose(..., rtol=2e-2, atol=2e-2)` against `torch.nn.functional.conv3d`. Bias is supplied as float32 and converted to bf16 for the independent reference, matching the existing test contract.

## Bounded timing record

Method: one call per case after a warm JIT cache; wall time from `time.perf_counter`; CUDA time from separate start/end events; no warmup loops, synthetic burn, sleep loops, or repeated work. The complete one-pass timing process took 4.565853 seconds.

| Case | Result | Max abs error | Wall seconds | CUDA event ms |
|---|---:|---:|---:|---:|
| N=0 NCDHW->NCDHW | PASS | 0.0 | 0.018775863 | 0.188602000 |
| N=0 NCDHW->NDHWC | PASS | 0.0 | 0.000255452 | 0.061880000 |
| N=0 NDHWC->NCDHW | PASS | 0.0 | 0.000093411 | 0.035799999 |
| N=0 NDHWC->NDHWC | PASS | 0.0 | 0.000056900 | 0.017240001 |
| N=1 NCDHW->NCDHW | PASS | 0.25 | 1.515261971 | 303.178588867 |
| N=1 NCDHW->NDHWC | PASS | 0.25 | 0.065680927 | 65.010940552 |
| N=1 NDHWC->NCDHW | PASS | 0.25 | 0.000350433 | 0.156241000 |
| N=1 NDHWC->NDHWC | PASS | 0.25 | 0.000260863 | 0.091600999 |
| N=2 NCDHW->NCDHW | PASS | 0.25 | 0.113861231 | 88.344810486 |
| N=2 NCDHW->NDHWC | PASS | 0.25 | 0.064427334 | 64.042510986 |
| N=2 NDHWC->NCDHW | PASS | 0.25 | 0.000281802 | 0.140322000 |
| N=2 NDHWC->NDHWC | PASS | 0.25 | 0.000286592 | 0.112360999 |
| N=3 NCDHW->NCDHW | PASS | 0.25 | 0.096757862 | 89.406585693 |
| N=3 NCDHW->NDHWC | PASS | 0.25 | 0.066774786 | 66.312210083 |
| N=3 NDHWC->NCDHW | PASS | 0.25 | 0.000291863 | 0.146000996 |
| N=3 NDHWC->NDHWC | PASS | 0.25 | 0.000208652 | 0.086961001 |
| kernel [1, 1, 1] pad [0, 0, 0] | PASS | 0.0 | 0.017018457 | 1.094133019 |
| kernel [1, 1, 3] pad [0, 0, 1] | PASS | 0.125 | 0.067235511 | 65.795173645 |
| kernel [1, 3, 1] pad [0, 1, 0] | PASS | 0.125 | 0.068894036 | 66.945472717 |
| kernel [3, 1, 1] pad [1, 0, 0] | PASS | 0.125 | 0.066524004 | 65.525527954 |
| kernel [3, 3, 3] pad [1, 1, 1] | PASS | 0.25 | 0.000400053 | 0.218923002 |
| kernel [5, 1, 1] pad [2, 0, 0] | PASS | 0.125 | 0.069915025 | 64.094161987 |
| empty spatial output | REJECTED | n/a | 0.000067050 | n/a |
