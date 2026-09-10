#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""Warp-wide stable sort against an exact host ordering oracle."""

from __future__ import annotations

import pytest

import flydsl.compiler as flyc
import flydsl.expr as fx

try:
    import torch
except ImportError:
    torch = None


INT32_MAX = 2**31 - 1


def run_warp_sort(keys, values, *, width, active_count=None):
    block = keys.numel()
    has_tail = active_count is not None

    @flyc.kernel(known_block_size=[block, 1, 1])
    def kernel(Keys: fx.Tensor, Values: fx.Tensor, OutKeys: fx.Tensor, OutValues: fx.Tensor):
        lane = fx.thread_idx.x
        active = lane < fx.Int32(active_count) if has_tail else None
        if has_tail:
            key, value = fx.coop.universal.warp_sort(
                Keys[lane],
                Values[lane],
                width=width,
                active=active,
                inactive_key=fx.Int32(INT32_MAX),
                inactive_value=fx.Int32(-1),
            )
        else:
            key, value = fx.coop.universal.warp_sort(Keys[lane], Values[lane], width=width)
        OutKeys[lane] = key
        OutValues[lane] = value

    @flyc.jit
    def launch(
        Keys: fx.Tensor,
        Values: fx.Tensor,
        OutKeys: fx.Tensor,
        OutValues: fx.Tensor,
        stream: fx.Stream = fx.Stream(None),
    ):
        kernel(Keys, Values, OutKeys, OutValues).launch(
            grid=(1, 1, 1), block=(block, 1, 1), stream=stream
        )

    out_keys = torch.zeros_like(keys)
    out_values = torch.zeros_like(values)
    launch(keys, values, out_keys, out_values, stream=torch.cuda.Stream())
    torch.cuda.synchronize()
    return out_keys.cpu(), out_values.cpu()


def host_order(keys, values, *, width, active_count=None):
    """Exact per-group ordering, with ties resolved by original lane order."""
    expected_keys = []
    expected_values = []
    for group in range(keys.numel() // width):
        entries = []
        for lane in range(width):
            index = group * width + lane
            if active_count is None or lane < active_count:
                entries.append((int(keys[index]), int(values[index])))
            else:
                entries.append((INT32_MAX, -1))
        order = sorted(range(width), key=lambda lane: entries[lane])
        expected_keys.extend(entries[lane][0] for lane in order)
        expected_values.extend(entries[lane][1] for lane in order)
    return (
        torch.tensor(expected_keys, dtype=torch.int32),
        torch.tensor(expected_values, dtype=torch.int32),
    )


@pytest.mark.l2_device
@pytest.mark.rocm_lower
@pytest.mark.skipif(torch is None or not torch.cuda.is_available(), reason="requires GPU")
@pytest.mark.parametrize("case", ("distinct", "ties", "partial_tail"))
def test_warp_sort_matches_host_order(case):
    width = fx.num_warp_threads()
    if case == "distinct":
        keys = torch.arange(width, dtype=torch.int32, device="cuda").flip(0)
    elif case == "ties":
        keys = torch.tensor([5, 2, 5, 1, 2, 5, 1, 3] * (width // 8), dtype=torch.int32, device="cuda")
    else:
        keys = torch.arange(width, dtype=torch.int32, device="cuda").flip(0)
    values = torch.arange(width, dtype=torch.int32, device="cuda")
    active_count = 13 if case == "partial_tail" else None

    out_keys, out_values = run_warp_sort(keys, values, width=width, active_count=active_count)
    expected_keys, expected_values = host_order(
        keys.cpu(), values.cpu(), width=width, active_count=active_count
    )

    assert torch.equal(out_keys, expected_keys)
    assert torch.equal(out_values, expected_values)
    if case == "partial_tail":
        assert bool((out_keys[:active_count] != INT32_MAX).all())
        assert bool((out_keys[active_count:] == INT32_MAX).all())


@pytest.mark.l2_device
@pytest.mark.rocm_lower
@pytest.mark.skipif(torch is None or not torch.cuda.is_available(), reason="requires GPU")
def test_warp_sort_narrow_width_groups():
    width = fx.num_warp_threads() // 2
    block = 2 * fx.num_warp_threads()
    keys = torch.arange(block, dtype=torch.int32, device="cuda").flip(0)
    values = torch.arange(block, dtype=torch.int32, device="cuda")

    out_keys, out_values = run_warp_sort(keys, values, width=width)
    expected_keys, expected_values = host_order(keys.cpu(), values.cpu(), width=width)

    assert torch.equal(out_keys, expected_keys)
    assert torch.equal(out_values, expected_values)
