# Autotune exact-tie determinism report

## Scope

This change makes the generic autotuner's exact timing ties independent of candidate order. It does not change invalid-candidate pruning, artifact identity/loading, cache-key axes, or timing measurement. The added GPU test uses three valid RMSNorm candidates with the same benchmark result and checks both forward and reverse candidate order.

## Environment

- Image: `amdpilotv2/open-job:gbt350-20260909`
- Image ID: `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`
- GPU: one AMD Instinct MI350X, `gfx950`, unique ID `0x5fb42ff90866060e`, serial `692517020502`
- Python: `/opt/venv/bin/python` (3.12.3)
- Torch: `/opt/venv/lib/python3.12/site-packages/torch/__init__.py`, version `2.9.1+rocm7.2.0.git7e1940d4`
- Triton: `/opt/venv/lib/python3.12/site-packages/triton/__init__.py`, version `3.5.1+rocm7.2.0.gita272dfa8`
- Installed baseline FlyDSL: `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`, version `0.2.4`
- Modified source checkout: `/job/FlyDSL`, base commit `ed70142704e1a6d5563fb53e1607e3a4b85d7111`
- GPU validation source/native hybrid: checkout Python sources at `/tmp/flydsl-src-copy-j-e6c1d55db215-v2/flydsl` with native MLIR bindings from FlyDSL wheel `0.3.2` at `/tmp/flydsl-wheel-j-e6c1d55db215/flydsl/_mlir`

The installed-source baseline is recorded separately in `/job/baseline-first.json`. It is not proof for later checkout changes.

## Baseline

The exact current RMSNorm test could not run against installed FlyDSL `0.2.4`:

```bash
PYTHONPATH=/job/FlyDSL FLYDSL_AUTOTUNE=0 \
  FLYDSL_AUTOTUNE_CACHE_DIR=/tmp/flydsl-cache-j-e6c1d55db215/baseline-first-supported \
  /opt/venv/bin/python -m pytest -q \
  tests/kernels/test_rmsnorm_autotune.py::test_rmsnorm_autotuned_default_uses_current_stream_and_skips_search
```

Raw result: collection failed with `ImportError: cannot import name 'get_warp_size' from 'flydsl.runtime.device'`.

The supported neighboring GPU control was the existing vector-add example:

```bash
PYTHONPATH=/job/FlyDSL FLYDSL_AUTOTUNE=0 \
  FLYDSL_AUTOTUNE_CACHE_DIR=/tmp/flydsl-cache-j-e6c1d55db215/baseline-vector-add \
  /opt/venv/bin/python /job/FlyDSL/examples/01-vectorAdd.py
```

Raw result: `PASS`, complete-process wall time `2.605683 s`. The example checks `torch.allclose(A + B, C)` after synchronization. No synthetic burn, sleep loop, unbounded loop, or repeated work was used.

## Reproduction

Run the focused GPU-free tie test:

```bash
PYTHONPATH=/tmp/flydsl-src-copy-j-e6c1d55db215-v2:/job/FlyDSL \
  FLYDSL_AUTOTUNE_CACHE_DIR=/tmp/flydsl-cache-j-e6c1d55db215/unit-full-v2 \
  /opt/venv/bin/python -m pytest -q \
  tests/unit/test_autotune.py::test_equal_timing_tie_break_is_independent_of_candidate_order
```

Run the real GPU contract:

```bash
PYTHONPATH=/tmp/flydsl-src-copy-j-e6c1d55db215-v2:/job/FlyDSL \
  FLYDSL_AUTOTUNE_CACHE_DIR=/tmp/flydsl-cache-j-e6c1d55db215/gpu-rmsnorm-all \
  /opt/venv/bin/python -m pytest -q \
  tests/kernels/test_rmsnorm_autotune.py::test_rmsnorm_equal_timing_tie_is_independent_of_candidate_order
```

The GPU test uses these valid candidates, all benchmarked at `1.0 ms`:

```python
Config(BLOCK_THREADS=128, waves_per_eu=1)
Config(BLOCK_THREADS=256, waves_per_eu=1)
Config(BLOCK_THREADS=512, waves_per_eu=1)
```

It runs the set forward and reversed, requires the same selected config (`BLOCK_THREADS=128`, `waves_per_eu=1`), then executes a cache hit with search disabled. Every selected and cached output is compared with the independent float32 RMSNorm reference using `torch.testing.assert_close(..., rtol=0, atol=2e-2)`.

## Raw validation results

- `tests/unit/test_autotune.py`: `56 passed in 0.92s`
- `tests/kernels/test_rmsnorm_autotune.py`: `6 passed in 3.08s`
- Focused tie GPU test: `1 passed in 1.44s`
- Black check on changed Python files: `3 files would be left unchanged`
- Ruff check on changed Python files: `All checks passed!`
- `git diff --check`: passed

## Limitations

The checkout had no built `_mlir` artifacts and no local LLVM/MLIR installation. GPU validation therefore paired the modified checkout Python sources with the closest available FlyDSL `0.3.2` native bindings in a private temporary directory. This mismatch is recorded above; a normal source build can rerun the same tests without the hybrid path.
