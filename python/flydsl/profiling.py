# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""Reusable GPU event timing for FlyDSL kernels."""

import statistics
from typing import Callable, Optional, Sequence, Union

__all__ = ["do_bench"]

_BENCH_MAX_BATCHES = 5
_BENCH_BACKLOG_CYCLES = 20_000_000


def _get_torch():
    """Import PyTorch lazily so ordinary FlyDSL imports stay lightweight."""
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("GPU profiling requires PyTorch with CUDA or HIP support") from exc
    if not torch.cuda.is_available():
        raise RuntimeError("GPU profiling requires an available CUDA or HIP device")
    return torch


def _bench_batch_sizes(rep: int) -> list[int]:
    """Split ``rep`` calls into a few non-empty timing windows."""
    if type(rep) is not int or rep <= 0:
        raise ValueError(f"rep must be a positive integer, got {rep!r}")
    batches = min(_BENCH_MAX_BATCHES, rep)
    base, extra = divmod(rep, batches)
    return [base + (index < extra) for index in range(batches)]



def do_bench(
    fn: Callable[[], object],
    warmup: int = 5,
    rep: int = 25,
    quantiles: Optional[Sequence[float]] = None,
) -> Union[float, list[float]]:
    """Benchmark current-stream GPU work without timing a host-starved launch.

    A fresh event pair around every launch on an empty stream can over-read
    short kernels because the GPU may execute the start event before the host
    submits the kernel. This helper first queues a same-stream GPU sleep, then
    submits a batch of launches between one event pair while that backlog is
    executing. The sleep is outside the timed interval but gives the host time
    to enqueue the complete batch. Several batch averages are summarized by
    their median.

    ``warmup`` and ``rep`` are iteration counts. Timings are returned in
    milliseconds. By default the median batch average is returned; a non-empty
    ``quantiles`` sequence returns the corresponding sorted batch averages.
    ``fn`` must enqueue asynchronous work on PyTorch's current CUDA/HIP stream
    and must not synchronize internally. The helper synchronizes once after
    warmup and once after each measured batch.
    """
    if type(warmup) is not int or warmup < 0:
        raise ValueError(f"warmup must be a non-negative integer, got {warmup!r}")
    if quantiles is not None and any(not 0.0 <= quantile <= 1.0 for quantile in quantiles):
        raise ValueError("quantiles must be between 0 and 1")

    batch_sizes = _bench_batch_sizes(rep)
    torch = _get_torch()
    sleep = getattr(torch.cuda, "_sleep", None)
    if not callable(sleep):
        raise RuntimeError("accurate short-kernel profiling requires torch.cuda._sleep for a GPU-side backlog")

    for _ in range(warmup):
        fn()
    torch.cuda.synchronize()

    times = []
    for calls in batch_sizes:
        sleep(_BENCH_BACKLOG_CYCLES)
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        start.record()
        for _ in range(calls):
            fn()
        end.record()
        end.synchronize()
        times.append(start.elapsed_time(end) / calls)

    times.sort()
    if quantiles:
        return [times[min(int(quantile * len(times)), len(times) - 1)] for quantile in quantiles]
    return statistics.median(times)
