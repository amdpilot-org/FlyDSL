# MI350X gfx950 BlockReduce validation

## Result

The existing reusable block-wide sum, `flydsl.extension.coop.BlockReduce` with `fx.ReductionOp.ADD`, passed the bounded synthetic validation on one AMD Instinct MI350X (`gfx950`).

- Existing device suite: **73 passed, 12 deselected, 0 failed**.
- Focused gfx950 harness: **120 passed, 0 failed**.
- Every returned thread held the same block-wide result in all 120 focused cases.
- Both implemented policies passed: `BlockReduceAlgorithm.WARP_REDUCTIONS` and `BlockReduceAlgorithm.RAKING`.
- The collective itself rejects a non-power-of-two block product. Tail cases were validated by launching a power-of-two block and masking inactive lanes to zero before calling `BlockReduce`.

This is an architecture verification, not a claim that every possible reduction order or input is free of overflow.

## Scope and source

- Mirror scope: `amdpilot-org/FlyDSL` issue 348 (OPEN).
- Read-only context: `ROCm/FlyDSL` issue 1016 (OPEN), which proposes reusable cooperative building blocks.
- Related change: `ROCm/FlyDSL` pull request 1031, commit `c3bd00455f711bd4f8d521951e0f5d9162437d8d`.
- Delivery clone base: `amdpilot-org/FlyDSL` `main` at `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.
- No upstream issue, pull request, or comment was posted or changed.

Relevant source paths in this clone:

- `python/flydsl/extension/coop/block/reduce.py`
- `python/flydsl/extension/coop/block/_spec.py`
- `python/flydsl/extension/coop/_common.py`
- `tests/extension/coop/test_block_reduce.py`
- `reports/j-75416052437a/validate_block_reduce_gfx950.py`

The `BlockReduce` and shared helper files in the execution wheel are byte-identical to the files in this clone. The wheel SHA-256 is:

```text
aeb32115bb3c3f6f779354c17a9cb1f21fe49335be13d149d47ac39da12d2683
```

## Environment

Qualified image: `amdpilotv2/open-job:gbt350-20260909`

Operator-provided local image ID:

```text
sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7
```

Container ID from `/proc/self/cgroup`:

```text
fc166f52feb222da535e49c138e61ec201cd18b8d7da738f75e2e16759594b30
```

Measured software:

| Component | Measured version | Path |
|---|---|---|
| Python | 3.12.3 | `/opt/venv/bin/python` |
| Torch | 2.9.1+rocm7.2.0.git7e1940d4 | `/opt/venv/lib/python3.12/site-packages/torch/__init__.py` |
| Triton | 3.5.1+rocm7.2.0.gita272dfa8 | `/opt/venv/lib/python3.12/site-packages/triton/__init__.py` |
| FlyDSL execution | 0.3.2 | `/job/.cache/flydsl-wheel/flydsl/__init__.py` |
| FlyDSL source clone | 0.3.3 at `ed701427...` | `/job/FlyDSL/python/flydsl/__init__.py` |
| AITER source marker | `0+gd9e5ef7ce08ee7045d583aed768cff41aa9210fe` | `/opt/aiter/aiter/_version.py` |
| HIP runtime | 7.2.26015-fc0010cf6a | Torch `torch.version.hip` |
| HIP compiler | ROCm 7.2.0, clang 22.0.0git | `/opt/rocm-7.2.0/lib/llvm/bin` |
| ROCm driver | 7.1.1.31500000 | `rocm-smi --showdriverversion` |

Native paths used:

- `/opt/rocm-7.2.0/lib/libamdhip64.so.7.2.70200`
- `/opt/rocm-7.2.0/lib/libhiprtc.so.7.2.70200`
- `/job/.cache/flydsl-wheel/flydsl/_mlir/_mlir_libs/_mlir.cpython-312-x86_64-linux-gnu.so`
- `/job/.cache/flydsl-wheel/flydsl/_mlir/_mlir_libs/_mlirDialectsFlyROCDL.cpython-312-x86_64-linux-gnu.so`
- `/job/.cache/flydsl-wheel/flydsl/_mlir/_mlir_libs/libFlyPythonCAPI.so.24.0git`
- `/job/.cache/flydsl-wheel/flydsl/_mlir/_mlir_libs/libfly_jit_runtime.so`

The image's preinstalled FlyDSL wheel is 0.2.4 and does not contain `flydsl.extension.coop`. The source tree at 0.3.3 also requires a newer `CopyOpCDNA4BufferLoadAsyncLDSType` native binding than that installed wheel. To avoid a full LLVM rebuild, the bounded run downloaded only the matching `flydsl==0.3.2` wheel into `/job/.cache/wheels`, extracted it under `/job/.cache/flydsl-wheel`, and put that private path first on `PYTHONPATH`. No existing Torch/ROCm stack component was replaced.

AITER was not used by this validation. Its source version marker is recorded above, but importing it fails after its JIT build with `ModuleNotFoundError: No module named 'aiter.jit.module_aiter_core'`. No model weights were downloaded.

## GPU identity

`rocm-smi` reported one GPU:

```text
Card Series:       AMD Instinct MI350X
Card Model:        0x75a0
GFX Version:       gfx950
Unique ID:         0x5e94f9cc641f4027
Serial Number:     692517020474
Node ID:           7
GUID:              51966
```

`rocminfo` reported:

```text
Marketing Name:     AMD Instinct MI350X
Name:               gfx950
Compute Unit:       256
Wavefront Size:     64
Workgroup Max Size: 1024
Max Waves Per CU:   32
Target:             amdgcn-amd-amdhsa--gfx950:sramecc+:xnack-
```

The runtime's `fx.num_warp_threads()` also returned 64.

## Correctness

The focused harness covered:

- Full power-of-two blocks: 64, 128, 256, and 1024 threads.
- One-wave blocks: 64 threads.
- Multi-wave blocks: 128, 256, and 1024 threads.
- Masked non-power-of-two active counts: 1, 33, 63, 65, 127, 129, 200, and 1023.
- dtypes: `float16`, `bfloat16`, `float32`, and `float64`.
- Both implemented algorithms.
- Adversarial cases: large mixed-sign finite values, cancellation, and random mixed signs.

The large mixed-sign case uses one positive finite maximum and negative values scaled by `2 * active_count`, so both the mathematical total and intermediate negative sums remain finite. The cancellation case uses `1`, `-1`, and the dtype's smallest normal value.

Observed maximum errors against same-device `torch.sum`:

| dtype | Cases | Maximum absolute error | Maximum finite relative error | Gate |
|---|---:|---:|---:|---|
| `float16` | 26 | 32.0 | 0.0018779342723004694 | exploratory `rtol=0.1`, `atol=0.1` |
| `bfloat16` | 26 | 1.329227995784916e+36 | 0.07053941908713693 | exploratory `rtol=0.1`, `atol=0.1` |
| `float32` | 42 | 2.028240960365167e+31 | 0.03389830508474576 | existing `rtol=1e-5`, `atol=1e-3` |
| `float64` | 26 | 3.99168061906944e+292 | 0.03389830508474576 | existing `rtol=1e-12`, `atol=1e-9` |

The `float32` and `float64` gates are unchanged from `tests/extension/coop/test_block_reduce.py`. There is no pre-existing fp16/bf16 gate in that suite, so the 10% exploratory gate is explicitly labeled rather than presented as an upstream expectation. Large absolute errors occur on large-magnitude inputs; cancellation cases pass through the existing absolute tolerance. All individual raw sums, references, errors, and gates are in `results.json`.

`BlockReduce[fx.Float32, 63, algorithm]` raises the expected `ValueError` for both algorithms:

```text
block_dim_x * block_dim_y * block_dim_z must be a power of two, got 63
```

Therefore, non-power-of-two tails are a caller responsibility: launch a power-of-two block, mask inactive lanes to the additive identity, and still call the collective from every thread. The harness validates that pattern. It does not claim native non-power-of-two block support.

## Wave and barrier behavior

The actual gfx950 wavefront is 64 lanes. The implementation narrows the logical warp to the block width when a block is smaller than one wave.

- `WARP_REDUCTIONS`: reduces each wave, lane 0 writes its wave aggregate to shared memory, issues one `barrier()`, and every thread folds the per-wave slots. A one-wave block takes the `num_warps == 1` path and does not need that shared-memory barrier.
- `RAKING`: stages every thread partial, issues a barrier, lets the first wave rake segments, lane 0 writes the result, and issues a second barrier before broadcast. A one-wave block has segment length 1 and bypasses shared memory and these barriers.

No gfx950-specific override is used by `BlockReduce`; the default policy is `WARP_REDUCTIONS`. The observed wave64 behavior was consistent across one-wave and multi-wave launches.

## Timing

Timing used CUDA/ROCm events around 500 launches after 50 warmup launches on one stream. These raw numbers include FlyDSL launch/dispatch overhead and are not isolated device-only kernel durations. No baseline is inferred.

| Algorithm | Block threads | Waves | 500-launch total ms | Mean us/launch |
|---|---:|---:|---:|---:|
| `WARP_REDUCTIONS` | 64 | 1 | 15.166333198547363 | 30.332666397094727 |
| `RAKING` | 64 | 1 | 17.846923828125 | 35.69384765625 |
| `WARP_REDUCTIONS` | 128 | 2 | 14.730408668518066 | 29.460817337036133 |
| `RAKING` | 128 | 2 | 14.54300594329834 | 29.08601188659668 |
| `WARP_REDUCTIONS` | 256 | 4 | 14.697608947753906 | 29.395217895507812 |
| `RAKING` | 256 | 4 | 14.479726791381836 | 28.959453582763672 |
| `WARP_REDUCTIONS` | 1024 | 16 | 14.474726676940918 | 28.949453353881836 |
| `RAKING` | 1024 | 16 | 14.40365219116211 | 28.80730438232422 |

## Reproduction

From `/job/FlyDSL`, with the private matching wheel prepared as described above:

```bash
export PYTHONPATH=/job/.cache/flydsl-wheel
export LD_LIBRARY_PATH=/job/.cache/flydsl-wheel/flydsl/_mlir/_mlir_libs:/opt/rocm/lib:${LD_LIBRARY_PATH:-}
export FLYDSL_RUNTIME_CACHE_DIR=/job/.cache/flydsl-runtime
export FLYDSL_AUTOTUNE_CACHE_DIR=/job/.cache/flydsl-autotune

/opt/venv/bin/python -m pytest -c tests/pytest.ini \
  tests/extension/coop/test_block_reduce.py \
  -m 'l2_device and rocm_lower' --maxfail=5 -vv

/opt/venv/bin/python reports/j-75416052437a/validate_block_reduce_gfx950.py \
  --output reports/j-75416052437a/results.json \
  --timing-warmup 50 --timing-iterations 500
```

The matching wheel was obtained with bounded retries and no dependencies:

```bash
/opt/venv/bin/python -m pip download --no-deps --only-binary=:all: \
  flydsl==0.3.2 -d /job/.cache/wheels
/opt/venv/bin/python -m zipfile -e \
  /job/.cache/wheels/flydsl-0.3.2-cp312-cp312-manylinux_2_27_x86_64.whl \
  /job/.cache/flydsl-wheel
```

## Artifacts

- `reports/j-75416052437a/REPORT.md`: this report.
- `reports/j-75416052437a/validate_block_reduce_gfx950.py`: focused harness.
- `reports/j-75416052437a/results.json`: all 120 raw correctness cases and eight timing configurations.
- `reports/j-75416052437a/validation.log`: raw focused-run output.
- `reports/j-75416052437a/environment.txt`: measured GPU, toolchain, native paths, and image identity.

## Limitations and unfinished work

- Native non-power-of-two block products are intentionally unsupported by `BlockReduce`; only masked tails were validated.
- Timing includes launch/dispatch overhead and was not cross-checked with a separate device-only profiler.
- The fp16/bf16 10% gate is exploratory because the existing suite has no gate for those dtypes.
- The source tree could not be executed directly with the image's 0.2.4 native bindings; the matching 0.3.2 wheel was used instead.
- AITER import is broken in this image and was not exercised.
