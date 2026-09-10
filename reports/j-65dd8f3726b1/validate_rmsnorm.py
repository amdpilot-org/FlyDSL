#!/usr/bin/env python3
"""Focused gfx950 validation for the plain FlyDSL RMSNorm contract."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

import torch

import flydsl
from flydsl.runtime.device import get_rocm_arch
from kernels.norm import rmsnorm_kernel as rmsnorm_impl


EPS = 1e-5
M = 512
HIDDEN_SIZES = (512, 4096, 4097, 8191, 8192)
DTYPES = ("bf16", "f16")

TOLERANCES = {
    "f16": {"rtol": 3e-2, "atol": 3e-2},
    "bf16": {"rtol": 1e-1, "atol": 2e-1},
}
WEIGHT_GRAD_TOLERANCE = {"rtol": 5e-3, "atol": 5e-2}
RSTD_TOLERANCE = {"rtol": 0.0, "atol": 1e-3}


def _torch_dtype(name: str) -> torch.dtype:
    return {"bf16": torch.bfloat16, "f16": torch.float16}[name]


def _max_abs_error(actual: torch.Tensor, expected: torch.Tensor) -> float:
    return (actual.detach().float() - expected.detach().float()).abs().max().item()


def _assert_close(actual: torch.Tensor, expected: torch.Tensor, *, rtol: float, atol: float) -> None:
    torch.testing.assert_close(actual.detach().float(), expected.detach().float(), rtol=rtol, atol=atol)


def _native_paths() -> list[str]:
    package_root = Path(flydsl.__file__).resolve().parent
    return sorted(str(path) for path in package_root.rglob("*.so"))


def _validate_case(dtype_name: str, hidden_size: int, device: torch.device) -> dict:
    dtype = _torch_dtype(dtype_name)
    torch.manual_seed(42 + hidden_size + (0 if dtype_name == "bf16" else 1000))

    x = torch.randn((M, hidden_size), device=device, dtype=dtype, requires_grad=True)
    weight = torch.rand((hidden_size,), device=device, dtype=torch.float32, requires_grad=True)
    dout = torch.randn_like(x)

    x_reference = x.detach().clone().float().requires_grad_(True)
    weight_reference = weight.detach().clone().requires_grad_(True)
    rstd_reference = torch.rsqrt(
        x_reference.square().mean(dim=1, keepdim=True) + EPS
    )
    out_reference = x_reference * rstd_reference * weight_reference
    dsource_reference, dweight_reference = torch.autograd.grad(
        (out_reference,),
        (x_reference, weight_reference),
        (dout.detach().float(),),
    )

    default_stream = torch.cuda.default_stream(device)
    side_stream = torch.cuda.Stream(device=device)
    assert side_stream != default_stream

    dtype_str = rmsnorm_impl._torch_dtype_to_str(dtype)
    weight_dtype_str = rmsnorm_impl._torch_dtype_to_str(weight.dtype)
    forward_key = (
        hidden_size,
        dtype_str,
        weight_dtype_str,
        True,
        float(EPS),
        device,
    )
    backward_path, num_programs = rmsnorm_impl._select_rmsnorm_bwd_config(
        M, hidden_size, dtype_str, device
    )
    backward_key = (
        backward_path,
        hidden_size,
        dtype_str,
        weight_dtype_str,
        num_programs,
        device,
    )

    forward_cache_size_before = len(rmsnorm_impl._FWD_CACHE)
    backward_cache_size_before = len(rmsnorm_impl._BWD_CACHE)

    with torch.cuda.stream(side_stream):
        current_stream = torch.cuda.current_stream(device)
        assert current_stream == side_stream
        out_probe, rstd = rmsnorm_impl.rmsnorm_fwd(
            x.detach(), weight.detach(), eps=EPS, store_rstd=True
        )
        out = rmsnorm_impl.rmsnorm(x, weight, eps=EPS)
        out.backward(dout)

    forward_launcher = rmsnorm_impl._FWD_CACHE[forward_key]
    forward_compiled = forward_launcher._cf
    backward_launcher = rmsnorm_impl._BWD_CACHE[backward_key]
    backward_compiled = backward_launcher._cf

    with torch.cuda.stream(side_stream):
        warm_out = rmsnorm_impl.rmsnorm(x, weight, eps=EPS)
        warm_out.backward(dout)

    side_stream.synchronize()
    torch.cuda.synchronize(device)

    assert rmsnorm_impl._FWD_CACHE[forward_key] is forward_launcher
    assert rmsnorm_impl._FWD_CACHE[forward_key]._cf is forward_compiled
    assert rmsnorm_impl._BWD_CACHE[backward_key] is backward_launcher
    assert rmsnorm_impl._BWD_CACHE[backward_key]._cf is backward_compiled

    tolerance = TOLERANCES[dtype_name]
    _assert_close(out, out_reference, **tolerance)
    _assert_close(warm_out, out_reference, **tolerance)
    _assert_close(
        rstd,
        rstd_reference.squeeze(1),
        **RSTD_TOLERANCE,
    )
    _assert_close(x.grad, dsource_reference, **tolerance)
    _assert_close(weight.grad, dweight_reference, **WEIGHT_GRAD_TOLERANCE)

    result = {
        "dtype": dtype_name,
        "M": M,
        "N": hidden_size,
        "weight_dtype": "f32",
        "backward_path": backward_path,
        "num_programs": num_programs,
        "non_default_stream": True,
        "default_stream_raw": default_stream.cuda_stream,
        "execution_stream_raw": side_stream.cuda_stream,
        "forward_cache_reused": True,
        "backward_cache_reused": True,
        "forward_cache_size_before": forward_cache_size_before,
        "forward_cache_size_after": len(rmsnorm_impl._FWD_CACHE),
        "backward_cache_size_before": backward_cache_size_before,
        "backward_cache_size_after": len(rmsnorm_impl._BWD_CACHE),
        "tolerances": {
            "output_and_x_grad": tolerance,
            "weight_grad": WEIGHT_GRAD_TOLERANCE,
            "rstd": RSTD_TOLERANCE,
        },
        "max_abs_errors": {
            "output": _max_abs_error(out, out_reference),
            "rstd": _max_abs_error(rstd, rstd_reference.squeeze(1)),
            "x_grad": _max_abs_error(x.grad, dsource_reference),
            "weight_grad": _max_abs_error(weight.grad, dweight_reference),
        },
        "passed": True,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise SystemExit("CUDA/ROCm device is unavailable")
    if torch.cuda.device_count() != 1:
        raise SystemExit(f"expected one assigned GPU, found {torch.cuda.device_count()}")

    device = torch.device("cuda", torch.cuda.current_device())
    properties = torch.cuda.get_device_properties(device)
    arch = str(get_rocm_arch())
    if arch != "gfx950":
        raise SystemExit(f"expected gfx950, found {arch}")

    results = []
    for dtype_name in DTYPES:
        for hidden_size in HIDDEN_SIZES:
            case = _validate_case(dtype_name, hidden_size, device)
            results.append(case)
            print(
                f"PASS {dtype_name} M={M} N={hidden_size} "
                f"path={case['backward_path']} errors={case['max_abs_errors']}",
                flush=True,
            )

    report = {
        "passed": all(case["passed"] for case in results),
        "scope": {
            "operation": "plain FlyDSL RMSNorm",
            "input_dtypes": DTYPES,
            "weight_dtype": "f32",
            "M": M,
            "hidden_sizes": HIDDEN_SIZES,
            "eps": EPS,
            "autograd_reference": "independent Torch FP32 autograd",
            "non_default_current_stream": True,
            "warm_cache_reuse": True,
        },
        "environment": {
            "python": sys.executable,
            "python_version": sys.version,
            "platform": platform.platform(),
            "torch": torch.__version__,
            "torch_path": torch.__file__,
            "flydsl": flydsl.__version__,
            "flydsl_path": flydsl.__file__,
            "flydsl_native_paths": _native_paths(),
            "gpu_name": properties.name,
            "gpu_arch": arch,
            "gpu_device_count": torch.cuda.device_count(),
            "gpu_uuid": getattr(properties, "uuid", None),
            "gpu_multi_processor_count": properties.multi_processor_count,
        },
        "results": results,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2) + "\n")
    print(f"PASS {len(results)}/{len(results)} cases", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
