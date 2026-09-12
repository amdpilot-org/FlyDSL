#!/usr/bin/env python3
"""Independent deterministic GPU control for raw-pointer FlyDSL vector add."""

import json

import torch

import flydsl.compiler as flyc
import flydsl.expr as fx


@flyc.kernel
def control_vec_add_kernel(
    a: fx.Pointer,
    b: fx.Pointer,
    c: fx.Pointer,
    n: fx.Int32,
):
    idx = fx.block_idx.x * fx.block_dim.x + fx.thread_idx.x
    if idx < n:
        c[idx] = a[idx] + b[idx]


@flyc.jit
def control_vec_add(
    a: fx.Pointer,
    b: fx.Pointer,
    c: fx.Pointer,
    n: fx.Int32,
    stream: fx.Stream = fx.Stream(None),
):
    block_dim = 256
    grid_x = (n + block_dim - 1) // block_dim
    control_vec_add_kernel(a, b, c, n).launch(
        grid=(grid_x, 1, 1), block=(block_dim, 1, 1), stream=stream
    )


def main() -> None:
    size = 1031
    host_index = torch.arange(size, dtype=torch.float32)
    expected = torch.sin(host_index * 0.03125) + (host_index.remainder(17) - 8.0) * 0.125
    a_dev = torch.sin(host_index * 0.03125).cuda()
    b_dev = ((host_index.remainder(17) - 8.0) * 0.125).cuda()
    c_dev = torch.full((size,), float("nan"), device="cuda", dtype=torch.float32)
    stream = torch.cuda.Stream()

    control_vec_add(
        flyc.from_c_void_p(fx.Float32, a_dev.data_ptr()),
        flyc.from_c_void_p(fx.Float32, b_dev.data_ptr()),
        flyc.from_c_void_p(fx.Float32, c_dev.data_ptr()),
        size,
        stream=stream,
    )
    torch.cuda.synchronize()
    actual = c_dev.cpu()
    max_abs_error = (actual - expected).abs().max().item()
    all_finite = bool(torch.isfinite(actual).all().item())
    passed = all_finite and max_abs_error <= 1.0e-6
    print(
        json.dumps(
            {
                "device": torch.cuda.get_device_name(0),
                "size": size,
                "max_abs_error": max_abs_error,
                "all_finite": all_finite,
                "first_outputs": actual[:5].tolist(),
                "last_outputs": actual[-5:].tolist(),
                "passed": passed,
            },
            indent=2,
        )
    )
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
