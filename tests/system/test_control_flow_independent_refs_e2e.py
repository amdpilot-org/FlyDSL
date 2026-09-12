#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

"""GPU regressions for independent values across dynamic control flow."""

import pytest
import torch

import flydsl.compiler as flyc
import flydsl.expr as fx

pytestmark = [pytest.mark.l2_device, pytest.mark.rocm_lower]


@flyc.kernel
def _branch_refs_kernel(Out: fx.Tensor, flag: fx.Int32):
    scalar = fx.Int32(3)
    scalar_ref = scalar
    vector = fx.Vector.filled((4,), 2, fx.Int32)
    vector_ref = vector

    if flag > fx.Int32(0):
        scalar = scalar + fx.Int32(10)
        vector = vector + fx.Int32(20)
    else:
        scalar = scalar - fx.Int32(1)
        vector = vector - fx.Int32(1)

    Out[0] = scalar
    Out[1] = scalar_ref
    Out[2] = vector.reduce(fx.ReductionOp.ADD)
    Out[3] = vector_ref.reduce(fx.ReductionOp.ADD)


@flyc.jit
def _branch_refs(Out: fx.Tensor, flag: fx.Int32, stream: fx.Stream = fx.Stream(None)):
    _branch_refs_kernel(Out, flag).launch(grid=(1, 1, 1), block=(1, 1, 1), stream=stream.value)


@flyc.kernel
def _loop_refs_kernel(Out: fx.Tensor, n: fx.Int32):
    scalar = fx.Int32(3)
    scalar_ref = scalar
    vector = fx.Vector.filled((4,), 2, fx.Int32)
    vector_ref = vector

    for i in range(n):
        if (i % fx.Int32(2)) == fx.Int32(0):
            scalar = scalar + fx.Int32(10)
            vector = vector + fx.Int32(20)
        else:
            scalar = scalar - fx.Int32(1)
            vector = vector - fx.Int32(1)

    Out[0] = scalar
    Out[1] = scalar_ref
    Out[2] = vector.reduce(fx.ReductionOp.ADD)
    Out[3] = vector_ref.reduce(fx.ReductionOp.ADD)


@flyc.jit
def _loop_refs(Out: fx.Tensor, n: fx.Int32, stream: fx.Stream = fx.Stream(None)):
    _loop_refs_kernel(Out, n).launch(grid=(1, 1, 1), block=(1, 1, 1), stream=stream.value)


@flyc.kernel
def _for_else_refs_kernel(Out: fx.Tensor, n: fx.Int32):
    scalar = fx.Int32(3)
    scalar_ref = scalar
    vector = fx.Vector.filled((4,), 2, fx.Int32)
    vector_ref = vector

    for _ in range(n):
        scalar = scalar + fx.Int32(1)
        vector = vector + fx.Int32(1)
    else:
        scalar = scalar + fx.Int32(10)
        vector = vector + fx.Int32(20)

    Out[0] = scalar
    Out[1] = scalar_ref
    Out[2] = vector.reduce(fx.ReductionOp.ADD)
    Out[3] = vector_ref.reduce(fx.ReductionOp.ADD)


@flyc.jit
def _for_else_refs(Out: fx.Tensor, n: fx.Int32, stream: fx.Stream = fx.Stream(None)):
    _for_else_refs_kernel(Out, n).launch(grid=(1, 1, 1), block=(1, 1, 1), stream=stream.value)


def _out():
    out = torch.zeros(4, device="cuda", dtype=torch.int32)
    return out, flyc.from_torch_tensor(out).mark_layout_dynamic(leading_dim=0, divisibility=1)


@pytest.mark.parametrize(("flag", "expected"), [(1, [13, 3, 88, 8]), (0, [2, 3, 4, 8])])
def test_branch_updates_do_not_modify_independent_refs(flag, expected):
    if not torch.cuda.is_available():
        pytest.skip("CUDA/ROCm device required")
    out, t_out = _out()
    _branch_refs(t_out, fx.Int32(flag))
    torch.cuda.synchronize()
    torch.testing.assert_close(out.cpu(), torch.tensor(expected, dtype=torch.int32), rtol=0, atol=0)


def test_nested_branch_loop_carries_updates_not_independent_refs():
    if not torch.cuda.is_available():
        pytest.skip("CUDA/ROCm device required")
    out, t_out = _out()
    _loop_refs(t_out, fx.Int32(4))
    torch.cuda.synchronize()
    # Two even iterations add 10/20, two odd iterations subtract 1.
    torch.testing.assert_close(out.cpu(), torch.tensor([21, 3, 160, 8], dtype=torch.int32), rtol=0, atol=0)


@pytest.mark.parametrize(("n", "expected"), [(0, [13, 3, 88, 8]), (3, [16, 3, 100, 8])])
def test_for_else_updates_values_and_preserves_independent_refs(n, expected):
    if not torch.cuda.is_available():
        pytest.skip("CUDA/ROCm device required")
    out, t_out = _out()
    _for_else_refs(t_out, fx.Int32(n))
    torch.cuda.synchronize()
    torch.testing.assert_close(out.cpu(), torch.tensor(expected, dtype=torch.int32), rtol=0, atol=0)
