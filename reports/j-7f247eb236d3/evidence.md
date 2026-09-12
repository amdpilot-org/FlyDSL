# Duplicate ROCDL target investigation

Base commit: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`

Python: `/tmp/amdpilot-repo-j-7f247eb236d3/venv/bin/python`

Imported FlyDSL source: `/job/repo/python/flydsl/__init__.py`

Prepared native library: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`

Raw evidence is retained under `/job/job-artifacts/j-7f247eb236d3/`.

## Reproduction and repair

Before the repair, `reproduce_duplicate_targets.py` compiled one no-op kernel
for `gfx1201` with `fast_fp_math=True` and `unsafe_fp_math=True`. The resulting
`gpu.binary` had no offloading handler and contained two objects:

```text
gpu_objects=2
target[0]=#rocdl.target<chip = "gfx1201">
target[1]=#rocdl.target<chip = "gfx1201", flags = {fast, no_wave64, unsafe_math}>
```

Raw files:

- `/job/job-artifacts/j-7f247eb236d3/before-gfx1201.txt`
- `/job/job-artifacts/j-7f247eb236d3/before-gfx1201.mlir`
- `/job/job-artifacts/j-7f247eb236d3/regression-before.txt`

After making the backend attach-target pass the sole target owner, the same
command emits one object, so the hinted object is necessarily the selected
object:

```text
gpu_objects=1
target[0]=#rocdl.target<chip = "gfx1201", flags = {fast, no_wave64, unsafe_math}>
```

Raw files:

- `/job/job-artifacts/j-7f247eb236d3/after-gfx1201.txt`
- `/job/job-artifacts/j-7f247eb236d3/after-gfx1201.mlir`
- `/job/job-artifacts/j-7f247eb236d3/regression-after.txt`

The canonical target spelling omits values equal to ROCDL defaults. The
non-default `fast`, `unsafe_math`, and RDNA wave32 (`no_wave64`) flags remain
visible on the sole serialized object. The pipeline continues to pass `O=2`,
`abi=600`, `correct-sqrt=true`, `daz=false`, and `finite-only=false` to
`rocdl-attach-target`; those default-valued fields are canonicalized out of the
printed target attribute.

## gfx950 execution and compiler evidence

`validate_gfx950.py` ran a 4,099-element FP32 vector add on the assigned AMD
Instinct MI350X (`gfx950:sramecc+:xnack-`). A CPU-side PyTorch addition was the
independent numerical reference. The maximum absolute error was zero.

The final binary contained exactly one object with
`#rocdl.target<chip = "gfx950", flags = {fast, unsafe_math}>`. The emitted ISA
identifies `.amdgcn_target "amdgcn-amd-amdhsa-unknown-gfx950"` and contains the
expected `global_load_dword`, `v_add_f32_e32`, `global_store_dword`, and
`s_endpgm` instructions for `_vector_add_kernel_0`.

Raw files:

- `/job/job-artifacts/j-7f247eb236d3/gfx950-validation.txt`
- `/job/job-artifacts/j-7f247eb236d3/gfx950-dump/_vector_add_kernel_0/11_rocdl_attach_target.mlir`
- `/job/job-artifacts/j-7f247eb236d3/gfx950-dump/_vector_add_kernel_0/19_gpu_module_to_binary.mlir`
- `/job/job-artifacts/j-7f247eb236d3/gfx950-dump/_vector_add_kernel_0/20_llvm_ir.ll`
- `/job/job-artifacts/j-7f247eb236d3/gfx950-dump/_vector_add_kernel_0/21_final_isa.s`
- `/job/job-artifacts/j-7f247eb236d3/focused-tests.txt`

No C++ source changed, so a native rebuild was neither required nor performed.
The original `gfx1201` case was compile-only because the assigned device is
`gfx950`; actual execution was verified on `gfx950`.
