#!/usr/bin/env python3
"""Record bounded plain-RMSNorm input-layout evidence on one gfx950 GPU."""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

import torch
import triton

import flydsl
from flydsl.runtime.device import get_rocm_arch
from kernels.norm import rmsnorm_kernel as rmsnorm_impl


EPS = 1e-5
TIMED_CALLS = 20
OUTPUT_ATOL = 2e-2
RSTD_ATOL = 1e-3
AUTOGRAD_RTOL = 1e-1
AUTOGRAD_ATOL = 2e-1
DWEIGHT_RTOL = 1e-1
DWEIGHT_ATOL = 5e-1


def _native_paths() -> list[str]:
    package_root = Path(flydsl.__file__).resolve().parent
    return sorted(str(path) for path in package_root.rglob("*.so"))


def _git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def _container_id() -> str:
    text = Path("/proc/self/cgroup").read_text()
    return text.split("docker/")[-1].splitlines()[0].rstrip(")")


def _gpu_identity() -> dict:
    raw = subprocess.check_output(
        ["rocm-smi", "--showproductname", "--showserial", "--showuniqueid", "--json"],
        text=True,
    )
    return {
        "torch_name": torch.cuda.get_device_name(0),
        "capability": list(torch.cuda.get_device_capability(0)),
        "device_count": torch.cuda.device_count(),
        "rocm_arch": get_rocm_arch(),
        "rocm_smi": json.loads(raw),
    }


def _time_forward(case, x_flat, weight, rows, hidden, device) -> dict:
    start = time.monotonic()
    output, rstd = rmsnorm_impl.rmsnorm_fwd(x_flat, weight, eps=EPS, store_rstd=True)
    torch.cuda.synchronize(device)
    first_execution_seconds = time.monotonic() - start

    x_reference = x_flat.detach().to(torch.float32)
    weight_reference = weight.detach().to(torch.float32)
    rstd_reference = torch.rsqrt(x_reference.square().mean(dim=1) + EPS)
    output_reference = x_reference * rstd_reference[:, None] * weight_reference
    output_max_abs = (output.to(torch.float32) - output_reference).abs().max().item()
    rstd_max_abs = (rstd - rstd_reference).abs().max().item()

    starts = [torch.cuda.Event(enable_timing=True) for _ in range(TIMED_CALLS)]
    ends = [torch.cuda.Event(enable_timing=True) for _ in range(TIMED_CALLS)]
    for index in range(TIMED_CALLS):
        starts[index].record()
        rmsnorm_impl.rmsnorm_fwd(x_flat, weight, eps=EPS, store_rstd=True)
        ends[index].record()
    torch.cuda.synchronize(device)
    samples_ms = [starts[index].elapsed_time(ends[index]) for index in range(TIMED_CALLS)]

    return {
        "case": case,
        "rows": rows,
        "hidden_size": hidden,
        "dtype": "bf16",
        "weight_dtype": "bf16",
        "eps": EPS,
        "output_max_abs": output_max_abs,
        "rstd_max_abs": rstd_max_abs,
        "output_atol": OUTPUT_ATOL,
        "rstd_atol": RSTD_ATOL,
        "passed": output_max_abs <= OUTPUT_ATOL and rstd_max_abs <= RSTD_ATOL,
        "timing_method": "CUDA events; 20 timed calls",
        "first_execution_seconds": first_execution_seconds,
        "timed_median_ms": statistics.median(samples_ms),
        "timed_mean_ms": statistics.mean(samples_ms),
        "timed_samples_ms": samples_ms,
    }


def _forward_cases(device) -> list[dict]:
    torch.manual_seed(749)
    cases = (
        ("contiguous_2d", (37, 512), 0, (37,)),
        ("row_strided_2d", (37, 4096), 128, (37,)),
        ("contiguous_3d", (38, 512), 0, (2, 19)),
        ("row_strided_3d", (38, 4096), 128, (2, 19)),
    )
    results = []
    for name, (rows, hidden), padding, leading_shape in cases:
        base_shape = leading_shape + (hidden + padding,)
        base = torch.randn(base_shape, device=device, dtype=torch.bfloat16)
        x = base[..., :hidden] if padding else base
        x_flat = x.reshape(-1, hidden)
        weight = torch.rand((hidden,), device=device, dtype=torch.bfloat16)
        base_snapshot = base.detach().clone()
        result = _time_forward(name, x_flat, weight, rows, hidden, device)
        result.update(
            {
                "input_shape": list(x.shape),
                "flat_shape": list(x_flat.shape),
                "flat_stride": list(x_flat.stride()),
                "zero_copy_flatten": x_flat.data_ptr() == x.data_ptr(),
                "untouched_storage_sentinel": torch.equal(base.detach(), base_snapshot),
            }
        )
        results.append(result)
    return results


def _autograd_case(device) -> dict:
    torch.manual_seed(749)
    rows, hidden, padding = 513, 512, 128
    base = torch.randn((rows, hidden + padding), device=device, dtype=torch.bfloat16)
    x = base[:, :hidden].requires_grad_(True)
    weight = torch.rand((hidden,), device=device, dtype=torch.bfloat16).requires_grad_(True)
    dout = torch.randn((rows, hidden), device=device, dtype=torch.bfloat16)
    base_snapshot = base.detach().clone()

    start = time.monotonic()
    output = rmsnorm_impl.rmsnorm(x, weight)
    torch.autograd.backward(output, dout)
    torch.cuda.synchronize(device)
    first_execution_seconds = time.monotonic() - start

    x_reference = x.detach().to(torch.float32).requires_grad_(True)
    weight_reference = weight.detach().to(torch.float32).requires_grad_(True)
    rstd_reference = torch.rsqrt(x_reference.square().mean(dim=1, keepdim=True) + EPS)
    output_reference = x_reference * rstd_reference * weight_reference
    dx_reference, dweight_reference = torch.autograd.grad(
        output_reference,
        (x_reference, weight_reference),
        dout.to(torch.float32),
    )
    output_max_abs = (output.to(torch.float32) - output_reference.detach()).abs().max().item()
    dx_max_abs = (x.grad.to(torch.float32) - dx_reference.detach()).abs().max().item()
    dweight_max_abs = (weight.grad.to(torch.float32) - dweight_reference.detach()).abs().max().item()
    output_close = torch.allclose(
        output.to(torch.float32), output_reference.detach(), rtol=AUTOGRAD_RTOL, atol=AUTOGRAD_ATOL
    )
    dx_close = torch.allclose(
        x.grad.to(torch.float32), dx_reference.detach(), rtol=AUTOGRAD_RTOL, atol=AUTOGRAD_ATOL
    )
    dweight_close = torch.allclose(
        weight.grad.to(torch.float32),
        dweight_reference.detach(),
        rtol=DWEIGHT_RTOL,
        atol=DWEIGHT_ATOL,
    )

    return {
        "case": "row_strided_autograd",
        "rows": rows,
        "hidden_size": hidden,
        "dtype": "bf16",
        "weight_dtype": "bf16",
        "eps": EPS,
        "output_max_abs": output_max_abs,
        "dx_max_abs": dx_max_abs,
        "dweight_max_abs": dweight_max_abs,
        "autograd_rtol": AUTOGRAD_RTOL,
        "autograd_atol": AUTOGRAD_ATOL,
        "dweight_rtol": DWEIGHT_RTOL,
        "dweight_atol": DWEIGHT_ATOL,
        "passed": (
            output_close
            and dx_close
            and dweight_close
        ),
        "first_execution_seconds": first_execution_seconds,
        "untouched_storage_sentinel": torch.equal(base.detach(), base_snapshot),
    }


def _refusal_cases(device) -> list[dict]:
    torch.manual_seed(749)
    hidden, rows = 512, 513
    weight = torch.rand((hidden,), device=device, dtype=torch.bfloat16)
    transposed = torch.randn((hidden, rows), device=device, dtype=torch.bfloat16).T
    permuted = torch.randn((2, rows // 2, hidden), device=device, dtype=torch.bfloat16).permute(1, 0, 2)

    results = []
    for name, view, expected_message in (
        ("transposed_last_dim", transposed, "unit-stride last dimension"),
        ("permuted_flatten_copy", permuted, "flattenable row-contiguous view"),
    ):
        started = time.monotonic()
        try:
            rmsnorm_impl.rmsnorm(view, weight)
        except ValueError as error:
            results.append(
                {
                    "case": name,
                    "refused": True,
                    "exception": type(error).__name__,
                    "message": str(error),
                    "expected_message": expected_message,
                    "passed": expected_message in str(error),
                    "elapsed_seconds": time.monotonic() - started,
                }
            )
        else:
            results.append(
                {
                    "case": name,
                    "refused": False,
                    "exception": None,
                    "expected_message": expected_message,
                    "passed": False,
                    "elapsed_seconds": time.monotonic() - started,
                }
            )
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    device = torch.device("cuda", torch.cuda.current_device())

    result = {
        "label": "plain RMSNorm input-layout admission on gfx950",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": {
            "repository": "https://github.com/amdpilot-org/FlyDSL.git",
            "commit": _git_commit(),
            "workdir": str(Path.cwd()),
        },
        "image": {
            "expected_local_image_id": "sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7",
            "container_id": _container_id(),
        },
        "python": {
            "executable": sys.executable,
            "version": sys.version,
            "platform": platform.platform(),
        },
        "native_paths": {
            "torch": torch.__file__,
            "torch_hip": getattr(torch.version, "hip", None),
            "triton": triton.__file__,
            "flydsl": flydsl.__file__,
            "flydsl_native_modules": _native_paths(),
        },
        "gpu": _gpu_identity(),
        "commands": [
            "PYTHONPATH=/tmp/flydsl-shim-j-8400c2d12044:/job/FlyDSL FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-8400c2d12044 FLYDSL_GPU_ARCH=gfx950 /opt/venv/bin/python reports/j-8400c2d12044/validate_rmsnorm_layouts.py reports/j-8400c2d12044/results.json",
            "PYTHONPATH=/tmp/flydsl-shim-j-8400c2d12044:/job/FlyDSL FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-8400c2d12044 FLYDSL_GPU_ARCH=gfx950 /opt/venv/bin/python -m pytest -q tests/kernels/test_rmsnorm.py::test_rmsnorm_forward_layout_admission tests/kernels/test_rmsnorm.py::test_rmsnorm_row_strided_autograd_and_refusal",
        ],
        "numerical_gates": {
            "forward_output_atol": OUTPUT_ATOL,
            "forward_rstd_atol": RSTD_ATOL,
            "autograd_rtol": AUTOGRAD_RTOL,
            "autograd_atol": AUTOGRAD_ATOL,
            "dweight_rtol": DWEIGHT_RTOL,
            "dweight_atol": DWEIGHT_ATOL,
        },
        "forward_results": _forward_cases(device),
        "autograd_result": _autograd_case(device),
        "refusal_results": _refusal_cases(device),
    }
    result["passed"] = all(
        case["passed"]
        for case in result["forward_results"] + [result["autograd_result"]] + result["refusal_results"]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
