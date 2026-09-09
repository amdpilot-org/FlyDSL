# Bounded intra-kernel timing prototype

## Result

This branch prototypes per-block timing on one assigned MI300X (`gfx942`) using
FlyDSL's inline-assembly primitive and the AMDGPU `s_memrealtime` instruction.
It does not add a profiling framework or distributed communication.

The bounded run succeeded on one GPU:

- `imbalanced_copy_kernel` launches 16 blocks of 256 threads. Block `b`
  performs `(b + 1) * 64` copy iterations; each iteration copies 256 `int32`
  values through FlyDSL pointer loads and stores.
- With `instrument=True`, `read_block_clock()` reads `s_memrealtime` before and
  after the block-local loop, and thread 0 stores the elapsed 64-bit cycle count
  to `Timings[b]`.
- Both `instrument=False` and `instrument=True` outputs pass the unchanged
  numerical gate `torch.equal(output, expected)`. The gate is computed
  independently from timing.
- The final 16-block run recorded `[1832, 3164, 4612, 5608, 7024, 7968, 9764,
  11544, 12504, 13844, 15300, 17112, 18088, 20348, 21148, 22624]` cycles for
  blocks 0 through 15. The approximately linear increase makes the deliberate
  workload imbalance visible without relying on the timing values for correctness.

## Overhead and clocks

- The 16-block cycle regression has an intercept of 135.7 cycles. Using the
  one-block empirical clock calibration of about 0.0936 GHz, this is about
  1.45 microseconds. The JSON's `cycle_regression_intercept_us` uses the
  whole-kernel lower-bound clock estimate and therefore reports a more
  conservative 1.78 microseconds.
- The final event medians differ by 0.441 microseconds, but repeated event
  measurements ranged from roughly -13.6 to +15.1 microseconds. Event timing is
  therefore not a reliable sub-microsecond overhead measurement for this
  workload; the cycle intercept is the better bounded estimate.
- Three one-block calibration samples observed about 0.0884, 0.0957, and
  0.0912 GHz. `rocm-smi` reported `sclk` at 132 MHz in the GPU's low-power
  state. These are empirical observations, not an architectural guarantee of
  `s_memrealtime` frequency.
- `s_memrealtime` supplies a raw 64-bit counter. The observed calibration
  implies roughly 10-11 nanoseconds per tick, while instruction issue, block
  scheduling, and event synchronization add coarser noise. Only elapsed counts
  from the same block are compared; absolute cross-block timestamps are not
  recorded, avoiding assumptions about cross-XCD clock comparability.

## Negative result preserved

An initial probe used `flydsl.expr.extern.ffi("clock64", [], "uint64")`. The
generated object left `clock64` unresolved and HIP reported
`hipErrorNoBinaryForGpu`, followed by invalid module/function handles. That
path was not used. The supported FlyDSL inline-assembly primitive with
`s_memrealtime` compiled and ran correctly.

## Issue context

Read-only context was captured from ROCm/FlyDSL issue 831, `[Feature]:
Intra-kernel profiling`. The issue is open and requests intra-kernel profiling;
its timeline contains no implementation or related merge. No upstream issue, PR,
or comment was posted or modified. Raw API captures are in
`artifacts/issue-831/`.

## Reproduction

Run from the repository root:

```bash
FLYDSL_GPU_ARCH=gfx942 /opt/venv/bin/python examples/06-intra_kernel_timing.py
```

The focused test is:

```bash
/opt/venv/bin/python -m pytest tests/kernels/test_intra_kernel_timing.py -q
```

The final 16-block measurement is:

```bash
FLYDSL_GPU_ARCH=gfx942 /opt/venv/bin/python examples/06-intra_kernel_timing.py \
  --grid-blocks 16 --work-multiplier 64 --repetitions 50
```

The one-block clock calibration is:

```bash
FLYDSL_GPU_ARCH=gfx942 /opt/venv/bin/python examples/06-intra_kernel_timing.py \
  --grid-blocks 1 --work-multiplier 4096 --repetitions 30
```

## Environment

- Qualified image: `amdpilotv2/open-job-mi300:jit-config-readable-260909-banff5`,
  local image ID
  `sha256:39fe745feda79ecf4c17f4d806d8ef12150bef720f2f07f5c63a20b3ccfd63f1`.
- Working clone: `/job/FlyDSL`, base commit
  `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.
- Python: `/opt/venv/bin/python` (3.10.12).
- Installed FlyDSL source: `/opt/venv/lib/python3.10/site-packages/flydsl`.
- FlyDSL native runtime:
  `/opt/venv/lib/python3.10/site-packages/flydsl/_mlir/_mlir_libs/libfly_jit_runtime.so`.
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`, HIP `7.2.26015-fc0010cf6a`.
- ROCm tools: `/opt/rocm/bin/hipcc`, `/opt/rocm/bin/rocm-smi`,
  `/opt/rocm/bin/rocminfo`.
- GPU: one AMD Instinct MI300X, `gfx942`, unique ID
  `0xd77d585f96863a60`, serial `692440004359`.

Raw outputs are under `artifacts/`, including the final result, repeated clock
samples, calibration samples, focused test log, `rocm-smi` output, environment
capture, and issue 831 API captures.

## Uncertainty and left undone

- The clock frequency is empirical and varies with GPU power state; no
  architectural frequency contract is claimed.
- Event-level overhead is noisy and can be negative in individual runs; it is
  reported as a limitation rather than hidden.
- The prototype records one elapsed value per block from thread 0. It does not
  attempt wave-level timing, cross-XCD timestamp alignment, or a reusable
  profiling framework.
- No model weights, distributed communication, or additional framework stack
  were used.

## Reproduction

Run from the repository root:

```bash
/opt/venv/bin/python examples/06-intra_kernel_timing.py
```

The example launches `imbalanced_copy_kernel` with eight blocks. Block `b`
performs `(b + 1) * work_multiplier` copy iterations, so later blocks do more
work. The `instrument` constexpr controls whether the two clock reads and
per-block timing store are compiled into the kernel.

Raw environment and result artifacts are recorded in this directory.
