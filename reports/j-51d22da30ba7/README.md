# gfx950 AST control-flow investigation

## Conclusion

This investigation produced no production code change. ROCm/FlyDSL issue 688 is a
general request to discover AST-rewriter issues that could cause hard-to-detect
functional errors. It has no comments and no linked pull requests. The tested
mirror commit already contains two directly relevant changes:

- `3eefcd3d10e3d12fad84c658d4f26c9a3e3416c9` carries Python containers through
  dynamic `if`, `for`, `while`, and ternary control flow.
- `01d63f7d04d5040e3d9df77feb6d083936b9d86a` isolates mutable state across
  dynamic `if` branches so tracing one branch cannot contaminate its sibling.

Both changes are already working on the assigned gfx950 GPU. Adding another AST
rewriter change would duplicate those fixes and broaden the requested scope.

## Tested source

- Mirror base and tested commit: `ed70142704e1a6d5563fb53e1607e3a4b85d7111`
- Branch: `amdpilot/j-51d22da30ba7`
- GPU: one AMD Instinct MI350X, `gfx950`, driver `7.1.1.31500000`
- Image: `amdpilotv2/open-job:gbt350-20260909`, local ID
  `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`
- Interpreter: `/opt/venv/bin/python` (Python 3.12.3)
- Installed stack: Torch `2.9.1+rocm7.2.0.git7e1940d4`, Triton
  `3.5.1+rocm7.2.0.gita272dfa8`, FlyDSL package `0.2.4`

The installed FlyDSL Python package is at
`/opt/venv/lib/python3.12/site-packages/flydsl`, with native MLIR bindings under
`/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs`. The checkout
Python source is under `/job/FlyDSL/python/flydsl`.

## Installed-source first baseline

The first execution objective used the preinstalled interpreter and package,
before cloning or editing the mirror. The probe is a bounded one-block,
64-thread kernel with a dynamic 12-iteration loop, nested dynamic branches, an
`Int32` loop-carried accumulator, and a value read after control flow.

The first attempt failed before GPU launch with:

```text
ValueError: Operand 0 of operation "fly.memref.store_vec" must be a Value
```

The supported neighboring control converted the DSL numeric with `.ir_value()`
before the scalar store. It passed the independent explicit Python integer
reference exactly:

- maximum absolute difference: `0`
- first GPU execution (`perf_counter` around JIT call plus synchronize):
  `0.45149003341794014 s`
- process wall time: `2.481941504 s`
- bounds: 1 block, 64 threads, 12 loop iterations, 1 repetition

The complete installed-source record is retained outside the repository at
`/job/baseline-first.json`. It is explicitly labeled as evidence for the
preinstalled source only, not for later checkout changes.

## Checkout validation

The checkout Python version is `0.3.3`, while the installed native package is
`0.2.4`. A direct source/native overlay therefore failed at pass registration:

```text
ValueError: 'convert-rocdl-fastmath-ops' does not refer to a registered pass
```

No matching MLIR development build exists in the image. To avoid an unnecessary
full native rebuild, validation used a job-private overlay under
`/tmp/flydsl-cache-j-51d22da30ba7`. It copied checkout Python, attached the
installed native `_mlir` bindings, and omitted only the unavailable unrelated
fast-math pass from the ROCm backend pipeline. No repository file was changed by
that compatibility overlay.

Results on the assigned gfx950 GPU:

- `tests/unit/test_dynamic_controlflow_list_carry.py`: passed
- `tests/unit/test_for_dispatch_paths.py`: passed
- `tests/unit/test_while_dispatch_paths.py`: passed
- Combined targeted unit set: 41 passed in `0.76 s`
- `tests/system/test_dynamic_controlflow_list_carry_e2e.py`: 21 passed in
  `2.37 s` (`4.547136000 s` process wall time)
- Independent accumulator probe: maximum absolute difference `0`, JIT plus
  synchronize `0.4432005602866411 s`, process wall time `2.482379008 s`

The system suite covers dynamic `if`, `for`, `while`, ternary, nested container,
and scalar accumulator paths. Its assertions are exact integer references. The
additional probe uses an independent explicit Python accumulation reference.

## Reproduction

From the repository root, with the job-private source/native overlay described
above:

```bash
export PYTHONPATH=/tmp/flydsl-cache-j-51d22da30ba7/source-overlay-v3/python_packages/python
export FLYDSL_RUNTIME_ENABLE_CACHE=0
/opt/venv/bin/python -m pytest -q \
  tests/unit/test_dynamic_controlflow_list_carry.py \
  tests/unit/test_for_dispatch_paths.py \
  tests/unit/test_while_dispatch_paths.py
/opt/venv/bin/python -m pytest -q \
  tests/system/test_dynamic_controlflow_list_carry_e2e.py
```

The accumulator probe is retained at `/job/baseline_control_flow.py` by the job
host. It uses one block, 64 threads, and 12 bounded iterations; it contains no
unbounded loop, sleep loop, synthetic burn, or repeated GPU work.

## IR and scope

No numerical discrepancy was observed, so no generated IR was retained. This
follows the requested discrepancy-only IR policy.

Left undone: no full LLVM/MLIR or FlyDSL native rebuild was performed because
the image has no matching MLIR development install, the relevant AST behavior is
Python-level, and the installed native bindings were sufficient for the bounded
compatibility validation. No upstream issue, pull request, or comment was posted
or modified.
