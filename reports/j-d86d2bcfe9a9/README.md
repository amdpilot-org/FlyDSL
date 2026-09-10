# gfx950 public shuffle-width investigation

## Scope

This investigation covers the `fx.shuffle_*` child of ROCm/FlyDSL issue 934
(upstream issue 940). It intentionally excludes max/min semantics, NaN
arithmetic, and kernel migration.

## Environment

- Campaign: `repo-e2e-20260909`
- Job: `j-d86d2bcfe9a9`
- Required image: `amdpilotv2/open-job:gbt350-20260909`, local image ID
  `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`
- GPU: one AMD Instinct MI350X, `gfx950`, serial `692517020513`, unique ID
  `0xcb3b7f83d3aa787d`, ROCm driver `7.1.1.31500000`
- Python: `/opt/venv/bin/python` (Python 3.12.3)
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`
- Working clone: `/job/flydsl`
- Tested source commit: `ed70142704e1a6d5563fb53e1607e3a4b85d7111`; the final
  rerun also included this branch's documentation-only source change
- Tested source overlay: `/tmp/flydsl-cache-j-d86d2bcfe9a9/overlay-v1`
- Native modules: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs`

The image's installed FlyDSL wheel is `0.2.4`; the mirror source is `0.3.3`.
The image has no MLIR CMake installation, so a full native rebuild was not
available. The GPU probe used the mirror Python source over the image's native
modules. One unrelated newer pipeline pass, `convert-rocdl-fastmath-ops`, was
removed from the private overlay because it was absent from the image's native
modules. No such change was made to the repository.

## GPU probe

Run from the repository root with the qualified interpreter and a source/native
overlay as described above:

```bash
PYTHONPATH=/tmp/flydsl-cache-j-d86d2bcfe9a9/overlay-v1 \
FLYDSL_RUNTIME_ENABLE_CACHE=0 \
FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-d86d2bcfe9a9/runtime-cache \
FLYDSL_DUMP_IR=1 \
FLYDSL_DUMP_DIR=/tmp/flydsl-cache-j-d86d2bcfe9a9/dumps-final \
python reports/j-d86d2bcfe9a9/shuffle_probe.py
```

The probe launches one 64-thread block (one wave on gfx950) and tests the public
`fx.shuffle_idx`, `fx.shuffle_xor`, `fx.shuffle_up`, and `fx.shuffle_down`
operations. It uses distinct high-bit bit patterns for `Int16`, `Int32`, and
`Int64`, and also covers `Float16`, `BFloat16`, and `Float64`.

Cases:

- `idx` lanes 0 and 63
- `xor` offsets 1 and 63
- `up` offsets 1 and 63
- `down` offsets 1 and 63

The host oracle computes source lanes independently and compares valid lanes
bit-for-bit. It records, but does not assert, raw values for invalid `up` and
`down` lanes because the MLIR `valid` result is intentionally discarded.

Raw result: `shuffle_gfx950_raw.json`
SHA-256: `92e967de746760fcb55660b4d1768851b91128840333e211c9bcedace6286a0e`

Result: **48/48 valid-lane cases matched exactly; 0 mapping failures.**

## Lowering

The final LLVM and ISA dumps showed:

- 16-bit integer and float operands: one `llvm.amdgcn.ds.bpermute`, one
  `ds_bpermute_b32`
- 32-bit operands: one `llvm.amdgcn.ds.bpermute`, one `ds_bpermute_b32`
- 64-bit integer and float operands: two `llvm.amdgcn.ds.bpermute` calls, two
  `ds_bpermute_b32` instructions

No public-layer widening or splitting is needed on gfx950. The observed gap was
diagnostic: the API did not document that `valid` is discarded and boundary
sources are unspecified. The code change documents that contract, and the new
backend-agnostic unit tests pin mode emission, `Int32` conversion, supported
operand widths, vector shape/dtype preservation, exports, and the invalid-mode
diagnostic.

## Validation

```bash
PYTHONPATH=/tmp/flydsl-cache-j-d86d2bcfe9a9/overlay-v1 \
FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-d86d2bcfe9a9/runtime-cache \
python -m pytest -q tests/unit/test_gpu_shuffle_ops.py
```

Result: `14 passed`.

`ruff` is not installed in the qualified image, so formatting was not run.
No numerical gates for max/min or NaN arithmetic were changed, and no kernels
were migrated.
