# Empty autotune candidate-set investigation

## Scope

This change isolates the empty candidate-set behavior requested by ROCm/FlyDSL
issue 770. It does not change ranking ties, artifact loading, state restoration,
or candidate validation. Open mirror PR 428 already covers non-empty pruning and
real candidate failures; this change covers the distinct case where pruning
removes every candidate before dispatch.

## Environment

- Image: `amdpilotv2/open-job:gbt350-20260909`
- Local image ID: `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`
- GPU: one assigned AMD Instinct MI350X, `gfx950`, serial `692517020513`
- Driver: ROCm `7.1.1.31500000`
- Interpreter: `/opt/venv/bin/python` (Python 3.12.3)
- Torch: `2.9.1+rocm7.2.0.git7e1940d4` at
  `/opt/venv/lib/python3.12/site-packages/torch/__init__.py`
- Triton: `3.5.1+rocm7.2.0.gita272dfa8` at
  `/opt/venv/lib/python3.12/site-packages/triton/__init__.py`
- Installed FlyDSL baseline: `0.2.4` at
  `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`
- Checkout source: `/job/FlyDSL/python/flydsl/autotune.py`, version `0.3.3`
- Checkout native overlay: FlyDSL `0.3.2` wheel extracted to
  `/tmp/flydsl-cache-j-2558fd8b9bf8/native/flydsl/_mlir/_mlir_libs`

The installed-source baseline is recorded in `/job/baseline-first.json`. It is
not proof for checkout changes. The first relevant installed Aiter test was
unsupported because `aiter.jit.module_aiter_core` was not importable; with its
generated module on the path, Aiter required Triton 3.6 while the qualified
stack has 3.5.1. The supported neighboring control was a real FlyDSL vector-add
kernel, exact against an independent Torch reference, with a cold-process time of
2.538743 seconds.

The checkout has no native build artifacts. For bounded GPU validation, the
checkout Python sources were overlaid with the compatible prebuilt FlyDSL 0.3.2
native tree under `/tmp`; the qualified Torch/ROCm environment was not replaced.
No LLVM rebuild or full model weights were used.

## Reproduction

The real GPU operator is the RMSNorm direct-JIT autotune adopter. The finite
matrix is `M=8`, `N=8192`, `bf16` input and weight, seed 0, and a seven-config
search space. `prune_configs_by` was replaced with a function returning an empty
list. `_bench_one` was replaced with a guard that fails if called, proving that
no candidate is dispatched.

Before the fix, forced search printed `[autotune] tuning 0 configs...`, raised
`RuntimeError("All autotune configs failed")`, and had no chained cause. The
output sentinel remained unchanged. Normal service already used its heuristic
default and matched the independent reference.

After the fix:

- Normal service uses the heuristic default without benchmarking.
- Forced search raises `RuntimeError("Autotune pruning removed all candidate configs")`.
- No candidate is benchmarked or dispatched.
- The output sentinel remains unchanged on refusal.
- The independent Torch RMSNorm reference remains finite.

The independent reference is:

```python
x.float() * torch.rsqrt((x.float() * x.float()).mean(-1, keepdim=True) + 1e-5) * gamma.float()
```

The unchanged numerical gate is `torch.testing.assert_close(..., rtol=0, atol=2e-2)`.
The measured normal-path maximum absolute error was `0.00781035423`.

## Commands

```bash
PYTHONPATH=/job/baseline-logs:/job/FlyDSL/python:/job/FlyDSL \
FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-2558fd8b9bf8/runtime \
FLYDSL_AUTOTUNE_CACHE_DIR=/tmp/flydsl-cache-j-2558fd8b9bf8/autotune \
/opt/venv/bin/python -m pytest -c tests/pytest.ini \
  tests/unit/test_autotune.py::test_empty_pruned_search_refuses_precisely -q

PYTHONPATH=/job/baseline-logs:/job/FlyDSL/python:/job/FlyDSL \
FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-2558fd8b9bf8/runtime \
FLYDSL_AUTOTUNE_CACHE_DIR=/tmp/flydsl-cache-j-2558fd8b9bf8/autotune \
/opt/venv/bin/python -m pytest -c tests/pytest.ini \
  tests/kernels/test_rmsnorm_autotune.py::test_rmsnorm_empty_pruned_candidates_fallback_then_refuse_search -q

PYTHONPATH=/job/baseline-logs:/job/FlyDSL/python:/job/FlyDSL \
FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-2558fd8b9bf8/runtime \
FLYDSL_AUTOTUNE_CACHE_DIR=/tmp/flydsl-cache-j-2558fd8b9bf8/autotune \
/opt/venv/bin/python -m pytest -c tests/pytest.ini \
  tests/unit/test_autotune.py tests/kernels/test_rmsnorm_autotune.py -q
```

## Results

- Focused empty-prune unit regression: 1 passed.
- Focused MI350X RMSNorm empty-prune regression: 1 passed in 2.77 seconds.
- Affected unit and RMSNorm device files: 62 passed in 4.63 seconds.
- `git diff --check`: passed.
- Post-fix forced refusal message:
  `Autotune pruning removed all candidate configs`.
- Post-fix normal-path maximum absolute error: `0.00781035423`.

Raw logs are retained outside the repository in `/job/baseline-logs/`. The
checkout test harness is also outside the repository in
`/job/baseline-logs/sitecustomize.py`.

## Limitations

The checkout Python version is 0.3.3 while the bounded native overlay is 0.3.2.
The changed code is Python-only and the overlay provides the matching newer
native dialect symbols required by the checkout. A full source build was not
performed because the image has no MLIR development installation. Formatter
binaries were not installed; `git diff --check` was used instead.
