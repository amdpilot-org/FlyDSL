# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""Warp-scope ``warp_ballot`` / ``warp_all`` / ``warp_any``.

The kernel below asks three questions about one predicate across a full warp:

  1. **Which lanes are active?** ``warp_ballot(True)`` returns the exact
     active-lane mask, including the partial-wave tail when the block is
     smaller than the hardware wave.
  2. **Do all active lanes satisfy the predicate?** ``warp_all`` compares the
     predicate mask against that active mask.
  3. **Does any active lane satisfy it?** ``warp_any`` checks whether the
     predicate mask is nonzero.
"""

import torch

import flydsl.compiler as flyc
import flydsl.expr as fx

BLOCK = 64
PREDICATE_LIMIT = 37


@flyc.kernel(known_block_size=[BLOCK, 1, 1])
def warp_vote(
    ActiveCount: fx.Int32,
    PredicateLimit: fx.Int32,
    ActiveMasks: fx.Tensor,
    PredicateMasks: fx.Tensor,
    Alls: fx.Tensor,
    Anys: fx.Tensor,
):
    tid = fx.thread_idx.x
    if tid < ActiveCount:
        predicate = tid < PredicateLimit
        ActiveMasks[tid] = fx.coop.warp_ballot(True)
        PredicateMasks[tid] = fx.coop.warp_ballot(predicate)
        Alls[tid] = fx.Int32(fx.coop.warp_all(predicate))
        Anys[tid] = fx.Int32(fx.coop.warp_any(predicate))


@flyc.jit
def launch(
    ActiveCount: fx.Int32,
    PredicateLimit: fx.Int32,
    ActiveMasks: fx.Tensor,
    PredicateMasks: fx.Tensor,
    Alls: fx.Tensor,
    Anys: fx.Tensor,
):
    warp_vote(ActiveCount, PredicateLimit, ActiveMasks, PredicateMasks, Alls, Anys).launch(
        grid=(1, 1, 1), block=(BLOCK, 1, 1)
    )


active_count = 37
active_masks = torch.zeros(BLOCK, dtype=torch.int64, device="cuda")
predicate_masks = torch.zeros(BLOCK, dtype=torch.int64, device="cuda")
alls = torch.zeros(BLOCK, dtype=torch.int32, device="cuda")
anys = torch.zeros(BLOCK, dtype=torch.int32, device="cuda")

launch(active_count, PREDICATE_LIMIT, active_masks, predicate_masks, alls, anys)
torch.cuda.synchronize()

expected_active = (1 << active_count) - 1
expected_predicate = (1 << PREDICATE_LIMIT) - 1
expected_all = int(expected_predicate == expected_active)
expected_any = int(expected_predicate != 0)

if (
    torch.equal(active_masks[:active_count], torch.full((active_count,), expected_active, dtype=torch.int64, device="cuda"))
    and torch.equal(predicate_masks[:active_count], torch.full((active_count,), expected_predicate, dtype=torch.int64, device="cuda"))
    and torch.equal(alls[:active_count], torch.full((active_count,), expected_all, dtype=torch.int32, device="cuda"))
    and torch.equal(anys[:active_count], torch.full((active_count,), expected_any, dtype=torch.int32, device="cuda"))
):
    print(f"PASS ({active_count} active lanes, predicate mask {expected_predicate:#x})")
else:
    print("FAIL")
    raise SystemExit(1)
