# Autotune candidate evaluation report

## Scope

This investigation covers candidate evaluation only: ordinary no-search execution,
an explicit bounded valid/invalid candidate set, pruning, selected-result
correctness, and retention of a real candidate error. It intentionally does not
retest artifact loading, state reset, or cache-key axes.

Reference context: ROCm/FlyDSL issue 770 and related PRs 783, 785, 786, and
788. The mirror checkout already contains the merged candidate-validation and
failure-chaining behavior, so this change adds focused device coverage rather
than duplicating an existing fix.

## Environment

- Image: `amdpilotv2/open-job:gbt350-20260909`
- Local image ID: `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`
- GPU: one AMD Instinct MI350X, `gfx950`, unique ID `0x6e4208b780600d88`
- Interpreter: `/opt/venv/bin/python`
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`
- Installed FlyDSL baseline: `0.2.4` at
  `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`
- Checkout commit: `ed70142704e1a6d5563fb53e1607e3a4b85d7111`

The checkout has Python source version `0.3.3` but no native build artifacts.
For exact-source GPU validation, a job-private copy of the checkout Python
sources was combined with the native `_mlir` tree and `flydsl.libs` from the
prebuilt FlyDSL `0.3.2` wheel. The wheel was installed only under `/tmp`; the
qualified Torch/ROCm stack was not modified.

## Installed-source baseline

The installed `0.2.4` wheel does not contain the current RMSNorm autotune
adopter. The supported neighboring control was the target-neutral vector-add
example:

```bash
FLYDSL_AUTOTUNE=0 \
FLYDSL_CACHE_DIR=/tmp/flydsl-cache-baseline-1789009004543863185 \
/opt/venv/bin/python /tmp/01-vectorAdd.py
```

Result:

```text
PASS
status=0 elapsed_seconds=2.627903
```

The example compares `C` with the independent Torch reference `A + B` using
`torch.allclose`. Timing is one bounded wall-clock measurement around the
complete first process, including import, JIT compilation, launch,
synchronization, and reference comparison. This is installed-source evidence
only and is not proof for later checkout changes.

## GPU validation

The new device test uses a small vector-add kernel with:

- valid candidate: `block_dim=64`, `vec_width=4`
- invalid candidate: `block_dim=0`, `vec_width=4`
- pruning predicate: `0 < block_dim <= 256`
- independent reference: `torch.testing.assert_close(output, a + b, rtol=0, atol=0)`

The no-search case forces `_bench_one` to fail if called, proving that the
ordinary default path does not search. The forced-search case proves that only
the valid candidate is benchmarked after pruning and that the selected winner
produces the independent reference result. The all-invalid case retains the
real compiler validation error:

```text
known_block_size[0] must be positive, got 0
```

Validation command:

```bash
PYTHONPATH=/tmp/flydsl-source-0.3.2-native-1789009239543165593:/job/FlyDSL \
FLYDSL_CACHE_DIR=/tmp/flydsl-cache-source-native-1789009288197307548 \
FLYDSL_AUTOTUNE_CACHE_DIR=/tmp/flydsl-cache-source-native-1789009288197307548/autotune \
FLYDSL_AUTOTUNE_CONFIG_DIR=/tmp/flydsl-cache-source-native-1789009288197307548/artifacts \
/opt/venv/bin/python -m pytest \
  tests/unit/test_autotune_device.py \
  tests/kernels/test_rmsnorm_autotune.py::test_rmsnorm_autotuned_default_uses_current_stream_and_skips_search \
  -q --no-header
```

Result:

```text
4 passed in 1.63s
status=0 elapsed_seconds=3.862720
```

The elapsed value is the bounded wall-clock time for the complete pytest
process, including interpreter startup and JIT compilation.

Existing policy coverage also passed:

```bash
PYTHONPATH=/tmp/flydsl-source-0.3.2-native-1789009239543165593:/job/FlyDSL \
/opt/venv/bin/python -m pytest tests/unit/test_autotune.py -q --no-header
```

Result:

```text
55 passed in 0.74s
```

## Limitations

- The checkout Python sources are version `0.3.3`; the compatible prebuilt
  native wheel is version `0.3.2`. No LLVM rebuild was performed.
- `block_dim=999` was not used as the invalid candidate because the newer
  native stack accepts it. `block_dim=0` fails consistently with a real
  compiler validation error on both tested native stacks.
- No synthetic GPU burn, unbounded loop, sleep loop, or repeated work was used.
