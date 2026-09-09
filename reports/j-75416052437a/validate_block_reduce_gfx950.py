#!/usr/bin/env python3
"""Focused MI350X/gfx950 validation for flydsl.extension.coop.BlockReduce."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import torch
import flydsl
import flydsl.compiler as flyc
import flydsl.expr as fx


ALGORITHMS = (
    fx.coop.BlockReduceAlgorithm.WARP_REDUCTIONS,
    fx.coop.BlockReduceAlgorithm.RAKING,
)
TYPES = {
    "float16": (fx.Float16, torch.float16),
    "bfloat16": (fx.BFloat16, torch.bfloat16),
    "float32": (fx.Float32, torch.float32),
    "float64": (fx.Float64, torch.float64),
}
GATES = {
    "float32": {"rtol": 1e-5, "atol": 1e-3},
    "float64": {"rtol": 1e-12, "atol": 1e-9},
    "float16": {"rtol": 0.1, "atol": 0.1},
    "bfloat16": {"rtol": 0.1, "atol": 0.1},
}


def linear_tid(block_size):
    dim_x, dim_y, _ = block_size
    tid = fx.thread_idx.x
    if dim_y > 1:
        tid = tid + fx.thread_idx.y * fx.Int32(dim_x)
    return tid


def make_launch(dtype, torch_dtype, block_size, algorithm, active_count):
    block_threads = math.prod(block_size)

    @flyc.kernel(known_block_size=list(block_size))
    def kernel(A: fx.Tensor, Out: fx.Tensor):
        block_reduce = fx.coop.BlockReduce[dtype, block_size, algorithm]
        storage = fx.SharedAllocator().allocate(block_reduce.SharedStorage).peek()
        tid = linear_tid(block_size)
        value = (tid < fx.Int32(active_count)).select(A[tid], dtype(0))
        Out[tid] = block_reduce(value, fx.ReductionOp.ADD, storage=storage)

    @flyc.jit
    def launch(A: fx.Tensor, Out: fx.Tensor, stream: fx.Stream = fx.Stream(None)):
        kernel(A, Out).launch(grid=(1, 1, 1), block=block_size, stream=stream)

    return launch, block_threads, torch_dtype


def adversarial_values(active_count, torch_dtype):
    device = "cuda"
    values = torch.zeros(active_count, dtype=torch_dtype, device=device)
    if active_count:
        values[0] = torch.finfo(torch_dtype).max
    if active_count > 1:
        values[1:] = -torch.finfo(torch_dtype).max / (2 * active_count)
    return values


def cancellation_values(active_count, torch_dtype):
    device = "cuda"
    values = torch.zeros(active_count, dtype=torch_dtype, device=device)
    if active_count:
        values[0] = 1
    if active_count > 1:
        values[1] = -1
    if active_count > 2:
        values[2:] = torch.finfo(torch_dtype).tiny
    return values


def run_case(name, dtype, torch_dtype, block_size, algorithm, active_count, values):
    launch, block_threads, _ = make_launch(dtype, torch_dtype, block_size, algorithm, active_count)
    device_values = torch.ones(block_threads, dtype=torch_dtype, device="cuda")
    device_values[:active_count] = values
    output = torch.zeros(block_threads, dtype=torch_dtype, device="cuda")
    stream = torch.cuda.Stream()
    launch(device_values, output, stream=stream)
    stream.synchronize()

    reference = device_values[:active_count].sum()
    reference64 = device_values[:active_count].to(torch.float64).sum()
    got = output[0].item()
    expected = reference.item()
    expected64 = reference64.item()
    absolute_error = abs(got - expected)
    relative_error = absolute_error / abs(expected) if expected else absolute_error
    gate = GATES[name]
    passed = (
        torch.equal(output, output[0].expand(block_threads))
        and math.isfinite(got)
        and math.isfinite(expected)
        and (
            got == expected
            if gate["rtol"] == 0
            else absolute_error <= gate["atol"] + gate["rtol"] * abs(expected)
        )
    )
    return {
        "case": name,
        "algorithm": algorithm.name,
        "block_size": list(block_size),
        "block_threads": block_threads,
        "active_threads": active_count,
        "waves": math.ceil(block_threads / 64),
        "all_threads_equal": bool(torch.equal(output, output[0].expand(block_threads))),
        "flydsl_sum": got,
        "torch_sum": expected,
        "torch_float64_sum": expected64,
        "absolute_error": absolute_error,
        "relative_error": relative_error,
        "gate": gate,
        "passed": bool(passed),
    }


def time_case(dtype, torch_dtype, block_size, algorithm, warmup, iterations):
    block_threads = math.prod(block_size)
    launch, _, _ = make_launch(dtype, torch_dtype, block_size, algorithm, block_threads)
    values = torch.randn(block_threads, dtype=torch.float32, device="cuda").to(torch_dtype)
    output = torch.zeros(block_threads, dtype=torch_dtype, device="cuda")
    stream = torch.cuda.Stream()
    for _ in range(warmup):
        launch(values, output, stream=stream)
    stream.synchronize()
    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    start.record(stream)
    for _ in range(iterations):
        launch(values, output, stream=stream)
    end.record(stream)
    end.synchronize()
    total_ms = start.elapsed_time(end)
    return {
        "algorithm": algorithm.name,
        "block_size": list(block_size),
        "block_threads": block_threads,
        "waves": math.ceil(block_threads / 64),
        "warmup": warmup,
        "iterations": iterations,
        "total_ms": total_ms,
        "mean_us_per_launch": total_ms * 1000 / iterations,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("reports/j-75416052437a/results.json"))
    parser.add_argument("--timing-warmup", type=int, default=50)
    parser.add_argument("--timing-iterations", type=int, default=500)
    args = parser.parse_args()

    torch.manual_seed(348)
    correctness = []
    for type_name, (dtype, torch_dtype) in TYPES.items():
        for algorithm in ALGORITHMS:
            for block_threads in (64, 128, 256, 1024):
                active_count = block_threads
                values = torch.randn(active_count, dtype=torch_dtype, device="cuda")
                correctness.append(
                    run_case(
                        type_name,
                        dtype,
                        torch_dtype,
                        (block_threads, 1, 1),
                        algorithm,
                        active_count,
                        values,
                    )
                )

    tail_cases = (
        (64, 1),
        (64, 33),
        (64, 63),
        (128, 65),
        (128, 127),
        (256, 129),
        (256, 200),
        (1024, 1023),
    )
    for block_threads, active_count in tail_cases:
        for algorithm in ALGORITHMS:
            values = torch.randn(active_count, dtype=torch.float32, device="cuda")
            correctness.append(
                run_case(
                    "float32",
                    fx.Float32,
                    torch.float32,
                    (block_threads, 1, 1),
                    algorithm,
                    active_count,
                    values,
                )
            )

    adversarial_blocks = ((64, 63), (128, 127), (256, 200))
    for type_name, (dtype, torch_dtype) in TYPES.items():
        for block_threads, active_count in adversarial_blocks:
            for algorithm in ALGORITHMS:
                for case_name, values in (
                    ("large_mixed_sign", adversarial_values(active_count, torch_dtype)),
                    ("cancellation", cancellation_values(active_count, torch_dtype)),
                    ("random_mixed_sign", torch.randn(active_count, dtype=torch_dtype, device="cuda")),
                ):
                    result = run_case(
                        type_name,
                        dtype,
                        torch_dtype,
                        (block_threads, 1, 1),
                        algorithm,
                        active_count,
                        values,
                    )
                    result["adversarial_case"] = case_name
                    correctness.append(result)

    timing = []
    for block_threads in (64, 128, 256, 1024):
        for algorithm in ALGORITHMS:
            timing.append(
                time_case(
                    fx.Float32,
                    torch.float32,
                    (block_threads, 1, 1),
                    algorithm,
                    args.timing_warmup,
                    args.timing_iterations,
                )
            )

    pow2_rejection = []
    for algorithm in ALGORITHMS:
        try:
            fx.coop.BlockReduce[fx.Float32, 63, algorithm]
        except ValueError as error:
            pow2_rejection.append({"algorithm": algorithm.name, "error": str(error)})
        else:
            pow2_rejection.append({"algorithm": algorithm.name, "error": None})

    result = {
        "gpu_name": torch.cuda.get_device_name(0),
        "gpu_capability": list(torch.cuda.get_device_capability(0)),
        "wave_threads": int(fx.num_warp_threads()),
        "flydsl_version": flydsl.__version__,
        "torch_version": torch.__version__,
        "correctness": correctness,
        "timing": timing,
        "non_power_of_two_block_rejection": pow2_rejection,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    failed = [case for case in correctness if not case["passed"]]
    print(json.dumps(result, indent=2))
    if failed:
        raise SystemExit(f"{len(failed)} correctness cases failed")


if __name__ == "__main__":
    main()
