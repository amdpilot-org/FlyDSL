# Vector.reduce extrema contract investigation

## Scope

This investigation covers the public `Vector.reduce("max")` and
`Vector.reduce("min")` floating-point contract on one assigned MI350X
(`gfx950`). It intentionally does not migrate kernels or change reduction
behavior.

Read-only upstream context:

- ROCm/FlyDSL issue 934 remains open and lists issue 939 as its
  `Vector.reduce` child.
- ROCm/FlyDSL issue 939 is closed as completed, has no comments, no linked
  pull request, and no closing commit. The current mapping remains
  `max -> maxnumf` and `min -> minimumf`.

## Contract

The public floating-point reduction mapping is unchanged:

- `max` generates `vector.reduction <maxnumf>` and follows documented
  `arith.maxnumf`: NaN is suppressed, and `-0.0`/`+0.0` may return either
  signed zero.
- `min` generates `vector.reduction <minimumf>` and follows documented
  `arith.minimumf`: NaN propagates, and `-0.0` is less than `+0.0`.

`maximumf` and `maxnumf` are therefore not interchangeable. This change
documents that distinction and adds explicit GPU oracles rather than relying on
Torch's `max`/`min` or assuming NaN behavior.

Mirror PR 355 validates scalar expression extrema lowering. This investigation
is distinct because it exercises the public `Vector.reduce` operation and its
one-dimensional vector-reduction mapping.

`reduction_profile` is accepted by the current API but ignored. The GPU test
therefore covers supported launch layouts of 64 threads (one wave) and 128
threads (two waves) rather than claiming unsupported reduction-profile control.

## Environment

- GPU: AMD Instinct MI350X, `gfx950`, driver `7.1.1.31500000`, unique ID
  `0x5fb42ff90866060e`, serial `692517020502`.
- Required image: `amdpilotv2/open-job:gbt350-20260909`, local image ID
  `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.
- Interpreter: `/opt/venv/bin/python`.
- Installed FlyDSL: `0.2.4` at
  `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`.
- Installed Torch: `2.9.1+rocm7.2.0.git7e1940d4`, HIP
  `7.2.26015-fc0010cf6a`.
- Installed Triton: `3.5.1+rocm7.2.0.gita272dfa8`.
- Native modules:
  `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/_mlirDialectsFlyROCDL.cpython-312-x86_64-linux-gnu.so`,
  `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/libfly_jit_runtime.so`,
  and
  `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/_mlirDialectsFly.cpython-312-x86_64-linux-gnu.so`.
- Persistent checkout: `/job/FlyDSL`, base commit
  `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.

## Early installed-source baseline

The first successful installed-source GPU execution used a fresh private JIT
cache and completed in `0.39416765235364437` seconds. Timing used
`time.perf_counter` around the FlyDSL JIT call plus `torch.cuda.synchronize`;
the first measurement includes compilation.

The baseline used a four-element `fx.Vector.from_elements` reduction and
explicit Python oracles for the documented scalar operations. All 16 records
matched:

| Threads | Case | Max result | Min result |
|---:|---|---:|---:|
| 64 | finite `[1, -3, 2, 0]` | `2.0` | `-3.0` |
| 64 | NaN `[NaN, 1, 0, 0]` | `1.0` | `NaN` |
| 64 | infinity `[-inf, 1, inf, 0]` | `inf` | `-inf` |
| 64 | signed zero `[-0, +0, +0, +0]` | either signed zero | `-0.0` |
| 128 | finite `[1, -3, 2, 0]` | `2.0` | `-3.0` |
| 128 | NaN `[NaN, 1, 0, 0]` | `1.0` | `NaN` |
| 128 | infinity `[-inf, 1, inf, 0]` | `inf` | `-inf` |
| 128 | signed zero `[-0, +0, +0, +0]` | either signed zero | `-0.0` |

The complete raw baseline is saved outside the repository at
`/job/baseline-first.json`. It is labeled as installed-source evidence and is
not proof for later checkout changes.

An intermediate 128-thread max record was invalid because its probe wrapper
accidentally invoked the min kernel. The saved baseline was replaced by a
corrected fresh-cache rerun before delivery.

## Checkout validation

Commands:

```bash
cd /job/FlyDSL
export PYTHONPATH=/job/FlyDSL
export LD_LIBRARY_PATH=/opt/venv/lib/python3.12/site-packages/flydsl.libs:/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs
export FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-installed-control-j-01b838b8b223
python -m pytest -c tests/pytest.ini tests/kernels/test_vector_reduce_semantics.py -q
python -m pytest -c tests/pytest.ini tests/unit/test_vector.py -q
python -m pytest -c tests/pytest.ini tests/language/test_arithmetic_types.py -q -k reduce
```

Results:

- New GPU contract test: 16 passed.
- Existing `tests/unit/test_vector.py`: 85 passed.
- Existing reduction tests in `tests/language/test_arithmetic_types.py`:
  17 passed, 378 deselected.

A private source overlay of checkout Python `0.3.3` over installed native
`0.2.4` failed before GPU execution because the checkout pipeline requests
`convert-rocdl-fastmath-ops`, which is not registered by the installed native
stack. The image has no MLIR CMake development tree, so a full checkout build
was not attempted within this bounded job. The supported control executes the
checkout test file unchanged with the qualified installed FlyDSL native stack.

## Left undone

- No full source build of checkout `0.3.3` was run.
- No reduction behavior or kernel call sites were changed.
- No upstream issue, pull request, or comment was posted or modified.
