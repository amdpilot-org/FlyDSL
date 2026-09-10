#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

"""Regression tests for tiled-copy retile diagnostics and broadcast stores."""

import pytest
import torch

import flydsl.compiler as flyc
import flydsl.expr as fx
from flydsl._mlir import ir

pytestmark = [pytest.mark.l2_device, pytest.mark.rocm_lower]

if not torch.cuda.is_available():
    pytest.skip("CUDA/ROCm not available", allow_module_level=True)


@flyc.kernel
def retile_mismatch_kernel(
    A: fx.Tensor,
    B: fx.Tensor,
    tile_m: fx.Constexpr[int],
    tile_n: fx.Constexpr[int],
):
    bx = fx.block_idx.x
    by = fx.block_idx.y
    tid = fx.thread_idx.x
    A = A[None, bx, by]

    tv_tile_mn = (32, 64)
    tv_layout = fx.make_layout(((8, 32), 8), ((256, 1), 32))
    load_atom = fx.make_copy_atom(fx.UniversalCopy128b(), fx.Float32)
    store_atom = fx.make_copy_atom(fx.UniversalAtomicAdd(fx.Float32), fx.Float32)
    tiled_load = fx.make_tiled_copy(load_atom, tv_layout, tv_tile_mn)
    tiled_store = fx.make_tiled_copy(store_atom, tv_layout, tv_tile_mn)
    broadcast_b = fx.composition(B, fx.make_layout((tile_m, tile_n), (0, 0)))
    part_a = tiled_load.get_slice(tid).partition_S(A)
    tiled_store_slice = tiled_store.get_slice(tid)
    part_b = tiled_store_slice.partition_D(broadcast_b)

    for bm in fx.range_constexpr(tile_m // tv_tile_mn[0]):
        for bn in fx.range_constexpr(tile_n // tv_tile_mn[1]):
            frag = fx.make_fragment_like(part_a[None, bm, bn])
            fx.copy(load_atom, part_a[None, bm, bn], frag)
            frag = tiled_store_slice.retile(frag)
            fx.copy(store_atom, frag, part_b[None, bm, bn])


@flyc.jit
def retile_mismatch(
    A: fx.Tensor,
    B: fx.Tensor,
    tile_m: fx.Constexpr[int],
    tile_n: fx.Constexpr[int],
):
    A = fx.tiled_divide(A, (tile_m, tile_n))
    grid_x = fx.get_scalar(A.shape[1])
    grid_y = fx.get_scalar(A.shape[2])
    retile_mismatch_kernel(A, B, tile_m, tile_n).launch(
        grid=(grid_x, grid_y, 1), block=(256, 1, 1)
    )


@flyc.kernel
def broadcast_sum_kernel(
    A: fx.Tensor,
    B: fx.Tensor,
    tile_m: fx.Constexpr[int],
    tile_n: fx.Constexpr[int],
):
    bx = fx.block_idx.x
    by = fx.block_idx.y
    tid = fx.thread_idx.x
    A = A[None, bx, by]

    tv_tile_mn = (32, 64)
    tv_layout = fx.make_layout(((8, 32), 8), ((256, 1), 32))
    load_atom = fx.make_copy_atom(fx.UniversalCopy128b(), fx.Float32)
    store_atom = fx.make_copy_atom(fx.UniversalAtomicAdd(fx.Float32), fx.Float32)
    tiled_load = fx.make_tiled_copy(load_atom, tv_layout, tv_tile_mn)
    tiled_store = fx.make_tiled_copy(store_atom, tv_layout, tv_tile_mn)
    broadcast_b = fx.composition(B, fx.make_layout((tile_m, tile_n), (0, 0)))
    part_a = tiled_load.get_slice(tid).partition_S(A)
    part_b = tiled_store.get_slice(tid).partition_D(broadcast_b)

    for bm in fx.range_constexpr(tile_m // tv_tile_mn[0]):
        for bn in fx.range_constexpr(tile_n // tv_tile_mn[1]):
            frag = fx.make_fragment_like(part_a[None, bm, bn])
            fx.copy(load_atom, part_a[None, bm, bn], frag)
            frag = fx.make_view(fx.get_iter(frag), fx.make_layout((1, 8), (0, 1)))
            fx.copy(store_atom, frag, part_b[None, bm, bn])


@flyc.jit
def broadcast_sum(
    A: fx.Tensor,
    B: fx.Tensor,
    tile_m: fx.Constexpr[int],
    tile_n: fx.Constexpr[int],
):
    A = fx.tiled_divide(A, (tile_m, tile_n))
    grid_x = fx.get_scalar(A.shape[1])
    grid_y = fx.get_scalar(A.shape[2])
    broadcast_sum_kernel(A, B, tile_m, tile_n).launch(
        grid=(grid_x, grid_y, 1), block=(256, 1, 1)
    )


def test_retile_rank_mismatch_reports_diagnostic():
    A = torch.randn(64, 64, device="cuda", dtype=torch.float32)
    B = torch.zeros(1, device="cuda", dtype=torch.float32)

    with pytest.raises(ir.MLIRError, match="input layout rank"):
        retile_mismatch(A, B, 64, 64)


def test_broadcast_atomic_sum_matches_torch_with_guards():
    sentinel = -987654.0
    torch.manual_seed(732)
    a_storage = torch.full((64 * 64 + 2,), sentinel, device="cuda", dtype=torch.float32)
    a_storage[1:-1] = torch.randn(64 * 64, device="cuda", dtype=torch.float32)
    A = a_storage[1:-1].view(64, 64)
    b_storage = torch.full((3,), sentinel, device="cuda", dtype=torch.float32)
    b_storage[1] = 0.0
    B = b_storage[1:2]

    broadcast_sum(A, B, 64, 64)
    torch.cuda.synchronize()

    expected = A.sum()
    assert torch.allclose(B, expected, rtol=2e-6, atol=2e-5)
    assert torch.equal(a_storage[[0, -1]], torch.full((2,), sentinel, device="cuda"))
    assert torch.equal(b_storage[[0, 2]], torch.full((2,), sentinel, device="cuda"))
