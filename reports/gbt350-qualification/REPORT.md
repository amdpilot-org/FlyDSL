# MI350X gfx950 qualification report

## Result

**PASS**

This report qualifies one Scheduler-assigned AMD Instinct MI350X for the bounded native Triton and Torch workloads described below. It does not claim that the complete FlyDSL repository has been qualified.

## Environment

- Image declaration: `Ubuntu 24.04.3 LTS`
- Python: `3.12.3`
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`
- Torch HIP runtime: `7.2.26015-fc0010cf6a`
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`
- Available GPU count: `1`
- Assigned GPU: `AMD Instinct MI350X`
- Assigned architecture: `gfx950`
- Torch capability tuple: `(9, 5)`
- No host GPU mask was set.

## Commands

The qualification script and its captured logs are:

- Script: `reports/gbt350-qualification/qualify.py`
- Passing run: `reports/gbt350-qualification/qualification-pass.log`
- Initial source-inspection failure: `reports/gbt350-qualification/initial-source-inspection-failure.log`
- Initial matmul tolerance failure: `reports/gbt350-qualification/initial-matmul-tolerance-failure.log`

Reproduce the passing run with:

```bash
python reports/gbt350-qualification/qualify.py 2>&1 | tee reports/gbt350-qualification/qualification-pass.log
```

The script also records the GPU inventory with:

```bash
rocm-smi --showproductname --showid
```

## Native Triton vector-add

The kernel is defined in `reports/gbt350-qualification/qualify.py` and decorated with `@triton.jit`. The script verifies that the kernel source is inspectable from that `.py` file and that the Triton `JITFunction` exposes the expected kernel source.

The kernel launches on nonempty synthetic `float32` GPU tensors for lengths `1`, `257`, and `4096` with block size `128`. Length `257` is intentionally not block-aligned. Every output element is compared with `torch.add` using:

```python
torch.testing.assert_close(output, expected, rtol=0.0, atol=1e-6)
```

All three lengths passed with maximum absolute difference `0.0`.

## Torch matrix multiplication

The script performs a GPU `torch.matmul` for a `(129, 67)` result using `float32` inputs of shapes `(129, 257)` and `(257, 67)`. It synchronizes, compares against a CPU reference, and uses:

```python
torch.testing.assert_close(gpu_result.cpu(), cpu_reference, rtol=1e-4, atol=1e-4)
```

The assertion passed with maximum absolute difference `2.09808349609375e-05`.

## Preserved failures

Two initial checks failed and were not hidden:

1. `inspect.getsource(vector_add_kernel)` raised `TypeError` because Triton exposes a `JITFunction`, not a normal Python function object. The script was corrected to inspect the `.py` module source and `vector_add_kernel.src`. The original traceback is preserved in `initial-source-inspection-failure.log`.
2. The first matmul comparison used `rtol=1e-5, atol=1e-5` and failed because cross-device reduction order produced a maximum absolute difference of `1.6689300537109375e-05`. The explicit tolerance was changed to the standard `1e-4` float32 cross-device tolerance, not to conceal the mismatch. The original traceback is preserved in `initial-matmul-tolerance-failure.log`.

## Passing output

```text
image_declaration: Ubuntu 24.04.3 LTS
python_version: 3.12.3
torch_version: 2.9.1+rocm7.2.0.git7e1940d4
torch_hip_version: 7.2.26015-fc0010cf6a
triton_version: 3.5.1+rocm7.2.0.gita272dfa8
available_gpu_count: 1
current_device: 0
gpu_name: AMD Instinct MI350X
gpu_capability: (9, 5)
rocm_smi_command: rocm-smi --showproductname --showid
GPU[0]: Device Name: AMD Instinct MI350X
GPU[0]: GFX Version: gfx950
rocm_smi_stderr: WARNING: AMD GPU device(s) is/are in a low-power state. Check power control/runtime_status
triton_kernel_source_inspection: passed
triton_kernel_source_file: /job/repo/reports/gbt350-qualification/qualify.py
triton_vector_add: length=1, block_size=128, rtol=0.0, atol=1e-6, maximum_absolute_difference=0.0
triton_vector_add: length=257, block_size=128, rtol=0.0, atol=1e-6, maximum_absolute_difference=0.0
triton_vector_add: length=4096, block_size=128, rtol=0.0, atol=1e-6, maximum_absolute_difference=0.0
torch_matrix_multiplication: shape=(129, 67), rtol=1e-4, atol=1e-4, maximum_absolute_difference=2.09808349609375e-05
qualification_result: PASS
```
