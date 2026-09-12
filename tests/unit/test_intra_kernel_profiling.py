#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""ROCm intra-kernel timestamp regression and real-kernel demonstration."""

import statistics

import pytest

import flydsl.compiler as flyc
import flydsl.expr as fx

try:
    import torch
except ImportError:
    torch = None

pytestmark = [pytest.mark.l2_device, pytest.mark.rocm_lower]

if torch is None or not torch.cuda.is_available():
    pytest.skip("ROCm device not available", allow_module_level=True)


@flyc.kernel
def profiled_vector_add_kernel(
    a: fx.Pointer,
    b: fx.Pointer,
    out: fx.Pointer,
    timestamps: fx.Pointer,
    n: fx.Int32,
    instrument: fx.Constexpr[bool],
):
    tid = fx.thread_idx.x
    bid = fx.block_idx.x
    idx = bid * fx.block_dim.x + tid

    if instrument and tid == 0:
        fx.rocdl.record_timestamp(timestamps, bid * 2)

    if idx < n:
        out[idx] = a[idx] + b[idx]

    # The barrier makes completion of the workgroup's vector-add stage the
    # boundary measured by lane zero.  record_timestamp itself is not a fence.
    if instrument:
        fx.barrier()
        if tid == 0:
            fx.rocdl.record_timestamp(timestamps, bid * 2 + 1)


@flyc.jit
def profiled_vector_add(
    a: fx.Pointer,
    b: fx.Pointer,
    out: fx.Pointer,
    timestamps: fx.Pointer,
    n: fx.Int32,
    instrument: fx.Constexpr[bool],
    stream: fx.Stream = fx.Stream(None),
):
    block = 256
    profiled_vector_add_kernel(a, b, out, timestamps, n, instrument).launch(
        grid=((n + block - 1) // block, 1, 1), block=(block, 1, 1), stream=stream
    )


def _ptr(dtype, tensor):
    return flyc.from_c_void_p(dtype, tensor.data_ptr())


def test_profiled_vector_add_records_ordered_stage_times():
    n = 8192
    blocks = (n + 255) // 256
    torch.manual_seed(831)
    a = torch.randn(n, device="cuda", dtype=torch.float32)
    b = torch.randn_like(a)
    out = torch.empty_like(a)
    timestamps = torch.zeros(blocks * 2, device="cuda", dtype=torch.uint64)

    profiled_vector_add(
        _ptr(fx.Float32, a),
        _ptr(fx.Float32, b),
        _ptr(fx.Float32, out),
        _ptr(fx.Uint64, timestamps),
        n,
        True,
        stream=torch.cuda.current_stream(),
    )
    torch.cuda.synchronize()

    torch.testing.assert_close(out, a + b, rtol=0, atol=0)
    pairs = timestamps.cpu().view(torch.int64).reshape(blocks, 2)
    elapsed = pairs[:, 1] - pairs[:, 0]
    assert torch.all(pairs[:, 0] > 0)
    assert torch.all(elapsed > 0)
    print(
        "stage ticks:",
        f"min={elapsed.min().item()}",
        f"median={elapsed.median().item()}",
        f"max={elapsed.max().item()}",
    )


def test_profiling_is_opt_in_and_reports_launch_overhead():
    n = 8192
    blocks = (n + 255) // 256
    a = torch.randn(n, device="cuda", dtype=torch.float32)
    b = torch.randn_like(a)
    out = torch.empty_like(a)
    timestamps = torch.zeros(blocks * 2, device="cuda", dtype=torch.uint64)
    args = (
        _ptr(fx.Float32, a),
        _ptr(fx.Float32, b),
        _ptr(fx.Float32, out),
        _ptr(fx.Uint64, timestamps),
        n,
    )

    # Compile/warm both constexpr specializations before timing.
    for instrument in (False, True):
        for _ in range(10):
            profiled_vector_add(*args, instrument, stream=torch.cuda.current_stream())
        torch.cuda.synchronize()

    def measure(instrument):
        samples = []
        for _ in range(25):
            start = torch.cuda.Event(enable_timing=True)
            end = torch.cuda.Event(enable_timing=True)
            start.record()
            for _ in range(100):
                profiled_vector_add(*args, instrument, stream=torch.cuda.current_stream())
            end.record()
            end.synchronize()
            samples.append(start.elapsed_time(end) * 1000 / 100)
        return statistics.median(samples)

    plain_us = measure(False)
    profiled_us = measure(True)
    print(
        "launch median:",
        f"plain={plain_us:.3f}us",
        f"profiled={profiled_us:.3f}us",
        f"delta={profiled_us - plain_us:.3f}us",
        f"ratio={profiled_us / plain_us:.3f}x",
    )
    torch.testing.assert_close(out, a + b, rtol=0, atol=0)


def test_uninstrumented_specialization_preserves_vector_add():
    n = 4099
    blocks = (n + 255) // 256
    a = torch.randn(n, device="cuda", dtype=torch.float32)
    b = torch.randn_like(a)
    out = torch.empty_like(a)
    unused_timestamps = torch.zeros(blocks * 2, device="cuda", dtype=torch.uint64)
    profiled_vector_add(
        _ptr(fx.Float32, a),
        _ptr(fx.Float32, b),
        _ptr(fx.Float32, out),
        _ptr(fx.Uint64, unused_timestamps),
        n,
        False,
        stream=torch.cuda.current_stream(),
    )
    torch.cuda.synchronize()
    torch.testing.assert_close(out, a + b, rtol=0, atol=0)
    assert torch.count_nonzero(unused_timestamps).item() == 0
