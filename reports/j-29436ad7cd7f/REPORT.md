# Independent review of PR 694 at `fce1faf`

Upstream issue: https://github.com/ROCm/FlyDSL/issues/726

Candidate mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/693

Review mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/695

## Recommendation

Accept. The exact candidate commit `fce1fafcee5a397b7e5ce3b7cf9061af19a40dcd`
fully resolves the original request under the approved design assumption: persistent
execution is opt-in, while the default call remains source-compatible and retains
the existing two-dimensional launch and mathematical result.

This is a full original-issue fix, not merely test hardening. On the recorded base
`acf7e67b7d22847e345938ca54fcc137bd7b2a1f`, passing `persistent=True` to the real
MoE GEMM1 entry point fails with `TypeError: compile_moe_gemm1() got an unexpected
keyword argument 'persistent'`. The base's existing default GEMM1 numerical suite
still passes 12/12, isolating the missing feature from unrelated kernel health.

## Candidate inspection

The implementation adds `persistent=False` and a positive
`persistent_grid_multiplier` to the existing
`kernels/moe/moe_gemm_2stage/gemm1.py` builder. The default maps the original 2-D
grid to one logical tile per CTA. The opt-in mode launches at most
`compute_units * multiplier` CTAs and grid-strides over the flattened
`(expert-block, channel-block)` worklist. No native C++ source changed.

The source path was `/job/repo/kernels/moe/moe_gemm_2stage/gemm1.py`. Python
`flydsl` imported from `/job/repo/python/flydsl/__init__.py`. The prepared native
extension imported through
`/job/repo/python/flydsl/_mlir/_mlir_libs/_mlir.cpython-312-x86_64-linux-gnu.so`,
which resolves to the pinned wheel under `/opt/venv/lib/python3.12/site-packages`.
Because the candidate changes only Python kernel construction/tests and no native
compiler source, the documented native rebuild was not applicable.

## GPU and numerical evidence

Tests ran on the single assigned AMD Instinct MI350X,
`gfx950:sramecc+:xnack-`, with 256 compute units, Torch
`2.9.1+rocm7.2.0.git7e1940d4`, and HIP `7.2.26015-fc0010cf6a`.

- Candidate regression: 8/8 persistent cases passed.
- Broad GEMM1 selection: 205 passed, 96 architecture/configuration skips.
- The candidate's validation harness passed all eight dtype/shape pairs against
  Torch references. Persistent/reference cosine ranged from 0.9999985 to
  0.9999987. Its 520/522-logical-tile cases exceed the 256-CTA persistent grid.
- Independent adversarial cases covered underfilled and repeated-iteration grids,
  masked tails, `tile_n` 64/128/256, multipliers 1/2/3, f16 and bf16 output, and
  fp8/int8/int8smooth/packed-int4 input. All persistent results had cosine above
  0.9999986 versus the independent Torch result and were bitwise equal to the
  corresponding default outputs. A 776-tile case forced multiple iterations.
- Multipliers 0 and -1 were independently confirmed to raise `ValueError`.
- Outputs were initialized with NaNs in the independent cases; no NaNs remained,
  providing a guard against omitted work tiles.

## Timing

The candidate harness used identical tensors, 20 warmups, and seven batches of
100 GPU-event-timed launches. In this rerun, persistent/default mean ratios ranged
from 1.002 to 1.499, except fp8 at 2051 tokens at 1.057 with visibly higher
variability (7.81--11.55 us persistent). The independent suite observed ratios
from 0.962 to 1.515, including one large outlier batch. These results support the
candidate's cautious statement that persistent mode is not a promised speedup and
should remain opt-in.

## Commands and retained evidence

The raw logs, exact candidate patch, fetched issue/PR JSON, import paths, and timing
JSON are retained outside the revision-switching checkout at
`/job/review-evidence-j-29436ad7cd7f/`.

Key commands were:

```text
/tmp/amdpilot-repo-j-29436ad7cd7f/venv/bin/python -m pytest -q tests/kernels/test_moe_gemm_2stage.py::test_moe_gemm1_numeric --tb=short
/tmp/amdpilot-repo-j-29436ad7cd7f/venv/bin/python -m pytest -q tests/kernels/test_moe_gemm_2stage.py::test_moe_gemm1_persistent_numeric --tb=short
/tmp/amdpilot-repo-j-29436ad7cd7f/venv/bin/python -m pytest -q tests/kernels/test_moe_gemm_2stage.py -k gemm1 --tb=short
PYTHONPATH=/job/repo /tmp/amdpilot-repo-j-29436ad7cd7f/venv/bin/python /job/review-evidence-j-29436ad7cd7f/independent_persistent_review.py
HIP_VISIBLE_DEVICES=0 PYTHONPATH=/job/repo FLYDSL_RUNTIME_CACHE_DIR=/tmp/amdpilot-repo-j-29436ad7cd7f/cache/candidate-validation /tmp/amdpilot-repo-j-29436ad7cd7f/venv/bin/python reports/j-9870aaa06078/validate_persistent_gemm1.py
```

## Limitations

Only gfx950 was available, so gfx94-family execution remains unverified. Timing is
synthetic and variable and does not qualify production-model performance. The
upstream issue was read through GitHub's public API because the configured
fine-grained token was rejected by the ROCm organization policy; its live content
matched the supplied snapshot. No remaining correctness counterexample was found
within the supported GEMM1 contract.
