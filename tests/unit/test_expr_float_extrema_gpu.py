#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""GPU contract coverage for the public FP32 expression extrema APIs."""

import math
from pathlib import Path

import pytest

import flydsl.compiler as flyc
import flydsl.expr as fx

try:
    import torch
except ImportError:
    torch = None


pytestmark = [pytest.mark.l2_device, pytest.mark.rocm_lower]

if torch is None or not torch.cuda.is_available():
    pytest.skip("CUDA/ROCm not available", allow_module_level=True)


@flyc.kernel
def _float_extrema_kernel(
    lhs: fx.Pointer,
    rhs: fx.Pointer,
    maximum: fx.Pointer,
    minimum: fx.Pointer,
    maxnum: fx.Pointer,
    minnum: fx.Pointer,
    maximum_compat: fx.Pointer,
    minimum_compat: fx.Pointer,
    size: fx.Int32,
):
    idx = fx.block_idx.x * fx.block_dim.x + fx.thread_idx.x
    if idx < size:
        a = lhs[idx]
        b = rhs[idx]
        maximum[idx] = fx.max(a, b)
        minimum[idx] = fx.min(a, b)
        maxnum[idx] = fx.maxnumf(a, b)
        minnum[idx] = fx.minnumf(a, b)
        maximum_compat[idx] = fx.maximumf(a, b)
        minimum_compat[idx] = fx.minimumf(a, b)


@flyc.jit
def _run_float_extrema(
    lhs: fx.Pointer,
    rhs: fx.Pointer,
    maximum: fx.Pointer,
    minimum: fx.Pointer,
    maxnum: fx.Pointer,
    minnum: fx.Pointer,
    maximum_compat: fx.Pointer,
    minimum_compat: fx.Pointer,
    size: fx.Int32,
    stream: fx.Stream = fx.Stream(None),
):
    block_dim = 64
    grid_x = (size + block_dim - 1) // block_dim
    _float_extrema_kernel(
        lhs,
        rhs,
        maximum,
        minimum,
        maxnum,
        minnum,
        maximum_compat,
        minimum_compat,
        size,
    ).launch(grid=(grid_x, 1, 1), block=(block_dim, 1, 1), stream=stream)


def _ptr(tensor):
    return flyc.from_c_void_p(fx.Float32, tensor.data_ptr())


def _ieee_propagating_extreme(lhs, rhs, *, take_max):
    """Independent reference for MLIR maximumf/minimumf semantics."""
    result = []
    for a, b in zip(lhs.tolist(), rhs.tolist()):
        if math.isnan(a) or math.isnan(b):
            result.append(float("nan"))
        elif a == 0.0 and b == 0.0:
            result.append(0.0 if take_max else -0.0)
        else:
            result.append(max(a, b) if take_max else min(a, b))
    return torch.tensor(result, dtype=torch.float32)


def _libm_number_extreme(lhs, rhs, *, take_max):
    """Independent reference for the documented libm fmax/fmin contract."""
    result = []
    for a, b in zip(lhs.tolist(), rhs.tolist()):
        if math.isnan(a):
            result.append(b)
        elif math.isnan(b):
            result.append(a)
        elif a == 0.0 and b == 0.0:
            result.append(0.0 if take_max else -0.0)
        else:
            result.append(max(a, b) if take_max else min(a, b))
    return torch.tensor(result, dtype=torch.float32)


def _assert_float_contract(actual, expected):
    assert torch.equal(torch.isnan(actual), torch.isnan(expected))
    finite = ~torch.isnan(expected)
    assert torch.equal(actual[finite], expected[finite])
    zero = finite & (expected == 0)
    assert torch.equal(torch.signbit(actual[zero]), torch.signbit(expected[zero]))


def test_public_fp32_extrema_execute_contracts_on_gpu():
    lhs_cpu = torch.tensor(
        [-7.5, 4.0, 3.25, float("nan"), 8.0, float("nan"), -0.0, 0.0],
        dtype=torch.float32,
    )
    rhs_cpu = torch.tensor(
        [2.0, -9.0, 3.25, 6.0, float("nan"), float("nan"), 0.0, -0.0],
        dtype=torch.float32,
    )
    lhs = lhs_cpu.cuda()
    rhs = rhs_cpu.cuda()
    outputs = [torch.empty_like(lhs) for _ in range(6)]

    _run_float_extrema(
        _ptr(lhs),
        _ptr(rhs),
        *(_ptr(output) for output in outputs),
        lhs.numel(),
        stream=torch.cuda.current_stream(),
    )
    torch.cuda.synchronize()
    maximum, minimum, maxnum, minnum, maximum_compat, minimum_compat = [
        output.cpu() for output in outputs
    ]

    expected_maximum = _ieee_propagating_extreme(lhs_cpu, rhs_cpu, take_max=True)
    expected_minimum = _ieee_propagating_extreme(lhs_cpu, rhs_cpu, take_max=False)
    expected_maxnum = _libm_number_extreme(lhs_cpu, rhs_cpu, take_max=True)
    expected_minnum = _libm_number_extreme(lhs_cpu, rhs_cpu, take_max=False)

    _assert_float_contract(maximum, expected_maximum)
    _assert_float_contract(minimum, expected_minimum)
    _assert_float_contract(maximum_compat, expected_maximum)
    _assert_float_contract(minimum_compat, expected_minimum)
    _assert_float_contract(maxnum, expected_maxnum)
    _assert_float_contract(minnum, expected_minnum)

    imported_native = __import__("flydsl._mlir", fromlist=["__path__"])
    assert "/native-build/" in str(Path(next(iter(imported_native.__path__))).resolve())
