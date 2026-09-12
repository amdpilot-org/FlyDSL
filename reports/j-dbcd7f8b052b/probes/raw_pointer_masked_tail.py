#!/usr/bin/env python3

"""Deterministic GPU control for raw pointers and a masked vector tail."""

import json

import torch

import flydsl.compiler as flyc
import flydsl.expr as fx


@flyc.kernel
def raw_pointer_masked_tail_kernel(
    a: fx.Pointer,
    b: fx.Pointer,
    c: fx.Pointer,
    n: fx.Int32,
):
    idx = fx.block_idx.x * fx.block_dim.x + fx.thread_idx.x
    if idx < n:
        c[idx] = a[idx] + b[idx]


@flyc.jit
def raw_pointer_masked_tail(
    a: fx.Pointer,
    b: fx.Pointer,
    c: fx.Pointer,
    n: fx.Int32,
    stream: fx.Stream = fx.Stream(None),
):
    block_dim = 256
    grid_x = (n + block_dim - 1) // block_dim
    raw_pointer_masked_tail_kernel(a, b, c, n).launch(
        grid=(grid_x, 1, 1), block=(block_dim, 1, 1), stream=stream
    )


def main() -> None:
    torch.manual_seed(0)
    logical_size = 1031
    block_dim = 256
    allocation_size = ((logical_size + block_dim - 1) // block_dim) * block_dim
    sentinel = -12345.0

    indices = torch.arange(allocation_size, device="cuda", dtype=torch.float32)
    a = indices * 0.25 - 7.0
    b = indices * -0.5 + 19.0
    c = torch.full_like(a, sentinel)

    raw_pointer_masked_tail(
        flyc.from_c_void_p(fx.Float32, a.data_ptr()),
        flyc.from_c_void_p(fx.Float32, b.data_ptr()),
        flyc.from_c_void_p(fx.Float32, c.data_ptr()),
        logical_size,
        stream=torch.cuda.Stream(),
    )
    torch.cuda.synchronize()

    expected = a[:logical_size] + b[:logical_size]
    max_abs_error = (c[:logical_size] - expected).abs().max().item()
    tail_unchanged = bool(torch.all(c[logical_size:] == sentinel).item())
    if max_abs_error != 0.0 or not tail_unchanged:
        raise AssertionError(
            f"control failed: max_abs_error={max_abs_error}, tail_unchanged={tail_unchanged}"
        )

    props = torch.cuda.get_device_properties(torch.cuda.current_device())
    print(
        json.dumps(
            {
                "allocation_size": allocation_size,
                "block_dim": block_dim,
                "device_index": torch.cuda.current_device(),
                "gpu_name": props.name,
                "logical_size": logical_size,
                "max_abs_error": max_abs_error,
                "status": "passed",
                "tail_elements": allocation_size - logical_size,
                "tail_unchanged": tail_unchanged,
                "torch_version": torch.__version__,
                "torch_hip_version": torch.version.hip,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
