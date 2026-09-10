# FlyDSL issue 862 specialization investigation

## Result

The requested scalar and enum-mode specialization behavior is already fixed on the tested `main` commit. Commit `c3bd00455f711bd4f8d521951e0f5d9162437d8d` (upstream PR 1031) adds `enum.Enum` to `_collect_closure_scalar_vals`; scalar closure values were already included. No FlyDSL compiler change is therefore proposed.

This report adds a bounded real-GPU probe and raw results showing that scalar and mode specializations get distinct JIT manager keys, do not reuse incompatible generated code, and match independent Torch references through both cold compilation and cold disk-load paths.

## Scope

- Upstream context: ROCm/FlyDSL issue 862, "reduce Flydsl compile time".
- Issue 862 has no comments. Its timeline links merged PR 964, which only defaults `CMAKE_BUILD_TYPE` to `RelWithDebInfo`; it does not change specialization identity.
- The relevant existing fix is commit `c3bd00455f711bd4f8d521951e0f5d9162437d8d`, which is an ancestor of tested `main` commit `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.
- This investigation is limited to compiler specialization identity. It does not test concurrent cache publication or attribute latency to compilation.

## Environment

- Image: `amdpilotv2/open-job:gbt350-20260909`, local ID `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.
- GPU: one assigned AMD Instinct MI350X, `gfx950`, Torch capability `(9, 5)`.
- Interpreter: `/opt/venv/bin/python`.
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`, HIP `7.2.26015-fc0010cf6a`.
- Installed FlyDSL: `0.2.4` at `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`.
- Installed MLIR extensions: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/`.
- Checkout: `/job/FlyDSL`, commit `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.
- All caches were job-private under `/tmp`, outside `/job`.

## Installed-source baseline

`/job/baseline-first.json` records the first installed-source GPU execution. It uses the package documentation's 128-element float32 vector-add kernel, a fresh `FLYDSL_RUNTIME_CACHE_DIR`, and `time.perf_counter` around the first call followed by `torch.cuda.synchronize`.

- Elapsed first GPU execution: `0.4114648848772049` seconds.
- Independent reference: Torch `A + B`.
- Maximum absolute error: `0.0`.
- `torch.allclose`: `true`.
- Cached native artifact: `vectorAdd_2540f6a518de8ec9f803623374a5bd99/cb698ff3ff7c561c.pkl`, 24146 bytes.

This installed-source baseline is environment context only and is not proof of behavior in the later checkout.

## Checkout compatibility

Directly running current `main` with the installed 0.2.4 MLIR extensions fails before GPU execution:

```text
ValueError: MLIR Textual PassPipeline Parser:
'convert-rocdl-fastmath-ops' does not refer to a registered pass or pass pipeline
```

The image has no `cmake`, `clang++`, or compatible prebuilt MLIR development tree, so a source rebuild is not a bounded operation here. As a meaningful neighboring control, `compat_vector_add.py` removes only that one new pass from the in-memory pipeline while retaining current `main` Python logic and the installed native/runtime libraries. With that labeled compatibility shim, `examples/01-vectorAdd.py` reports `PASS` on gfx950.

The specialization probe applies the same single-pass compatibility shim. It does not alter repository compiler code or claim to test the unshimmed current pipeline.

## Specialization probe

`specialization_cache_probe.py` defines a pointer kernel whose generated code depends on:

- a scalar closure value (`scale`), and
- an enum closure value (`Mode.ADD` versus `Mode.MAX`).

It exercises four bounded cases: scales `2.0` and `3.0` crossed with `ADD` and `MAX`. Each case uses 1024 float32 elements and an independent Torch reference:

- `ADD`: `A * scale + B`.
- `MAX`: `torch.maximum(A, B) * scale`.

The probe records the JIT manager key, cold-call time, warm in-process call time, and numerical error. `populate` compiles all four cases in one process. `load` starts a separate process with the same disk cache and evaluates the cases in reverse order, forcing cold disk loads rather than in-process reuse.

### Commands

```bash
SRC=/tmp/flydsl-src-j-098141cbd04d-v3
cp -a /job/FlyDSL/python/flydsl "$SRC/flydsl"
ln -sfn /opt/venv/lib/python3.12/site-packages/flydsl/_mlir "$SRC/flydsl/_mlir"

export PYTHONPATH="$SRC"
export FLYDSL_SOURCE_COMMIT=$(git -C /job/FlyDSL rev-parse HEAD)
export FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-098141cbd04d-specialization

/opt/venv/bin/python reports/j-098141cbd04d/specialization_cache_probe.py populate \
  reports/j-098141cbd04d/specialization_populate.json

/opt/venv/bin/python reports/j-098141cbd04d/specialization_cache_probe.py load \
  reports/j-098141cbd04d/specialization_load.json
```

The actual run used a timestamped fresh cache directory recorded in both JSON result files.

## Observed identity

The full argument cache key is identical across the four cases because pointer, dtype, size, stream, target, and invalidating environment values are identical. That is expected: closure/source specialization is represented by `manager_key`, which selects a separate cache directory and therefore a separate compiled artifact.

The four manager keys were distinct in both phases:

- `4e5f8e2e8e19750cadf54ab1be7cde37`
- `2d15b60f373064ddde30c6a26a88613e`
- `5159a869fe6d1a479dc616e0471c23d7`
- `b08065c044b50d794d5f803a85531b49`

All eight cold/warm calls had maximum absolute error `0.0` and `allclose=true`. Reverse-order cold disk loads also produced the correct mode and scale for every case, so incompatible generated code was not reused.

## Regression test

The existing upstream regression was also run directly against current `main`:

```bash
PYTHONPATH=/tmp/flydsl-src-j-098141cbd04d-v3 \
/opt/venv/bin/python -m pytest -q \
  tests/unit/test_jit_cache_key_completeness.py::test_enum_closures_reach_the_cache_key
```

Result: `1 passed in 0.45s`.

## Limitations

- No source rebuild was attempted because the qualified image lacks the required build toolchain and compatible MLIR development files.
- The current-`main` GPU probe uses the documented one-pass compatibility shim because installed native extensions predate the new fastmath pass. This is labeled in every result and does not modify compiler behavior in the repository.
- The probe is intentionally small and bounded; it is not a latency benchmark and does not attempt to solve issue 862's broader compile-time cost.
- No upstream issue, pull request, or comment was posted or modified.
