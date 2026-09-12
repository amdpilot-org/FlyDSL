#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""Generated-behavior coverage for the supported early-return contract."""

import pytest
import torch

import flydsl.compiler as flyc
import flydsl.expr as fx
from flydsl.expr import const_expr

pytestmark = [pytest.mark.l2_device, pytest.mark.rocm_lower]


@flyc.kernel
def _compile_time_return_kernel(Out: fx.Tensor, skip: fx.Constexpr[bool]):
    if const_expr(skip):
        return
    Out[0] = fx.Int32(41)


@flyc.jit
def _compile_time_return_launch(
    Out: fx.Tensor,
    skip: fx.Constexpr[bool],
    stream: fx.Stream = fx.Stream(None),
):
    _compile_time_return_kernel(Out, skip).launch(grid=(1, 1, 1), block=(1, 1, 1), stream=stream.value)


@flyc.kernel
def _nested_dynamic_if_kernel(Out: fx.Tensor, selector: fx.Int32):
    value = fx.Int32(3)
    if selector > fx.Int32(0):
        if selector > fx.Int32(1):
            value = fx.Int32(11)
        else:
            value = fx.Int32(7)
    Out[selector] = value


@flyc.jit
def _nested_dynamic_if_launch(
    Out: fx.Tensor,
    selector: fx.Int32,
    stream: fx.Stream = fx.Stream(None),
):
    _nested_dynamic_if_kernel(Out, selector).launch(grid=(1, 1, 1), block=(1, 1, 1), stream=stream.value)


def _tensor(values):
    out = torch.tensor(values, device="cuda", dtype=torch.int32)
    return out, flyc.from_torch_tensor(out).mark_layout_dynamic(leading_dim=0, divisibility=1)


def test_compile_time_conditional_return_preserves_function_return_semantics(monkeypatch):
    if not torch.cuda.is_available():
        pytest.skip("CUDA/ROCm device required")
    monkeypatch.setenv("FLYDSL_RUNTIME_ENABLE_CACHE", "0")

    skipped, t_skipped = _tensor([23])
    written, t_written = _tensor([23])
    _compile_time_return_launch(t_skipped, True)
    _compile_time_return_launch(t_written, False)
    torch.cuda.synchronize()

    # The compile-time true path returns before generating a store; the false
    # path generates and executes the store.
    torch.testing.assert_close(skipped.cpu(), torch.tensor([23], dtype=torch.int32), rtol=0, atol=0)
    torch.testing.assert_close(written.cpu(), torch.tensor([41], dtype=torch.int32), rtol=0, atol=0)


def test_nested_dynamic_conditionals_generate_and_execute_correctly(monkeypatch):
    if not torch.cuda.is_available():
        pytest.skip("CUDA/ROCm device required")
    monkeypatch.setenv("FLYDSL_RUNTIME_ENABLE_CACHE", "0")

    out, t_out = _tensor([-1, -1, -1])
    for selector in range(3):
        _nested_dynamic_if_launch(t_out, selector)
    torch.cuda.synchronize()

    reference = torch.tensor([3, 7, 11], dtype=torch.int32)
    torch.testing.assert_close(out.cpu(), reference, rtol=0, atol=0)

    compiled = list(_nested_dynamic_if_launch._mem_cache.values())
    assert compiled
    source_ir = compiled[-1].source_ir
    assert source_ir.count("scf.if") >= 2
