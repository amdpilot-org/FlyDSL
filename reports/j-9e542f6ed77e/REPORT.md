# Uint32/Uint8 signedness validation on MI350X (gfx950)

## Result

The installed-source FlyDSL stack reproduces the logical unsigned-dtype reconstruction
defect on one assigned AMD Instinct MI350X (`gfx950`). The existing upstream candidate
**ROCm/FlyDSL PR 920**, commit
`de526e0aeafdf4d42896bbf635d2dc14fa599233`, fixes all eight affected cases when tested
unchanged at its own base and pinned MLIR.

- Installed-source baseline: FlyDSL `0.2.4`; four unsigned cases failed, four signed controls passed.
- Candidate PR 920: FlyDSL source `0.3.0`; all eight validation cases passed.
- Candidate focused tests: `65 passed in 4.68s`.
- No FlyDSL code fix is duplicated here. PR 920 is preserved as tested and remains the candidate fix.

This is a new MI350X result. The earlier MI300X result is context only and was not used as proof.

## Environment

- Qualified image: `amdpilotv2/open-job:gbt350-20260909`.
- Requested local image ID: `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.
- GPU: one AMD Instinct MI350X, `gfx950`, ROCm SMI GUID `42642`, serial `692517019400`, device capability `(9, 5)`.
- Python: `/opt/venv/bin/python` (resolved executable `/usr/bin/python3.12`, version `3.12.3`).
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`, `/opt/venv/lib/python3.12/site-packages/torch/__init__.py`.
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`, `/opt/venv/lib/python3.12/site-packages/triton/__init__.py`.
- Installed FlyDSL: `0.2.4`, `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`.
- Installed native runtime: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/libfly_jit_runtime.so`.
- Mirror base: `ed70142704e1a6d5563fb53e1607e3a4b85d7111` (`main`).
- Candidate source: `/job/FlyDSL-candidate`, commit `de526e0aeafdf4d42896bbf635d2dc14fa599233`, parent `9a5c08e77355f915ad35965bea8ea88f0af33bf3`.
- Candidate build: `/tmp/flydsl-cache-j-9e542f6ed77e/candidate-build-nb29/python_packages/flydsl`.
- Candidate native extensions: `/tmp/flydsl-cache-j-9e542f6ed77e/candidate-build-nb29/python_packages/flydsl/_mlir/_mlir_libs`.
- Candidate MLIR pin: LLVM `7f77ca0dbda4abbf9af06537b2c475f20ccd6007`, installed at `/tmp/flydsl-cache-j-9e542f6ed77e/mlir-install-nb29`.

The image ID is the operator-provided qualified local identity. Container hostname was not treated as image identity.

## Early installed-source baseline

The first real GPU execution was a 128-element Int32 load/add/store kernel using the installed
FlyDSL stack. It used `grid=(2,1,1)`, `block=(64,1,1)`, and compared exactly against
`torch.arange(128, dtype=torch.int32, device='cuda') + 1`.

- Exact match: `true`; maximum absolute difference: `0`.
- Timing method: `time.perf_counter` around allocation, first JIT compile, launch, and stream synchronize.
- First GPU execution elapsed time: `0.6819050563499331` seconds.
- Artifact: `/job/baseline-first.json`.

The first launch attempt used dynamic `input_tensor.shape[0]` as a grid dimension and failed
with `MLIRError: GetOp: mode length 1 exceeds input depth 0`. The fixed-grid neighboring control
above ran successfully. This installed-source baseline is labeled separately and is not proof for
later checkout changes.

## Validation design

`validate_signedness.py` launches real gfx950 kernels through Pointer and Tensor arguments across
the JIT and kernel boundaries. Each case loads one element per thread, performs a right shift by
four, converts to `Int32`, and stores to global memory. References are computed independently with
Python integers before launch.

The unchanged numerical gates are exact:

1. Observed output list must equal the independently computed expected list exactly.
2. Reconstructed boundary label must equal the requested logical dtype.

No floating-point tolerance is used. High-bit values intentionally straddle the sign bit:

- Uint32 bits: `0x00000000`, `0x00000001`, `0x7FFFFFFF`, `0x80000000`, `0xC0000000`, `0xFFFFFFFE`, `0xFFFFFFFF`, `0x80000007`.
- Uint8 bits: `0x00`, `0x01`, `0x7F`, `0x80`, `0xC0`, `0xFE`, `0xFF`, `0x87`.

Unsigned references use logical right shift. Signed `Int32`/`Int8` controls use arithmetic right
shift. Torch has no native `uint32`, so the Tensor Uint32 case reinterprets `torch.int32` storage
with `fx.recast_iter(fx.Uint32, ...)`. Tensor Uint8 uses `torch.uint8` storage.

## Raw results

### Installed-source FlyDSL 0.2.4

| Case | Boundary label | Gate |
|---|---|---|
| pointer Uint32 | `Int32` | FAIL |
| pointer Int32 control | `Int32` | PASS |
| tensor Uint32 | `Int32` | FAIL |
| tensor Int32 control | `Int32` | PASS |
| pointer Uint8 | `Int8` | FAIL |
| pointer Int8 control | `Int8` | PASS |
| tensor Uint8 | `Int8` | FAIL |
| tensor Int8 control | `Int8` | PASS |

Unsigned Uint32 expected `[0, 0, 134217727, 134217728, 201326592, 268435455, 268435455, 134217728]`
but observed `[0, 0, 134217727, -134217728, -67108864, -1, -1, -134217728]`.

Unsigned Uint8 expected `[0, 0, 7, 8, 12, 15, 15, 8]` but observed
`[0, 0, 7, -8, -4, -1, -1, -8]`. The signed controls observed those signed values exactly as
expected, isolating the demonstrated reconstruction/sign-extension discrepancy to unsigned dtypes.

### Candidate PR 920 commit `de526e0`

| Case | Boundary label | Expected | Observed | Gate |
|---|---|---|---|---|
| pointer Uint32 | `Uint32` | unsigned list | same | PASS |
| pointer Int32 control | `Int32` | signed list | same | PASS |
| tensor Uint32 | `Uint32` | unsigned list | same | PASS |
| tensor Int32 control | `Int32` | signed list | same | PASS |
| pointer Uint8 | `Uint8` | `[0, 0, 7, 8, 12, 15, 15, 8]` | same | PASS |
| pointer Int8 control | `Int8` | `[0, 0, 7, -8, -4, -1, -1, -8]` | same | PASS |
| tensor Uint8 | `Uint8` | `[0, 0, 7, 8, 12, 15, 15, 8]` | same | PASS |
| tensor Int8 control | `Int8` | `[0, 0, 7, -8, -4, -1, -1, -8]` | same | PASS |

Raw JSON artifacts are `/job/installed-unsigned-results.json` and
`/job/candidate-pr920-gfx950-results.json`.

## Reproduction

The candidate was fetched read-only from its existing fork branch and checked out unchanged:

```bash
git fetch https://github.com/Arist12/FlyDSL.git fix/701-unsigned-signedness:refs/remotes/candidate/pr920
git worktree add --detach /job/FlyDSL-candidate de526e0aeafdf4d42896bbf635d2dc14fa599233
```

The candidate-pinned minimal MLIR and FlyDSL native extensions were built with job-private paths
under `/tmp/flydsl-cache-j-9e542f6ed77e`. The affected validation command was:

```bash
CACHE=/tmp/flydsl-cache-j-9e542f6ed77e
PYTHONPATH="$CACHE/candidate-build-nb29/python_packages" \
LD_LIBRARY_PATH="$CACHE/candidate-build-nb29/python_packages/flydsl/_mlir/_mlir_libs:$CACHE/mlir-install-nb29/lib:/opt/rocm/lib" \
FLYDSL_RUNTIME_ENABLE_CACHE=0 ARCH=gfx950 \
/opt/venv/bin/python reports/j-9e542f6ed77e/validate_signedness.py --json
```

Focused candidate tests:

```bash
CACHE=/tmp/flydsl-cache-j-9e542f6ed77e
cd /job/FlyDSL-candidate
PYTHONPATH="$CACHE/candidate-build-nb29/python_packages" \
LD_LIBRARY_PATH="$CACHE/candidate-build-nb29/python_packages/flydsl/_mlir/_mlir_libs:$CACHE/mlir-install-nb29/lib:/opt/rocm/lib" \
FLYDSL_RUNTIME_ENABLE_CACHE=0 ARCH=gfx950 \
/opt/venv/bin/python -m pytest -q tests/unit/test_unsigned_tensor_dtype.py tests/language/test_unsigned_semantics.py
```

## Limits and unfinished work

- PR 920 was tested unchanged at its own base and pinned MLIR; it was not rebased or merged onto current mirror `main`.
- Current mirror `main` source could not run against the installed 0.2.4 native runtime because its newer pipeline requires the absent `convert-rocdl-fastmath-ops` pass. The installed-source baseline is therefore reported separately.
- The candidate’s native vector-load inference also could not be validated by mixing its Python source with the older installed native runtime (`ValueError: dtype Uint32 does not match vector element type ui32`); a matching native build was required.
- No full model weights, alternate framework stack, synthetic burn, unbounded loop, or repeated GPU work were used.
- No upstream issue, PR, comment, or review was posted or modified.
