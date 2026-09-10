#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""GPU conformance tests for signed integer floor division and remainder."""

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
def signed_div_rem_kernel(
    lhs: fx.Pointer,
    rhs: fx.Pointer,
    quotient: fx.Pointer,
    remainder: fx.Pointer,
    block_dim: fx.Constexpr[int],
):
    idx = fx.block_idx.x * block_dim + fx.thread_idx.x
    lhs_value = (lhs + idx).load()
    rhs_value = (rhs + idx).load()
    (quotient + idx).store(lhs_value // rhs_value)
    (remainder + idx).store(lhs_value % rhs_value)


@flyc.jit
def signed_div_rem(
    lhs: fx.Pointer,
    rhs: fx.Pointer,
    quotient: fx.Pointer,
    remainder: fx.Pointer,
    n: fx.Int32,
    block_dim: fx.Constexpr[int],
    stream: fx.Stream = fx.Stream(None),
):
    grid_x = (n + block_dim - 1) // block_dim
    signed_div_rem_kernel(
        lhs, rhs, quotient, remainder, block_dim
    ).launch(
        grid=(grid_x, 1, 1),
        block=(block_dim, 1, 1),
        stream=stream,
    )


@flyc.kernel
def signed_trunc_div_rem_kernel(
    lhs: fx.Pointer,
    rhs: fx.Pointer,
    quotient: fx.Pointer,
    remainder: fx.Pointer,
    block_dim: fx.Constexpr[int],
):
    idx = fx.block_idx.x * block_dim + fx.thread_idx.x
    lhs_value = (lhs + idx).load()
    rhs_value = (rhs + idx).load()
    quotient_value = fx.arith.divsi(lhs_value.ir_value(), rhs_value.ir_value())
    remainder_value = fx.arith.remsi(lhs_value.ir_value(), rhs_value.ir_value())
    (quotient + idx).store(type(lhs_value)(quotient_value))
    (remainder + idx).store(type(lhs_value)(remainder_value))


@flyc.jit
def signed_trunc_div_rem(
    lhs: fx.Pointer,
    rhs: fx.Pointer,
    quotient: fx.Pointer,
    remainder: fx.Pointer,
    n: fx.Int32,
    block_dim: fx.Constexpr[int],
    stream: fx.Stream = fx.Stream(None),
):
    grid_x = (n + block_dim - 1) // block_dim
    signed_trunc_div_rem_kernel(
        lhs, rhs, quotient, remainder, block_dim
    ).launch(
        grid=(grid_x, 1, 1),
        block=(block_dim, 1, 1),
        stream=stream,
    )


@pytest.mark.parametrize(
    ("dtype", "torch_dtype"),
    [
        (fx.Int8, torch.int8),
        (fx.Int16, torch.int16),
        (fx.Int32, torch.int32),
        (fx.Int64, torch.int64),
    ],
)
def test_signed_floor_division_and_remainder(dtype, torch_dtype):
    lhs = torch.tensor(
        [7, -7, 7, -7, 123, -123, 1, -1],
        device="cuda",
        dtype=torch_dtype,
    )
    rhs = torch.tensor(
        [3, 3, -3, -3, 17, 17, 5, 5],
        device="cuda",
        dtype=torch_dtype,
    )
    quotient = torch.zeros_like(lhs)
    remainder = torch.zeros_like(lhs)
    stream = torch.cuda.Stream()
    lhs_ptr = flyc.from_c_void_p(dtype, lhs.data_ptr())
    rhs_ptr = flyc.from_c_void_p(dtype, rhs.data_ptr())
    quotient_ptr = flyc.from_c_void_p(dtype, quotient.data_ptr())
    remainder_ptr = flyc.from_c_void_p(dtype, remainder.data_ptr())

    signed_div_rem(
        lhs_ptr,
        rhs_ptr,
        quotient_ptr,
        remainder_ptr,
        lhs.numel(),
        lhs.numel(),
        stream=stream,
    )
    torch.cuda.synchronize()

    expected_quotient = torch.div(lhs, rhs, rounding_mode="floor")
    expected_remainder = lhs - expected_quotient * rhs
    assert torch.equal(quotient, expected_quotient)
    assert torch.equal(remainder, expected_remainder)


@pytest.mark.parametrize(
    ("dtype", "torch_dtype"),
    [
        (fx.Int8, torch.int8),
        (fx.Int16, torch.int16),
        (fx.Int32, torch.int32),
        (fx.Int64, torch.int64),
    ],
)
def test_signed_truncating_division_and_remainder(dtype, torch_dtype):
    lhs = torch.tensor(
        [7, -7, 7, -7, 123, -123, 1, -1],
        device="cuda",
        dtype=torch_dtype,
    )
    rhs = torch.tensor(
        [3, 3, -3, -3, 17, 17, 5, 5],
        device="cuda",
        dtype=torch_dtype,
    )
    quotient = torch.zeros_like(lhs)
    remainder = torch.zeros_like(lhs)
    stream = torch.cuda.Stream()
    lhs_ptr = flyc.from_c_void_p(dtype, lhs.data_ptr())
    rhs_ptr = flyc.from_c_void_p(dtype, rhs.data_ptr())
    quotient_ptr = flyc.from_c_void_p(dtype, quotient.data_ptr())
    remainder_ptr = flyc.from_c_void_p(dtype, remainder.data_ptr())

    signed_trunc_div_rem(
        lhs_ptr,
        rhs_ptr,
        quotient_ptr,
        remainder_ptr,
        lhs.numel(),
        lhs.numel(),
        stream=stream,
    )
    torch.cuda.synchronize()

    expected_quotient = torch.div(lhs, rhs, rounding_mode="trunc")
    expected_remainder = lhs - expected_quotient * rhs
    assert torch.equal(quotient, expected_quotient)
    assert torch.equal(remainder, expected_remainder)


def _int128_tensor(values):
    data = b"".join(value.to_bytes(16, "little", signed=True) for value in values)
    return torch.frombuffer(bytearray(data), dtype=torch.uint8).clone().cuda()


def _unpack_int128(tensor, index):
    value = tensor[index * 16 : (index + 1) * 16]
    return int.from_bytes(value.cpu().numpy().tobytes(), "little", signed=True)


def test_signed_int128_floor_division_and_remainder():
    lhs_values = [7, -7, 7, -7, 123, -123, 1, -1]
    rhs_values = [3, 3, -3, -3, 17, 17, 5, 5]
    lhs = _int128_tensor(lhs_values)
    rhs = _int128_tensor(rhs_values)
    quotient = _int128_tensor([0] * len(lhs_values))
    remainder = _int128_tensor([0] * len(lhs_values))
    stream = torch.cuda.Stream()
    lhs_ptr = flyc.from_c_void_p(fx.Int128, lhs.data_ptr())
    rhs_ptr = flyc.from_c_void_p(fx.Int128, rhs.data_ptr())
    quotient_ptr = flyc.from_c_void_p(fx.Int128, quotient.data_ptr())
    remainder_ptr = flyc.from_c_void_p(fx.Int128, remainder.data_ptr())

    signed_div_rem(
        lhs_ptr,
        rhs_ptr,
        quotient_ptr,
        remainder_ptr,
        len(lhs_values),
        len(lhs_values),
        stream=stream,
    )
    torch.cuda.synchronize()

    expected_quotient = [a // b for a, b in zip(lhs_values, rhs_values)]
    expected_remainder = [a - (a // b) * b for a, b in zip(lhs_values, rhs_values)]
    actual_quotient = [_unpack_int128(quotient, index) for index in range(len(lhs_values))]
    actual_remainder = [_unpack_int128(remainder, index) for index in range(len(lhs_values))]
    assert actual_quotient == expected_quotient
    assert actual_remainder == expected_remainder
