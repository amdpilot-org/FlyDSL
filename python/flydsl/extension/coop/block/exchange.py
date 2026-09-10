# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""Block-wide blocked/striped arrangement exchange."""

from ...._mlir import ir
from ...._mlir.dialects import llvm as _llvm
from ....compiler import jit
from ....expr.primitive import range_constexpr
from ....expr.typing import Vector

__all__ = [
    "blocked_to_striped",
    "striped_to_blocked",
]


def _barrier():
    _llvm.inline_asm(ir.Type.parse("!llvm.void"), [], "s_barrier", "", has_side_effects=True)


@jit
def blocked_to_striped(items, tid, slots, block_threads, items_per_thread):
    """Reorder consecutive per-thread items into block-striped items.

    Thread ``t`` owns blocked items ``t * items_per_thread .. t * items_per_thread +
    items_per_thread - 1`` on input and striped items ``t + i * block_threads`` on
    output. Every thread must reach the call together, and *slots* must have
    ``block_threads * items_per_thread`` elements.
    """
    for item in range_constexpr(items_per_thread):
        slots[tid * items_per_thread + item] = items[item]
    _barrier()
    return Vector.from_elements([slots[tid + item * block_threads] for item in range_constexpr(items_per_thread)])


@jit
def striped_to_blocked(items, tid, slots, block_threads, items_per_thread):
    """Reorder block-striped per-thread items back into consecutive items.

    This is the inverse of :func:`blocked_to_striped`. Every thread must reach
    the call together, and *slots* must have ``block_threads * items_per_thread``
    elements.
    """
    for item in range_constexpr(items_per_thread):
        slots[tid + item * block_threads] = items[item]
    _barrier()
    return Vector.from_elements([slots[tid * items_per_thread + item] for item in range_constexpr(items_per_thread)])
