#!/usr/bin/env python3
"""Measure intra-kernel per-block timing on one AMD gfx950 GPU."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any

import torch
import flydsl

import flydsl.compiler as flyc
import flydsl.expr as fx
from flydsl._mlir import ir
from flydsl._mlir.dialects import llvm


def read_memrealtime() -> fx.Int64:
    """Read gfx950's 64-bit s_memrealtime counter."""
    raw = llvm.inline_asm(
        ir.IntegerType.get_signless(64),
        [],
        "s_memrealtime $0\ns_waitcnt vmcnt(0)",
        "=s",
        has_side_effects=True,
    )
    return fx.as_dsl_value(raw)


@flyc.kernel
def unequal_work_kernel(
    In: fx.Tensor,
    Out: fx.Tensor,
    Timing: fx.Tensor,
    base_iters: fx.Int32,
    step_iters: fx.Int32,
    instrument: fx.Constexpr[bool],
):
    bid = fx.block_idx.x
    tid = fx.thread_idx.x
    g = bid * 128 + tid

    iterations = base_iters + step_iters * fx.Int32(bid)
    value = In[g]
    accumulator = value

    if fx.const_expr(instrument):
        start = read_memrealtime()

    for _ in range(iterations):
        accumulator = accumulator * fx.Float32(1.000001) + value

    if fx.const_expr(instrument):
        end = read_memrealtime()
        if tid == 0:
            Timing[bid * 2 + 0] = start
            Timing[bid * 2 + 1] = end

    Out[g] = accumulator


@flyc.jit
def unequal_work_launch(
    In: fx.Tensor,
    Out: fx.Tensor,
    Timing: fx.Tensor,
    base_iters: fx.Int32,
    step_iters: fx.Int32,
    blocks: fx.Constexpr[int],
    instrument: fx.Constexpr[bool],
    stream: fx.Stream = fx.Stream(None),
):
    unequal_work_kernel(
        In,
        Out,
        Timing,
        base_iters,
        step_iters,
        instrument,
    ).launch(
        grid=(blocks, 1, 1),
        block=(128, 1, 1),
        stream=stream.value,
    )


def median(values: list[float]) -> float:
    return statistics.median(values)


def event_times_ms(launch, warmup: int, runs: int, capture=None) -> list[float]:
    for _ in range(warmup):
        launch()
    torch.cuda.synchronize()

    times: list[float] = []
    for _ in range(runs):
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        start.record()
        launch()
        end.record()
        torch.cuda.synchronize()
        if capture is not None:
            capture()
        times.append(start.elapsed_time(end))
    return times


def tensor_checksum(tensor: torch.Tensor) -> str:
    return hashlib.sha256(tensor.detach().cpu().contiguous().numpy().tobytes()).hexdigest()


def timing_rows(timing: torch.Tensor, blocks: int) -> list[dict[str, int]]:
    values = timing.detach().cpu().tolist()
    return [
        {
            "block": block,
            "start": values[block * 2],
            "end": values[block * 2 + 1],
            "delta": values[block * 2 + 1] - values[block * 2],
        }
        for block in range(blocks)
    ]


def run_mode(
    *,
    blocks: int,
    threads: int,
    base_iters: int,
    step_iters: int,
    instrument: bool,
    warmup: int,
    runs: int,
) -> dict[str, Any]:
    elements = blocks * threads
    inp = torch.arange(elements, dtype=torch.float32, device="cuda")
    out = torch.zeros_like(inp)
    timing = torch.zeros(blocks * 2, dtype=torch.int64, device="cuda")

    t_inp = flyc.from_torch_tensor(inp).mark_layout_dynamic(leading_dim=0, divisibility=1)
    t_out = flyc.from_torch_tensor(out).mark_layout_dynamic(leading_dim=0, divisibility=1)
    t_timing = flyc.from_torch_tensor(timing).mark_layout_dynamic(leading_dim=0, divisibility=1)

    def launch():
        unequal_work_launch(
            t_inp,
            t_out,
            t_timing,
            fx.Int32(base_iters),
            fx.Int32(step_iters),
            blocks,
            instrument,
        )

    timing_history: list[list[dict[str, int]]] = []

    def capture_timing():
        timing_history.append(timing_rows(timing, blocks))

    times = event_times_ms(launch, warmup, runs, capture=capture_timing)
    torch.cuda.synchronize()

    median_deltas = []
    for block in range(blocks):
        median_deltas.append(
            int(median([rows[block]["delta"] for rows in timing_history]))
        )

    return {
        "instrumented": instrument,
        "blocks": blocks,
        "threads_per_block": threads,
        "base_iters": base_iters,
        "step_iters": step_iters,
        "event_times_ms": times,
        "event_median_ms": median(times),
        "event_min_ms": min(times),
        "event_max_ms": max(times),
        "timing_rows": timing_rows(timing, blocks),
        "timing_median_deltas": median_deltas,
        "output_checksum_sha256": tensor_checksum(out),
        "output_tensor": out,
        "output_sum": float(out.detach().cpu().sum()),
        "output_max_abs": float(out.detach().cpu().abs().max()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blocks", type=int, default=8)
    parser.add_argument("--threads", type=int, default=128)
    parser.add_argument("--base-iters", type=int, default=50_000)
    parser.add_argument("--step-iters", type=int, default=50_000)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument("--zero-runs", type=int, default=100)
    parser.add_argument("--cal-iters", type=int, default=1_000_000)
    parser.add_argument("--json-out", type=Path, default=Path("timing_results.json"))
    args = parser.parse_args()

    if args.threads != 128:
        raise SystemExit("This probe currently hard-codes the 128-thread FlyDSL indexing")
    if not torch.cuda.is_available():
        raise SystemExit("No CUDA/HIP device is available")

    torch.cuda.set_device(0)
    properties = torch.cuda.get_device_properties(0)

    uninstrumented = run_mode(
        blocks=args.blocks,
        threads=args.threads,
        base_iters=args.base_iters,
        step_iters=args.step_iters,
        instrument=False,
        warmup=args.warmup,
        runs=args.runs,
    )
    instrumented = run_mode(
        blocks=args.blocks,
        threads=args.threads,
        base_iters=args.base_iters,
        step_iters=args.step_iters,
        instrument=True,
        warmup=args.warmup,
        runs=args.runs,
    )
    uninstrumented_output = uninstrumented.pop("output_tensor")
    instrumented_output = instrumented.pop("output_tensor")

    zero_work = run_mode(
        blocks=args.blocks,
        threads=args.threads,
        base_iters=0,
        step_iters=0,
        instrument=True,
        warmup=2,
        runs=args.zero_runs,
    )
    zero_deltas = [row["delta"] for row in zero_work["timing_rows"]]
    zero_starts = [row["start"] for row in zero_work["timing_rows"]]
    instrumented_starts = [row["start"] for row in instrumented["timing_rows"]]
    instrumented_ends = [row["end"] for row in instrumented["timing_rows"]]

    calibration = run_mode(
        blocks=1,
        threads=args.threads,
        base_iters=args.cal_iters,
        step_iters=0,
        instrument=True,
        warmup=3,
        runs=11,
    )
    calibration_delta = calibration["timing_median_deltas"][0]
    calibration_seconds = calibration["event_median_ms"] / 1000.0
    timer_frequency_hz = calibration_delta / calibration_seconds

    output_equal = torch.equal(uninstrumented_output, instrumented_output)
    output_max_abs_diff = float(
        (uninstrumented_output - instrumented_output).abs().max().item()
    )
    overhead_ms = instrumented["event_median_ms"] - uninstrumented["event_median_ms"]
    overhead_percent = 100.0 * overhead_ms / uninstrumented["event_median_ms"]

    per_block = []
    for block, row in enumerate(instrumented["timing_rows"]):
        iterations = args.base_iters + args.step_iters * row["block"]
        per_block.append(
            {
                **row,
                "iterations": iterations,
                "median_delta": instrumented["timing_median_deltas"][block],
            }
        )

    result = {
        "gpu": {
            "name": torch.cuda.get_device_name(0),
            "capability": list(torch.cuda.get_device_capability(0)),
            "total_memory_bytes": properties.total_memory,
            "torch_version": torch.__version__,
            "torch_hip_version": torch.version.hip,
            "flydsl_version": flydsl.__version__,
        },
        "configuration": {
            key: str(value) if isinstance(value, Path) else value
            for key, value in vars(args).items()
        },
        "uninstrumented": uninstrumented,
        "instrumented": instrumented,
        "zero_work": {
            "event_times_ms": zero_work["event_times_ms"],
            "event_median_ms": zero_work["event_median_ms"],
            "event_min_ms": zero_work["event_min_ms"],
            "event_max_ms": zero_work["event_max_ms"],
            "deltas": zero_deltas,
            "min_delta": min(zero_deltas),
            "median_delta": int(median(zero_deltas)),
            "max_delta": max(zero_deltas),
            "unique_deltas": sorted(set(zero_deltas)),
            "start_spread": max(zero_starts) - min(zero_starts),
        },
        "calibration": {
            "iterations": args.cal_iters,
            "timer_delta": calibration_delta,
            "event_median_ms": calibration["event_median_ms"],
            "timer_frequency_hz": timer_frequency_hz,
        },
        "comparison": {
            "output_equal": output_equal,
            "output_equal_torch_equal": output_equal,
            "output_max_abs_diff": output_max_abs_diff,
            "uninstrumented_checksum": uninstrumented["output_checksum_sha256"],
            "instrumented_checksum": instrumented["output_checksum_sha256"],
            "uninstrumented_event_median_ms": uninstrumented["event_median_ms"],
            "instrumented_event_median_ms": instrumented["event_median_ms"],
            "instrumentation_overhead_ms": overhead_ms,
            "instrumentation_overhead_percent": overhead_percent,
        },
        "per_block": per_block,
        "timer_skew": {
            "start_spread_ticks": max(instrumented_starts) - min(instrumented_starts),
            "end_spread_ticks": max(instrumented_ends) - min(instrumented_ends),
        },
    }

    args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
