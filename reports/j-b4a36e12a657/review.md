# Independent review of candidate PR 503

- Upstream issue: https://github.com/ROCm/FlyDSL/issues/732
- Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/515
- Prepared base: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`
- Candidate head: `0d04a0606079e3dce8bad3e888db4c28bac9d05b`
- Assigned device: AMD Instinct MI350X, gfx950, ROCm 7.2 / Torch 2.9.1+rocm7.2

## Result and recommendation

The candidate **fixes the original reported problem** on the available architecture. On a native rebuild of the prepared base, the reported `retile()` path aborts in `intTupleZip2ByImpl` with `Mismatched ranks in intTupleZip2By`. After checking out and rebuilding the exact candidate head, the same reproducer compiles and runs correctly. Minimum-tile and larger multi-tile boundary cases also run correctly.

Recommendation: accept the implementation for the reported defect. The candidate regression's `rel=2e-4, abs=2e-4` assertion is substantially looser than the errors observed here (at most `1.76e-5`), so tightening that test would improve its sensitivity, but independent measurements confirm the numerical result without relying on that tolerance.

The exact MI308X architecture from the report was unavailable; gfx950 is verified, MI308X remains unverified.

## Evidence

Python sources resolved to `/job/repo/python/flydsl`, and each revision was rebuilt with:

```text
/tmp/amdpilot-repo-j-b4a36e12a657/venv/bin/python /opt/amdpilot/rebuild-native.py /job
```

Both rebuilds passed. The base build recorded working-tree SHA-256 `e766acdc4a4a5012943b7877f88e1121e5e62c686986a4b2327be1f5b3a81759`; the candidate build recorded `bd59fdc2cbd5412580b99745838a7a5f9e9c75ac3361807fc7d708f2d1ac9dab`. The pinned LLVM revision was `e2a39f504fee836e4def9581bed817ecc327b9dc`.

Base reproduction (exit 134):

```text
FLYDSL_RUNTIME_CACHE_DIR=/job/review-cache-j-b4a36e12a657/base \
  /tmp/amdpilot-repo-j-b4a36e12a657/venv/bin/python \
  /job/review-evidence-j-b4a36e12a657/repro_original.py
```

It aborted at `include/flydsl/Dialect/Fly/Utils/IntTupleUtils.h:887` with the reported rank-mismatch assertion.

Candidate original and adversarial GPU cases (all exit 0), using the same reproducer with `TILE_M`, `TILE_N`, and `SEED`:

| Shape | Seed | GPU result | CPU float64 reference | Absolute error |
|---|---:|---:|---:|---:|
| 32x64 | 1 | -31.476594924926758 | -31.476590846315958 | 4.0786108e-06 |
| 64x64 | 0 | -64.26806640625 | -64.26808400535083 | 1.7599101e-05 |
| 64x128 | 2 | -213.99159240722656 | -213.99158514896408 | 7.2582625e-06 |
| 128x128 | 3 | -6.347418785095215 | -6.347404400286905 | 1.4384808e-05 |

The 32x64 case is the minimum single copy tile; the larger cases exercise repeated tile loops. Compiler dumps for 64x64 contain 16 `atomicrmw fadd` operations in LLVM IR and 16 `global_atomic_cmpswap` instructions in gfx950 ISA, whose target is explicitly `amdgcn-amd-amdhsa-unknown-gfx950`.

Candidate regression (exit 0):

```text
FLYDSL_RUNTIME_CACHE_DIR=/job/review-cache-j-b4a36e12a657/candidate-pytest \
  /tmp/amdpilot-repo-j-b4a36e12a657/venv/bin/python -m pytest -q -s \
  tests/kernels/test_retile_atomic.py
```

Result: 2 passed. This also confirms the no-retile path now produces the intended focused incompatibility diagnostic.

Candidate unit suite (exit 0):

```text
FLYDSL_RUNTIME_CACHE_DIR=/job/review-cache-j-b4a36e12a657/candidate-unit \
  /tmp/amdpilot-repo-j-b4a36e12a657/venv/bin/python -m pytest -q tests/unit
```

Result: 1098 passed, 17 skipped.

Raw logs, the reproducer, native build output, and compiler IR/ISA are retained under `/job/review-evidence-j-b4a36e12a657/`. No LLVM modification was required.
