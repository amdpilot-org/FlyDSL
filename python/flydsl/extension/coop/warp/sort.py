# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""Warp-wide stable sorting."""

from ....expr.gpu import lane_id, shuffle_down, shuffle_up
from ....expr.numeric import Int32
from .._common import resolve_warp_width

__all__ = ["warp_sort"]


def warp_sort(key, value=None, *, width=None, active=None, inactive_key=None, inactive_value=None):
    """Stably sort one key (and optional payload) across *width* lanes.

    Every lane supplies one scalar key and, optionally, one scalar payload. The
    returned key (or ``(key, payload)`` pair) is the element that belongs in
    that lane after an ascending sort. Ties are stable by the original lane
    order inside each *width*-lane group.

    *active* marks lanes that hold real inputs. Inactive lanes are replaced with
    *inactive_key* (and *inactive_value* when a payload is sorted), which must
    sort after every active key. All physical lanes still participate in the
    shuffle network; only the masked values are replaced.
    """
    width = resolve_warp_width(width, "warp_sort width")
    lane = lane_id() % width

    if active is not None:
        if inactive_key is None:
            raise ValueError("warp_sort(active=...) requires inactive_key")
        key = active.select(key, inactive_key)
        if value is not None:
            if inactive_value is None:
                raise ValueError("warp_sort(active=..., value=...) requires inactive_value")
            value = active.select(value, inactive_value)
    elif inactive_key is not None or inactive_value is not None:
        raise ValueError("inactive_key and inactive_value require active")

    rank = lane
    for phase in range(width):
        is_lower = (lane & Int32(1)) == Int32(phase & 1)
        down_key = shuffle_down(key, 1, width)
        up_key = shuffle_up(key, 1, width)
        other_key = is_lower.select(down_key, up_key)

        down_rank = shuffle_down(rank, 1, width)
        up_rank = shuffle_up(rank, 1, width)
        other_rank = is_lower.select(down_rank, up_rank)

        valid = is_lower.select(lane < Int32(width - 1), lane > Int32(0))
        other_key = valid.select(other_key, key)
        other_rank = valid.select(other_rank, rank)
        ordered = (key < other_key) | ((key == other_key) & (rank < other_rank))
        keep_own = is_lower == ordered

        key = keep_own.select(key, other_key)
        rank = keep_own.select(rank, other_rank)
        if value is not None:
            down_value = shuffle_down(value, 1, width)
            up_value = shuffle_up(value, 1, width)
            other_value = is_lower.select(down_value, up_value)
            other_value = valid.select(other_value, value)
            value = keep_own.select(value, other_value)

    return key if value is None else (key, value)
