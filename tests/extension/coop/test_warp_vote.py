#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""Warp vote and ballot primitives, compared against exact bit masks."""

from __future__ import annotations

import pytest
from coop_common import WARP_SIZE

import flydsl.compiler as flyc
import flydsl.expr as fx
from flydsl.compiler.backends import current_target

try:
    import torch
except ImportError:
    torch = None


portable = fx.coop.universal

VOTE_WIDTHS = tuple(1 << exponent for exponent in range(WARP_SIZE.bit_length()))


def _is_gfx9():
    return current_target().arch.startswith("gfx9")


requires_rocm = pytest.mark.skipif(not _is_gfx9(), reason="the ROCDL override is gfx9-only")


def _run_vote(module, predicate_limit, *, block, active_count, width):
    """Run one vote kernel through *module* and return its exact outputs."""

    @flyc.kernel(known_block_size=[block, 1, 1])
    def kernel(
        PredicateLimit: fx.Int32,
        ActiveCount: fx.Int32,
        ActiveMasks: fx.Tensor,
        PredicateMasks: fx.Tensor,
        Alls: fx.Tensor,
        Anys: fx.Tensor,
    ):
        tid = fx.thread_idx.x
        if tid < ActiveCount:
            predicate = tid < PredicateLimit
            ActiveMasks[tid] = module.warp_ballot(True, width=width)
            PredicateMasks[tid] = module.warp_ballot(predicate, width=width)
            Alls[tid] = fx.Int32(module.warp_all(predicate, width=width))
            Anys[tid] = fx.Int32(module.warp_any(predicate, width=width))

    @flyc.jit
    def launch(
        PredicateLimit: fx.Int32,
        ActiveCount: fx.Int32,
        ActiveMasks: fx.Tensor,
        PredicateMasks: fx.Tensor,
        Alls: fx.Tensor,
        Anys: fx.Tensor,
        stream: fx.Stream = fx.Stream(None),
    ):
        kernel(PredicateLimit, ActiveCount, ActiveMasks, PredicateMasks, Alls, Anys).launch(
            grid=(1, 1, 1), block=(block, 1, 1), stream=stream
        )

    warp_threads = fx.num_warp_threads()
    mask_dtype = torch.int64 if warp_threads == 64 else torch.int32
    active_masks = torch.full((block,), -1, dtype=mask_dtype, device="cuda")
    predicate_masks = torch.full((block,), -1, dtype=mask_dtype, device="cuda")
    alls = torch.full((block,), -1, dtype=torch.int32, device="cuda")
    anys = torch.full((block,), -1, dtype=torch.int32, device="cuda")
    launch(predicate_limit, active_count, active_masks, predicate_masks, alls, anys, stream=torch.cuda.Stream())
    torch.cuda.synchronize()
    return active_masks.cpu(), predicate_masks.cpu(), alls.cpu(), anys.cpu()


def _expected(predicate_limit, active_count, width):
    """Exact independent bit masks and vote predicates for one case."""
    bits = 64 if WARP_SIZE == 64 else 32
    active_mask = (1 << active_count) - 1
    predicate_mask = (1 << predicate_limit) - 1
    if active_mask >= 1 << (bits - 1):
        active_mask -= 1 << bits
    if predicate_mask >= 1 << (bits - 1):
        predicate_mask -= 1 << bits
    return {
        "active_mask": active_mask,
        "predicate_mask": predicate_mask,
        "all": int(predicate_mask == active_mask),
        "any": int(predicate_mask != 0),
    }


@pytest.mark.l2_device
@pytest.mark.rocm_lower
@pytest.mark.skipif(torch is None or not torch.cuda.is_available(), reason="requires GPU")
@pytest.mark.parametrize("width", VOTE_WIDTHS, ids=lambda width: f"w{width}")
@pytest.mark.parametrize("predicate_limit", ("none", "half", "all"), ids=str)
def test_vote_agrees_with_the_portable_form_on_full_active_lanes(predicate_limit, width):
    """Every full-active width must agree with the portable shuffle form."""
    block = fx.num_warp_threads()
    active_count = width
    if predicate_limit == "none":
        limit = 0
    elif predicate_limit == "half":
        limit = width // 2
    else:
        limit = width

    fast_active, fast_predicate, fast_alls, fast_anys = _run_vote(
        fx.coop, limit, block=block, active_count=active_count, width=width
    )
    ref_active, ref_predicate, ref_alls, ref_anys = _run_vote(
        portable, limit, block=block, active_count=active_count, width=width
    )

    assert torch.equal(fast_active, ref_active)
    assert torch.equal(fast_predicate, ref_predicate)
    assert torch.equal(fast_alls, ref_alls)
    assert torch.equal(fast_anys, ref_anys)

    expected = _expected(limit, active_count, width)
    assert torch.equal(fast_active[:active_count], torch.full((active_count,), expected["active_mask"], dtype=fast_active.dtype))
    assert torch.equal(fast_predicate[:active_count], torch.full((active_count,), expected["predicate_mask"], dtype=fast_predicate.dtype))
    assert torch.equal(fast_alls[:active_count], torch.full((active_count,), expected["all"], dtype=torch.int32))
    assert torch.equal(fast_anys[:active_count], torch.full((active_count,), expected["any"], dtype=torch.int32))


@pytest.mark.l2_device
@pytest.mark.rocm_lower
@pytest.mark.skipif(torch is None or not torch.cuda.is_available(), reason="requires GPU")
@requires_rocm
@pytest.mark.parametrize("active_count", (1, 3, 7, 13, 31, 37, 63, 64), ids=str)
@pytest.mark.parametrize("predicate_limit", ("none", "half", "all"), ids=str)
def test_rocdl_vote_handles_partial_wave_tails(predicate_limit, active_count):
    """The ROCDL override must preserve exact masks for partial active waves."""
    block = fx.num_warp_threads()
    width = block
    if predicate_limit == "none":
        limit = 0
    elif predicate_limit == "half":
        limit = active_count // 2
    else:
        limit = active_count

    active_masks, predicate_masks, alls, anys = _run_vote(
        fx.coop, limit, block=block, active_count=active_count, width=width
    )
    expected = _expected(limit, active_count, width)

    assert torch.equal(active_masks[:active_count], torch.full((active_count,), expected["active_mask"], dtype=active_masks.dtype))
    assert torch.equal(predicate_masks[:active_count], torch.full((active_count,), expected["predicate_mask"], dtype=predicate_masks.dtype))
    assert torch.equal(alls[:active_count], torch.full((active_count,), expected["all"], dtype=torch.int32))
    assert torch.equal(anys[:active_count], torch.full((active_count,), expected["any"], dtype=torch.int32))
    assert torch.equal(active_masks[active_count:], torch.full((block - active_count,), -1, dtype=active_masks.dtype))
    assert torch.equal(predicate_masks[active_count:], torch.full((block - active_count,), -1, dtype=predicate_masks.dtype))
    assert torch.equal(alls[active_count:], torch.full((block - active_count,), -1, dtype=torch.int32))
    assert torch.equal(anys[active_count:], torch.full((block - active_count,), -1, dtype=torch.int32))
