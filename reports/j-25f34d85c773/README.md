# BF16 preshuffle GEMM tail-boundary investigation

## Scope and baseline

This investigation covers the high-level tiled BF16 preshuffle GEMM path on gfx950. It is distinct from ROCm/FlyDSL issue 821, which reports a fixed-shape FP8 `fx.gemm` VGPR comparison and `BufferCopy*` legalization failure on gfx942. The public issue page showed no linked pull requests or rendered comments; no upstream issue, pull request, or comment was modified.

The delivery branch is cut from `main` at commit `ed70142704e1a6d5563fb53e1607e3a4b85d7111`. That commit already contains merged PRs 1007 and 1008, so this work does not duplicate their A-tile loading and BF16 async-copy fixes.

The installed-source baseline used `/opt/venv/bin/python3`, FlyDSL 0.2.4 at `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`, Torch `2.9.1+rocm7.2.0.git7e1940d4`, and Triton `3.5.1+rocm7.2.0.gita272dfa8`. The direct gfx950 A16W16 test was unsupported by the installed wheel because `flydsl.expr.rocdl.cdna4` lacks `BufferLoadAsyncLDS128b`. The meaningful neighboring control was the checked-in BF16 preshuffle GEMM test; its sync and async-copy cases both passed. The first supported control process took 29.464133 seconds by wall-clock timing around pytest, including startup, collection, JIT compilation, warmup, and bounded execution.

## Environment

- GPU: one AMD Instinct MI350X, gfx950, unique ID `0x5e94f9cc641f4027`, serial `692517020474`, node ID 7.
- Qualified image: `amdpilotv2/open-job:gbt350-20260909`, local image ID `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.
- Torch HIP: `7.2.26015-fc0010cf6a`.
- FlyDSL native libraries: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/libFlyPythonCAPI.so.23.0git` and `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/libfly_jit_runtime.so`.
- Job-private cache: `/tmp/flydsl-cache-j-25f34d85c773`.

## Boundary results

The new test uses BF16 inputs and BF16 output, an independent FP32-accumulated Torch `mm` reference, and `-8192` sentinels in guard storage after A, B, and C. The numerical gate is unchanged at `rtol=0.1`, `atol=0.1`.

- `M=32,N=64,K=64`: passed; max absolute error `0.020447731018066406`, mean absolute error `0.0029120412655174732`, and zero A/B/C guard changes.
- `M=33,N=64,K=64`: passed; max absolute error `0.03091716766357422`, mean absolute error `0.00304132211022079`, and zero A/B/C guard changes. This is a non-multiple M boundary around `tile_m=32`.
- `M=32,N=80,K=64`: before validation, this non-multiple N boundary produced 1437/2560 mismatched elements, max absolute error `9.637928009033203`, and errors concentrated in columns 0-47. Rounding the grid and bounding B did not make the preshuffle layout tail-safe. The path now rejects this unsupported combination with `ValueError: tile_n must be a positive divisor of N`.
- `M=32,N=64,K=65`: this non-multiple K boundary is rejected with `ValueError: tile_k must be a positive divisor of K`.

Predication was inspected only after the observed N-tail error. A and C already use real-extent buffer descriptors, but B uses the preshuffle layout and the host grid used truncating division in N. Resource usage was also inspected for the supported M-tail kernel: 22 VGPRs, no VGPR spills, 4096 bytes fixed group segment, 0 bytes private segment, and 256-thread workgroup. Final ISA reported `.amdhsa_next_free_vgpr 22` and `.amdhsa_next_free_sgpr 16`; kernel metadata reported `vgpr_count=22`, `sgpr_count=22`, and zero spills. No performance cliff was measured, so no broader resource comparison was performed.

## Reproduction

```bash
export FLYDSL_CACHE_DIR=/tmp/flydsl-cache-j-25f34d85c773
python3 -m pytest -q -s tests/kernels/test_preshuffle_gemm_boundaries.py
python3 -m pytest -q tests/kernels/test_preshuffle_gemm.py \
  -k 'bf16 and 33-1024-2048-32-64-512 and eager and sync_copy' -x
```

The first command covers the sentinel-protected M boundary and explicit N/K tail rejection. The second reruns the affected existing BF16 sync/async-copy control. Both completed successfully on the assigned MI350X. No synthetic GPU burn, unbounded loop, sleep loop, model-weight download, or node-wide state change was used.

Final validation on the delivery branch:

- `tests/kernels/test_preshuffle_gemm_boundaries.py`: 4 passed in 4.20 seconds.
- Affected existing control: 2 passed in 10.86 seconds.
- Full relevant BF16 subset of `tests/kernels/test_preshuffle_gemm.py`: 47 passed, 5 skipped, 118 deselected in 103.22 seconds.
