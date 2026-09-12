# Independent review of candidate PR 499

- Upstream issue: https://github.com/ROCm/FlyDSL/issues/993
- Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/522
- Candidate: https://github.com/amdpilot-org/FlyDSL/pull/499
- Prepared base: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`
- Exact candidate head: `e07df13d07ff0d388a492f71cfd8cef336b05203`
- Recommendation: **accept the candidate for the reported layout API and transpose-elision problem**.

## Verdict

The original problem reproduced on the prepared base: `conv3d_implicit(..., layout="NDHWC", out_layout="NDHWC")` failed with `TypeError: _conv3d_impl() got an unexpected keyword argument 'layout'`. The exact candidate fixes that public API failure, returns numerically correct NDHWC output, and permits two convolutions to remain NDHWC without invoking `_ncdhw_to_ndhwc` between layers.

This is a full fix for the behavior requested in the issue, within the architecture exercised. A CUDA profiler provided independent runtime evidence: an NCDHW invocation recorded `transpose_kernel_0`, while the equivalent NDHWC invocation recorded no transpose event. PyTorch `conv3d` was the independent numerical reference; tolerances were not weakened from the candidate's strictest regression (`rtol=2e-2`, `atol=2e-2`).

## Environment and imports

Tests used `/tmp/amdpilot-repo-j-b60669aba68b/venv/bin/python` with `PYTHONPATH=/job/repo`. The Python implementation loaded from `/job/repo/kernels/conv/conv3d_implicit.py`, so revision switches changed the implementation under test. FlyDSL Python loaded from `/job/repo/python/flydsl/__init__.py`. The native MLIR libraries remained the prepared pinned wheel under `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`; hashes are in `raw/native-sha256.txt`.

The candidate changes only Python, tests, and its own report artifacts. It has no native C++ changes, so the prepared native rebuild command was not applicable and was not run.

GPU execution was real on one AMD Instinct MI355X (`gfx950`), with Torch `2.9.1+rocm7.2.0.git7e1940d4` and HIP `7.2.26015-fc0010cf6a`.

## Commands and results

Base reproduction (exit 1, expected failure):

```bash
PYTHONPATH=/job/repo /tmp/amdpilot-repo-j-b60669aba68b/venv/bin/python /job/review-evidence/base_reproduction.py
```

Candidate regressions (exit 0, 5 passed):

```bash
env PYTHONPATH=/job/repo XDG_CACHE_HOME=/tmp/amdpilot-repo-j-b60669aba68b/cache FLYDSL_CACHE_DIR=/tmp/amdpilot-repo-j-b60669aba68b/cache /tmp/amdpilot-repo-j-b60669aba68b/venv/bin/python -m pytest -q tests/kernels/test_conv3d_implicit.py -k 'layout_contract or ndhwc_chain or ndhwc_splitk' -vv
```

Independent adversarial GPU cases (exit 0):

```bash
env PYTHONPATH=/job/repo XDG_CACHE_HOME=/tmp/amdpilot-repo-j-b60669aba68b/cache FLYDSL_CACHE_DIR=/tmp/amdpilot-repo-j-b60669aba68b/cache /tmp/amdpilot-repo-j-b60669aba68b/venv/bin/python /job/review-evidence/candidate_adversarial.py
```

Measured unaligned input/output channels with mixed stride and dilation, grouped convolution with channel padding and split-K, unbatched NDHWC, a two-layer 1x1 NDHWC chain with zero input-transpose calls, and rejection of a rank-inappropriate layout. Every numerical case matched PyTorch at `rtol=2e-2`, `atol=2e-2`; the recorded maximum absolute error was zero for these deterministic bf16 cases.

CUDA transpose profile (exit 0):

```bash
env PYTHONPATH=/job/repo XDG_CACHE_HOME=/tmp/amdpilot-repo-j-b60669aba68b/cache FLYDSL_CACHE_DIR=/tmp/amdpilot-repo-j-b60669aba68b/cache /tmp/amdpilot-repo-j-b60669aba68b/venv/bin/python /job/review-evidence/candidate_profile.py
```

Measured `ncdhw_transpose_events=['transpose_kernel_0']` and `ndhwc_transpose_events=[]`.

Complete candidate convolution module (exit 0, 62 passed in 159.73 seconds):

```bash
env PYTHONPATH=/job/repo XDG_CACHE_HOME=/tmp/amdpilot-repo-j-b60669aba68b/cache FLYDSL_CACHE_DIR=/tmp/amdpilot-repo-j-b60669aba68b/cache /tmp/amdpilot-repo-j-b60669aba68b/venv/bin/python -m pytest -q tests/kernels/test_conv3d_implicit.py
```

Candidate diff hygiene (exit 0):

```bash
git diff --check acf7e67b7d22847e345938ca54fcc137bd7b2a1f e07df13d07ff0d388a492f71cfd8cef336b05203
```

## Limitations

The reported MI350X/ROCm 7.1.1 environment and the largest production shapes were not available. Validation used the available, same-ISA-family MI355X/gfx950 with ROCm 7.2. The review establishes correctness and actual transpose elimination, but does not independently reproduce the issue author's end-to-end Wan VAE timing or the claimed 20 ms network saving. Direct API access to the upstream issue was denied by the organization token policy, so the supplied issue snapshot and the accessible mirror issue were used as problem data.

Raw outputs and import/native path evidence are retained in `raw/`.
