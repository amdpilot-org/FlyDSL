#!/usr/bin/env python3
"""Independent raw-pointer vector-add tail and output-canary probe."""

import json

import torch

import flydsl
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
    torch.manual_seed(614)
    n = 1009
    guard = 37
    sentinel = -123456.75

    a = torch.randn(n, device="cuda", dtype=torch.float32)
    b = torch.randn(n, device="cuda", dtype=torch.float32)
    storage = torch.full((n + 2 * guard,), sentinel, device="cuda", dtype=torch.float32)
    out = storage[guard : guard + n]
    stream = torch.cuda.Stream()

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
    prefix_untouched = bool(torch.eq(storage[:guard], sentinel).all().item())
    suffix_untouched = bool(torch.eq(storage[guard + n :], sentinel).all().item())
    result = {
        "case": "independent_masked_tail_pointer_vector_add",
        "length": n,
        "power_of_two": (n & (n - 1)) == 0,
        "block_dim": 256,
        "grid_x": (n + 255) // 256,
        "tail_lanes": 256 - (n % 256),
        "guard_elements_each_side": guard,
        "sentinel_value": sentinel,
        "prefix_sentinel_untouched": prefix_untouched,
        "suffix_sentinel_untouched": suffix_untouched,
        "max_abs_error": delta.max().item(),
        "mean_abs_error": delta.mean().item(),
        "mismatch_count_at_rtol_1e-6_atol_1e-6": int(
            (~torch.isclose(out, reference, rtol=1e-6, atol=1e-6)).sum().item()
        ),
        "torch_reference": "torch.add(a, b)",
        "gpu_name": torch.cuda.get_device_name(0),
        "gpu_arch": torch.cuda.get_device_properties(0).gcnArchName,
        "visible_device_count": torch.cuda.device_count(),
        "flydsl_source_import": flydsl.__file__,
        "flydsl_expr_import": fx.__file__,
        "torch_import": torch.__file__,
        "torch_version": torch.__version__,
        "torch_hip_version": torch.version.hip,
    }
    print(json.dumps(result, indent=2, sort_keys=True))

    assert not result["power_of_two"]
    assert result["tail_lanes"] > 0
    assert prefix_untouched and suffix_untouched
    assert result["mismatch_count_at_rtol_1e-6_atol_1e-6"] == 0


if __name__ == "__main__":
    main()
