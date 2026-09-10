# AOT non-default stream validation on MI350X

## Scope

This investigation validates stream ordering for the documented AOT
`flyc.compile` launch path. It is intentionally distinct from ROCm/FlyDSL
issue 621's broader AOT schema work, scalar specialization, and artifact
relocation.

No runtime fix was needed on the tested stack. The delivery adds a focused GPU
regression for a producer and consumer compiled with `flyc.compile`, joined by
a CUDA/ROCm event, and checked against independent CPU references.

## Environment

- Image: `amdpilotv2/open-job:gbt350-20260909`
- Expected local image ID: `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`
- GPU: one AMD Instinct MI350X, `gfx950`, UUID `GPU-fa55ca8c650dfefb`
- Python: `/opt/venv/bin/python`
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`, `/opt/venv/lib/python3.12/site-packages/torch/__init__.py`
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`, `/opt/venv/lib/python3.12/site-packages/triton/__init__.py`
- Installed FlyDSL: `0.2.4`, `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`
- Installed native runtime: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/libfly_jit_runtime.so`
- Delivery checkout: `/job/FlyDSL`
- PR base: `ed70142704e1a6d5563fb53e1607e3a4b85d7111`
- Job-private caches: `/tmp/flydsl-cache-j-aa49f7eb871c`

## Installed-source baseline

The baseline used the preinstalled FlyDSL package, not the later checkout, and
is not proof for checkout changes.

Command:

```bash
TRITON_CACHE_DIR=/tmp/flydsl-cache-j-aa49f7eb871c/triton \
FLYDSL_CACHE_DIR=/tmp/flydsl-cache-j-aa49f7eb871c/flydsl \
python /job/baseline_installed_flydsl.py
```

Raw result:

- Kernel: `baseline_copy_i32`, 4,096 `int32` elements
- Requested stream: `torch.cuda.current_stream()`
- Actual stream handle: `0` (default stream)
- Timing: `time.perf_counter` around `flyc.compile`, first launch, and synchronize
- First GPU execution elapsed: `0.297022557 s`
- Independent reference: `source.clone()`
- Maximum absolute error: `0`
- Result: exact match, passed
- Log: `/job/baseline-logs/installed-flydsl-copy.log`

The neighboring installed Aiter split-K control built
`module_aiter_core.so` successfully but was refused before collection because
the image has Triton `3.5.1` while the installed Aiter package requires at
least `3.6.0`. The concrete error and 23.573878-second control timing are in
`/job/baseline-first.json`.

## Checkout runtime note

The checkout reports FlyDSL `0.3.3`, but the image contains FlyDSL `0.2.4`
native bindings. Running checkout Python directly against those bindings
failed in the MLIR pass pipeline with:

```text
ValueError: 'convert-rocdl-fastmath-ops' does not refer to a registered pass or pass pipeline
```

The failure occurred before kernel launch. Because this delivery changes only
a Python test, the real GPU cases were run from the delivery checkout with the
qualified installed FlyDSL runtime. No Torch/ROCm package was replaced.

## Non-default AOT stream validation

The new test creates two non-default streams. It asserts both handles are
nonzero and distinct, waits for the default stream on the producer, compiles
and launches the producer, records a producer event, makes the consumer wait
for that event, compiles and launches the consumer, records a consumer event,
and makes the default stream wait for it.

The outputs are compared with CPU-computed references using
`torch.allclose(..., atol=1e-5, rtol=1e-5)`. This leaves the numerical gates
unchanged from the existing stream tests while making the references
independent of the GPU outputs.

The first attempt used `stream=producer` as a keyword and was refused before
launch:

```text
TypeError: CompileCallable.__call__() got an unexpected keyword argument 'stream'
```

This matches the documented positional-only `flyc.compile` contract. The
corrected positional call passed. There was no unsupported-stream refusal on
the qualified runtime.

Focused command:

```bash
TRITON_CACHE_DIR=/tmp/flydsl-cache-j-aa49f7eb871c/triton \
FLYDSL_CACHE_DIR=/tmp/flydsl-cache-j-aa49f7eb871c/flydsl \
pytest -q tests/unit/test_multi_stream_launch.py::TestCrossStreamDependency::test_compiled_function_non_default_stream_event_order
```

Raw result:

```text
1 passed in 2.46s
AOT_NONDEFAULT_STREAM_WALL_SECONDS=4.789168
AOT_NONDEFAULT_STREAM_EXIT_CODE=0
```

Affected neighboring set:

```bash
TRITON_CACHE_DIR=/tmp/flydsl-cache-j-aa49f7eb871c/triton \
FLYDSL_CACHE_DIR=/tmp/flydsl-cache-j-aa49f7eb871c/flydsl \
pytest -q tests/unit/test_multi_stream_launch.py \
  -k 'compiled_function_non_default_stream_event_order or diamond_pipeline_with_event_sync or default_streams or same_stream_dependent_correct'
```

Raw result:

```text
4 passed, 4 deselected in 2.61s
AFFECTED_STREAM_SET_WALL_SECONDS=4.931653
AFFECTED_STREAM_SET_EXIT_CODE=0
```

## Upstream context

- ROCm/FlyDSL issue 621, “More robust AOT,” is open and has no comments.
- Issues 630 and 632 cross-reference it as part of the v0.3 “Robust AOT” roadmap.
- PR 455, merged as `4643be1e84fe03d161f3c95ea32423db27747e00`, fixed the AOT
  stream cache key so stream representations do not create spurious artifacts.
- PR 672, merged as `3e7f66e713c72b03cefddf3bb1cb26f8992288d4`, added fast
  dispatch for changing runtime arguments, including streams.
- Current `main` already contains both changes. This delivery does not
  duplicate those fixes; it adds event-ordered, independent-reference coverage
  for the documented non-default `flyc.compile` path.

No upstream issue, PR, or comment was posted or modified.
