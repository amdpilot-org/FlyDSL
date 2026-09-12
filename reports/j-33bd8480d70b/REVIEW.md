# Independent review of amdpilot-org/FlyDSL PR 672

Reviewed candidate: `0ee04fd2a644b75ce07df281c8c37fba3e80680f`

Recorded base: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`

Recommendation: **request changes**

The candidate substantially implements the requested extraction. On the recorded base,
`from flydsl.testing import checkAllclose, run_perftest` fails because
`flydsl.testing` does not exist. At the exact candidate commit, the public module exists,
exports all 13 callables formerly implemented by `tests.test_common`, and the compatibility
module re-exports the same objects. The candidate regression passed (28 passed, 2 skipped),
and an independent HIP-event benchmark on one AMD Instinct MI355X/gfx950 returned the exact
NumPy CPU reference (`max_abs_error=0.0`).

The remaining defect is in the installed API contract. `flydsl.testing` imports pandas at
module import time, but the prepared FlyDSL wheel has no `Requires-Dist` metadata and the
repository has no `requirements.txt`, so pandas is not declared as a runtime dependency.
In a fresh process that makes pandas unavailable, the exact two-name import proposed by the
issue fails immediately with `ModuleNotFoundError`. This can be addressed by declaring the
dependency or by deferring pandas import to the profiler-only helpers so the primary
correctness and HIP-event benchmarking helpers remain importable.

No C++, MLIR, LLVM, or other native source changed. A native rebuild was therefore not
applicable. Candidate Python was loaded from `/job/repo/python/flydsl/testing.py`; the native
namespace resolved through `/job/repo/python/flydsl/_mlir`, the prepared symlink to
`/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`.

Environment limits: validation used ROCm 7.2 / Torch 2.9.1 on one gfx950 device. CUDA/NVIDIA,
HIP graph mode, and the torch-profiler timing mode were not independently exercised. These
do not cause the recommendation; the reproducible undeclared-dependency import failure does.

Raw command output and exit codes are retained under `raw/`.

Upstream issue: https://github.com/ROCm/FlyDSL/issues/304

Candidate mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/670

Review mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/674
