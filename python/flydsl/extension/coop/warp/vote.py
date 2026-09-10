# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""Warp-wide vote and ballot primitives — the portable form."""

from ....expr.gpu import lane_id, num_warp_threads, shuffle_idx
from ....expr.numeric import Boolean, Int32, Int64
from .._common import resolve_warp_width

__all__ = ["warp_ballot", "warp_all", "warp_any"]


def _mask_dtype():
    """Return the lane-mask integer type for the target's wave."""
    return Int64 if num_warp_threads() == 64 else Int32


def _group_base(width):
    """Return the first lane of the calling lane's *width*-lane group."""
    return (lane_id() // width) * width


def warp_ballot(predicate, *, width=None):
    """Return the ballot mask for *predicate* over one *width*-lane group.

    The portable form assumes every lane in the group is active. A target
    override may relax that assumption; see the ROCm override for the
    partial-wave behavior this repository tests on gfx950.
    """
    width = resolve_warp_width(width, "warp_ballot width")
    dtype = _mask_dtype()
    predicate_value = Int32(Boolean(predicate))
    base = _group_base(width)
    mask = dtype(0)
    for source in range(width):
        value = shuffle_idx(predicate_value, base + source, width)
        bit = dtype(value & 1)
        mask |= bit << source
    return mask


def warp_all(predicate, *, width=None):
    """Return whether every active lane in the group satisfies *predicate*."""
    width = resolve_warp_width(width, "warp_all width")
    mask = warp_ballot(predicate, width=width)
    full_mask = _mask_dtype()((1 << width) - 1)
    return mask == full_mask


def warp_any(predicate, *, width=None):
    """Return whether any active lane in the group satisfies *predicate*."""
    width = resolve_warp_width(width, "warp_any width")
    mask = warp_ballot(predicate, width=width)
    return mask != 0
