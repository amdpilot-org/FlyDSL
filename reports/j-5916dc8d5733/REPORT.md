# MI350 convolution throughput investigation

## Outcome

The reported throughput gap is reproduced on one assigned MI350X (`gfx950`) with the checked-out implementation at base commit `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`. Across three representative BF16 convolution shapes, the current FlyDSL public call is **1.37x to 1.71x slower** than a preallocated Torch BF16 GEMM with identical implicit-GEMM dimensions and FLOP count.

No production tuning change is proposed. The current heuristic selects `(32, 32, 1, 2)`, and it is the fastest of every shipped ladder tile on all three measured shapes. Selecting `(64, 64, 2, 2)` instead is 3.5%, 12.1%, and 5.6% slower; `(128, 128, 2, 4)` is 36.6%, 40.0%, and 15.6% slower. A selector change would therefore be unjustified for this matrix.

Upstream issue: https://github.com/ROCm/FlyDSL/issues/861

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/505

The related draft mirror PR https://github.com/amdpilot-org/FlyDSL/pull/383 was inspected before testing. Its older environment needed compatibility shims and found a 64x64 win. This checkout imports FlyDSL 0.3.3 from the repository, has the required native APIs, and contains later convolution work including barrier batching and occupancy-based tile selection. The earlier result does not reproduce on the current base.

## Method

The shape matrix uses existing repository-test shapes:

| Shape | Input | Weight | Implicit GEMM `(M,N,K)` | FLOPs |
|---|---|---|---:|---:|
| `conv3d_medium` | `(1,128,6,40,40)` | `(128,128,3,3,3)` | `(9600,128,3456)` | 8,493,465,600 |
| `conv3d_tail` | `(2,64,6,18,18)` | `(192,64,3,3,3)` | `(3888,192,1728)` | 2,579,890,176 |
| `conv2d_common` | `(2,64,1,24,28)` | `(128,64,1,3,3)` | `(1344,128,576)` | 198,180,864 |

Timing uses GPU events on the current stream, ten warmups, and 100 individually synchronized samples. Convolution timing covers the actual public `conv3d_implicit` call with NDHWC output, including output allocation and dispatch; weight packing is memoized by warmup. GEMM timing uses `torch.mm(..., out=...)` with a preallocated BF16 output. This is a compute-density comparison, not a claim that GEMM and implicit convolution have identical memory access.

Numerical references are independent `torch.nn.functional.conv3d` results. Every tile passes `torch.allclose(rtol=2e-2, atol=2e-2)`. Complete individual timing samples, GPU identity snapshots, import paths, errors, and summary statistics are in `raw_measurements.json`.

## Results

| Shape | Current conv | Equivalent GEMM | Conv/GEMM | Conv TFLOP/s | GEMM TFLOP/s |
|---|---:|---:|---:|---:|---:|
| `conv3d_medium` | 0.05908 ms | 0.03900 ms | 1.51x | 143.8 | 217.8 |
| `conv3d_tail` | 0.03874 ms | 0.02832 ms | 1.37x | 66.6 | 91.1 |
| `conv2d_common` | 0.03272 ms | 0.01912 ms | 1.71x | 6.1 | 10.4 |

| Shape | 32x32 (current) | 64x64 | 128x128 |
|---|---:|---:|---:|
| `conv3d_medium` | 0.05908 ms | 0.06112 ms | 0.08068 ms |
| `conv3d_tail` | 0.03874 ms | 0.04344 ms | 0.05422 ms |
| `conv2d_common` | 0.03272 ms | 0.03454 ms | 0.03784 ms |

The measurements establish the gap but do not isolate it to a compiler defect. No compiler/ISA claim is made, so no speculative ISA conclusion is presented. Closing the remaining gap likely requires a broader kernel-design experiment beyond choosing among the current tile ladder, such as reducing implicit-addressing and public-call overhead while retaining tail and layout support.

## Reproduction

From the repository root, with job-private caches:

```bash
export FLYDSL_RUNTIME_CACHE_DIR=/tmp/amdpilot-repo-j-5916dc8d5733/cache/runtime
export FLYDSL_AUTOTUNE_CACHE_DIR=/tmp/amdpilot-repo-j-5916dc8d5733/cache/autotune
export TRITON_CACHE_DIR=/tmp/amdpilot-repo-j-5916dc8d5733/cache/triton
export TORCHINDUCTOR_CACHE_DIR=/tmp/amdpilot-repo-j-5916dc8d5733/cache/inductor
/tmp/amdpilot-repo-j-5916dc8d5733/venv/bin/python \
  reports/j-5916dc8d5733/bench_conv_gap.py \
  --output reports/j-5916dc8d5733/raw_measurements.json \
  --warmup 10 --repetitions 100
```

## Limitations

- These are three small, test-derived shapes rather than a full production model trace.
- Torch GEMM is an independent compute-density reference, not a FlyDSL GEMM kernel and not an end-to-end convolution replacement.
- The benchmark intentionally reports the public convolution call. It does not claim that all of the measured gap is MFMA execution time.
- No native C++ source changed, so a native rebuild was neither required nor performed. The loaded Python implementation is `/job/repo/python/flydsl`, and the native extension remains `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir` as recorded by the prepared environment.
