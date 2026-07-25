#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

"""Benchmark for the L1/093 grouped top-k MoE routing backward port.

Measures ``kernel_ms`` per workload shape for:
  * ``reference_run``   — PyTorch eager baseline (torch.compile OFF)
  * ``optimized_run``   — Triton fused steps 1-4 + aten GEMM step 5
  * graphed ``optimized_run`` — the above captured in a CUDA graph (full
    delivered solution; collapses per-call launch overhead)

Timing methodology mirrors ``test_harness.py``: 5 warmup + 20 timed iterations,
per-iteration CUDA events.  The primary metric is the average graphed
``kernel_ms`` across all 16 shapes, reported in the AMDPILOT_METRIC envelope.

Acceptance gate: graphed kernel_ms < 0.9 * eager kernel_ms on >= 80% of shapes.

Run:
    python -m tests.kernels.bench_sol_execbench_l1_093_grouped_topk_moe_routing_backward
"""

from __future__ import annotations

import os
import sys

# Make the repo root importable when run as a script.
_THIS = os.path.abspath(__file__)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_THIS)))  # FlyDSL/
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import torch  # noqa: E402

from kernels.sol_execbench.l1_093_grouped_topk_moe_routing_backward import (  # noqa: E402
    WORKLOAD_SHAPES,
    get_inputs,
    make_graphed_runner,
    optimized_run,
    reference_run,
)

WARMUP_ITERS = 5
TIMING_ITERS = 20
# A shape "wins" if the optimized (graphed) kernel_ms is below this fraction of
# the eager kernel_ms.  Matches the task acceptance criterion (0.9x baseline).
WIN_RATIO = 0.9


def _time_fn(fn, inputs, device) -> float:
    """Time ``fn(**inputs)`` over TIMING_ITERS with per-iter CUDA events."""
    for _ in range(WARMUP_ITERS):
        _ = fn(**inputs)
    torch.cuda.synchronize(device)

    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    times_ms = []
    for _ in range(TIMING_ITERS):
        start.record()
        _ = fn(**inputs)
        end.record()
        torch.cuda.synchronize(device)
        times_ms.append(start.elapsed_time(end))
    return sum(times_ms) / len(times_ms)


def main() -> int:
    device = torch.device("cuda")
    gpu_name = torch.cuda.get_device_name(0)
    print(f"GPU: {gpu_name!r}", flush=True)
    print(f"Device: {device}", flush=True)
    print(f"Warmup iters: {WARMUP_ITERS}, Timing iters: {TIMING_ITERS}", flush=True)
    print(f"Workload shapes (N): {WORKLOAD_SHAPES}", flush=True)
    print(f"Win gate: optimized (graphed) < {WIN_RATIO}x eager", flush=True)
    print("", flush=True)

    graphed = make_graphed_runner(optimized_run)
    header = (
        f"{'N':>6s} {'eager_ms':>10s} {'opt_ms':>10s} {'graph_ms':>10s} "
        f"{'graph/eager':>12s} {'speedup':>9s} {'status':>7s}"
    )
    print(header, flush=True)
    print("-" * len(header), flush=True)

    rows = []
    wins = 0
    for N in WORKLOAD_SHAPES:
        torch.manual_seed(1234 + N)
        torch.cuda.manual_seed_all(1234 + N)
        inputs = get_inputs(N, device)

        eager_ms = _time_fn(reference_run, inputs, device)
        opt_ms = _time_fn(optimized_run, inputs, device)
        graph_ms = _time_fn(graphed, inputs, device)

        ratio = graph_ms / eager_ms if eager_ms > 0 else float("inf")
        speedup = eager_ms / graph_ms if graph_ms > 0 else 0.0
        won = graph_ms < WIN_RATIO * eager_ms
        wins += int(won)
        status = "WIN" if won else "LOSS"
        rows.append((N, eager_ms, opt_ms, graph_ms, ratio, speedup, status))
        print(
            f"{N:>6d} {eager_ms:>10.4f} {opt_ms:>10.4f} {graph_ms:>10.4f} "
            f"{ratio:>11.3f} {speedup:>8.2f}x {status:>7s}",
            flush=True,
        )

    n = len(rows)
    avg_eager = sum(r[1] for r in rows) / n
    avg_opt = sum(r[2] for r in rows) / n
    avg_graph = sum(r[3] for r in rows) / n
    avg_speedup = avg_eager / avg_graph if avg_graph > 0 else 0.0
    win_pct = 100.0 * wins / n

    print("-" * len(header), flush=True)
    print(
        f"{'AVG':>6s} {avg_eager:>10.4f} {avg_opt:>10.4f} {avg_graph:>10.4f} "
        f"{avg_graph / avg_eager:>11.3f} {avg_speedup:>8.2f}x {win_pct:>6.1f}%",
        flush=True,
    )
    print("", flush=True)
    print(f"Average kernel_ms (graphed) across {n} shapes: {avg_graph:.4f} ms", flush=True)
    print(f"Average kernel_ms (eager)   across {n} shapes: {avg_eager:.4f} ms", flush=True)
    print(f"Speedup: {avg_speedup:.2f}x", flush=True)
    print(f"Win rate (<{WIN_RATIO}x eager): {wins}/{n} = {win_pct:.1f}%", flush=True)
    print("", flush=True)

    # Canonical metric envelope (graphed = full delivered solution).
    print("===== AMDPILOT_METRIC v1 =====", flush=True)
    print(f"metric_value: {avg_graph}", flush=True)
    print("===== END AMDPILOT_METRIC =====", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
