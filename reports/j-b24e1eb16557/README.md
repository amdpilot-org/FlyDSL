# gfx950 investigation for ROCm/FlyDSL issue 732

## Scope and environment

- Campaign: `repo-e2e-20260909`; coordination tracker: `amdpilot-org/amdpilotv2` issue 402.
- GPU: one AMD Instinct MI350X, `gfx950`, ROCm device node 2, GUID 36538.
- Qualified image: `amdpilotv2/open-job:gbt350-20260909`, local image ID `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7` (operator-provided; Docker is not available inside the job container).
- Python: `/opt/venv/bin/python`; Torch `2.9.1+rocm7.2.0.git7e1940d4`; Triton `3.5.1+rocm7.2.0.gita272dfa8`.
- Installed FlyDSL baseline: version 0.2.4 at `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`.
- Persistent source checkout: `/job/FlyDSL`, base `main` at `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.
- Source-build Python package: `/tmp/flydsl-cache-j-b24e1eb16557/fly-build-main/python_packages/flydsl/__init__.py`.
- Pinned MLIR install: `/tmp/flydsl-cache-j-b24e1eb16557/mlir_install`.

The installed-source baseline is evidence for the preinstalled environment only and is not proof for later checkout changes.

## Early baseline

The first relevant FlyDSL candidate was the existing AITER split-K HGEMM test at `/opt/aiter/aiter/ops/flydsl/test_flydsl_splitk_hgemm.py` (AITer commit `d9e5ef7ce08ee7045d583aed768cff41aa9210fe`). It failed during collection after 23.326 seconds with `ModuleNotFoundError: No module named 'aiter.jit.module_aiter_core'`; no FlyDSL kernel launched.

The supported neighboring control was a bounded Triton kernel that loaded source, stored a copy, and used `tl.atomic_add`. It compared both outputs against independent Torch operations:

- Copy: `torch.equal(copy, src)` passed with maximum delta 0.
- Atomic sum: `torch.equal(atomic_sum, src + src)` passed with maximum delta 0.
- First GPU execution, including Triton JIT: 2.688 seconds by `time.perf_counter`.
- Steady-state kernel: 0.169441 ms by CUDA events.

The complete record is in `/job/baseline-first.json`.

## Issue 732 results

The issue uses `UniversalCopy128b` for loads and `UniversalAtomicAdd` for a broadcast scalar destination. The three cases were run on the installed 0.2.4 wheel, source `main`, preserved PR #918 head, and the corrected source branch.

- No retile: this is an invalid vector atomic layout. Installed 0.2.4 reported `unsupported cmpxchg`. Source `main` reported a 16-byte atomic error and, in one run, returned zero rather than the expected sum. This is not counted as a valid wrong-result case. PR #918 head `742a6a69011c117c4c259c6c34efe7d081595a96` (fix commit `933e351992d2ff71b5c66561b73bb8ff74a5cf3c`) turns it into `vectorized atomic ops are unsupported, need a scalar-sized copy atom`.
- `retile`: installed 0.2.4 and source `main` aborted in `IntTupleUtils.h` with `Mismatched ranks in intTupleZip2By`. PR #918 does not address this case. The branch correction now reports that input layout rank 2 must equal tiled-copy rank plus value mode 3, and advises retiling the full partitioned fragment before indexing tile modes.
- Explicit broadcast view: the issue's workaround is a valid GPU path. It produced the exact expected sum on installed 0.2.4, source `main`, PR #918, and the corrected branch. For the source branch, expected and actual were both `-64.2680740` with absolute error 0.

PR #918 was tested as a candidate and is intentionally not duplicated in this change.

## Guarded and tail evidence

The valid 64×64 case used flat allocations with sentinel guard elements on both sides. The corrected branch produced expected `-120.8905716` and actual `-120.8905945` (absolute error `2.288818e-05`), within `rtol=2e-6, atol=2e-5`. All A and B guard elements remained unchanged.

The same unmasked issue kernel was then given non-tile-aligned and small shapes. Every non-exact shape produced a wrong sum while all guard elements remained unchanged, showing reads beyond the logical input rather than guard writes:

- `64x65`: expected `-112.8054733`, actual `-987868.1875`.
- `65x64`: expected `-112.8054733`, actual `765203.3125`.
- `65x65`: expected `-120.5542908`, actual `653882.25`.
- `64x66`: expected `-120.8305435`, actual `-987853.25`.
- `64x67`: expected `-111.7126923`, actual `-987839.3125`.
- `64x68`: expected `-129.2678986`, actual `-987886.9375`.
- `1x1`: expected `-1.8243021`, actual `-1975309.75`.
- `1x2`: expected `-3.0304623`, actual `-7987744.0`.
- `1x3`: expected `-2.3356347`, actual `192802416.0`.
- `1x4`: expected `-3.6001768`, actual `44259200.0`.
- `2x2`: expected `-3.6001768`, actual `-39592760.0`.
- `3x3`: expected `-6.2010708`, actual `154196960.0`.
- `4x4`: expected `-6.6225653`, actual `38333180.0`.

These tail results are reported separately from the invalid-layout diagnostics. They are not corrected here: the issue's kernel has no tail predicate, and adding masking would be a second, undemonstrated behavioral change beyond the one diagnostic correction.

## Reproduction

Build the pinned MLIR toolchain and FlyDSL with job-private caches, then run:

```bash
export PYTHONPATH=/tmp/flydsl-cache-j-b24e1eb16557/fly-build-main/python_packages:/job/FlyDSL
export LD_LIBRARY_PATH=/tmp/flydsl-cache-j-b24e1eb16557/fly-build-main/python_packages/flydsl/_mlir/_mlir_libs:/tmp/flydsl-cache-j-b24e1eb16557/mlir_install/lib
export FLYDSL_GPU_ARCH=gfx950
/opt/venv/bin/python -m pytest -q /job/FlyDSL/tests/unit/test_tiled_copy_retile.py -s
/opt/venv/bin/python -m pytest -q /job/FlyDSL/tests/unit/test_universal_atomic.py -s
```

The new suite contains two cases: the rank-mismatch diagnostic and the guarded valid broadcast sum. The unchanged universal atomic suite contains six scalar atomic cases.

## Result

- New suite: 2 passed.
- Unchanged `test_universal_atomic.py`: 6 passed.
- One correction: reject mismatched `tiled_copy.retile` input rank with a source-located diagnostic.
- Left undone: PR #918 remains the candidate for the vector-atomic diagnostic; tail masking and a formal tile-alignment contract are not changed.
