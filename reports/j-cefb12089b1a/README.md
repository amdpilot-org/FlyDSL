# Conv3d channels-last validation report

## Scope

- Read-only upstream context: ROCm/FlyDSL issue 993 and both comments.
- Current mirror `main` already supports channels-last convolution through `input_layout` / `output_layout`.
- Open mirror PR 315 adds the issue-requested `layout` / `out_layout` aliases.
- PR 315: https://github.com/amdpilot-org/FlyDSL/pull/315
- Issue 993: https://github.com/ROCm/FlyDSL/issues/993
- Tested PR 315 commit `19f7acc4e61f06f99742ffcb326585be43fb685a` and current `main` commit `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.
- No implementation was duplicated or modified.

## GPU evidence

- Full PR 315 test file: **72 passed in 237.30 s** on one AMD Instinct MI350X (`gfx950`, capability `(9,5)`).
- Custom finite controls: **17/17 passed** for both alias and legacy API modes.
- Controls cover:
  - finite-input superposition with bias subtracted once on each side;
  - independent depthwise channel impulses for all four channels;
  - forced `splitk=1` and `splitk=2`;
  - channels-last input and output;
  - a finite sentinel bound case.
- Independent reference: CPU float32 `torch.nn.functional.conv3d` cross-correlation.
- Maximum absolute error in every custom control: **0.0**.
- First synchronized GPU execution:
  - PR 315 alias mode: `0.3370858021080494 s`;
  - current `main` legacy mode: `0.1688271528109908 s`.

## Installed-source baseline

The preinstalled FlyDSL `0.2.4` wheel does not contain `conv3d_implicit`. A neighboring installed AITER causal-conv1d FlyDSL control was used instead.

- First synchronized GPU execution: `0.12086394242942333 s`.
- First numerical comparison failed with max absolute error `0.75`.
- The subsequent call failed with `HIP error: an illegal memory access was encountered`.
- This baseline is environment context only and is not proof for later checkout changes.

## Reproduction

```bash
export PYTHONPATH=/tmp/flydsl-cache-j-cefb12089b1a/wheel-0.3.2:.
export FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-cefb12089b1a/runtime
export FLYDSL_AUTOTUNE_CACHE_DIR=/tmp/flydsl-cache-j-cefb12089b1a/autotune
export FLYDSL_GPU_ARCH=gfx950

# PR 315 alias mode
CONV3D_USE_ALIAS=1 /opt/venv/bin/python reports/j-cefb12089b1a/conv3d_controls.py

# Current main legacy mode
CONV3D_USE_ALIAS=0 /opt/venv/bin/python reports/j-cefb12089b1a/conv3d_controls.py

# Full PR 315 test file
git switch --detach 19f7acc4e61f06f99742ffcb326585be43fb685a
/opt/venv/bin/python -m pytest -q tests/kernels/test_conv3d_implicit.py --disable-warnings
```

## Environment

- Image: `amdpilotv2/open-job:gbt350-20260909`
- Local image ID: `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`
- Interpreter: `/opt/venv/bin/python`
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`
- FlyDSL runtime used for checkout: `0.3.2`, installed under `/tmp/flydsl-cache-j-cefb12089b1a/wheel-0.3.2`

## Remaining scope

- No whole-network benchmark, GroupNorm, or spatial-parallelism claim.
- No upstream issue, pull request, or comment was posted or changed.
- PR 315 remains open and is not merged here.
