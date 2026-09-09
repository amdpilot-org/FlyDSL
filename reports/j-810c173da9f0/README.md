# FlyDSL AST control-flow validation on gfx942

## Result

The bounded matrix passed on one assigned AMD Instinct MI300X (`gfx942`). All six
supported numeric cases matched their independent Python/Torch references under
the unchanged exact gate `torch.equal` (`rtol=0`, `atol=0`). The dynamic-if
`None` initialization case produced the existing clear `TypeError` diagnostic.
No new wrong result or diagnostic gap was measured, so no compiler fix was made.

The matrix covers:

- a value assigned in a dynamic `if` and used after the branch;
- nested dynamic `if` branches;
- a loop-carried accumulator in `for index in range(count)`;
- a loop-carried accumulator and condition value in `while`;
- a dynamic branch nested inside `for`;
- a `fx.Float32` branch value used after control flow.

The kernels use the DSL's existing operation names, including `fx.Int32`,
`fx.Float32`, `fx.Tensor`, `if`, `for ... in range(...)`, `while`, and indexed
`Out[0]` stores. Raw actual/expected values are in `results.json`.

## Tested revisions

- Source: `ed70142704e1a6d5563fb53e1607e3a4b85d7111` (`main`, FlyDSL `0.3.3`)
- Source Python path: `/job/FlyDSL/python`
- Preinstalled FlyDSL distribution: `0.3.1` at
  `/opt/venv/lib/python3.10/site-packages/flydsl`
- Native MLIR candidate: FlyDSL `0.3.2` wheel, extracted at
  `/tmp/flydsl-wheel-032-extract/flydsl`
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`
- HIP runtime: `7.2.26015-fc0010cf6a`
- GPU: AMD Instinct MI300X, `gfx942`
- Required image identity:
  `sha256:dfc9419089c338b5712da4841768b38b1ab79f3da41f8c58c3cd4dfcc1147ff1`

The preinstalled `0.3.1` native stack does not register the source `0.3.3`
pipeline pass `convert-rocdl-fastmath-ops`. The bounded `0.3.2` wheel was
therefore used as the native MLIR/runtime candidate with the cloned source
Python package. This pairing is recorded explicitly and does not claim that the
preinstalled native module was built from the tested source commit.

## Candidate validation

Read-only upstream context:

- ROCm/FlyDSL issue 688 is open, has no comments, and links no changes.
- Upstream PR 346, merged as `21536b06810a5fe3f6d5cf03b3668b2ed6a0498c`,
  introduced dynamic `scf.if` result derivation and branch live-out handling.
  It is present in the tested source and in the preinstalled `0.3.1` runtime.
- Upstream PR 1003, merged as
  `01d63f7d04d5040e3d9df77feb6d083936b9d86a`, isolates mutable Python
  container state across dynamic branch tracing. It is an ancestor of the tested
  source commit.
- Upstream PR 232 was closed without merging and describes older while/nested
  control-flow work; the tested source contains the current equivalent coverage.

Validation at the tested source commit:

- New matrix: 6/6 numeric cases passed; 1/1 diagnostic case passed.
- Existing focused system tests: 48/48 passed.
- PR 1003 unit suite: 28/28 passed.
- Preinstalled `0.3.1` live-out reproducer: 1/1 passed.

No duplicate fix was applied because the relevant behavior is already fixed in
the tested source.

## Reproduction

From the repository root, with `/opt/venv/bin/python` and one gfx942 GPU:

```bash
mkdir -p /tmp/flydsl-wheel-032-download /tmp/flydsl-wheel-032-extract
/opt/venv/bin/python -m pip download flydsl==0.3.2 \
  --no-deps --no-build-isolation -d /tmp/flydsl-wheel-032-download
unzip /tmp/flydsl-wheel-032-download/flydsl-0.3.2-*.whl \
  -d /tmp/flydsl-wheel-032-extract
ln -sfn /tmp/flydsl-wheel-032-extract/flydsl/_mlir python/flydsl/_mlir

export FLYDSL_NATIVE_MLIR_PACKAGE=/tmp/flydsl-wheel-032-extract/flydsl
export LD_LIBRARY_PATH=/tmp/flydsl-wheel-032-extract/flydsl/_mlir/_mlir_libs:${LD_LIBRARY_PATH:-}
export FLYDSL_SOURCE_COMMIT=$(git rev-parse HEAD)
export FLYDSL_GPU_ARCH=gfx942
export FLYDSL_IMAGE_ID=sha256:dfc9419089c338b5712da4841768b38b1ab79f3da41f8c58c3cd4dfcc1147ff1
export FLYDSL_RUNTIME_ENABLE_CACHE=0
export FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-j810c-cache

/opt/venv/bin/python reports/j-810c173da9f0/control_flow_matrix.py \
  --output reports/j-810c173da9f0/results.json
```

The untracked `python/flydsl/_mlir` link is a job-private native-runtime
artifact and is not part of this report patch.
