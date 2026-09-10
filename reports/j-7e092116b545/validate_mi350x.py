#!/usr/bin/env python3

"""Validate flydsl.profiling.do_bench with a real elementwise GPU kernel."""

import json
import statistics

import torch

from flydsl.profiling import do_bench


def main() -> None:
    torch.manual_seed(304)
    element_count = 1 << 23
    left = torch.randn(element_count, device="cuda", dtype=torch.float32)
    right = torch.randn(element_count, device="cuda", dtype=torch.float32)
    output = torch.empty_like(left)
    stream = torch.cuda.current_stream()
    calls = 0

    def elementwise_add() -> None:
        nonlocal calls
        calls += 1
        torch.add(left, right, out=output)

    elementwise_add()
    torch.cuda.synchronize()
    expected = left + right
    assert torch.allclose(output, expected, rtol=1e-5, atol=1e-6)
    max_abs_diff = (output - expected).abs().max().item()
    calls = 0

    quantiles = [0.0, 0.25, 0.5, 0.75, 0.9, 1.0]
    reported_ms = do_bench(elementwise_add, warmup=5, rep=25, quantiles=quantiles)
    assert calls == 30
    torch.cuda.synchronize()
    assert torch.allclose(output, expected, rtol=1e-5, atol=1e-6)

    for _ in range(5):
        elementwise_add()
    torch.cuda.synchronize()
    direct_per_call_ms = []
    for _ in range(25):
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        start.record(stream)
        elementwise_add()
        end.record(stream)
        end.synchronize()
        direct_per_call_ms.append(start.elapsed_time(end))
    direct_per_call_ms.sort()

    direct_batch_ms = []
    for batch_calls in (5, 5, 5, 5, 5):
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        start.record(stream)
        for _ in range(batch_calls):
            elementwise_add()
        end.record(stream)
        end.synchronize()
        direct_batch_ms.append(start.elapsed_time(end) / batch_calls)
    direct_batch_ms.sort()

    bad = output.clone()
    bad[0] += 1.0
    try:
        assert torch.allclose(bad, expected, rtol=1e-5, atol=1e-6)
    except AssertionError:
        intentional_failure_caught = True
    else:
        intentional_failure_caught = False
    assert intentional_failure_caught

    reported_median_us = statistics.median(reported_ms) * 1e3
    direct_per_call_median_us = statistics.median(direct_per_call_ms) * 1e3
    direct_batch_median_us = statistics.median(direct_batch_ms) * 1e3
    result = {
        "gpu": torch.cuda.get_device_name(0),
        "capability": torch.cuda.get_device_capability(0),
        "torch": torch.__version__,
        "hip": torch.version.hip,
        "stream": str(stream),
        "elements": element_count,
        "dtype": str(left.dtype),
        "max_abs_diff": max_abs_diff,
        "post_benchmark_correct": torch.allclose(output, expected, rtol=1e-5, atol=1e-6),
        "intentional_numerical_failure_caught": intentional_failure_caught,
        "reported_quantiles_ms": reported_ms,
        "reported_quantiles_us": [value * 1e3 for value in reported_ms],
        "reported_median_us": reported_median_us,
        "direct_per_call_ms": direct_per_call_ms,
        "direct_per_call_us": [value * 1e3 for value in direct_per_call_ms],
        "direct_per_call_median_us": direct_per_call_median_us,
        "direct_batch_ms": direct_batch_ms,
        "direct_batch_us": [value * 1e3 for value in direct_batch_ms],
        "direct_batch_median_us": direct_batch_median_us,
        "ratio_reported_over_direct_per_call": reported_median_us / direct_per_call_median_us,
        "ratio_reported_over_direct_batch": reported_median_us / direct_batch_median_us,
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
