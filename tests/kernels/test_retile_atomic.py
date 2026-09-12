# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""Regression coverage for retile with different load and store copy atoms."""

import pytest
import torch

import flydsl.compiler as flyc
import flydsl.expr as fx


pytestmark = [pytest.mark.l2_device, pytest.mark.rocm_lower]

_TILE_M = 64
_TILE_N = 64
_TV_TILE_MN = (32, 64)


@flyc.kernel
def _sum_kernel(A: fx.Tensor, B: fx.Tensor, use_retile: fx.Constexpr[bool]):
    tid = fx.thread_idx.x
    A = A[None, fx.block_idx.x, fx.block_idx.y]

    tv_layout = fx.make_layout(((8, 32), 8), ((256, 1), 32))
    load_atom = fx.make_copy_atom(fx.UniversalCopy128b(), fx.Float32)
    store_atom = fx.make_copy_atom(fx.UniversalAtomicAdd(fx.Float32), fx.Float32)
    tiled_load = fx.make_tiled_copy(load_atom, tv_layout, _TV_TILE_MN)
    tiled_store = fx.make_tiled_copy(store_atom, tv_layout, _TV_TILE_MN)

    broadcasted_B = fx.composition(B, fx.make_layout((_TILE_M, _TILE_N), (0, 0)))
    part_A = tiled_load.get_slice(tid).partition_S(A)
    store_slice = tiled_store.get_slice(tid)
    part_B = store_slice.partition_D(broadcasted_B)

    for bm in fx.range_constexpr(_TILE_M // _TV_TILE_MN[0]):
        for bn in fx.range_constexpr(_TILE_N // _TV_TILE_MN[1]):
            frag = fx.make_fragment_like(part_A[None, bm, bn])
            fx.copy(load_atom, part_A[None, bm, bn], frag)
            if use_retile:
                frag = store_slice.retile(frag)
            fx.copy(store_atom, frag, part_B[None, bm, bn])


@flyc.jit
def _sum(A: fx.Tensor, B: fx.Tensor, use_retile: fx.Constexpr[bool]):
    A = fx.tiled_divide(A, (_TILE_M, _TILE_N))
    _sum_kernel(A, B, use_retile).launch(
        grid=(fx.get_scalar(A.shape[1]), fx.get_scalar(A.shape[2]), 1),
        block=(256, 1, 1),
    )


def _inputs():
    torch.manual_seed(1729)
    return (
        torch.randn((_TILE_M, _TILE_N), device="cuda", dtype=torch.float32),
        torch.zeros(1, device="cuda", dtype=torch.float32),
    )


def test_retile_fragment_for_scalar_atomic_add():
    A, B = _inputs()
    reference = A.cpu().double().sum().item()

    _sum(A, B, True)
    torch.cuda.synchronize()

    assert B.item() == pytest.approx(reference, rel=2e-4, abs=2e-4)


def test_unretiled_fragment_reports_incompatible_value_groups():
    A, B = _inputs()

    with pytest.raises(Exception, match="incompatible value-group counts: 2 versus 8"):
        _sum(A, B, False)
