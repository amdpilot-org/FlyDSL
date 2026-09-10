# FlyDSL cache-publication investigation

## Conclusion

No core FlyDSL change is proposed. The cache-publication behavior targeted by this investigation is already working and already present in `main`:

- `JitCacheManager` uses a per-key advisory `FileLock` for readers, writers, and compile misses.
- Cache writes serialize through a same-directory temporary file and `os.replace`.
- The bounded four-process cold-cache experiment produced one complete pickle, one lock file, no temporary files, no partial-cache load errors, and four exact reference matches.

The already-working publication change is preserved in commit `9d80c1336b3761f2a5511af3e06b4c748702f118` (`[3/5] autotune: add offline config artifacts (#770) (#786)`). It is included in the tested `main` revision `ed70142704e1a6d5563fb53e1607e3a4b85d7111`. This report does not duplicate that fix.

## Environment

- Delivery repository: `amdpilot-org/FlyDSL`
- PR base: `main` at `ed70142704e1a6d5563fb53e1607e3a4b85d7111`
- Image: `amdpilotv2/open-job:gbt350-20260909`, local image ID `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`
- GPU: one assigned AMD Instinct MI350X, `gfx950`, serial `692517019400`, node ID `5`
- Python: `/opt/venv/bin/python3`
- FlyDSL wheel: `0.2.4`, `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`
- FlyDSL native modules: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs`
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`, `/opt/venv/lib/python3.12/site-packages/torch/__init__.py`
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`, `/opt/venv/lib/python3.12/site-packages/triton/__init__.py`
- HIP: `7.2.26015-fc0010cf6a`, `/opt/rocm/bin/hipcc`
- Job-private cache root: `/tmp/flydsl-cache-j-f91c5f66a6b2`

The installed-source baseline is recorded separately in `/job/baseline-first.json`. It is evidence for the preinstalled wheel only and is not proof of later checkout changes.

## Issue 862 context

Read-only context is ROCm/FlyDSL issue 862, `[Issue]: reduce Flydsl compile time`:

- State: open
- Comments: 0
- Linked pull requests: none
- Assignee: `xudoyuan`
- Milestone: `v0.5`

The issue reports FlyDSL JIT compile time relative to Triton on MI355 and ROCm 7.2. It does not describe a partial-cache publication failure. No upstream issue, PR, or comment was posted or changed.

## Installed-source baseline

The first GPU execution used the preinstalled FlyDSL wheel and the existing vector-add example:

```bash
FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-f91c5f66a6b2/baseline-installed \
  /opt/venv/bin/python3 /job/FlyDSL/examples/01-vectorAdd.py
```

- Kernel: `examples/01-vectorAdd.py`, shape `[100, 1000]`, float32
- Reference: `torch.allclose(A + B, C)`
- Result: `PASS`, exit code `0`
- Cold-cache process wall time: `3299 ms`, measured with `date +%s%N` around the complete Python process
- Cache pickle: `/tmp/flydsl-cache-j-f91c5f66a6b2/baseline-installed/vector_add_2481fecf4a6976d3b0f5cf8777735e1d/9cd83d6ddf2b5059.pkl` (`32141` bytes)

An AITER neighboring control was attempted first:

```bash
cd /opt/aiter && /opt/venv/bin/python3 -m pytest -q --collect-only \
  op_tests/flydsl_tests/test_silu_and_mul_fq.py
```

It was unsupported in the installed AITER environment with `ModuleNotFoundError: No module named 'aiter.jit.module_aiter_core'`. The direct installed FlyDSL vector-add control above was the meaningful supported GPU baseline.

## Retained reference

The reference was generated before concurrency testing with seed `20260910`:

```bash
FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-f91c5f66a6b2/reference-cache \
  /opt/venv/bin/python3 reports/j-f91c5f66a6b2/vector_add_worker.py \
    --example /job/FlyDSL/examples/01-vectorAdd.py \
    --reference /tmp/flydsl-cache-j-f91c5f66a6b2/reference-output/vector_add_reference.pt \
    --output /tmp/flydsl-cache-j-f91c5f66a6b2/reference-output/vector_add_reference_run.pt \
    --label reference --create-reference
```

- Reference artifact: `/tmp/flydsl-cache-j-f91c5f66a6b2/reference-output/vector_add_reference.pt`
- Reference run artifact: `/tmp/flydsl-cache-j-f91c5f66a6b2/reference-output/vector_add_reference_run.pt`
- Reference comparison: `allclose=true`, maximum absolute difference `0.0`

## Bounded four-process experiment

Four Python processes started simultaneously against one empty cache directory and the retained reference:

```bash
/opt/venv/bin/python3 reports/j-f91c5f66a6b2/run_bounded_cache_experiment.py \
  --processes 4 \
  --python /opt/venv/bin/python3 \
  --example /job/FlyDSL/examples/01-vectorAdd.py \
  --worker /job/FlyDSL/reports/j-f91c5f66a6b2/vector_add_worker.py \
  --reference /tmp/flydsl-cache-j-f91c5f66a6b2/reference-output/vector_add_reference.pt \
  --cache-dir /tmp/flydsl-cache-j-f91c5f66a6b2/concurrency-4 \
  --results-dir /tmp/flydsl-cache-j-f91c5f66a6b2/concurrency-4-results \
  --timeout-seconds 300
```

| Process | Exit | Wall seconds | Reference match | Max abs diff |
|---|---:|---:|---|---:|
| process-1 | 0 | 3.415 | yes | 0.0 |
| process-2 | 0 | 3.414 | yes | 0.0 |
| process-3 | 0 | 3.414 | yes | 0.0 |
| process-4 | 0 | 3.414 | yes | 0.0 |

Published artifacts:

- Lock: `/tmp/flydsl-cache-j-f91c5f66a6b2/concurrency-4/vector_add_2481fecf4a6976d3b0f5cf8777735e1d/589bbe0250dca637.lock` (`0` bytes)
- Pickle: `/tmp/flydsl-cache-j-f91c5f66a6b2/concurrency-4/vector_add_2481fecf4a6976d3b0f5cf8777735e1d/589bbe0250dca637.pkl` (`32141` bytes)
- Raw result: `reports/j-f91c5f66a6b2/experiment.json`

There were no `.tmp` files after publication and no `Failed to load cache` messages. The experiment was bounded to four processes and a 300-second timeout; no endless stress or synthetic GPU work was used.

## Checkout source validation

The current checkout Python sources were imported with `PYTHONPATH=/job/FlyDSL/python` and the installed native modules. A direct vector-add execution failed before kernel launch because the installed native runtime does not register the current source pipeline pass:

```text
ValueError: MLIR Textual PassPipeline Parser:1:236: error:
'convert-rocdl-fastmath-ops' does not refer to a registered pass or pass pipeline
```

This is a native/Python revision mismatch. Rebuilding LLVM or replacing the qualified Torch/ROCm stack was explicitly out of scope, so no source-build GPU claim is made.

The checkout’s atomic-write behavior was validated without a native rebuild:

```bash
cd /job/FlyDSL && PYTHONPATH=/job/FlyDSL/python \
  /opt/venv/bin/python3 -m pytest -q tests/unit/test_atomic_write.py
```

Result: `3 passed`.

## Reproduction

The report scripts are bounded and use the existing vector-add example. They do not download weights, rebuild LLVM, or modify shared caches. Use a fresh job-private cache directory for each cold-cache run.

1. Generate the reference with `vector_add_worker.py --create-reference`.
2. Run `run_bounded_cache_experiment.py --processes 4`.
3. Inspect `experiment.json`, the single `.pkl`, the `.lock`, and confirm no `.tmp` files remain.

## Left undone

- No core patch is proposed because the publication behavior is already fixed in `main`.
- The current checkout Python source was not executed end-to-end on GPU because its required native pass is absent from the installed wheel; a matching native build would be needed.
- No latency attribution or endless stress campaign was performed; this investigation is limited to cache-publication correctness.
