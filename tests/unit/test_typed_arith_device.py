#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""Run typed extrema semantics on a real GPU."""

import math

import pytest
import torch

import flydsl.compiler as flyc
import flydsl.expr as fx

pytestmark = [pytest.mark.l2_device, pytest.mark.rocm_lower]


@flyc.kernel
def int_extrema_kernel(a: fx.Int32, b: fx.Int32, maximum: fx.Pointer, minimum: fx.Pointer):
    maximum[0] = fx.max(a, b)
    minimum[0] = fx.min(a, b)


@flyc.kernel
def uint_extrema_kernel(a: fx.Uint32, b: fx.Uint32, maximum: fx.Pointer, minimum: fx.Pointer):
    maximum[0] = fx.max(a, b)
    minimum[0] = fx.min(a, b)


@flyc.kernel
def float_extrema_kernel(
    a: fx.Float32,
    b: fx.Float32,
    maximum: fx.Pointer,
    minimum: fx.Pointer,
    maxnum: fx.Pointer,
    minnum: fx.Pointer,
):
    maximum[0] = fx.max(a, b)
    minimum[0] = fx.min(a, b)
    maxnum[0] = fx.maxnumf(a, b)
    minnum[0] = fx.minnumf(a, b)


@flyc.jit
def int_extrema(
    a: fx.Int32,
    b: fx.Int32,
    maximum: fx.Pointer,
    minimum: fx.Pointer,
    stream: fx.Stream = fx.Stream(None),
):
    int_extrema_kernel(a, b, maximum, minimum).launch(grid=(1, 1, 1), block=(1, 1, 1), stream=stream)


@flyc.jit
def uint_extrema(
    a: fx.Uint32,
    b: fx.Uint32,
    maximum: fx.Pointer,
    minimum: fx.Pointer,
    stream: fx.Stream = fx.Stream(None),
):
    uint_extrema_kernel(a, b, maximum, minimum).launch(grid=(1, 1, 1), block=(1, 1, 1), stream=stream)


@flyc.jit
def float_extrema(
    a: fx.Float32,
    b: fx.Float32,
    maximum: fx.Pointer,
    minimum: fx.Pointer,
    maxnum: fx.Pointer,
    minnum: fx.Pointer,
    stream: fx.Stream = fx.Stream(None),
):
    float_extrema_kernel(a, b, maximum, minimum, maxnum, minnum).launch(grid=(1, 1, 1), block=(1, 1, 1), stream=stream)


def _pointer(dtype, tensor):
    return flyc.from_c_void_p(dtype, tensor.data_ptr())


def _assert_float_result(result, expected):
    if expected is None:
        return
    if math.isnan(expected):
        assert math.isnan(result.item())
        return

    assert result.item() == expected
    expected_bits = torch.tensor(expected, dtype=torch.float32).view(torch.int32).item()
    assert result.view(torch.int32).item() == expected_bits


@pytest.mark.skipif(torch is None or not torch.cuda.is_available(), reason="requires GPU")
def test_integer_extrema_signedness_on_gpu():
    stream = torch.cuda.Stream()
    cases = [
        (-5, 3, 3, -5),
        (3, -5, 3, -5),
        (-(2**31), 2**31 - 1, 2**31 - 1, -(2**31)),
    ]
    for lhs, rhs, expected_max, expected_min in cases:
        maximum = torch.zeros(1, dtype=torch.int32, device="cuda")
        minimum = torch.zeros(1, dtype=torch.int32, device="cuda")
        int_extrema(
            lhs,
            rhs,
            _pointer(fx.Int32, maximum),
            _pointer(fx.Int32, minimum),
            stream=stream,
        )
        torch.cuda.synchronize()
        assert maximum.item() == expected_max
        assert minimum.item() == expected_min


@pytest.mark.skipif(torch is None or not torch.cuda.is_available(), reason="requires GPU")
def test_unsigned_extrema_on_gpu():
    stream = torch.cuda.Stream()
    cases = [
        (0xFFFFFFFB, 3, 0xFFFFFFFB, 3),
        (3, 0xFFFFFFFB, 0xFFFFFFFB, 3),
        (0, 0xFFFFFFFF, 0xFFFFFFFF, 0),
    ]
    for lhs, rhs, expected_max, expected_min in cases:
        maximum = torch.zeros(1, dtype=torch.uint32, device="cuda")
        minimum = torch.zeros(1, dtype=torch.uint32, device="cuda")
        uint_extrema(
            lhs,
            rhs,
            _pointer(fx.Uint32, maximum),
            _pointer(fx.Uint32, minimum),
            stream=stream,
        )
        torch.cuda.synchronize()
        assert maximum.item() == expected_max
        assert minimum.item() == expected_min


@pytest.mark.skipif(torch is None or not torch.cuda.is_available(), reason="requires GPU")
def test_float_extrema_semantics_on_gpu():
    stream = torch.cuda.Stream()
    nan = math.nan
    cases = [
        (-1.25, 2.5, 2.5, -1.25, 2.5, -1.25),
        (2.5, -1.25, 2.5, -1.25, 2.5, -1.25),
        (nan, 7.0, nan, nan, 7.0, 7.0),
        (7.0, nan, nan, nan, 7.0, 7.0),
        (-0.0, 0.0, 0.0, -0.0, None, None),
        (0.0, -0.0, 0.0, -0.0, None, None),
        (-0.0, -0.0, -0.0, -0.0, None, None),
        (0.0, 0.0, 0.0, 0.0, None, None),
    ]
    for lhs, rhs, expected_max, expected_min, expected_maxnum, expected_minnum in cases:
        outputs = [torch.zeros(1, dtype=torch.float32, device="cuda") for _ in range(4)]
        float_extrema(lhs, rhs, *(_pointer(fx.Float32, output) for output in outputs), stream=stream)
        torch.cuda.synchronize()
        _assert_float_result(outputs[0], expected_max)
        _assert_float_result(outputs[1], expected_min)
        _assert_float_result(outputs[2], expected_maxnum)
        _assert_float_result(outputs[3], expected_minnum)
