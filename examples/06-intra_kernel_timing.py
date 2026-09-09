# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""Bounded per-block timing for a deliberately imbalanced copy kernel."""

import argparse
import json
import statistics
import time

import torch

import flydsl.compiler as flyc
import flydsl.expr as fx
from flydsl._mlir import ir
from flydsl._mlir.dialects import llvm


def read_block_clock():
    """Read the AMDGPU 64-bit real-time counter with a side-effecting inline asm."""
    return llvm.inline_asm(
        ir.IntegerType.get_signless(64),
        [],
        "s_memrealtime $0",
        "=s",
        has_side_effects=True,
    )


@flyc.kernel
def imbalanced_copy_kernel(
    Input: fx.Pointer,
    Output: fx.Pointer,
    Timings: fx.Pointer,
    work_multiplier: fx.Int32,
    block_dim: fx.Constexpr[int],
    grid_blocks: fx.Constexpr[int],
    instrument: fx.Constexpr[bool],
):
    bid = fx.block_idx.x
    tid = fx.thread_idx.x
    start_clock = fx.Uint64(0)

    if instrument:
        start_clock = read_block_clock()

    work_iters = (bid + 1) * work_multiplier
    for iteration in range(work_iters):
        offset = bid * block_dim + iteration * grid_blocks * block_dim + tid
        (Output + offset).store((Input + offset).load())

    if instrument:
        elapsed_clock = read_block_clock() - start_clock
        if tid == 0:
            (Timings + bid).store(elapsed_clock)


@flyc.jit
def imbalanced_copy(
    Input: fx.Pointer,
    Output: fx.Pointer,
    Timings: fx.Pointer,
    work_multiplier: fx.Int32,
    block_dim: fx.Constexpr[int],
    grid_blocks: fx.Constexpr[int],
    instrument: fx.Constexpr[bool],
    stream: fx.Stream = fx.Stream(None),
):
    imbalanced_copy_kernel(
        Input,
        Output,
        Timings,
        work_multiplier,
        block_dim,
        grid_blocks,
        instrument,
    ).launch(
        grid=(grid_blocks, 1, 1),
        block=(block_dim, 1, 1),
        stream=stream,
    )


def expected_output(input_tensor, work_multiplier, block_dim, grid_blocks):
    expected = torch.zeros_like(input_tensor)
    for block in range(grid_blocks):
        for iteration in range((block + 1) * work_multiplier):
            start = block * block_dim + iteration * grid_blocks * block_dim
            expected[start : start + block_dim] = input_tensor[start : start + block_dim]
    return expected


def median_event_us(launch, warmup, repetitions):
    stream = torch.cuda.Stream()
    samples = []
    sync_costs_us = []
    for _ in range(warmup):
        launch(stream)
    torch.cuda.synchronize()
    for _ in range(repetitions):
        start = torch.cuda.Event(enable_timing=True)
        stop = torch.cuda.Event(enable_timing=True)
        start.record(stream)
        launch(stream)
        stop.record(stream)
        before_sync = time.perf_counter_ns()
        stop.synchronize()
        sync_costs_us.append((time.perf_counter_ns() - before_sync) / 1000.0)
        samples.append(start.elapsed_time(stop) * 1000.0)
    return samples, statistics.median(sync_costs_us)


def run_case(work_multiplier, block_dim, grid_blocks, warmup, repetitions):
    element_count = grid_blocks * block_dim * grid_blocks * work_multiplier
    input_tensor = torch.arange(element_count, dtype=torch.int32, device="cuda")
    output_tensor = torch.zeros_like(input_tensor)
    timing_tensor = torch.zeros(grid_blocks, dtype=torch.int64, device="cuda")

    input_pointer = flyc.from_c_void_p(fx.Int32, input_tensor.data_ptr())
    output_pointer = flyc.from_c_void_p(fx.Int32, output_tensor.data_ptr())
    timing_pointer = flyc.from_c_void_p(fx.Int64, timing_tensor.data_ptr())

    def launch(stream, instrument):
        imbalanced_copy(
            input_pointer,
            output_pointer,
            timing_pointer,
            work_multiplier,
            block_dim,
            grid_blocks,
            instrument,
            stream=stream,
        )

    expected = expected_output(input_tensor, work_multiplier, block_dim, grid_blocks)

    launch(torch.cuda.Stream(), instrument=False)
    torch.cuda.synchronize()
    uninstrumented_exact = torch.equal(output_tensor, expected)

    output_tensor.zero_()
    timing_tensor.zero_()
    launch(torch.cuda.Stream(), instrument=True)
    torch.cuda.synchronize()
    instrumented_exact = torch.equal(output_tensor, expected)
    block_cycles = timing_tensor.cpu().tolist()

    uninstrumented_us, uninstrumented_sync_us = median_event_us(
        lambda stream: launch(stream, instrument=False), warmup, repetitions
    )
    instrumented_us, instrumented_sync_us = median_event_us(
        lambda stream: launch(stream, instrument=True), warmup, repetitions
    )

    uninstrumented_median = statistics.median(uninstrumented_us)
    instrumented_median = statistics.median(instrumented_us)
    event_overhead_estimate_us = instrumented_median - uninstrumented_median
    observed_clock_ghz = max(block_cycles) / statistics.median(instrumented_us) / 1000.0
    work_iterations = [(block + 1) * work_multiplier for block in range(grid_blocks)]
    if len(block_cycles) > 1:
        cycle_slope, cycle_intercept = statistics.linear_regression(work_iterations, block_cycles)
        cycle_intercept_us = cycle_intercept / (observed_clock_ghz * 1000.0)
    else:
        cycle_slope = None
        cycle_intercept = None
        cycle_intercept_us = None

    return {
        "work_multiplier": work_multiplier,
        "block_dim": block_dim,
        "grid_blocks": grid_blocks,
        "element_count": element_count,
        "uninstrumented_exact": uninstrumented_exact,
        "instrumented_exact": instrumented_exact,
        "block_cycles": block_cycles,
        "uninstrumented_event_us": uninstrumented_us,
        "instrumented_event_us": instrumented_us,
        "uninstrumented_median_us": uninstrumented_median,
        "instrumented_median_us": instrumented_median,
        "cycle_regression_slope_cycles_per_iteration": cycle_slope,
        "cycle_regression_intercept_cycles": cycle_intercept,
        "cycle_regression_intercept_us": cycle_intercept_us,
        "event_overhead_estimate_us": event_overhead_estimate_us,
        "uninstrumented_sync_median_us": uninstrumented_sync_us,
        "instrumented_sync_median_us": instrumented_sync_us,
        "observed_clock_ghz": observed_clock_ghz,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-multiplier", type=int, default=128)
    parser.add_argument("--block-dim", type=int, default=256)
    parser.add_argument("--grid-blocks", type=int, default=8)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--repetitions", type=int, default=30)
    args = parser.parse_args()

    result = run_case(
        args.work_multiplier,
        args.block_dim,
        args.grid_blocks,
        args.warmup,
        args.repetitions,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
