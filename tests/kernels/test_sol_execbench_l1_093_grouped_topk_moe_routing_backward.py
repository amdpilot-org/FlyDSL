#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

"""Parity harness for the L1/093 grouped top-k MoE routing backward port.

Verifies the optimized implementation (Triton fused steps 1-4 + aten GEMM step 5,
optionally CUDA-graph replayed) against the PyTorch eager reference on every
workload shape from SOL-ExecBench ``workload.jsonl``.

Acceptance gate: max_abs_diff < 1e-2 for both ``grad_hidden_states`` and
``grad_weight`` on all 16 shapes.

Run:
    python -m tests.kernels.test_sol_execbench_l1_093_grouped_topk_moe_routing_backward
    pytest tests/kernels/test_sol_execbench_l1_093_grouped_topk_moe_routing_backward.py -v
"""

from __future__ import annotations

import os
import sys

import pytest

# Make the repo root importable when run as a script or via pytest from a
# subdirectory (mirrors tests/kernels/benchmark_common.py).
_THIS = os.path.abspath(__file__)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_THIS)))  # FlyDSL/
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    import torch
except ImportError:  # pragma: no cover
    torch = None

if torch is None or not torch.cuda.is_available():
    pytest.skip("CUDA/ROCm not available. Skipping GPU parity tests.", allow_module_level=True)

from kernels.sol_execbench.l1_093_grouped_topk_moe_routing_backward import (  # noqa: E402
    WORKLOAD_SHAPES,
    get_inputs,
    make_graphed_runner,
    optimized_run,
    reference_run,
)

TOL = 1e-2
SEED_BASE = 1234


def _seeded_inputs(N: int, device: torch.device) -> dict:
    """Generate deterministic inputs for shape N (seeded for reproducibility)."""
    torch.manual_seed(SEED_BASE + N)
    torch.cuda.manual_seed_all(SEED_BASE + N)
    return get_inputs(N, device)


@pytest.mark.l2_device
@pytest.mark.parametrize("N", WORKLOAD_SHAPES, ids=[f"N{n}" for n in WORKLOAD_SHAPES])
def test_parity_optimized_vs_eager(N: int) -> None:
    """optimized_run (Triton fused + aten GEMM) must match eager within TOL."""
    device = torch.device("cuda")
    inputs = _seeded_inputs(N, device)

    ref_hs, ref_w = reference_run(**inputs)
    opt_hs, opt_w = optimized_run(**inputs)

    d_hs = (opt_hs - ref_hs).abs().max().item()
    d_w = (opt_w - ref_w).abs().max().item()
    assert d_hs < TOL, f"N={N}: grad_hidden_states max_abs_diff={d_hs:.3e} >= {TOL}"
    assert d_w < TOL, f"N={N}: grad_weight max_abs_diff={d_w:.3e} >= {TOL}"


@pytest.mark.l2_device
@pytest.mark.parametrize("N", WORKLOAD_SHAPES, ids=[f"N{n}" for n in WORKLOAD_SHAPES])
def test_parity_graphed_vs_eager(N: int) -> None:
    """CUDA-graph replay of optimized_run must match eager within TOL.

    Graph replay executes the identical kernels, so this is expected to be
    bit-identical (max_abs_diff == 0); the gate is the same 1e-2 tolerance.
    """
    device = torch.device("cuda")
    inputs = _seeded_inputs(N, device)

    ref_hs, ref_w = reference_run(**inputs)
    graphed = make_graphed_runner(optimized_run)
    g_hs, g_w = graphed(**inputs)

    d_hs = (g_hs - ref_hs).abs().max().item()
    d_w = (g_w - ref_w).abs().max().item()
    assert d_hs < TOL, f"N={N}: graphed grad_hidden_states max_abs_diff={d_hs:.3e} >= {TOL}"
    assert d_w < TOL, f"N={N}: graphed grad_weight max_abs_diff={d_w:.3e} >= {TOL}"


def _main() -> int:
    """Script entry point: run parity on all shapes and print a summary."""
    device = torch.device("cuda")
    print(f"Parity check (tol={TOL}) on {len(WORKLOAD_SHAPES)} shapes")
    print(f"GPU: {torch.cuda.get_device_name(0)!r}")
    print("-" * 78)
    all_pass = True
    graphed = make_graphed_runner(optimized_run)
    for N in WORKLOAD_SHAPES:
        inputs = _seeded_inputs(N, device)
        ref_hs, ref_w = reference_run(**inputs)
        opt_hs, opt_w = optimized_run(**inputs)
        g_hs, g_w = graphed(**inputs)

        d_hs = (opt_hs - ref_hs).abs().max().item()
        d_w = (opt_w - ref_w).abs().max().item()
        dg_hs = (g_hs - ref_hs).abs().max().item()
        dg_w = (g_w - ref_w).abs().max().item()
        ok = (d_hs < TOL) and (d_w < TOL) and (dg_hs < TOL) and (dg_w < TOL)
        all_pass &= ok
        status = "PASS" if ok else "FAIL"
        print(
            f"N={N:>5d}  opt[hs={d_hs:.2e} w={d_w:.2e}]  "
            f"graph[hs={dg_hs:.2e} w={dg_w:.2e}]  {status}"
        )
    print("-" * 78)
    print(f"PARITY (tol={TOL}): {'PASS' if all_pass else 'FAIL'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(_main())
