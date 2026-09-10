# FlyDSL custom-op Inductor prototype

## Result

This narrow prototype wraps the existing FlyDSL vector-add operation from
`examples/01-vectorAdd.py` in a Torch custom operator and compares eager
execution with `torch.compile(..., fullgraph=True, backend="inductor")`.
The custom operator has an explicit fake implementation. Both an aligned shape
and a predicated tail shape pass on the assigned MI350X (`gfx950`), including a
warm second compiled invocation on a non-default current stream.

This is not a FlyDSL Inductor backend. Inductor treats the FlyDSL call as an
opaque custom operator; it does not lower or optimize FlyDSL internals.

## Scope

- Wrapped operation: `examples/01-vectorAdd.py::vector_add`
- Custom operator: `flydsl_prototype::vector_add`
- Mutation declaration: `mutates_args={"output"}`
- Device registration: `device_types="cuda"`
- Fake/meta behavior: `torch.library.register_fake`, returning `None`
- Compile mode: `fullgraph=True`, `dynamic=False`, `backend="inductor"`
- Aligned shape: `(128, 128)`
- Tail shape: `(100, 1000)`
- Current stream: non-default stream ID `246601504`
- Warm reuse: second invocation of the same compiled callable and shape

The wrapper is isolated under `reports/j-ad628f12156f/`. It does not add an
Inductor backend, migrate production dispatch, register a global FlyDSL
dispatch path, or change kernel semantics.

## Environment and provenance

- Mirror clone: `/job/FlyDSL`
- PR base: `main` at `ed70142704e1a6d5563fb53e1607e3a4b85d7111`
- Source operation: `/job/FlyDSL/examples/01-vectorAdd.py`
- Qualified image ID: `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`
- Python interpreter: `/opt/venv/bin/python3`
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`
- FlyDSL package: `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`
- Torch module: `/opt/venv/lib/python3.12/site-packages/torch/__init__.py`
- Torch ROCm library: `/opt/venv/lib/python3.12/site-packages/torch/lib/libtorch_hip.so`
- FlyDSL ROCm dialect: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/_mlirDialectsFlyROCDL.cpython-312-x86_64-linux-gnu.so`
- FlyDSL JIT runtime: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/libfly_jit_runtime.so`
- ROCm HIP runtime: `/opt/rocm-7.2.0/lib/libamdhip64.so.7.2.70200`
- GPU: AMD Instinct MI350X, `gfx950`, Torch capability `(9, 5)`, UUID `35653934-6639-6363-3634-316634303237`
- ROCm SMI identity: node ID `7`, GUID `51966`, PCI bus ID `134`
- Job-private caches: `/tmp/flydsl-cache-j-ad628f12156f/{flydsl,triton,inductor,tmp}`

The complete source and native-module path list is retained in
`reports/j-ad628f12156f/results.json`.

## Reproduction

Run from `/job/FlyDSL` with the qualified interpreter:

```bash
export FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-ad628f12156f/flydsl
export TRITON_CACHE_DIR=/tmp/flydsl-cache-j-ad628f12156f/triton
export TORCHINDUCTOR_CACHE_DIR=/tmp/flydsl-cache-j-ad628f12156f/inductor
export TMPDIR=/tmp/flydsl-cache-j-ad628f12156f/tmp

/opt/venv/bin/python3 -m py_compile \
  examples/01-vectorAdd.py \
  reports/j-ad628f12156f/inductor_custom_op_prototype.py

/opt/venv/bin/python3 examples/01-vectorAdd.py

/opt/venv/bin/python3 \
  reports/j-ad628f12156f/inductor_custom_op_prototype.py \
  --output reports/j-ad628f12156f/results.json

rocm-smi --showproduct --showdriverversion
```

## Raw results

The primary numerical gate remains the example's default
`torch.allclose(output, expected)` check. `torch.equal` and maximum absolute
difference are also recorded as observations. No numerical tolerance was
loosened.

| Shape | Path | `allclose` | `equal` | Max abs diff | GPU time |
|---|---|---:|---:|---:|---:|
| `(128, 128)` | eager | true | true | `0.0` | `417.185791015625 ms` |
| `(128, 128)` | compiled cold | true | true | `0.0` | `1200.439453125 ms` |
| `(128, 128)` | compiled warm | true | true | `0.0` | `0.28852400183677673 ms` |
| `(100, 1000)` | eager | true | true | `0.0` | `0.13748100399971008 ms` |
| `(100, 1000)` | compiled cold | true | true | `0.0` | `21.966968536376953 ms` |
| `(100, 1000)` | compiled warm | true | true | `0.0` | `0.2539229989051819 ms` |

The fake check passed with `FakeTensor` inputs and returned `NoneType`. The
first eager and compiled timings include FlyDSL JIT and Inductor compilation
work; they are not a performance benchmark. The warm timings demonstrate reuse
after compilation.

The complete raw JSON is in `reports/j-ad628f12156f/results.json`.

## Unsupported and unfinished integration

- No unsupported failure occurred for this narrow forward-only custom-op path.
- Inductor does not inspect or lower FlyDSL MLIR; the custom-op boundary is opaque.
- No FlyDSL Inductor backend is implemented.
- No production dispatch or existing FlyDSL kernel is migrated.
- No autograd/backward registration, dynamic-shape reuse, CUDA graph capture,
  multi-GPU execution, non-float32 dtype, or non-ROCm device is claimed.
- The timings are single-run diagnostic measurements, not tuned benchmarks.

Upstream `ROCm/FlyDSL` issue 691 is a terse open feature request titled
`[Feature]: inductor prototype`. It has no comments or linked changes. A search
of upstream pull requests for `inductor`, `torch.compile`, and `custom op`
found no already-working equivalent integration, so this result does not
duplicate an existing fix. No upstream issue, pull request, or comment was
posted or modified.
