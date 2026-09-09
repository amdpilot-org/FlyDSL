#!/usr/bin/env python3

import inspect
import platform
import subprocess
from pathlib import Path

import torch
import triton
import triton.language as tl


@triton.jit
def vector_add_kernel(
    input_a_ptr,
    input_b_ptr,
    output_ptr,
    element_count,
    BLOCK_SIZE: tl.constexpr,
):
    offsets = tl.program_id(0) * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < element_count
    input_a = tl.load(input_a_ptr + offsets, mask=mask, other=0.0)
    input_b = tl.load(input_b_ptr + offsets, mask=mask, other=0.0)
    tl.store(output_ptr + offsets, input_a + input_b, mask=mask)


def print_environment() -> None:
    os_release = Path("/etc/os-release").read_text(encoding="utf-8")
    pretty_name = next(
        line.split("=", 1)[1].strip('"')
        for line in os_release.splitlines()
        if line.startswith("PRETTY_NAME=")
    )
    rocm_smi = subprocess.run(
        ["rocm-smi", "--showproductname", "--showid"],
        check=True,
        capture_output=True,
        text=True,
    )
    print(f"image_declaration: {pretty_name}")
    print(f"python_version: {platform.python_version()}")
    print(f"torch_version: {torch.__version__}")
    print(f"torch_hip_version: {torch.version.hip}")
    print(f"triton_version: {triton.__version__}")
    print(f"available_gpu_count: {torch.cuda.device_count()}")
    print(f"current_device: {torch.cuda.current_device()}")
    print(f"gpu_name: {torch.cuda.get_device_name(0)}")
    print(f"gpu_capability: {torch.cuda.get_device_capability(0)}")
    print("rocm_smi_command: rocm-smi --showproductname --showid")
    print(rocm_smi.stdout.rstrip())
    if rocm_smi.stderr:
        print(f"rocm_smi_stderr: {rocm_smi.stderr.rstrip()}")


def verify_environment() -> None:
    assert torch.cuda.device_count() == 1, f"expected exactly one GPU, got {torch.cuda.device_count()}"
    assert torch.cuda.get_device_name(0) == "AMD Instinct MI350X", torch.cuda.get_device_name(0)
    assert torch.cuda.get_device_capability(0) == (9, 5), torch.cuda.get_device_capability(0)
    rocm_smi = subprocess.run(
        ["rocm-smi", "--showproductname", "--showid"],
        check=True,
        capture_output=True,
        text=True,
    )
    normalized_output = " ".join(rocm_smi.stdout.split())
    assert "GFX Version: gfx950" in normalized_output, normalized_output


def verify_triton_vector_add() -> None:
    module_source = Path(__file__).read_text(encoding="utf-8")
    kernel_source = vector_add_kernel.src
    assert "@triton.jit" in module_source
    assert "def vector_add_kernel" in module_source
    assert "def vector_add_kernel" in kernel_source
    print("triton_kernel_source_inspection: passed")
    print(f"triton_kernel_source_file: {Path(__file__).resolve()}")

    lengths = [1, 257, 4096]
    block_size = 128
    torch.manual_seed(0)
    for length in lengths:
        input_a = torch.randn(length, device="cuda", dtype=torch.float32)
        input_b = torch.randn(length, device="cuda", dtype=torch.float32)
        output = torch.empty_like(input_a)
        grid = (triton.cdiv(length, block_size),)
        vector_add_kernel[grid](input_a, input_b, output, length, BLOCK_SIZE=block_size)
        torch.cuda.synchronize()
        expected = torch.add(input_a, input_b)
        torch.testing.assert_close(output, expected, rtol=0.0, atol=1e-6)
        maximum_difference = (output - expected).abs().max().item()
        print(
            f"triton_vector_add: length={length}, block_size={block_size}, "
            f"rtol=0.0, atol=1e-6, maximum_absolute_difference={maximum_difference}"
        )


def verify_torch_matrix_multiplication() -> None:
    torch.manual_seed(1)
    left = torch.randn(129, 257, device="cuda", dtype=torch.float32)
    right = torch.randn(257, 67, device="cuda", dtype=torch.float32)
    gpu_result = torch.matmul(left, right)
    torch.cuda.synchronize()
    cpu_reference = torch.matmul(left.cpu(), right.cpu())
    torch.testing.assert_close(gpu_result.cpu(), cpu_reference, rtol=1e-4, atol=1e-4)
    maximum_difference = (gpu_result.cpu() - cpu_reference).abs().max().item()
    print(
        f"torch_matrix_multiplication: shape={tuple(gpu_result.shape)}, "
        f"rtol=1e-4, atol=1e-4, maximum_absolute_difference={maximum_difference}"
    )


def main() -> None:
    print_environment()
    verify_environment()
    verify_triton_vector_add()
    verify_torch_matrix_multiplication()
    print("qualification_result: PASS")


if __name__ == "__main__":
    main()
