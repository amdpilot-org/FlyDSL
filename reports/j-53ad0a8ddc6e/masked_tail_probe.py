#!/usr/bin/env python3
"""Independent raw-pointer vector-add probe with guarded output sentinels."""

import json

import torch

import flydsl.compiler as flyc
import flydsl.expr as fx


@flyc.kernel
def pointer_vec_add_kernel(
    a: fx.Pointer,
    b: fx.Pointer,
    out: fx.Pointer,
    n: fx.Int32,
):
    idx = fx.block_idx.x * fx.block_dim.x + fx.thread_idx.x
    if idx < n:
        out[idx] = a[idx] + b[idx]


@flyc.jit
def pointer_vec_add(
    a: fx.Pointer,
    b: fx.Pointer,
    out: fx.Pointer,
    n: fx.Int32,
    stream: fx.Stream = fx.Stream(None),
):
    block_dim = 256
    grid_x = (n + block_dim - 1) // block_dim
    pointer_vec_add_kernel(a, b, out, n).launch(
        grid=(grid_x, 1, 1), block=(block_dim, 1, 1), stream=stream
    )


def main() -> None:
    torch.manual_seed(5308)
    n = 4103
    guard = 37
    sentinel = -98765.5

    a = torch.randn(n, device="cuda", dtype=torch.float32)
    b = torch.randn(n, device="cuda", dtype=torch.float32)
    guarded_out = torch.full((n + 2 * guard,), sentinel, device="cuda", dtype=torch.float32)
    out = guarded_out[guard : guard + n]
    stream = torch.cuda.Stream()

    # The output pointer deliberately points inside a larger allocation. Any write
    # outside [0, n) changes one of the sentinel guard regions.
    pointer_vec_add(
        flyc.from_c_void_p(fx.Float32, a.data_ptr()),
        flyc.from_c_void_p(fx.Float32, b.data_ptr()),
        flyc.from_c_void_p(fx.Float32, out.data_ptr()),
        n,
        stream=stream,
    )
    torch.cuda.synchronize()

    reference = torch.add(a, b)
    delta = (out - reference).abs()
    prefix_untouched = bool(torch.eq(guarded_out[:guard], sentinel).all().item())
    suffix_untouched = bool(torch.eq(guarded_out[guard + n :], sentinel).all().item())
    measurements = {
        "length": n,
        "power_of_two": n > 0 and (n & (n - 1)) == 0,
        "block_dim": 256,
        "tail_lanes": n % 256,
        "guard_elements_each_side": guard,
        "sentinel": sentinel,
        "max_abs_error": delta.max().item(),
        "mean_abs_error": delta.mean().item(),
        "mismatch_count_at_1e-5": int((delta > 1e-5).sum().item()),
        "prefix_sentinel_untouched": prefix_untouched,
        "suffix_sentinel_untouched": suffix_untouched,
        "gpu_name": torch.cuda.get_device_name(0),
        "gpu_count": torch.cuda.device_count(),
    }
    print(json.dumps(measurements, indent=2, sort_keys=True))

    assert measurements["power_of_two"] is False
    assert measurements["tail_lanes"] != 0
    assert measurements["max_abs_error"] < 1e-5
    assert prefix_untouched and suffix_untouched


if __name__ == "__main__":
    main()
