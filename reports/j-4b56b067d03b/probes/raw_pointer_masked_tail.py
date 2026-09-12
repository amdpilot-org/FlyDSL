#!/usr/bin/env python3

"""Deterministic GPU control for raw pointers and masked vector-add tails."""

import json

import torch

import flydsl.compiler as flyc
import flydsl.expr as fx


BLOCK_SIZE = 256
SENTINEL = -12345.0
SIZES = (1, 255, 257, 4099)


@flyc.kernel
def masked_raw_pointer_vec_add_kernel(
    lhs: fx.Pointer,
    rhs: fx.Pointer,
    out: fx.Pointer,
    n: fx.Int32,
):
    index = fx.block_idx.x * fx.block_dim.x + fx.thread_idx.x
    if index < n:
        out[index] = lhs[index] + rhs[index]


@flyc.jit
def masked_raw_pointer_vec_add(
    lhs: fx.Pointer,
    rhs: fx.Pointer,
    out: fx.Pointer,
    n: fx.Int32,
    stream: fx.Stream = fx.Stream(None),
):
    grid_x = (n + BLOCK_SIZE - 1) // BLOCK_SIZE
    masked_raw_pointer_vec_add_kernel(lhs, rhs, out, n).launch(
        grid=(grid_x, 1, 1),
        block=(BLOCK_SIZE, 1, 1),
        stream=stream,
    )


def run_case(size: int) -> dict:
    padded_size = ((size + BLOCK_SIZE - 1) // BLOCK_SIZE) * BLOCK_SIZE
    indexes = torch.arange(padded_size, device="cuda", dtype=torch.float32)
    lhs = indexes * 0.25 - 17.0
    rhs = indexes * -0.5 + 3.0
    out = torch.full((padded_size,), SENTINEL, device="cuda", dtype=torch.float32)

    masked_raw_pointer_vec_add(
        flyc.from_c_void_p(fx.Float32, lhs.data_ptr()),
        flyc.from_c_void_p(fx.Float32, rhs.data_ptr()),
        flyc.from_c_void_p(fx.Float32, out.data_ptr()),
        size,
        stream=torch.cuda.current_stream(),
    )
    torch.cuda.synchronize()

    active_error = (out[:size] - (lhs[:size] + rhs[:size])).abs().max().item()
    tail_unchanged = bool(torch.all(out[size:] == SENTINEL).item())
    assert active_error == 0.0, (size, active_error)
    assert tail_unchanged, size
    return {
        "size": size,
        "padded_size": padded_size,
        "active_max_abs_error": active_error,
        "tail_elements": padded_size - size,
        "tail_sentinel_unchanged": tail_unchanged,
    }


def main() -> None:
    assert torch.cuda.is_available(), "ROCm GPU is unavailable"
    properties = torch.cuda.get_device_properties(torch.cuda.current_device())
    result = {
        "control": "deterministic raw-pointer vector add with masked tails",
        "device": torch.cuda.get_device_name(torch.cuda.current_device()),
        "device_count": torch.cuda.device_count(),
        "gcn_arch_name": getattr(properties, "gcnArchName", None),
        "torch_version": torch.__version__,
        "hip_version": torch.version.hip,
        "cases": [run_case(size) for size in SIZES],
        "result": "passed",
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
