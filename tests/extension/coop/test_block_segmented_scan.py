#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""Block-wide segmented inclusive scan."""

from __future__ import annotations

import pytest
from coop_common import WARP_SIZE

import flydsl.compiler as flyc
import flydsl.expr as fx

try:
    import torch
except ImportError:
    torch = None


SENTINEL = -123456789


def _segment_starts(block_threads, pattern):
    flags = torch.zeros(block_threads, dtype=torch.int32)
    if pattern == "reset-at-boundary":
        flags[0] = 1
        flags[WARP_SIZE - 1] = 1
        if block_threads > WARP_SIZE:
            flags[WARP_SIZE + 6] = 1
            flags[WARP_SIZE + 11] = 1
    else:
        if block_threads > WARP_SIZE:
            flags[WARP_SIZE + 6] = 1
            flags[WARP_SIZE + 11] = 1
    return flags


def _segmented_cumsum(values, flags):
    expected = torch.empty_like(values)
    running = 0
    for index, (value, flag) in enumerate(zip(values.tolist(), flags.tolist())):
        if flag:
            running = 0
        running = (running + value) % (1 << 32)
        if running >= (1 << 31):
            running -= 1 << 32
        expected[index] = running
    return expected


@pytest.mark.l2_device
@pytest.mark.rocm_lower
@pytest.mark.skipif(torch is None or not torch.cuda.is_available(), reason="requires GPU")
@pytest.mark.parametrize(
    "block_threads",
    (WARP_SIZE, 2 * WARP_SIZE),
    ids=("one-wave", "two-wave"),
)
@pytest.mark.parametrize(
    "pattern",
    ("reset-at-boundary", "carry-across-boundary"),
)
def test_segmented_inclusive_add_resets_short_segments(block_threads, pattern):
    """A true start flag resets the running fold, including across a wave boundary."""
    block_size = (block_threads, 1, 1)

    @flyc.kernel(known_block_size=list(block_size))
    def kernel(A: fx.Tensor, Flags: fx.Tensor, Out: fx.Tensor):
        block_scan = fx.coop.BlockScan[fx.Int32, block_size]
        storage = fx.SharedAllocator().allocate(block_scan.SharedStorage).peek()
        tid = fx.thread_idx.x
        Out[tid] = block_scan.segmented_inclusive(A[tid], Flags[tid], fx.ReductionOp.ADD, storage=storage)

    @flyc.jit
    def launch(A: fx.Tensor, Flags: fx.Tensor, Out: fx.Tensor, stream: fx.Stream = fx.Stream(None)):
        kernel(A, Flags, Out).launch(grid=(1, 1, 1), block=block_size, stream=stream)

    values = torch.arange(1, block_threads + 1, dtype=torch.int32, device="cuda")
    flags = _segment_starts(block_threads, pattern).to("cuda")
    out = torch.full((block_threads,), SENTINEL, dtype=torch.int32, device="cuda")
    launch(values, flags, out, stream=torch.cuda.Stream())
    torch.cuda.synchronize()

    result = out.cpu()
    expected = _segmented_cumsum(values.cpu(), flags.cpu())
    assert not torch.any(result == SENTINEL)
    assert torch.equal(result, expected)
