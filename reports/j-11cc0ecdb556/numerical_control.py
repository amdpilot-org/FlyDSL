#!/usr/bin/env python3
"""Independent GPU numerical control for the FlyDSL pointer vec-add test."""

import json

import torch


def main() -> None:
    torch.manual_seed(20260912)
    device = torch.device("cuda", 0)
    size = 4099
    a = torch.randn(size, device=device, dtype=torch.float32)
    b = torch.randn(size, device=device, dtype=torch.float32)
    gpu_sum = a + b
    cpu_reference = a.cpu().to(torch.float64) + b.cpu().to(torch.float64)
    max_abs_error = (gpu_sum.cpu().to(torch.float64) - cpu_reference).abs().max().item()
    result = {
        "device_count": torch.cuda.device_count(),
        "device_index": torch.cuda.current_device(),
        "device_name": torch.cuda.get_device_name(device),
        "size": size,
        "dtype": str(gpu_sum.dtype),
        "max_abs_error_vs_cpu_float64": max_abs_error,
        "finite": bool(torch.isfinite(gpu_sum).all().item()),
        "checksum": float(gpu_sum.sum(dtype=torch.float64).item()),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["finite"] or max_abs_error > 1e-5:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
