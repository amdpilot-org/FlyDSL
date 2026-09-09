# MI350X gfx950 autotune mutation validation

## Result

**PASS.** The current FlyDSL autotuner preserves `restore_value` and
`reset_to_zero` semantics across explicit search, final execution, and
job-private cache hits on one AMD Instinct MI350X (`gfx950`). A normal default
call made zero benchmark calls; explicit search made exactly three, one per
candidate. Every output comparison used exact `torch.equal` matching.

This is a validation report, not a framework redesign or a duplicate fix.
Read-only ROCm/FlyDSL issue 770 identifies PR 783 as the merged in-place
correctness fix. The tested source already contains that behavior, so this run
validates it on MI350X rather than changing it.

## Environment

| Item | Recorded value |
|---|---|
| Image | `amdpilotv2/open-job:gbt350-20260909` |
| Image ID | `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7` |
| GPU | AMD Instinct MI350X |
| GPU architecture | `gfx950` |
| GPU serial | `692517020509` |
| GPU node / GUID | `3` / `27295` |
| FlyDSL source commit | `ed70142704e1a6d5563fb53e1607e3a4b85d7111` |
| FlyDSL source version | `0.3.3` |
| Hybrid package version | `0.2.4` |
| Python | `/opt/venv/bin/python` |
| Torch | `2.9.1+rocm7.2.0.git7e1940d4` |
| Torch HIP | `7.2.26015-fc0010cf6a` |
| Triton | `3.5.1+rocm7.2.0.gita272dfa8` |
| ROCm/hip | `7.2.26015-fc0010cf6a` |

### Paths

- Current source autotuner: `/job/FlyDSL/python/flydsl/autotune.py`
- Hybrid autotuner used by the run: `/job/flydsl-hybrid/flydsl/autotune.py`
- Current source autotuner SHA-256: `a3cd737c86f2eb75c61b6936cafbf472b2d6906deb8cd0733e204fc04f0d629e`
- Hybrid autotuner SHA-256: `a3cd737c86f2eb75c61b6936cafbf472b2d6906deb8cd0733e204fc04f0d629e`
- Torch: `/opt/venv/lib/python3.12/site-packages/torch/__init__.py`
- Triton: `/opt/venv/lib/python3.12/site-packages/triton/__init__.py`
- Native MLIR package: `/job/flydsl-hybrid/flydsl/_mlir`

## Semantics validated

The tiny FlyDSL kernel performs `A = A + B` in place and writes the same sum to
`C`. It uses a 4096-element `float32` workload and three bounded candidates:
`BLOCK=64`, `BLOCK=128`, and `BLOCK=256`, with one warmup and three timed calls
per candidate.

- `restore_value=["A"]` snapshots `A` before benchmarking, restores it before each
  repetition, and restores it after search. Normal calls are not restored; a
  second call on the same `A` accumulates.
- `reset_to_zero=["C"]` zeroes `C` before every benchmark repetition and before
  every real execution, including cache hits.
- Explicit search is opt-in through `FLYDSL_AUTOTUNE=1`.
- A default call uses the supplied heuristic default without benchmarking.

## Phase results

| Phase | Searches | Exact result |
|---|---:|---|
| Normal default call | 0 | PASS |
| Explicit search over 3 configs | 3 | PASS |
| Final execution with chosen config | 0 additional | PASS |
| Repeated cache hit on fresh inputs | 0 additional | PASS |
| Repeated call on same `A` | 0 additional | PASS, accumulated as documented |

The chosen config was `BLOCK=128`. The default config was also `BLOCK=128`.
Search instrumentation counted calls to `Autotuner._bench_one` through a
wrapped `do_bench`; it did not rely on timing alone.

## Reproduction

```bash
cd /job/FlyDSL
export PYTHONPATH=/job/flydsl-hybrid
export LD_LIBRARY_PATH=/opt/venv/lib/python3.12/site-packages/flydsl.libs:/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs
/opt/venv/bin/python reports/j-54d968ba6fd6/validate_autotune_mutation.py
```

The script creates fresh job-private cache directories under:

- `/job/flydsl-autotune-cache-j-54d968ba6fd6/run-<pid>`
- `/job/flydsl-runtime-cache-j-54d968ba6fd6/run-<pid>`

It does not download model weights or modify node-wide cache state.

## Raw results

The complete machine-readable result is in
`reports/j-54d968ba6fd6/results.json`.

## Limitation

The qualified image does not contain CMake or an MLIR development tree, so the
current source tree cannot be rebuilt natively in this environment. The run
therefore used a job-private hybrid consisting of the current source
`autotune.py` and the source `utils/env.py` / `utils/file.py` dependencies,
together with the image's installed FlyDSL 0.2.4 compiler and native MLIR
extensions. The current and hybrid `autotune.py` SHA-256 values are identical.

This validates the current autotuner semantics on gfx950, but it is not a full
current-source native compiler build. No unsupported result is claimed beyond
that scope.
