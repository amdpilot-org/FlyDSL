#!/usr/bin/env python3

"""End-to-end checks for the public Vector.reduce extrema contract."""

import math

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
def _max_kernel(values: fx.Tensor, results: fx.Tensor):
    vector = fx.Vector.from_elements(
        [values[0], values[1], values[2], values[3]], dtype=fx.Float32
    )
    results[fx.thread_idx.x] = vector.reduce("max")


@flyc.kernel
def _min_kernel(values: fx.Tensor, results: fx.Tensor):
    vector = fx.Vector.from_elements(
        [values[0], values[1], values[2], values[3]], dtype=fx.Float32
    )
    results[fx.thread_idx.x] = vector.reduce("min")


@flyc.jit
def _launch_max(
    values: fx.Tensor,
    results: fx.Tensor,
    block_dim: fx.Constexpr[int],
    stream: fx.Stream = fx.Stream(None),
):
    _max_kernel(values, results).launch(
        grid=(1, 1, 1), block=(block_dim, 1, 1), stream=stream
    )


@flyc.jit
def _launch_min(
    values: fx.Tensor,
    results: fx.Tensor,
    block_dim: fx.Constexpr[int],
    stream: fx.Stream = fx.Stream(None),
):
    _min_kernel(values, results).launch(
        grid=(1, 1, 1), block=(block_dim, 1, 1), stream=stream
    )


def _maxnum_reference(values):
    result = values[0]
    for value in values[1:]:
        if math.isnan(result):
            result = value
        elif not math.isnan(value) and value > result:
            result = value
    return result


def _minimum_reference(values):
    result = values[0]
    for value in values[1:]:
        if math.isnan(result) or math.isnan(value):
            return math.nan
        if value < result or (
            value == 0 and math.copysign(1, value) < math.copysign(1, result)
        ):
            result = value
    return result


def _matches_reference(op, values, actual):
    if op == "max":
        if all(value == 0 for value in values):
            return actual == 0
        return actual == _maxnum_reference(values)

    expected = _minimum_reference(values)
    if math.isnan(expected):
        return math.isnan(actual)
    return actual == expected and math.copysign(1, actual) == math.copysign(1, expected)


@pytest.mark.parametrize("block_dim", [64, 128])
@pytest.mark.parametrize("op", ["max", "min"])
@pytest.mark.parametrize(
    ("name", "values"),
    [
        ("finite", [1.0, -3.0, 2.0, 0.0]),
        ("nan", [math.nan, 1.0, 0.0, 0.0]),
        ("infinity", [-math.inf, 1.0, math.inf, 0.0]),
        ("signed_zero", [-0.0, 0.0, 0.0, 0.0]),
    ],
)
def test_vector_reduce_extrema_contract(block_dim, op, name, values):
    device_values = torch.tensor(values, dtype=torch.float32, device="cuda")
    device_results = torch.empty(block_dim, dtype=torch.float32, device="cuda")
    stream = torch.cuda.Stream()

    if op == "max":
        _launch_max(device_values, device_results, block_dim, stream=stream)
    else:
        _launch_min(device_values, device_results, block_dim, stream=stream)
    torch.cuda.synchronize()

    assert all(
        _matches_reference(op, values, result.item()) for result in device_results
    )
