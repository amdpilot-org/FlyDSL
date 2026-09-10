# JIT compile-option identity investigation

## Result

- Wired the declared `FLYDSL_COMPILE_OPT_LEVEL` option into the ROCm `rocdl-attach-target` pass instead of leaving `O=2` hardcoded.
- Added a focused backend test proving the option reaches the target pass.
- Ran a finite real-GPU matrix on one assigned AMD Instinct MI350X (`gfx950`) using a 257-element `int32` pointer vector-add kernel.
- Kept every cache under `/tmp`, outside `/job`; no shared cache was edited and no compiler/toolchain rebuild was performed.
- All supported cold and warm cases matched an independent CPU Torch reference exactly with maximum absolute difference `0`.
- The incompatible `ARCH=gfx942` control produced a distinct target/cache identity, emitted `hipErrorNoBinaryForGpu`, and left the output sentinel unchanged; it was not silently reused on `gfx950`.

## Issue context

- Read-only context: ROCm/FlyDSL issue 862, `[Issue]: reduce Flydsl compile time`.
- The issue is open, has zero comments, and asks for reduced FlyDSL JIT compile time.
- Related upstream pull request 964, `[Build] Default CMAKE_BUILD_TYPE to RelWithDebInfo when unset`, is already merged. Its change is present in this checkout at `CMakeLists.txt:14` and was not duplicated.
- No upstream issue, pull request, or comment was posted or modified.

## Root cause and evidence

`FLYDSL_COMPILE_OPT_LEVEL` was already included in the JIT cache-invalidating environment tuple, but `RocmBackend._pipeline_parts()` hardcoded `O=2`. Consequently, changing the supported option split the cache without changing generated code.

Base-commit evidence from the tiny integer kernel:

| Case | Cache file | Compiled IR SHA-256 | Exact |
|---|---|---|---|
| opt 0 | `6ad85f2867931e64.pkl` | `b22e3d51288b21c06ce0ffd97801f4a4f5bad1b41afe8763ae86c5c86732a0ce` | yes |
| opt 2 | `cbb56ff99a8abbc7.pkl` | `b22e3d51288b21c06ce0ffd97801f4a4f5bad1b41afe8763ae86c5c86732a0ce` | yes |
| opt 3 | `5f2ac6a3e09a62e2.pkl` | `b22e3d51288b21c06ce0ffd97801f4a4f5bad1b41afe8763ae86c5c86732a0ce` | yes |

After the fix, optimization levels produce distinct code identities while retaining exact output:

| Case | Cache file | Compiled IR SHA-256 | Exact |
|---|---|---|---|
| opt 0 | `6ad85f2867931e64.pkl` | `dabb173d01d56121f4e358c359336594e5b891d1d9bb7a2a4b2ede5d61ec87a8` | yes |
| opt 2 | `cbb56ff99a8abbc7.pkl` | `b22e3d51288b21c06ce0ffd97801f4a4f5bad1b41afe8763ae86c5c86732a0ce` | yes |
| opt 3 | `5f2ac6a3e09a62e2.pkl` | `950b4c3302e9beae4bbe5d2767e688c8e73438a8a25b6498455a9c9817ee57f2` | yes |

The debug-info control also changed both cache and code identity. The verifier control intentionally shared the opt-2 cache identity because verification does not alter generated code. The complete raw base and fixed JSON is in `result.json`.

## GPU probe

The probe uses a real FlyDSL dispatch with:

- 257 `int32` elements;
- inputs bounded to `[0, 99]`;
- expected outputs bounded to `[0, 198]`;
- output initialized to `INT32_MIN` as a sentinel;
- an independent CPU `torch.add` reference created before GPU dispatch;
- one `perf_counter()` interval around one dispatch and final synchronize;
- no burn, unbounded loop, sleep loop, or repeated work.

The `ARCH=gfx942` mismatch control compiled for `GPUTarget(backend='rocm', arch='gfx942', warp_size=64)`, used cache file `cf0f4c1a5ced83b1.pkl`, and did not silently reuse the `gfx950` artifact. HIP reported `hipErrorNoBinaryForGpu`, `hipErrorInvalidHandle`, and the output remained `INT32_MIN`.

## Environment

- Image: `amdpilotv2/open-job:gbt350-20260909`
- Local image ID: `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`
- Python: `/opt/venv/bin/python3`
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`
- Installed FlyDSL: `0.2.4`
- Checkout FlyDSL: `0.3.3` at base commit `ed70142704e1a6d5563fb53e1607e3a4b85d7111`
- Installed native root: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs`
- GPU: one AMD Instinct MI350X, `gfx950`, Torch capability `(9, 5)`

The installed-source first-GPU baseline is recorded outside the repository in `/job/baseline-first.json`. Its minimal vector-add execution took `0.35488318279385567` seconds and matched Torch exactly. It is explicitly labeled as evidence for the preinstalled wheel, not proof for this checkout.

## Reproduction

The current checkout Python source cannot run unshimmed against the image's installed FlyDSL 0.2.4 native libraries because `convert-rocdl-fastmath-ops` is not registered there. Rebuilding the native stack was out of scope. The probe therefore uses a job-private source/native overlay and removes only that one unsupported pass in memory; repository compiler behavior is not changed by the shim.

```bash
SRC=/tmp/flydsl-src-j-8291668ade13-fix
mkdir -p "$SRC"
cp -a python/flydsl "$SRC/"
ln -sfn /opt/venv/lib/python3.12/site-packages/flydsl/_mlir "$SRC/flydsl/_mlir"

export PYTHONPATH="$SRC"
python reports/j-8291668ade13/compile_option_probe.py \
  --case opt0-debug0-verifier1 --mode cold \
  --cache-root /tmp/flydsl-cache-j-8291668ade13-fix/opt0 \
  --output /tmp/flydsl-results-j-8291668ade13-fix/opt0-cold.json

python reports/j-8291668ade13/compile_option_probe.py \
  --case opt0-debug0-verifier1 --mode warm \
  --cache-root /tmp/flydsl-cache-j-8291668ade13-fix/opt0 \
  --output /tmp/flydsl-results-j-8291668ade13-fix/opt0-warm.json
```

Repeat the same two commands for the other supported cases in `compile_option_probe.py`, then run:

```bash
python reports/j-8291668ade13/compile_option_probe.py \
  --case arch-gfx942-mismatch --mode cold \
  --cache-root /tmp/flydsl-cache-j-8291668ade13-fix/arch-gfx942-mismatch \
  --output /tmp/flydsl-results-j-8291668ade13-fix/arch-gfx942-mismatch.json
```

Focused validation:

```bash
PYTHONPATH="$SRC" python3 -m pytest -q tests/unit/test_compile_backends.py
PYTHONPATH="$SRC" python3 -m pytest -q \
  tests/unit/test_jit_cache_key_completeness.py::test_env_var_not_cached_within_process
python3 -m py_compile reports/j-8291668ade13/compile_option_probe.py
git diff --check
```

Results were `3 passed`, `1 passed`, successful compilation, and a clean diff check.

## Uncertainty

- Timings are single cold and single warm observations, not a statistical benchmark.
- The real-GPU matrix uses the labeled one-pass compatibility shim because the installed native extensions predate the checkout's new fastmath pass.
- Running the broader `tests/unit/test_compile_hints.py` suite under the same overlay produced four preexisting failures caused by that missing native pass; the focused backend and cache-key tests relevant to this change pass.
- No model weights were downloaded and no node-wide state was modified.
