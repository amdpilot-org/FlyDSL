# Integer vector reduction control on gfx950

## Scope

This investigation covers integer `Vector.reduce` semantics for signed and
unsigned inputs, element widths, and partially active vectors. It is distinct
from floating-point max/min reduction, shifts, shuffles, and pointer
reconstruction.

Upstream issue 934 and its related changes were read. Upstream PR 407 addresses
floating-point extrema and does not implement integer bitwise reductions, so
this change does not duplicate that fix. No upstream issue, PR, or comment was
posted or modified.

## Environment

- Campaign: `repo-e2e-20260909`
- GPU: one AMD Instinct MI350X, `gfx950`, device ID `0x75a0`, GUID `36538`,
  serial `692517020434`
- Qualified image: `amdpilotv2/open-job:gbt350-20260909`
- Local image ID:
  `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`
- Python: `/opt/venv/bin/python` (Python 3.12.3)
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`
- PR base: `ed70142704e1a6d5563fb53e1607e3a4b85d7111`
- Private build cache: `/tmp/flydsl-cache-j-168e48285a31`
- Built FlyDSL package:
  `/tmp/flydsl-cache-j-168e48285a31/flydsl-build/python_packages`
- Built native library directory:
  `/tmp/flydsl-cache-j-168e48285a31/flydsl-build/python_packages/flydsl/_mlir/_mlir_libs`

The installed-source baseline used FlyDSL `0.2.4` from
`/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`. Its native
modules were under
`/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs`. That
baseline is recorded separately in `/job/baseline-first.json` and is not proof
of behavior in this checkout.

## First installed-source GPU baseline

The first GPU control used the preinstalled FlyDSL interpreter and an existing
relevant `vector.reduction(add)` path from
`/opt/aiter/aiter/ops/flydsl/kernels/buffer_ops.py`. It reduced `int32x4`
`[1, 2, 3, 4]` on one active vector.

- GPU result: `10`
- Independent host reference: `10`, from
  `torch.Tensor.sum(dtype=torch.int32)` on the same input
- Comparison: exact match
- Timing method: `time.perf_counter` around `flyc.compile`, one kernel launch,
  and `torch.cuda.synchronize`
- First GPU execution elapsed time: `0.418100548` seconds
- Command wall time: `2.426660901` seconds
- Repetitions: one bounded execution

Attempting to import
`aiter.ops.flydsl.kernels.tensor_shim` for the same control failed with
`ModuleNotFoundError: No module named 'aiter.jit.module_aiter_core'`. Aiter
attempted a 18.3-second JIT build under
`/job/.aiter/jit/build/module_aiter_core` before the import failed. The
standalone `buffer_ops.py` source was loaded directly instead; no neighboring
control was substituted beyond that installed FlyDSL-only path.

## Semantics

`ReductionOp.AND`, `ReductionOp.OR`, and `ReductionOp.XOR` now map to MLIR
`vector.reduction <and>`, `<or>`, and `<xor>`, respectively. Bitwise
reductions are rejected with `TypeError` for floating-point vectors.

Integer `add` wraps modulo `2**width` in the vector element type. Signed
results use two's-complement representation; unsigned results use ordinary
modular representation. Integer `and`, `or`, and `xor` operate on element bit
patterns and are independent of signedness.

The existing `reduction_profile` argument remains accepted for API
compatibility but does not alter generated reductions. That pre-existing
behavior is unchanged by this work.

## GPU validation

The new GPU test compares every result with an independent Python host
reference. It covers:

- Signed and unsigned 8-, 16-, 32-, and 64-bit integers
- `add`, `and`, `or`, and `xor`
- Vector widths `1`, `2`, `4`, `8`, and `16`
- Partial active-vector counts `1`, `3`, `63`, and `127` of 128
- Overflow for `add` and inactive output preservation

Raw pytest summaries:

```text
tests/kernels/test_vector_integer_reduce.py
68 passed

tests/unit/test_vector.py tests/language/test_arithmetic_types.py
488 passed
```

Reproduction commands:

```bash
CACHE=/tmp/flydsl-cache-j-168e48285a31
export PYTHONPATH="$CACHE/flydsl-build/python_packages"
export LD_LIBRARY_PATH="$CACHE/flydsl-build/python_packages/flydsl/_mlir/_mlir_libs"
export FLYDSL_RUNTIME_ENABLE_CACHE=0

/opt/venv/bin/python -m pytest tests/kernels/test_vector_integer_reduce.py -q
/opt/venv/bin/python -m pytest tests/unit/test_vector.py tests/language/test_arithmetic_types.py -q
```

## Unsigned bridge limitation

The current Torch bridge does not support `uint16`, `uint32`, or `uint64`
memrefs. Unsigned GPU cases therefore use same-width signed Torch storage and
explicitly cast each element to the corresponding unsigned FlyDSL dtype inside
the kernel. Results are converted back to unsigned Python integers on the host
before exact comparison. This preserves unsigned semantics while avoiding an
unrelated bridge change.

## Notes and uncertainty

- No full model weights or alternate framework stack were downloaded.
- No synthetic GPU burn, unbounded loop, sleep loop, or repeated work was used.
- The installed-source baseline and checkout validation are labeled separately.
- The Aiter import failure is an environment limitation, not a FlyDSL test
  failure.
- No attempt was made to change floating-point reduction behavior or the
  existing `reduction_profile` semantics.
