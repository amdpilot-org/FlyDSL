# gfx950 loaded integer predicate and select validation

## Scope

- Read-only context: ROCm/FlyDSL issue 934, "Expression-layer arithmetic cleanup". The issue is open and has no comments.
- Related mirror PRs 418, 411, and 339 were inspected. PR 418 covers shifts and casts, while PRs 411 and 339 already validate upstream PR 920's unsigned signedness reconstruction.
- This work covers a distinct slice: public signed and unsigned comparisons and select predicates on values loaded from 32- and 64-bit GPU pointers.
- No upstream issue, pull request, or comment was posted or modified.

## Environment

- Campaign: `repo-e2e-20260909`.
- Image: `amdpilotv2/open-job:gbt350-20260909`, local ID `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.
- Python: `/opt/venv/bin/python` (Python 3.12).
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`.
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`.
- Installed FlyDSL: `0.2.4` at `/opt/venv/lib/python3.12/site-packages/flydsl`.
- Installed native bindings: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`.
- Mirror source: `/job/FlyDSL`, base commit `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.
- GPU: one AMD Instinct MI350X, `gfx950`, capability `(9, 5)`, ROCm agent UUID `GPU-9c60d586afa84d50`, chip ID `0x75a0`.

## Early installed-source baseline

`/job/baseline-first.json` records the first real GPU execution.

- Command: `/opt/venv/bin/python /job/baseline_first.py`.
- Kernel: `predicate_select_baseline`.
- Inputs: loaded 32- and 64-bit values through `fx.Tensor`.
- Predicates: `eq`, `ne`, signed and unsigned `lt`, `le`, `gt`, and `ge`.
- Matrix: 15 pairs per width, including zero, one, positive maximum, high bit, adjacent high-bit values, and equal boundaries.
- Result: 300/300 comparisons matched exact Python host references.
- First GPU execution elapsed time: `0.802701552` seconds, measured with `time.perf_counter` around one JIT dispatch and `torch.cuda.synchronize()`.
- This installed-source result is labeled separately and is not evidence for later checkout changes.

## Real gfx950 predicate/select results

The new GPU harness uses explicitly typed `fx.Pointer` arguments, loads both operands, and checks:

- operator comparisons (`==`, `!=`, `<`, `<=`, `>`, `>=`);
- explicit `arith.cmpi` signed and unsigned predicates;
- `Boolean.select`;
- `arith.select`.

Each of the four signed/unsigned 32/64-bit cases uses the same 15-pair sentinel matrix. Every predicate result and selected value is compared exactly against an independent Python host reference; there is no floating-point tolerance.

### Mirror main

- Source commit: `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.
- Result: failed with 32 mismatches.
- Failures: 16 predicate mismatches and 16 selected-value mismatches, split evenly between `Uint32` and `Uint64`.
- Pattern: every failure involves a high-bit unsigned value. Main reconstructs the unsigned pointer load as signed, so unsigned orderings and selects use signed semantics. Signed 32/64-bit cases and equality boundaries pass.
- One bounded dispatch and synchronization took `0.754733955` seconds.
- Raw results: `main-result.json`.

### Upstream PR 920 candidate

- Candidate: ROCm/FlyDSL PR 920, commit `de526e0aeafdf4d42896bbf635d2dc14fa599233`, preserved unchanged.
- Test method: candidate `python/flydsl` source overlay with the image's existing native bindings.
- Result: all 1,440 predicate/select checks passed with zero mismatches.
- One bounded dispatch and synchronization took `0.819224151` seconds.
- Raw results: `candidate-result.json`.
- No duplicate fix was applied. The candidate already preserves logical unsigned storage types and maps them to signless SSA values at the load boundary.

## Reproduction

The job-private cache is `/tmp/flydsl-cache-j-ab4cde533ae7`. The following commands use fresh overlay directories and do not modify the qualified Torch/ROCm stack.

```bash
cd /job/FlyDSL
CACHE=/tmp/flydsl-cache-j-ab4cde533ae7

# Main Python source over installed native bindings.
mkdir -p "$CACHE/main-overlay"
cp -a /opt/venv/lib/python3.12/site-packages/flydsl "$CACHE/main-overlay/"
cp -a python/flydsl/. "$CACHE/main-overlay/flydsl/"

# Preserved PR 920 Python source over installed native bindings.
mkdir -p "$CACHE/pr920-src" "$CACHE/pr920-overlay"
git archive --format=tar de526e0aeafdf4d42896bbf635d2dc14fa599233 python/flydsl \
  | tar -x -C "$CACHE/pr920-src"
cp -a /opt/venv/lib/python3.12/site-packages/flydsl "$CACHE/pr920-overlay/"
cp -a "$CACHE/pr920-src/python/flydsl/." "$CACHE/pr920-overlay/flydsl/"

export LD_LIBRARY_PATH="$CACHE/main-overlay/flydsl/_mlir/_mlir_libs:/opt/venv/lib/python3.12/site-packages/flydsl.libs"
export FLYDSL_RUNTIME_ENABLE_CACHE=0

PYTHONPATH="$CACHE/main-overlay:/job/FlyDSL" \
FLYDSL_RUNTIME_CACHE_DIR="$CACHE/runtime-main" \
/opt/venv/bin/python reports/j-ab4cde533ae7/run_validation.py \
  --label "mirror main source overlay with installed native bindings" \
  --source-commit ed70142704e1a6d5563fb53e1607e3a4b85d7111 \
  --output reports/j-ab4cde533ae7/main-result.json

PYTHONPATH="$CACHE/pr920-overlay:/job/FlyDSL" \
FLYDSL_RUNTIME_CACHE_DIR="$CACHE/runtime-pr920" \
/opt/venv/bin/python reports/j-ab4cde533ae7/run_validation.py \
  --label "upstream PR 920 Python source overlay with installed native bindings" \
  --source-commit de526e0aeafdf4d42896bbf635d2dc14fa599233 \
  --output reports/j-ab4cde533ae7/candidate-result.json
```

The main command exits nonzero after recording its mismatches. The candidate command exits zero.

## Limitations

- The image's native bindings predate current main's unrelated `convert-rocdl-fastmath-ops` pass. The report runner removes that pass from the parsed pipeline; no fastmath operation is exercised.
- The PR 920 control is a Python source overlay over the installed native bindings, not a full rebuild of PR 920's pinned native stack. It is sufficient for this predicate/select path and is labeled accordingly. PR 411 already records a full pinned candidate build for load/arithmetic/store behavior.
- Current main remains defective until PR 920 or an equivalent integration lands. The new GPU test is marked strict xfail so it documents the defect without duplicating the upstream fix.
- No full model weights, alternate framework stack, synthetic GPU burn, unbounded loop, sleep loop, or repeated GPU work was used.
