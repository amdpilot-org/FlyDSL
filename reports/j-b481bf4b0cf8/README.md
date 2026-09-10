# AOT gfx950 robustness slice

## Scope

This report covers ROCm/FlyDSL issue 621 ("More robust AOT"), read from the public issue API. The issue is open, has no comments, and asks for a schema because AOT currently has weak argument checks. No upstream issue, PR, or comment was modified. No already-working schema fix was found in the tested `main` revision.

The tested slice is a 1024-element float32 vector add. Its launcher signature is:

```text
a=float32[1024], b=float32[1024], out=float32[1024], n=int32,
const_n=1024, block_dim=64, vec_width=4, stream=fx.Stream
```

## Environment

- PR base: `amdpilot-org/FlyDSL` `main` at `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.
- Qualified image: `amdpilotv2/open-job:gbt350-20260909`, operator-provided local image ID `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`. Container hostname was not used as image identity.
- GPU: one assigned AMD Instinct MI350X, `gfx950`, Torch capability `(9, 5)`, unique ID `0xcdce14c4ed97e350`, serial `692517019400`, node ID `5`, GUID `42642`.
- Python: `/opt/venv/bin/python` (Python 3.12.3).
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`; Triton: `3.5.1+rocm7.2.0.gita272dfa8`.
- Installed FlyDSL used for actual gfx950 execution: `0.2.4`, source `/opt/venv/lib/python3.12/site-packages/flydsl/compiler/__init__.py`.
- Native modules: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/_mlir.cpython-312-x86_64-linux-gnu.so`, `_mlirDialectsFly.cpython-312-x86_64-linux-gnu.so`, `libFlyPythonCAPI.so.23.0git`, `libfly_jit_runtime.so`, and `/opt/venv/lib/python3.12/site-packages/triton/backends/amd/lib/libamdhip64.so`.
- Job-private cache: `/tmp/flydsl-cache-j-b481bf4b0cf8`, outside the repository.

## Reproduction

The probe is `aot_gfx950_probe.py`. It compiles with the disk cache enabled, then reloads in a separate process with `FLYDSL_RUNTIME_RUN_ONLY=1`.

```bash
CACHE=/tmp/flydsl-cache-j-b481bf4b0cf8
PYTHON=/opt/venv/bin/python

$PYTHON reports/j-b481bf4b0cf8/aot_gfx950_probe.py compile \
  "$CACHE/aot" "$CACHE/logs/compile-baseline.json"
$PYTHON reports/j-b481bf4b0cf8/aot_gfx950_probe.py run \
  "$CACHE/aot" "$CACHE/logs/run-baseline.json"

PYTHONPATH="$CACHE/overlay-installed" $PYTHON reports/j-b481bf4b0cf8/aot_gfx950_probe.py compile \
  "$CACHE/aot-patched-024" "$CACHE/logs/compile-patched.json"
PYTHONPATH="$CACHE/overlay-installed" $PYTHON reports/j-b481bf4b0cf8/aot_gfx950_probe.py run \
  "$CACHE/aot-patched-024" "$CACHE/logs/run-patched.json"
```

The unchanged numerical gate is:

```python
torch.allclose(actual, expected, rtol=1e-6, atol=1e-6)
```

## Results

Both baseline and patched reloads produced the same valid result as `torch.add`: `allclose=True`, maximum absolute error `0.0`, and output SHA-256 `5210a464f51774bb9e2a8b28a65fa40fadef118da093800ae7c2d0e7b2cf6c1b`.

The baseline and patched artifacts have the same identity because the change affects only the Python pre-launch wrapper, not compiled MLIR:

- Size: `28458` bytes.
- SHA-256: `1b82af7868a7ea648a817652ed05fb1c57aa10fe2bdb1ecf4922b95c2b2a41ea`.
- Baseline path: `/tmp/flydsl-cache-j-b481bf4b0cf8/aot/vec_add_69ff0479b02d28cbe3ed548c1c1f4eb8/11fdb25ff36bcfa5.pkl`.
- Patched path: `/tmp/flydsl-cache-j-b481bf4b0cf8/aot-patched-024/vec_add_b3a6de6f5472c488fb1b22b5765efa62/11fdb25ff36bcfa5.pkl`.

| Case | Baseline result | Patched result |
|---|---|---|
| `b` float64 instead of float32 | Launched; no raw error; output did not match Torch. | Rejected before launch: `TypeError: flyc.compile() argument 'b' dtype mismatch: expected torch.float32, got torch.float64`. |
| `b` rank 2 instead of rank 1 | Launched; no raw error; flat memory happened to match Torch. | Rejected before launch: `TypeError: flyc.compile() argument 'b' rank mismatch: expected 1, got 2`. |
| `n` float instead of int32 | Rejected by ctypes: `TypeError: 'float' object cannot be interpreted as an integer`. | Rejected before launch: `TypeError: flyc.compile() argument 'n' scalar mismatch: expected integer, got float`. |

Complete raw JSON is retained in `raw-results/`.

## Change

`CompiledFunction` now captures a lightweight schema from the resolved compile-time arguments. Before dispatch, it checks positional argument count, memref dtype and rank, and integer/float scalar category. Constexpr parameters remain count-only because their values are baked in and ignored on later calls. This is a narrow pre-launch guard, not an AOT redesign.

Focused validation:

```bash
PYTHONPATH=/tmp/flydsl-cache-j-b481bf4b0cf8/overlay-installed \
  /opt/venv/bin/python -m pytest -q \
  tests/unit/test_compiled_function_schema.py tests/unit/test_callstate_dispatch.py
```

Result: `16 passed`.

## Limitations

- Actual gfx950 execution used a job-private overlay of the image's FlyDSL `0.2.4` Python package with the schema patch applied; its native extensions were unchanged. This avoids replacing the qualified Torch/ROCm stack.
- An attempt to execute the full `main` Python tree against the image's older native extensions failed with `ImportError: cannot import name 'CopyOpCDNA4BufferLoadAsyncLDSType'`. That environment mismatch is recorded rather than claiming untested cross-version compatibility.
- The schema check is not a performance benchmark, does not validate every possible JitArgument family, and intentionally does not redesign artifact serialization or cross-version loading.
