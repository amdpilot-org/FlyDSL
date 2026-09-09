# Block-wide sum validation report

## Result

The reusable block-wide sum is already implemented by upstream PR 1031 and is present at mirror `main` commit `ed70142704e1a6d5563fb53e1607e3a4b85d7111`. No duplicate implementation was made.

The tested operation is `fx.coop.BlockReduce(..., fx.ReductionOp.ADD, ...)`, with both implemented policies: `WARP_REDUCTIONS` and `RAKING`.

## Reproduction

The preinstalled FlyDSL 0.3.1 wheel does not contain `flydsl.extension.coop`. The source checkout is version 0.3.3 but has no native build. A job-private FlyDSL 0.3.2 wheel was downloaded with `pip download flydsl==0.3.2 --no-deps` and used without installing it:

```bash
cd /job/FlyDSL
export PYTHONPATH=/job/task-artifacts/wheel-0.3.2
export LD_LIBRARY_PATH=/job/task-artifacts/wheel-0.3.2/flydsl/_mlir/_mlir_libs
HIP_VISIBLE_DEVICES=0 /opt/venv/bin/python -m pytest -q -ra tests/extension/coop/test_block_reduce.py
HIP_VISIBLE_DEVICES=0 /opt/venv/bin/python reports/j-f7dbc4043b7a/validate_block_reduce.py --json reports/j-f7dbc4043b7a/block_reduce_validation.json
```

Raw command output is retained in `block_reduce_validation.json`; timing and numerical results are summarized there.

## Environment

- Working source: `/job/FlyDSL`, commit `ed70142704e1a6d5563fb53e1607e3a4b85d7111`, Python version 0.3.3.
- Native candidate: `/job/task-artifacts/wheel-0.3.2/flydsl`, FlyDSL 0.3.2, libraries under `/job/task-artifacts/wheel-0.3.2/flydsl/_mlir/_mlir_libs`.
- Preinstalled package: `/opt/venv/lib/python3.10/site-packages/flydsl`, FlyDSL 0.3.1; it lacks `flydsl.extension.coop`.
- Python: `/opt/venv/bin/python`, Python 3.10.12.
- Torch: 2.9.1+rocm7.2.0.git7e1940d4; HIP 7.2.26015-fc0010cf6a.
- Compiler: `/opt/rocm-7.2.0/bin/hipcc`, HIP 7.2.26015-fc0010cf6a.
- GPU: one AMD Instinct MI300X, gfx942 (`sm_94` capability reported by Torch).
- Operator-specified image: `amdpilotv2/open-job-mi300:jit-config-readable-35122-260909`, local image ID `sha256:dfc9419089c338b5712da4841768b38b1ab79f3da41f8c58c3cd4dfcc1147ff1`.

## Coverage

- Existing suite: 85/85 tests passed in 4.13 seconds.
- Focused validation: 49/49 cases passed in 2.04 seconds; raw elapsed time is recorded in `block_reduce_validation.json`.
- One-wave and multiple-wave blocks: 64, 128, 256, and 1024 threads.
- Non-power-of-two tails: lengths 65, 133, 1000, and 4097, padded with zero contributors.
- Finite adversarial inputs: float32 tiny/-tiny, max/2/-max/2, subnormal-scale values, and cancellation pairs; int32 extrema and wraparound.
- Independent references: CPU Torch sums in float64 or int64, with explicit narrow-integer wraparound.
- Barrier correctness: two reductions reusing the same shared storage with an explicit block barrier.
- Wave64: target wave is 64 lanes; 32-thread blocks narrow the logical warp to 32, while 64/128/256 use one/four/eight warps.

## Numerical gates and timing

- Existing float32 gate: `rtol=1e-5`, `atol=1e-3`; existing float64 gate: `rtol=1e-12`, `atol=1e-9`.
- Focused float gate: `rtol=2e-5`, `atol=1e-5`; all observed focused float differences were zero. Integer references were exact with explicit wraparound.
- Mean time over 100 cache-warm launches, in microseconds:
  - `WARP_REDUCTIONS`: 64 threads 59.495, 128 threads 59.033, 256 threads 59.775, 1024 threads 59.063.
  - `RAKING`: 64 threads 57.879, 128 threads 61.454, 256 threads 57.006, 1024 threads 58.336.

These timings include the FlyDSL JIT launch wrapper, not only the emitted GPU kernel.

## Limits

The validation uses the 0.3.2 native wheel because no matching 0.3.3 wheel or prebuilt MLIR tree was available. This is recorded as a source/native version mismatch rather than hidden. No full model weights or additional framework stack were downloaded, and no upstream issue or PR was modified.
