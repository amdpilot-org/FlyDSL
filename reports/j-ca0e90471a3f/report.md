# gfx950 inclusive integer scan validation

## Outcome

The prefix-scan candidate from ROCm/FlyDSL issue 1016 is already implemented and
working. Upstream PR 1031, "[Ext][Coop] Add cooperative warp- and block-scope
collectives", was merged as mirror commit
`c3bd00455f711bd4f8d521951e0f5d9162437d8d`. I validated that exact candidate
commit on one assigned MI350X (`gfx950`) rather than duplicating the fix.

No production code change is needed. This report adds only a focused,
reproducible validation harness and evidence. I did not implement a primitive
library, multi-GPU scan, or a new exclusive variant; the existing exclusive scan
tests remained unchanged and passed as part of the block-scan suite.

## Environment

- Image: `amdpilotv2/open-job:gbt350-20260909`
- Local image ID: `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`
- GPU: one AMD Instinct MI350X, `gfx950`, serial `692517020475`, node ID 4, GUID 17079
- Python: `/opt/venv/bin/python`
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`, `/opt/venv/lib/python3.12/site-packages/torch`
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`, `/opt/venv/lib/python3.12/site-packages/triton`
- Delivery source: `/job/FlyDSL`
- Exact candidate worktree: `/tmp/flydsl-cache-j-ca0e90471a3f/FlyDSL-candidate`
- Native FlyDSL package: `/tmp/flydsl-cache-j-ca0e90471a3f/build-fly/python_packages/flydsl`
- Pinned LLVM/MLIR build: `/tmp/flydsl-cache-j-ca0e90471a3f/llvm-project/build-flydsl`
- Job-private cache: `/tmp/flydsl-cache-j-ca0e90471a3f`

The image's preinstalled FlyDSL Python package was older than the mirror and
did not contain the coop extension or the required ROCDL bindings. I preserved
the qualified Torch/ROCm stack and built the mirror's pinned LLVM/MLIR and
FlyDSL native components in the job-private cache. No model weights or another
framework stack were downloaded.

## Candidate and commits

- Read-only reference: ROCm/FlyDSL issue 1016
- Related merged upstream PR: ROCm/FlyDSL PR 1031
- Upstream PR head: `2f36fb3ffea89cf660fb5619b3b6e67059efdd33`
- Tested mirror candidate merge commit: `c3bd00455f711bd4f8d521951e0f5d9162437d8d`
- PR base/main commit: `ed70142704e1a6d5563fb53e1607e3a4b85d7111`

The exact candidate worktree used the native bindings built from the PR base.
The candidate and base have compatible native interfaces for this validation.

## Commands

The native build used:

```bash
CACHE=/tmp/flydsl-cache-j-ca0e90471a3f
export PATH="$CACHE/venv/bin:$PATH"
export LLVM_BUILD_PROFILE=amd-minimal
export LLVM_PACKAGE_INSTALL=0
bash "$CACHE/FlyDSL/scripts/build_llvm.sh" -j128 --no-install

export FLY_BUILD_DIR="$CACHE/build-fly"
export MLIR_PATH="$CACHE/llvm-project/build-flydsl"
export HIP_PLATFORM=amd
bash /job/FlyDSL/scripts/build.sh -j128
```

The exact-candidate test command used:

```bash
CACHE=/tmp/flydsl-cache-j-ca0e90471a3f
export PYTHONPATH="$CACHE/FlyDSL-candidate/python"
export TRITON_CACHE_DIR="$CACHE/triton"
export FLYDSL_CACHE_DIR="$CACHE/flydsl-candidate"
export LD_LIBRARY_PATH="$CACHE/build-fly/python_packages/flydsl/_mlir/_mlir_libs:/opt/rocm/lib:${LD_LIBRARY_PATH:-}"
/opt/venv/bin/python -m pytest -q --no-header --tb=short \
  tests/extension/coop/test_block_scan.py \
  tests/extension/coop/test_warp_rocdl.py
```

The sentinel validation used:

```bash
/opt/venv/bin/python reports/j-ca0e90471a3f/validate_scan.py
```

## Results

Exact candidate commit `c3bd00455f711bd4f8d521951e0f5d9162437d8d`:

```text
tests/extension/coop/test_block_scan.py
tests/extension/coop/test_warp_rocdl.py
110 passed in 12.14s
```

PR base/main commit `ed70142704e1a6d5563fb53e1607e3a4b85d7111`:

```text
tests/extension/coop/test_block_scan.py
62 passed in 6.73s

tests/extension/coop/test_warp_rocdl.py
48 passed in 6.70s
```

Sentinel-protected inclusive `int32` scan, compared exactly against an
independent CPU `torch.cumsum` reference:

```text
block=64  active=64  waves=1  active_exact=true  sentinel_exact=true
block=256 active=256 waves=4  active_exact=true  sentinel_exact=true
block=64  active=37  waves=1  active_exact=true  sentinel_exact=true
block=256 active=100 waves=4  active_exact=true  sentinel_exact=true
```

All active outputs matched exactly and every inactive output slot retained the
sentinel `-123456789`. The validation harness prints input, expected, and
output SHA-256 values for reproducible raw-result comparison. The complete raw
JSON receipt is retained in `reports/j-ca0e90471a3f/results.json`.

## Synchronization and wave assumptions

- `fx.num_warp_threads()` returned 64 on this MI350X.
- `BlockScan` requires a power-of-two block thread count, and every thread in
  the block must reach the collective call together.
- The specialization uses `warp_threads = min(64, block_threads)` and
  `num_warps = block_threads // warp_threads`.
- The `WARP_SCANS` policy scans each wave first. For multi-wave blocks, the
  last lane of each wave stores its inclusive aggregate in shared memory, the
  policy executes one block barrier, and each thread folds the aggregates from
  preceding waves. A one-wave block skips shared memory and that barrier.
- The dispatched gfx9 warp scan uses the ROCDL/DPP override for this integer
  path; the unchanged ROCDL suite also verifies the override's generated ISA.
- The collective leaves the block unsynchronized after its final shared-memory
  reads. A caller reusing the same storage must insert another block barrier.
- The sentinel validation keeps the launched block power-of-two. Inactive lanes
  contribute the additive identity `0` and still participate in the collective;
  only active lanes write output, so inactive slots remain sentinel-protected.

## Scope and upstream safety

No upstream issue, pull request, or comment was posted or modified. The
candidate is already merged and working, so this delivery intentionally contains
no duplicate scan implementation. No numerical gate was changed.
