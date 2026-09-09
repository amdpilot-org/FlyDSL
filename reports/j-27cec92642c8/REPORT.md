# Uint32/Uint8 signedness validation on MI300X (gfx942)

## Result

The existing upstream candidate **ROCm/FlyDSL PR 920**, commit
`de526e0aeafdf4d42896bbf635d2dc14fa599233`, fixes the reproduced defect when tested
unchanged on one assigned AMD Instinct MI300X (`gfx942`). No additional FlyDSL code fix
was made, and the candidate commit is preserved as tested.

- Baseline mirror `main` (`ed70142704e1a6d5563fb53e1607e3a4b85d7111`, source version `0.3.3`): 4 unsigned cases failed; 4 signed controls passed.
- Candidate `de526e0...` (source version `0.3.0`): all 8 validation cases passed.
- Candidate's focused upstream tests: `65 passed in 5.48s`.

The candidate stores logical unsignedness in pointer/memref element types (`ui8`, `ui32`)
and maps loads back to signless SSA integer types. This preserves `Uint8`/`Uint32` wrapper
semantics while keeping `arith` operations compatible with signless IR.

## Environment

- Requested qualified image: `amdpilotv2/open-job-mi300:jit-config-readable-260909-banff5`
- Requested local image ID: `sha256:39fe745feda79ecf4c17f4d806d8ef12150bef720f2f07f5c63a20b3ccfd63f1`
- Docker CLI was unavailable in the container, so image metadata could not be independently inspected. The container hostname was not treated as image identity.
- GPU: one AMD Instinct MI300X, `gfx942`, ROCm SMI GUID `6729`, device capability `(9, 4)`.
- Python: `/opt/venv/bin/python` (`3.10.12`).
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`, `/opt/venv/lib/python3.10/site-packages/torch/__init__.py`.
- HIP: `7.2.26015-fc0010cf6a`; ROCk module `6.19.14.31400000`.
- Preinstalled FlyDSL: `0.3.1`, `/opt/venv/lib/python3.10/site-packages/flydsl/__init__.py`.
- Preinstalled native FlyDSL extensions: `/opt/venv/lib/python3.10/site-packages/flydsl/_mlir/_mlir_libs/`.
- Baseline source build: `/job/FlyDSL/build-fly/python_packages/flydsl/`.
- Baseline native extensions: `/job/FlyDSL/build-fly/python_packages/flydsl/_mlir/_mlir_libs/`.
- Candidate source build: `/job/FlyDSL-candidate/build-fly-old/python_packages/flydsl/`.
- Candidate native extensions: `/job/FlyDSL-candidate/build-fly-old/python_packages/flydsl/_mlir/_mlir_libs/`.
- Baseline MLIR pin: LLVM `e2a39f504fee836e4def9581bed817ecc327b9dc`, installed at `/job/llvm-project/mlir_install`.
- Candidate MLIR pin: LLVM `7f77ca0dbda4abbf9af06537b2c475f20ccd6007`, installed at `/job/llvm-project-old/mlir_install`.

The exact candidate commit is based on `9a5c08e77355f915ad35965bea8ea88f0af33bf3`.
It does not compile against current `main`'s newer MLIR pin because ROCDL generated op
signatures changed. It compiled and ran unchanged against its own candidate-era pin.
No upstream issue, PR, or comment was posted or modified.

## Validation design

`validate_signedness.py` launches real gfx942 kernels through both the JIT and kernel
boundaries. Each case loads one element per thread, performs a right shift by four,
converts to `Int32`, and stores to global memory. The host computes references with
Python integers before launch.

The numerical gates are unchanged and exact:

1. The observed output list must equal the host-computed expected list exactly.
2. The reconstructed boundary label must equal the requested logical dtype.

No floating-point tolerance is used.

Input values intentionally straddle the sign bit:

- Uint32 bits: `0x00000000`, `0x00000001`, `0x7FFFFFFF`, `0x80000000`, `0xC0000000`, `0xFFFFFFFE`, `0xFFFFFFFF`, `0x80000007`.
- Uint8 bits: `0x00`, `0x01`, `0x7F`, `0x80`, `0xC0`, `0xFE`, `0xFF`, `0x87`.

The same bits are also run as signed `Int32`/`Int8` controls. Unsigned references use
logical right shift; signed controls use arithmetic right shift. Torch has no native
`uint32` dtype, so the Tensor Uint32 case reinterprets `torch.int32` storage with
`fx.recast_iter(fx.Uint32, ...)` before crossing the JIT/kernel boundary. The Tensor
Uint8 case uses `torch.uint8` storage and the same recast path.

## Raw results

### Baseline `ed701427` (fails unsigned cases)

| Case | Boundary label | Expected | Observed | Gate |
|---|---|---|---|---|
| pointer Uint32 | `Int32` | `[0, 0, 134217727, 134217728, 201326592, 268435455, 268435455, 134217728]` | `[0, 0, 134217727, -134217728, -67108864, -1, -1, -134217728]` | FAIL |
| pointer Int32 control | `Int32` | `[0, 0, 134217727, -134217728, -67108864, -1, -1, -134217728]` | same | PASS |
| tensor Uint32 | `Int32` | `[0, 0, 134217727, 134217728, 201326592, 268435455, 268435455, 134217728]` | `[0, 0, 134217727, -134217728, -67108864, -1, -1, -134217728]` | FAIL |
| tensor Int32 control | `Int32` | `[0, 0, 134217727, -134217728, -67108864, -1, -1, -134217728]` | same | PASS |
| pointer Uint8 | `Int8` | `[0, 0, 7, 8, 12, 15, 15, 8]` | `[0, 0, 7, -8, -4, -1, -1, -8]` | FAIL |
| pointer Int8 control | `Int8` | `[0, 0, 7, -8, -4, -1, -1, -8]` | same | PASS |
| tensor Uint8 | `Int8` | `[0, 0, 7, 8, 12, 15, 15, 8]` | `[0, 0, 7, -8, -4, -1, -1, -8]` | FAIL |
| tensor Int8 control | `Int8` | `[0, 0, 7, -8, -4, -1, -1, -8]` | same | PASS |

### Candidate `de526e0` (all cases pass)

| Case | Boundary label | Expected = Observed | Gate |
|---|---|---|---|
| pointer Uint32 | `Uint32` | `[0, 0, 134217727, 134217728, 201326592, 268435455, 268435455, 134217728]` | PASS |
| pointer Int32 control | `Int32` | `[0, 0, 134217727, -134217728, -67108864, -1, -1, -134217728]` | PASS |
| tensor Uint32 | `Uint32` | `[0, 0, 134217727, 134217728, 201326592, 268435455, 268435455, 134217728]` | PASS |
| tensor Int32 control | `Int32` | `[0, 0, 134217727, -134217728, -67108864, -1, -1, -134217728]` | PASS |
| pointer Uint8 | `Uint8` | `[0, 0, 7, 8, 12, 15, 15, 8]` | PASS |
| pointer Int8 control | `Int8` | `[0, 0, 7, -8, -4, -1, -1, -8]` | PASS |
| tensor Uint8 | `Uint8` | `[0, 0, 7, 8, 12, 15, 15, 8]` | PASS |
| tensor Int8 control | `Int8` | `[0, 0, 7, -8, -4, -1, -1, -8]` | PASS |

## Reproduction

The working clone was created with:

```bash
git clone https://github.com/amdpilot-org/FlyDSL.git /job/FlyDSL
cd /job/FlyDSL
git checkout -b amdpilot/j-27cec92642c8
```

The exact candidate was fetched and checked out without modification:

```bash
git fetch https://github.com/Arist12/FlyDSL.git fix/701-unsigned-signedness:refs/remotes/candidate/pr920
git worktree add --detach /job/FlyDSL-candidate de526e0aeafdf4d42896bbf635d2dc14fa599233
```

MLIR and FlyDSL were built with the repository scripts using job-private `/job` paths.
The focused validation command was:

```bash
PYTHONPATH=/job/FlyDSL-candidate/build-fly-old/python_packages \
LD_LIBRARY_PATH=/job/FlyDSL-candidate/build-fly-old/python_packages/flydsl/_mlir/_mlir_libs:/opt/rocm/lib \
FLYDSL_RUNTIME_ENABLE_CACHE=0 ARCH=gfx942 \
/opt/venv/bin/python reports/j-27cec92642c8/validate_signedness.py --json
```

The candidate's focused tests were run with:

```bash
cd /job/FlyDSL-candidate
PYTHONPATH=/job/FlyDSL-candidate/build-fly-old/python_packages \
LD_LIBRARY_PATH=/job/FlyDSL-candidate/build-fly-old/python_packages/flydsl/_mlir/_mlir_libs:/opt/rocm/lib \
FLYDSL_RUNTIME_ENABLE_CACHE=0 ARCH=gfx942 \
/opt/venv/bin/python -m pytest -q tests/unit/test_unsigned_tensor_dtype.py tests/language/test_unsigned_semantics.py
```

## Limits and unfinished work

- This is a validation report, not a merge/rebase of PR 920 onto current mirror `main`.
- The candidate was tested unchanged at its own base and pinned MLIR. A future integration
  will need to resolve current `main`'s newer ROCDL/MLIR API changes.
- No full model weights, alternate framework stack, or upstream repository modifications were used.
