# FlyDSL intra-kernel timing validation on one MI350X (gfx950)

## Status

Positive architecture-specific validation on the single assigned AMD Instinct MI350X.
The probe used FlyDSL's LLVM inline-assembly path to execute `s_memrealtime`,
recorded per-block start/end timestamps for deliberately unequal work, and
compared that path with the same kernel with instrumentation disabled.

No upstream issue, pull request, or comment was posted or modified. No model
weights were downloaded, and no distributed framework was used.

## Environment

- Image: `amdpilotv2/open-job:gbt350-20260909`
- Local image ID: `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`
- Source clone: `/job/FlyDSL`
- Tested source commit: `ed70142704e1a6d5563fb53e1607e3a4b85d7111`
- Python: `/opt/venv/bin/python`, Python 3.12.3
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`
- Torch HIP runtime: `7.2.26015-fc0010cf6a`
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`
- Installed FlyDSL wheel: `0.2.4`
- Source-tree FlyDSL version marker: `0.3.3`
- AITER: `0+gd9e5ef7ce08ee7045d583aed768cff41aa9210fe`
- ROCk module reported by `rocminfo`: `7.1.1.31500000`
- ROCm SMI: `4.0.0+fc0010cf6a`; ROCm SMI library: `7.8.0`
- glibc: `2.39`

The probe ran against the image's installed FlyDSL wheel because the source tree
does not contain the generated `_mlir` native bindings. The source clone was
used as the preserved reference checkout.

Native paths recorded verbatim in `environment.txt` include:

- FlyDSL Python package: `/opt/venv/lib/python3.12/site-packages/flydsl`
- FlyDSL native libraries: `/opt/venv/lib/python3.12/site-packages/flydsl.libs`
- FlyDSL MLIR libraries: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs`
- ROCm install: `/opt/rocm-7.2.0`
- AITER: `/opt/aiter`
- `libamdhip64.so.7.2.70200`
- `libhsa-runtime64.so.1.18.70200`
- `librccl.so.1.0.70200`
- `libamd_comgr.so.3.0.0`

## GPU identity

- Device: AMD Instinct MI350X
- ISA: `amdgcn-amd-amdhsa--gfx950:sramecc+:xnack-`
- Torch capability: `(9, 5)`
- Visible CUDA/HIP devices: `1`
- Unique ID: `0x593d46f1dbb5dce5`
- Serial: `692517020475`
- Card model: `0x75a0`
- GFX version: `gfx950`
- Wavefront size: `64`
- Workgroup max size: `1024`
- Global memory pool: `264224768` KiB

## Issue 831 context

ROCm/FlyDSL issue 831, `[Feature]: Intra-kernel profiling`, is open. Its body
requests intra-kernel profiling for communications and compute kernels, and
references cutedsl, tilelang, Triton, flashinfer, and an MI300X all-to-all
profiling blog. The two comments express support; neither supplies an
implementation. The full current description and comments are preserved in
`issue831.md`.

## Probe design

`timing_probe.py` defines one FlyDSL kernel with:

- 8 blocks
- 128 threads per block
- block `b` executing `50,000 + 50,000*b` dynamic loop iterations
- one global load and one global store per thread
- a float32 recurrence in the unequal-work loop
- `s_memrealtime` immediately before and after the recurrence when instrumented
- thread 0 storing each block's 64-bit start/end timestamps
- the same output arithmetic with instrumentation disabled

The timer is emitted with FlyDSL's LLVM `inline_asm` operation:

```asm
s_memrealtime $0
s_waitcnt vmcnt(0)
```

The output constraint is `=s`, and the result is wrapped as `fx.Int64`.

## Numerical and timing results

The final run used 5 warmup and 30 measured launches per mode.

| Gate | Result |
|---|---:|
| `torch.equal(uninstrumented, instrumented)` | `True` |
| SHA-256 output checksum equality | `True` |
| Maximum absolute output difference | `0.0` |
| Output SHA-256 | `88581645c28b1814c9c72a9060f3dd887a0564761d7f8f58934b9a7704fc81c9` |

| Mode | Event median |
|---|---:|
| Instrumentation disabled | `8.977139472961426 ms` |
| Instrumentation enabled | `11.957655906677246 ms` |
| Overhead | `2.9805164337158203 ms` |
| Relative overhead | `33.20118221057996%` |

Median per-block `s_memrealtime` durations:

| Block | Iterations | Timer ticks | Duration |
|---:|---:|---:|---:|
| 0 | 50,000 | 149,280 | 1.495813 ms |
| 1 | 100,000 | 299,642 | 3.002468 ms |
| 2 | 150,000 | 450,152 | 4.510606 ms |
| 3 | 200,000 | 604,752 | 6.059726 ms |
| 4 | 250,000 | 751,734 | 7.532513 ms |
| 5 | 300,000 | 901,264 | 9.030831 ms |
| 6 | 350,000 | 1,044,780 | 10.468888 ms |
| 7 | 400,000 | 1,191,632 | 11.940372 ms |

The durations scale with the deliberately unequal iteration counts. Block 7's
instrumented duration is close to the instrumented whole-kernel event median,
which is consistent with the longest block dominating this small concurrent grid.

## gfx950 timer limitations

- A 1,000,000-iteration calibration measured a median `2,985,716` timer ticks
  over `29.917423248291016 ms`, implying approximately
  `99,798,568.05249944 Hz`.
- The inferred tick period is approximately `10.020183851475164 ns`.
- Zero-work timer deltas were quantized to `12` or `16` ticks, or approximately
  `120.242 ns` and `160.323 ns`.
- The zero-work start spread was `145` ticks, approximately `1.453 us`.
- The unequal-work run had a start spread of `137` ticks, approximately
  `1.373 us`, showing that per-block timestamps are not a synchronized start.
- The unequal-work end spread was `1,042,821` ticks, approximately `10.449 ms`,
  dominated by the unequal block durations.
- The zero-work event median was `0.03848099894821644 ms`, with one outlier at
  `0.226282998919487 ms`.
- `s_memrealtime` is side-effecting scalar inline assembly in this FlyDSL
  version; it is not a first-class FlyDSL profiling operation.
- The measured frequency is an empirical calibration on this gfx950 instance,
  not a claim of a fixed architectural frequency.

## PR 829 candidate

ROCm/FlyDSL pull request 829, `[Feature] Extract reusable event-based
benchmarking helper`, was inspected on preserved head commit
`ce8ce9c892a7f6c6fec4d93086509139e393dbf0`. It adds `flydsl.profiling.do_bench`
and is an event-level whole-kernel timer, not an intra-kernel per-block timer.

Its targeted tests were run as-is:

```bash
PYTHONPATH=/tmp/flydsl-pr-829-worktree/python \
  /opt/venv/bin/python -m pytest \
  tests/unit/test_profiling.py tests/unit/test_autotune.py -q
```

Result: `31 passed`.

PR 829 therefore does not duplicate or replace the `s_memrealtime` probe used
here, and it does not resolve issue 831's intra-kernel profiling request.

## Reproduction

From `/job/FlyDSL`:

```bash
FLYDSL_RUNTIME_ENABLE_CACHE=0 \
  /opt/venv/bin/python reports/j-dda0dfd341b0/timing_probe.py \
  --json-out reports/j-dda0dfd341b0/timing_results.json \
  > reports/j-dda0dfd341b0/raw_results.txt
```

The complete JSON result is in `timing_results.json`, and the verbatim stdout is
in `raw_results.txt`. The full environment inventory is in `environment.txt`.
The command log is in `commands.txt`.

## Uncertainties and left undone

- The source tree was not rebuilt; the installed FlyDSL 0.2.4 wheel supplied the
  native MLIR and ROCm bindings used by the image.
- The timer frequency was inferred from one calibration workload rather than
  queried as a documented device attribute.
- The probe covers one 8-block, 128-thread configuration on the assigned
  MI350X; it does not claim a general performance model for all grids.
- PR 829 was tested only with its targeted unit tests because its event-level
  scope does not provide intra-kernel per-block timestamps.
