# MI350X gfx950 conv3d implicit layout validation

## Result

The candidate implementation at mirror pull request 315, commit
`19f7acc4e61f06f99742ffcb326585be43fb685a`, passed the synthetic two-layer
`conv3d_implicit` validation on one AMD Instinct MI350X (`gfx950`). All NCDHW,
NDHWC, mixed-input/output, explicit-intermediate-conversion, and
`out_layout=None` paths matched PyTorch at the unchanged gate
`rtol=2e-2, atol=2e-2`.

Mirror `main` at `ed70142704e1a6d5563fb53e1607e3a4b85d7111` does not expose the
public `layout` / `out_layout` arguments. Its baseline call failed before kernel
launch with:

```text
TypeError: _conv3d_impl() got an unexpected keyword argument 'layout'
```

This report does not duplicate the open candidate fix. It records an independent
MI350X/gfx950 qualification of that exact candidate commit.

## Scope and upstream context

- Public mirror issue: `amdpilot-org/FlyDSL` issue 344.
- Read-only upstream context: `ROCm/FlyDSL` issue 993, read through public REST.
  No upstream issue, pull request, or comment was changed.
- Issue 993 requests independent input and output layouts so a chained conv can
  keep NDHWC intermediates and avoid per-call NCDHW-to-NDHWC transposes.
- The issue timeline did not link an upstream pull request. Mirror pull request
  315 was selected as the bounded candidate because it implements the requested
  public API and tests.
- No model weights were downloaded. All tensors were synthetic and random.

## Environment

| Item | Recorded value |
| --- | --- |
| Qualified image | `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7` |
| GPU | AMD Instinct MI350X, device `0x75a0`, GUID `36538`, `gfx950` |
| GPU capability | `(9, 5)`, 256 CUs, 251.984 GiB reported memory |
| ROCm SMI driver | `7.1.1.31500000` |
| Torch | `2.9.1+rocm7.2.0.git7e1940d4` |
| Torch HIP | `7.2.26015-fc0010cf6a` |
| Triton | `3.5.1+rocm7.2.0.gita272dfa8` |
| AITER | `amd-aiter==0+gd9e5ef7ce08ee7045d583aed768cff41aa9210fe` |
| FlyDSL source/runtime | candidate source version `0.3.3`, rebuilt from the checkout |
| Python | `/opt/venv/bin/python`, Python `3.12.3` |
| Torch module | `/opt/venv/lib/python3.12/site-packages/torch/__init__.py` |
| Triton module | `/opt/venv/lib/python3.12/site-packages/triton/__init__.py` |
| AITER module | `/opt/aiter/aiter/__init__.py` |
| Rebuilt FlyDSL module | `/job/.flydsl-build/python_packages/flydsl/__init__.py` |
| HIP library | `/opt/rocm-7.2.0/lib/libamdhip64.so.7` |
| `hipcc` | HIP `7.2.26015-fc0010cf6a`, AMD clang `22.0.0git` |

The image ID above is the operator-provided local image ID. It was not treated
as a pullable registry digest and was not inferred from the container hostname.

The preinstalled FlyDSL distribution was `0.2.4`. Its Python API did not accept
the source kernel's `s_waitcnt(lgkmcnt=0)` spelling, causing 66 of the initial
72 candidate tests to fail before kernel execution. The qualified Torch, Triton,
AITER, and ROCm installations were preserved. Only the FlyDSL checkout runtime
and its pinned LLVM/MLIR dependency were rebuilt into job-private paths.

## Workload

The synthetic chain used bf16 activations and weights, float32 biases, and a
bf16 reference bias. The reference used `torch.nn.functional.conv3d` with the
same stride, padding, and bias semantics.

| Layer | Input | Weight | Stride | Padding |
| --- | --- | --- | --- | --- |
| 1 | `(2, 32, 5, 8, 10)` | `(64, 32, 3, 3, 3)` | `(1, 2, 1)` | `(1, 0, 1)` |
| 2 | reference layer 1 | `(48, 64, 3, 3, 3)` | `(1, 1, 2)` | `(0, 1, 1)` |

The random seed was `344`. The custom harness forced `splitk=1` for stable
direct-epilogue timing. The candidate's separate test suite also covers split-K
and autotuned paths.

## Numerical gate

Every correctness comparison in every path used the same gate:

```python
torch.allclose(actual.float(), expected.float(), rtol=2e-2, atol=2e-2)
```

The harness also recorded mismatch count, maximum absolute difference, and mean
absolute difference. No path changed the gate.

| Path | Intermediate max / mean abs diff | Final max / mean abs diff | Mismatches | Pass |
| --- | ---: | ---: | ---: | --- |
| NCDHW → NCDHW → NCDHW | `0.0078125 / 0.00034936` | `0.015625 / 0.00265329` | `0` | yes |
| NDHWC → NDHWC → NDHWC | `0.0078125 / 0.00034936` | `0.015625 / 0.00265329` | `0` | yes |
| NCDHW → NDHWC → NCDHW | `0.0078125 / 0.00034936` | `0.015625 / 0.00265329` | `0` | yes |
| NDHWC → NCDHW → NDHWC | `0.0078125 / 0.00034936` | `0.015625 / 0.00265329` | `0` | yes |
| Explicit NCDHW→NDHWC between layers | `0.0078125 / 0.00034936` | `0.015625 / 0.00265329` | `0` | yes |
| `out_layout=None` inherits NDHWC | `0.0078125 / 0.00034936` | `0.015625 / 0.00265329` | `0` | yes |

The explicit-conversion path also compared the converted intermediate against the
NDHWC view of the PyTorch reference: maximum absolute difference `0.0078125`,
mean absolute difference `0.00034936`, and zero mismatches.

## Measured conversion overhead

Timing used five warmups, 20 timed calls with CUDA events, and five profiled
calls. Profiler values are per-call self device time. Event-time deltas include
conv performance, launch, and allocation effects; the transpose column is the
actual conversion-kernel device time.

| Case | Event ms/call | Conv µs/call | Transpose µs/call | Other µs/call |
| --- | ---: | ---: | ---: | ---: |
| Single NCDHW input → NDHWC output | `0.0388685` | `8.5034` | `3.5590` | `0.0000` |
| Single NDHWC input → NDHWC output | `0.0259063` | `6.4950` | `0.0000` | `0.0000` |
| Two-layer NCDHW chain | `0.0704368` | `23.3024` | `6.6622` | `0.0000` |
| Two-layer NDHWC chain | `0.0474206` | `20.1982` | `0.0000` | `0.0000` |
| Two-layer mixed chain | `0.0581986` | `22.4062` | `3.0390` | `0.0000` |
| Two-layer explicit mid conversion | `0.0702708` | `22.7022` | `6.7020` | `0.0000` |
| Direct NCDHW→NDHWC transpose | `0.0110401` | `0.0000` | `2.8472` | `0.0000` |

Observed end-to-end deltas were:

- Single conversion path minus native NDHWC path: `0.0129622 ms` (`12.9622 µs`).
- Two-layer NCDHW chain minus two-layer NDHWC chain: `0.0230162 ms`
  (`23.0162 µs`).

The conversion kernel observed in the single-layer path was
`transpose_kernel_0`, with `3.5590 µs/call` self device time. The native-layout
path emitted no transpose kernel. The direct transpose measurement was
`2.8472 µs/call`. These are actual measurements from this run, not inferred
baselines.

## Commands

The working clone was created with:

```bash
cd /job
git clone --depth=100 https://github.com/amdpilot-org/FlyDSL.git FlyDSL
cd FlyDSL
git switch -c amdpilot/j-a6805b932c4a main
```

The candidate was tested without modifying it:

```bash
cd /job/FlyDSL
git fetch --depth=100 origin 19f7acc4e61f06f99742ffcb326585be43fb685a
git worktree add --detach /job/FlyDSL-candidate 19f7acc4e61f06f99742ffcb326585be43fb685a
```

The job-private LLVM/MLIR and FlyDSL runtime builds were:

```bash
export PIP_TARGET=/job/.build-deps
export PYTHONPATH=/job/.build-deps
export PATH=/job/.patchelf/bin:/job/.build-deps/cmake/data/bin:/job/.build-deps/bin:/opt/venv/bin:$PATH
export LLVM_BUILD_PROFILE=amd-minimal
export LLVM_INSTALL_DIR=/job/.llvm-mlir-install
export LLVM_INSTALL_TGZ=/job/.llvm-mlir-install.tgz
export FLY_BUILD_DIR=/job/.flydsl-build
export FLY_CACHE_DIR=/job/.flydsl-cache
export TRITON_CACHE_DIR=/job/.triton-cache
export MLIR_PATH=/job/.llvm-mlir-install
export HIP_PLATFORM=amd

cd /job/FlyDSL-candidate
git submodule update --init --recursive
bash scripts/build_llvm.sh -j32
bash scripts/build.sh -j32
```

Focused candidate tests:

```bash
cd /job/FlyDSL-candidate
export PYTHONPATH=/job/.flydsl-build/python_packages:/job/FlyDSL-candidate:/job/.build-deps
export FLY_CACHE_DIR=/job/.flydsl-cache
export TRITON_CACHE_DIR=/job/.triton-cache
/opt/venv/bin/python -m pytest tests/kernels/test_conv3d_implicit.py -vv --disable-warnings
```

Result:

```text
72 passed in 243.72s (0:04:03)
```

Custom MI350X validation:

```bash
cd /job/FlyDSL
export PYTHONPATH=/job/.flydsl-build/python_packages:/job/FlyDSL-candidate:/job/.build-deps
export FLY_CACHE_DIR=/job/.flydsl-cache
export TRITON_CACHE_DIR=/job/.triton-cache
export ROCM_PATH=/opt/rocm-7.2.0
export PATH=/opt/rocm-7.2.0/bin:/opt/venv/bin:$PATH
/opt/venv/bin/python reports/j-a6805b932c4a/validate_conv3d_mi350x.py \
  --candidate /job/FlyDSL-candidate \
  --output reports/j-a6805b932c4a/results.json
```

## Artifacts

- `reports/j-a6805b932c4a/validate_conv3d_mi350x.py`: reproducible validation and timing harness.
- `reports/j-a6805b932c4a/results.json`: complete environment, correctness, event, and profiler results.
- `reports/j-a6805b932c4a/run.log`: custom harness output.
- `reports/j-a6805b932c4a/baseline.log`: mirror-main public API baseline result.

## Uncertainty and left undone

- This validates small synthetic two-layer chains only. It does not claim Wan,
  MiniMax H3, whole-encoder, or production-shape performance.
- No model weights or external model repositories were downloaded.
- The timing sample is one MI350X run with 20 timed calls and five profiled
  calls. It is sufficient to record actual overhead for this workload, not a
  statistical performance characterization.
- AITER was recorded from package metadata and its installed module path. It
  was not imported during validation to avoid triggering unrelated JIT builds.
- The ROCm SMI driver reports `7.1.1.31500000`, while the userspace Torch/HIP
  and `hipcc` stack reports `7.2.26015-fc0010cf6a`; both values are retained.
- The candidate pull request remains open and is not merged by this report.
