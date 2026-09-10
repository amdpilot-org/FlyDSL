# Plain RMSNorm input-layout admission on gfx950

## Scope

This report covers plain RMSNorm input-layout admission only. It does not add
mixed-weight streams, fused-add/residual backward, hidden-size expansion, or a
Quack integration.

## Read-only issue context

Upstream issue 749, `[RFC] FlyDSL kernels in downstream libraries`, was read
without posting or changing it. Its current description and comments state that
RMSNorm PRs 795, 800, 855, and 884 already landed and that no FlyDSL-core work
blocks a constrained plain-RMSNorm downstream integration. Upstream `main`
and this PR base both point at `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.

This change therefore does not duplicate those landed feature PRs. It only
admits zero-copy row-contiguous/flattenable layouts and records clear refusal
for unsupported views.

The tested admission policy is:

- positive-size, non-scalar input;
- 1D weight whose length matches the input's last dimension;
- unit-stride last dimension;
- `reshape(-1, N)` must remain a zero-copy, row-contiguous view.

Contiguous 2D/3D inputs and row-strided slices are admitted directly. A
transposed last dimension and a permuted 3D view that would require a copy are
rejected with `ValueError` before kernel launch.

## Environment

- Repository: `https://github.com/amdpilot-org/FlyDSL.git`
- PR base: `main` at `ed70142704e1a6d5563fb53e1607e3a4b85d7111`
- Worktree: `/job/FlyDSL`
- Image: `amdpilotv2/open-job:gbt350-20260909`, expected local ID
  `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`
- GPU: one AMD Instinct MI350X, gfx950
- Python: `/opt/venv/bin/python`
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`
- FlyDSL wheel: `0.2.4`

The installed 0.2.4 wheel lacks `get_warp_size`, so the checkout used the
one-function compatibility shim in
`/tmp/flydsl-shim-j-8400c2d12044/sitecustomize.py`. The installed-source
baseline is `/job/baseline-first.json`; it is not proof for later checkout
changes.

`results.json` records the PR-base commit because the evidence was collected
from the patched worktree before the delivery commit was created. The tested
code is the code delivered by this PR.

## Reproduction

```bash
cd /job/FlyDSL
export PYTHONPATH=/tmp/flydsl-shim-j-8400c2d12044:/job/FlyDSL
export FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-8400c2d12044
export FLYDSL_GPU_ARCH=gfx950
/opt/venv/bin/python reports/j-8400c2d12044/validate_rmsnorm_layouts.py \
  reports/j-8400c2d12044/results.json
```

Focused tests:

```bash
cd /job/FlyDSL
PYTHONPATH=/tmp/flydsl-shim-j-8400c2d12044:/job/FlyDSL \
FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-8400c2d12044 \
FLYDSL_GPU_ARCH=gfx950 \
/opt/venv/bin/python -m pytest -q \
  tests/kernels/test_rmsnorm.py::test_rmsnorm_forward_layout_admission \
  tests/kernels/test_rmsnorm.py::test_rmsnorm_row_strided_autograd_and_refusal
```

Affected existing tests:

```bash
cd /job/FlyDSL
PYTHONPATH=/tmp/flydsl-shim-j-8400c2d12044:/job/FlyDSL \
FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-8400c2d12044 \
FLYDSL_GPU_ARCH=gfx950 \
/opt/venv/bin/python -m pytest -q \
  tests/kernels/test_rmsnorm.py::test_rmsnorm \
  tests/kernels/test_rmsnorm.py::test_rmsnorm_backward \
  tests/kernels/test_rmsnorm.py::test_rmsnorm_autograd \
  tests/kernels/test_rmsnorm.py::test_rmsnorm_eps_honored \
  tests/kernels/test_rmsnorm.py::test_rmsnorm_forward_layout_admission \
  tests/kernels/test_rmsnorm.py::test_rmsnorm_row_strided_autograd_and_refusal
```

## Numerical gates

The existing gates are unchanged:

- forward output: `atol=2e-2`
- forward `rstd`: `atol=1e-3`
- public autograd output/input gradient: `rtol=1e-1, atol=2e-1`
- public autograd weight gradient: `rtol=1e-1, atol=5e-1`

## Raw results

Machine-readable paths, GPU identity, native modules, timing, errors, and
refusal messages are in `reports/j-8400c2d12044/results.json`.

- Focused new tests: `5 passed in 2.24 s`
- Affected existing plus new tests: `9 passed in 12.38 s`
- Forward timing uses CUDA events with 20 bounded calls.
- All admitted row-strided cases preserve untouched backing storage.
- Unsupported transposed and permuted views raise clear `ValueError` messages.

No synthetic burn, unbounded loop, sleep loop, model-weight download, or
repeated GPU work was used.

## Left undone

No mixed-weight, fused-add/residual, hidden-size expansion, multi-architecture,
or Quack integration claim is made. `black` and `ruff` are not installed in
this image; `git diff --check` and the repository's 120-column limit were used
instead.
