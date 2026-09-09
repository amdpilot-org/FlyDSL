# MI350X gfx950 validation

## Summary

- The old attach behavior on current source commit `ed70142704e1a6d5563fb53e1607e3a4b85d7111` emits two `rocdl.target` attachments and two `gpu.object` entries for one kernel.
- Both baseline ELF code objects are 4,712 bytes and byte-identical with SHA-256 `43c0f182a007a4849cc417c6a0c95417a246f165f45cbfd8bf916bb98444fa6f`.
- Object 0 has only `chip = "gfx950"`; object 1 has `flags = {fast, unsafe_math}`. The default `#gpu.select_object` handler selects object 0, so the requested options do not survive into the selected object.
- The fix omits the initial bare target. `rocdl-attach-target` then creates the sole object, carrying `chip = "gfx950", flags = {fast, unsafe_math}`.
- The numerical gate is unchanged: `torch.allclose(..., rtol=1e-6, atol=1e-6)` passes and maximum absolute error is `0.0`.
- Across three fresh processes, mean compile-and-launch time improved from `478.763 ms` to `349.463 ms`; mean full-process wall time improved from `2.957124 s` to `2.815726 s`. These are small-sample measurements, not a general performance claim.

## Environment

- Image: `amdpilotv2/open-job:gbt350-20260909`, local ID `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.
- GPU: one AMD Instinct MI350X, `gfx950`, UUID `GPU-593d46f1dbb5dce5`, PCI `0000:66:00.0`, driver `7.1.1.31500000`.
- Python: `/opt/venv/bin/python3` version `3.12.3`.
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`, HIP `7.2.26015-fc0010cf6a`.
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`.
- Installed FlyDSL: `0.2.4` at `/opt/venv/lib/python3.12/site-packages/flydsl`.
- Source FlyDSL: `0.3.3` at `/job/FlyDSL/python/flydsl`, base commit `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.
- AITER: `0+gd9e5ef7ce08ee7045d583aed768cff41aa9210fe` at `/opt/aiter/aiter`. Default import attempted a JIT build and failed with `No module named aiter.jit.module_aiter_core`; `AITER_TRITON_ONLY=1` imports successfully.
- Native tools: `/opt/rocm/bin/rocminfo`, `/opt/rocm/bin/rocm-smi`, `/opt/rocm/bin/amdclang++`, and `/opt/rocm-7.2.0/lib/llvm/bin/llvm-objdump`.

## Issue context

- Read-only reference: ROCm/FlyDSL issue 1054, “Every kernel is compiled twice.”
- At the time of this run, the issue was open and had no comments or linked PR/timeline entries.
- No upstream issue, PR, or comment was modified.
- Current source still contained both attach sites: `RocmBackend.gpu_module_targets()` created a bare target, and `rocdl-attach-target` added the options-bearing target.

## Reproduction

The validation kernel is `reports/j-a79bc3c135c0/validate_gfx950.py`. It requests:

```python
{
    "fast_fp_math": True,
    "unsafe_fp_math": True,
    "waves_per_eu": 2,
    "maxnreg": 128,
}
```

It compiles and launches a 64×128 float32 vector-add kernel on the assigned MI350X, compares against Torch, parses the final MLIR, extracts each embedded ELF, and records target text, size, and SHA-256.

The image’s installed FlyDSL `0.2.4` native MLIR does not register current source’s `convert-rocdl-fastmath-ops` pass. To execute current source without replacing the installed stack, the job privately downloaded FlyDSL wheel `0.3.2` and used only its native `_mlir` bindings:

```bash
python3 -m pip download flydsl==0.3.2 --no-deps \
  --dest /job/.cache/j-a79bc3c135c0/wheels
python3 -m zipfile -e \
  /job/.cache/j-a79bc3c135c0/wheels/flydsl-0.3.2-cp312-cp312-manylinux_2_27_x86_64.whl \
  /job/.cache/j-a79bc3c135c0/flydsl-0.3.2
```

The source package path was overlaid on that wheel’s native package path. A temporary `python/flydsl/_mlir` symlink pointed to the job-private wheel extraction and was removed after each run. No installed package or node-wide state was changed.

Baseline used the old attach behavior:

```python
RocmBackend.gpu_module_targets = lambda self: [
    f'#rocdl.target<chip = "{self.target.arch}">'
]
```

The fixed source returns `[]`, allowing `rocdl-attach-target` to create the sole target.

## Raw results

- Current-source baseline: `reports/j-a79bc3c135c0/gfx950-current-source-baseline-result.json`
- Current-source fixed: `reports/j-a79bc3c135c0/gfx950-current-source-result.json`
- Three-run timing: `reports/j-a79bc3c135c0/current-source-cold-compile-results.json`
- Installed-stack baseline: `reports/j-a79bc3c135c0/gfx950-baseline-result.json`
- Installed-stack candidate: `reports/j-a79bc3c135c0/gfx950-candidate-result.json`
- Environment record: `reports/j-a79bc3c135c0/environment.json`

### Baseline

```text
rocdl_target_count: 2
gpu_object_count: 2
object 0 target: chip = "gfx950"
object 1 target: chip = "gfx950", flags = {fast, unsafe_math}
object 0 size: 4712 bytes
object 1 size: 4712 bytes
object 0 sha256: 43c0f182a007a4849cc417c6a0c95417a246f165f45cbfd8bf916bb98444fa6f
object 1 sha256: 43c0f182a007a4849cc417c6a0c95417a246f165f45cbfd8bf916bb98444fa6f
offloading_handler: #gpu.select_object
default_handler_selects_first_object: true
```

### Fixed

```text
rocdl_target_count: 1
gpu_object_count: 1
object 0 target: chip = "gfx950", flags = {fast, unsafe_math}
object 0 size: 4712 bytes
object 0 sha256: 43c0f182a007a4849cc417c6a0c95417a246f165f45cbfd8bf916bb98444fa6f
offloading_handler: #gpu.select_object
default_handler_selects_first_object: true
```

### Numerical gate

```text
max_abs_error: 0.0
torch.allclose(C, A + B, rtol=1e-6, atol=1e-6): true
```

### Cold-process timing

```text
baseline compile-and-launch ms: 464.932, 483.980, 487.378 (mean 478.763)
fixed compile-and-launch ms:    368.959, 353.401, 326.029 (mean 349.463)
baseline process wall s:       2.847385, 3.015795, 3.008192 (mean 2.957124)
fixed process wall s:          2.854020, 2.857259, 2.735898 (mean 2.815726)
```

## Fix and tests

- `python/flydsl/compiler/backends/rocm.py` now returns no implicit `gpu.module` target.
- `tests/unit/test_compile_hints.py` asserts the ROCm backend supplies no implicit target.
- Focused tests passed:

```text
tests/unit/test_compile_hints.py::TestCompileHintsPropagation::test_fp_math_reaches_pipeline
tests/unit/test_compile_hints.py::TestCompileHintsPropagation::test_rocm_module_has_no_implicit_target
2 passed
```

## Limitations

- The timing sample is three fresh processes per mode on one assigned GPU; it is not a statistical benchmark.
- The compatibility wheel is FlyDSL `0.3.2`, while source is `0.3.3`; only its native MLIR bindings were used. The Python source and fix came from the working clone.
- The emitted ELF artifacts are retained in the working tree for local inspection but are not intended as source deliverables.
