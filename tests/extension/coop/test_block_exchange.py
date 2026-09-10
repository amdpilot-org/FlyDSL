#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""Block-wide blocked/striped arrangement exchange."""

from __future__ import annotations

import pytest
from coop_common import linear_tid

import flydsl.compiler as flyc
import flydsl.expr as fx

try:
    import torch
except ImportError:
    torch = None


ITEMS_PER_THREAD = 3
SENTINEL = -123456789
EXCHANGE_CASES = (
    (64, 61, "one_wave_tail_61"),
    (128, 125, "two_wave_tail_125"),
)


def run_exchange(direction, block_threads, active_items):
    total_items = block_threads * ITEMS_PER_THREAD
    lane = torch.arange(total_items, dtype=torch.int32) // ITEMS_PER_THREAD
    item = torch.arange(total_items, dtype=torch.int32) % ITEMS_PER_THREAD
    values = (lane * 1000 + item + 1).to(torch.int32).cuda()
    output = torch.full((total_items,), SENTINEL, dtype=torch.int32, device="cuda")
    block_size = (block_threads, 1, 1)

    @flyc.kernel(known_block_size=list(block_size))
    def kernel(A: fx.Tensor, Out: fx.Tensor):
        storage_type = fx.Struct["slots" : fx.Array[fx.Int32, total_items]]
        storage = fx.SharedAllocator().allocate(storage_type).peek()
        tid = linear_tid(block_size)

        if direction == "blocked_to_striped":
            items = fx.Vector.from_elements([A[tid * ITEMS_PER_THREAD + item] for item in range(ITEMS_PER_THREAD)])
            exchanged = fx.coop.blocked_to_striped(items, tid, storage.slots, block_threads, ITEMS_PER_THREAD)
            for item in fx.range_constexpr(ITEMS_PER_THREAD):
                source_index = tid + item * block_threads
                if source_index < active_items:
                    Out[tid * ITEMS_PER_THREAD + item] = exchanged[item]
        else:
            items = fx.Vector.from_elements([A[tid + item * block_threads] for item in range(ITEMS_PER_THREAD)])
            exchanged = fx.coop.striped_to_blocked(items, tid, storage.slots, block_threads, ITEMS_PER_THREAD)
            for item in fx.range_constexpr(ITEMS_PER_THREAD):
                source_index = tid * ITEMS_PER_THREAD + item
                if source_index < active_items:
                    Out[tid * ITEMS_PER_THREAD + item] = exchanged[item]

    @flyc.jit
    def launch(A: fx.Tensor, Out: fx.Tensor, stream: fx.Stream = fx.Stream(None)):
        kernel(A, Out).launch(grid=(1, 1, 1), block=block_size, stream=stream)

    launch(values, output, stream=torch.cuda.Stream())
    torch.cuda.synchronize()

    host_values = values.cpu()
    expected = torch.full((total_items,), SENTINEL, dtype=torch.int32)
    for destination_index in range(total_items):
        lane = destination_index // ITEMS_PER_THREAD
        item = destination_index % ITEMS_PER_THREAD
        if direction == "blocked_to_striped":
            source_index = lane + item * block_threads
        else:
            source_index = destination_index
        if source_index < active_items:
            expected[destination_index] = host_values[source_index]

    return output.cpu(), expected


@pytest.mark.l2_device
@pytest.mark.rocm_lower
@pytest.mark.skipif(torch is None or not torch.cuda.is_available(), reason="requires GPU")
@pytest.mark.parametrize("direction", ("blocked_to_striped", "striped_to_blocked"))
@pytest.mark.parametrize("block_threads,active_items,case_id", EXCHANGE_CASES, ids=[case[2] for case in EXCHANGE_CASES])
def test_exchange(direction, block_threads, active_items, case_id):
    """Both directions preserve IDs exactly and leave inactive slots sentinel-filled."""
    output, expected = run_exchange(direction, block_threads, active_items)
    assert torch.equal(output, expected)
    active = expected != SENTINEL
    assert int(active.sum()) == active_items
    assert torch.equal(output[active], expected[active])
    assert torch.equal(output[~active], torch.full_like(output[~active], SENTINEL))
