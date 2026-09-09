# gfx942 ROCDL target investigation

## Result

The duplicate is reproducible on the assigned MI300X when the requested
`fast_fp_math` and `unsafe_fp_math` compile hints are enabled. Current source
is not fixed: it creates a bare `#rocdl.target` on `gpu.module`, and
`rocdl-attach-target` then adds a second target carrying the configured
options. With no offloading selector, the first bare object is selected.

The minimal correction keeps `rocdl-attach-target` as the sole target source.
That preserves target semantics and all requested compile options while
emitting one code object. Upstream `main` at `ed70142704e1a6d5563fb53e1607e3a4b85d7111`
still contains the old bare-target construction, and no fixing PR was found.

## Environment

- Campaign: `repo-e2e-20260909`
- Working clone: `/job/FlyDSL`, branch `main` at `ed70142704e1a6d5563fb53e1607e3a4b85d7111`
- Source Python: `/job/FlyDSL/python/flydsl`, version `0.3.3`
- Installed FlyDSL: `/opt/venv/lib/python3.10/site-packages/flydsl`, version `0.3.1`
- Source native runtime used for this run: FlyDSL `0.3.2` wheel `_mlir` extracted to `/job/task-artifacts/flydsl-0.3.2-native/flydsl/_mlir`
- Torch: `2.9.1+rocm7.2.0.lw.git7e1940d4`
- HIP: `7.2.26015-fc0010cf6a`
- GPU: one AMD Instinct MI300X, `gfx942`, GUID `9845`, device ID `0x74a1`
- Task-specified qualified image: `amdpilotv2/open-job-mi300:jit-config-readable-35122-260909`, local image ID `sha256:dfc9419089c338b5712da4841768b38b1ab79f3da41f8c58c3cd4dfcc1147ff1`
- Image verification limitation: no `docker`, `podman`, `nerdctl`, `ctr`, or `crictl` binary/socket was available inside the job, so the local image ID could not be independently queried. Hostname was not treated as image identity.

The source tree has no built `_mlir` directory and no MLIR CMake install was
present. The installed 0.3.1 native runtime lacks the current source's
`convert-rocdl-fastmath-ops` pass. To test current Python source without
changing the Torch/ROCm stack, only the FlyDSL 0.3.2 wheel's `_mlir` payload was
downloaded and extracted; no dependencies or model weights were installed.

## Upstream context

Read-only checks of ROCm/FlyDSL issue 1054 showed:

- Title: `[Issue]: Every kernel is compiled twice`
- State: open
- Comments: none
- Timeline: assignment only
- Upstream `main` matches the mirror base and still returns a bare target from `RocmBackend.gpu_module_targets()`.
- Commits after the issue date touching the relevant files are `15553b3` (cache hashing) and `4c68677` (fastmath lowering); neither fixes duplicate target attachment.

## Reproducer

The synthetic kernel is a 4099-element pointer vector add. It uses no model
weights and is compiled with:

```bash
export ARCH=gfx942
export FLYDSL_RUNTIME_ENABLE_CACHE=0
export COMPILE_ONLY=1
/opt/venv/bin/python reproduce.py --fast-hints --output baseline-hinted.mlir
```

The requested compile hints are:

```python
{"fast_fp_math": True, "unsafe_fp_math": True}
```

The exact target pass options are:

```text
rocdl-attach-target{O=2 abi=600 chip=gfx942 correct-sqrt=true daz=false fast=true features= finite-only=false module= triple=amdgcn-amd-amdhsa unsafe-math=true wave64=true}
```

## Baseline evidence

Before the correction, the hinted compilation emitted:

```text
gpu.binary @kernels [
  #gpu.object<#rocdl.target<chip = "gfx942">, ...>,
  #gpu.object<#rocdl.target<chip = "gfx942", flags = {fast, unsafe_math}>, ...>
]
```

- `#gpu.object` count: 2
- `#rocdl.target` count: 2
- Object 0: 4416 bytes, SHA-256 `3e442851d25f9fcf4629bb1537ed053040b4ae1be97e33f324b7068576e8ac29`
- Object 1: 4416 bytes, same SHA-256

Both payloads are ELF64 AMD GPU objects. `readelf` reports the AMDGPU note
target as `amdgcn-amd-amdhsa-unknown-gfx942`, and the `.comment` section names
AMD LLD 22.0.0 at LLVM commit
`7b800a19466229b8479a78de19143dc33c3ab9b5`. The identical hashes are expected
for this simple add kernel; fast-math flags do not alter its generated machine
code. They do alter the target attribute and therefore which configured object
would be selected in a kernel where those options matter.

With default hints, this native toolchain emitted one bare object because the
attach-target pass did not add a second target when its options matched the
defaults. The duplicate appears when the requested non-default fast/unsafe
options are present.

## Corrected evidence

After the correction, the hinted compilation emitted:

```text
gpu.binary @kernels [
  #gpu.object<#rocdl.target<chip = "gfx942", flags = {fast, unsafe_math}>, ...>
]
```

- `#gpu.object` count: 1
- `#rocdl.target` count: 1
- Object size: 4416 bytes
- SHA-256: `3e442851d25f9fcf4629bb1537ed053040b4ae1be97e33f324b7068576e8ac29`
- ELF machine: AMD GPU
- AMDGPU note target: `amdgcn-amd-amdhsa-unknown-gfx942`

The default-hints corrected compilation also emitted one object. Its target
prints as the chip-only attribute because MLIR omits default target fields;
the full pass options remain in the pipeline.

## Independent Torch comparison

The same 4099-element float32 tensors were passed to FlyDSL and
`torch.add`. Results were recorded without invented gates:

### Corrected, hinted compile and execution

```json
{
  "size": 4099,
  "torch_reference_sum": 32.931922912597656,
  "torch_output_sum": 32.931922912597656,
  "torch_reference_max_abs": 5.997529983520508,
  "torch_output_max_abs": 5.997529983520508,
  "max_abs_difference": 0.0,
  "allclose_rtol_0_atol_0": true,
  "allclose_default": true
}
```

### Corrected, default-hints execution

```json
{
  "size": 4099,
  "torch_reference_sum": 128.1805419921875,
  "torch_output_sum": 128.1805419921875,
  "torch_reference_max_abs": 5.641786575317383,
  "torch_output_max_abs": 5.641786575317383,
  "max_abs_difference": 0.0,
  "allclose_rtol_0_atol_0": true,
  "allclose_default": true
}
```

## Toolchain and tests

Available tools:

- `/opt/rocm/bin/rocm-smi`
- `/opt/rocm/bin/rocminfo`
- `/opt/rocm/bin/hipcc`
- `/usr/bin/readelf`
- `/usr/bin/objdump`

Unavailable in `PATH`: `clang`, `llvm-objdump`, `clang-offload-bundler`,
`rocm-objdump`, and `extractkernel`.

Focused validation:

```bash
LD_LIBRARY_PATH=/job/task-artifacts/flydsl-0.3.2-native/flydsl.libs \
PYTHONPATH=/job/FlyDSL/python \
/opt/venv/bin/python -m pytest -q \
  tests/unit/test_compile_hints.py \
  tests/unit/test_compile_backends.py \
  tests/unit/test_external_llvm_codegen.py
```

Result: 29 passed, 2 skipped.

## Limitations

- The full current-source native toolchain was not built because no MLIR CMake
  installation was available. Current Python source was paired with the 0.3.2
  wheel native runtime, which supports the current pass pipeline.
- The simple add kernel cannot numerically distinguish fast/unsafe math; the
  object target and exact pass options are the evidence that those requested
  options are preserved.
- The container image ID could not be independently queried with the available
  container tooling; the task-specified qualified image ID is recorded above.
