import pytest
import torch

import flydsl.compiler as flyc
import flydsl.expr as fx

pytestmark = [pytest.mark.l2_device, pytest.mark.rocm_lower]


@flyc.kernel
def signed32_kernel(
    shifted: fx.Pointer,
    cast8: fx.Pointer,
    cast16: fx.Pointer,
    cast32: fx.Pointer,
    cast64: fx.Pointer,
    n: fx.Int32,
    shift: fx.Int32,
):
    idx = fx.block_idx.x * fx.block_dim.x + fx.thread_idx.x
    if idx < n:
        values = fx.Vector.from_elements(
            [0, 1, 0x7FFFFFFF, -0x80000000, -1], fx.Int32
        )
        shifted[idx] = (values >> shift)[idx]
        cast8[idx] = values.to(fx.Int8)[idx]
        cast16[idx] = values.to(fx.Int16)[idx]
        cast32[idx] = values.to(fx.Int32)[idx]
        cast64[idx] = values.to(fx.Int64)[idx]


@flyc.jit
def signed32(
    shifted: fx.Pointer,
    cast8: fx.Pointer,
    cast16: fx.Pointer,
    cast32: fx.Pointer,
    cast64: fx.Pointer,
    n: fx.Int32,
    shift: fx.Int32,
    stream: fx.Stream = fx.Stream(None),
):
    block_dim = 64
    grid_x = (n + block_dim - 1) // block_dim
    signed32_kernel(
        shifted, cast8, cast16, cast32, cast64, n, shift
    ).launch(grid=(grid_x, 1, 1), block=(block_dim, 1, 1), stream=stream)


@flyc.kernel
def unsigned32_kernel(
    shifted: fx.Pointer,
    cast8: fx.Pointer,
    cast16: fx.Pointer,
    cast32: fx.Pointer,
    cast64: fx.Pointer,
    n: fx.Int32,
    shift: fx.Int32,
):
    idx = fx.block_idx.x * fx.block_dim.x + fx.thread_idx.x
    if idx < n:
        values = fx.Vector.from_elements(
            [0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF], fx.Uint32
        )
        shifted[idx] = (values >> shift)[idx]
        cast8[idx] = values.to(fx.Uint8)[idx]
        cast16[idx] = values.to(fx.Uint16)[idx]
        cast32[idx] = values.to(fx.Uint32)[idx]
        cast64[idx] = values.to(fx.Uint64)[idx]


@flyc.jit
def unsigned32(
    shifted: fx.Pointer,
    cast8: fx.Pointer,
    cast16: fx.Pointer,
    cast32: fx.Pointer,
    cast64: fx.Pointer,
    n: fx.Int32,
    shift: fx.Int32,
    stream: fx.Stream = fx.Stream(None),
):
    block_dim = 64
    grid_x = (n + block_dim - 1) // block_dim
    unsigned32_kernel(
        shifted, cast8, cast16, cast32, cast64, n, shift
    ).launch(grid=(grid_x, 1, 1), block=(block_dim, 1, 1), stream=stream)


@flyc.kernel
def signed64_kernel(
    shifted: fx.Pointer,
    cast8: fx.Pointer,
    cast16: fx.Pointer,
    cast32: fx.Pointer,
    cast64: fx.Pointer,
    n: fx.Int32,
    shift: fx.Int32,
):
    idx = fx.block_idx.x * fx.block_dim.x + fx.thread_idx.x
    if idx < n:
        values = fx.Vector.from_elements(
            [0, 1, 0x7FFFFFFFFFFFFFFF, -0x8000000000000000, -1], fx.Int64
        )
        shifted[idx] = (values >> shift)[idx]
        cast8[idx] = values.to(fx.Int8)[idx]
        cast16[idx] = values.to(fx.Int16)[idx]
        cast32[idx] = values.to(fx.Int32)[idx]
        cast64[idx] = values.to(fx.Int64)[idx]


@flyc.jit
def signed64(
    shifted: fx.Pointer,
    cast8: fx.Pointer,
    cast16: fx.Pointer,
    cast32: fx.Pointer,
    cast64: fx.Pointer,
    n: fx.Int32,
    shift: fx.Int32,
    stream: fx.Stream = fx.Stream(None),
):
    block_dim = 64
    grid_x = (n + block_dim - 1) // block_dim
    signed64_kernel(
        shifted, cast8, cast16, cast32, cast64, n, shift
    ).launch(grid=(grid_x, 1, 1), block=(block_dim, 1, 1), stream=stream)


@flyc.kernel
def unsigned64_kernel(
    shifted: fx.Pointer,
    cast8: fx.Pointer,
    cast16: fx.Pointer,
    cast32: fx.Pointer,
    cast64: fx.Pointer,
    n: fx.Int32,
    shift: fx.Int32,
):
    idx = fx.block_idx.x * fx.block_dim.x + fx.thread_idx.x
    if idx < n:
        values = fx.Vector.from_elements(
            [
                0,
                1,
                0x7FFFFFFFFFFFFFFF,
                0x8000000000000000,
                0xFFFFFFFFFFFFFFFF,
            ],
            fx.Uint64,
        )
        shifted[idx] = (values >> shift)[idx]
        cast8[idx] = values.to(fx.Uint8)[idx]
        cast16[idx] = values.to(fx.Uint16)[idx]
        cast32[idx] = values.to(fx.Uint32)[idx]
        cast64[idx] = values.to(fx.Uint64)[idx]


@flyc.jit
def unsigned64(
    shifted: fx.Pointer,
    cast8: fx.Pointer,
    cast16: fx.Pointer,
    cast32: fx.Pointer,
    cast64: fx.Pointer,
    n: fx.Int32,
    shift: fx.Int32,
    stream: fx.Stream = fx.Stream(None),
):
    block_dim = 64
    grid_x = (n + block_dim - 1) // block_dim
    unsigned64_kernel(
        shifted, cast8, cast16, cast32, cast64, n, shift
    ).launch(grid=(grid_x, 1, 1), block=(block_dim, 1, 1), stream=stream)


def _signed(value, width):
    value &= (1 << width) - 1
    return value - (1 << width) if value >= (1 << (width - 1)) else value


def _allocate_outputs(device, count, signed):
    dtypes = (
        [torch.int8, torch.int16, torch.int32, torch.int64]
        if signed
        else [torch.uint8, torch.uint16, torch.uint32, torch.uint64]
    )
    return [torch.zeros(count, dtype=dtype, device=device) for dtype in dtypes]


def _pointer(tensor, dtype):
    return flyc.from_c_void_p(dtype, tensor.data_ptr())


@pytest.mark.parametrize("shift", [0, 1, 31])
def test_signed32_expression_paths(shift):
    values = [0, 1, 0x7FFFFFFF, -0x80000000, -1]
    expected_shift = [value >> shift for value in values]
    expected_cast8 = [_signed(value, 8) for value in values]
    expected_cast16 = [_signed(value, 16) for value in values]
    expected_cast32 = [_signed(value, 32) for value in values]
    expected_cast64 = values

    device = torch.device("cuda")
    shifted = torch.zeros(len(values), dtype=torch.int32, device=device)
    cast8, cast16, cast32, cast64 = _allocate_outputs(device, len(values), signed=True)
    stream = torch.cuda.Stream()
    signed32(
        _pointer(shifted, fx.Int32),
        _pointer(cast8, fx.Int8),
        _pointer(cast16, fx.Int16),
        _pointer(cast32, fx.Int32),
        _pointer(cast64, fx.Int64),
        len(values),
        shift,
        stream=stream,
    )
    torch.cuda.synchronize()

    assert shifted.cpu().tolist() == expected_shift
    assert cast8.cpu().to(torch.int64).tolist() == expected_cast8
    assert cast16.cpu().to(torch.int64).tolist() == expected_cast16
    assert cast32.cpu().to(torch.int64).tolist() == expected_cast32
    assert cast64.cpu().tolist() == expected_cast64


@pytest.mark.parametrize("shift", [0, 1, 31])
def test_unsigned32_expression_paths(shift):
    bit_values = [0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF]
    expected_shift = [(value >> shift) & 0xFFFFFFFF for value in bit_values]
    expected_cast8 = [value & 0xFF for value in bit_values]
    expected_cast16 = [value & 0xFFFF for value in bit_values]
    expected_cast32 = bit_values
    expected_cast64 = bit_values

    device = torch.device("cuda")
    shifted = torch.zeros(len(bit_values), dtype=torch.uint32, device=device)
    cast8, cast16, cast32, cast64 = _allocate_outputs(device, len(bit_values), signed=False)
    stream = torch.cuda.Stream()
    unsigned32(
        _pointer(shifted, fx.Uint32),
        _pointer(cast8, fx.Uint8),
        _pointer(cast16, fx.Uint16),
        _pointer(cast32, fx.Uint32),
        _pointer(cast64, fx.Uint64),
        len(bit_values),
        shift,
        stream=stream,
    )
    torch.cuda.synchronize()

    assert shifted.view(torch.int32).cpu().to(torch.int64).tolist() == [
        _signed(value, 32) for value in expected_shift
    ]
    assert cast8.view(torch.int8).cpu().to(torch.int64).tolist() == [
        _signed(value, 8) for value in expected_cast8
    ]
    assert cast16.view(torch.int16).cpu().to(torch.int64).tolist() == [
        _signed(value, 16) for value in expected_cast16
    ]
    assert cast32.view(torch.int32).cpu().to(torch.int64).tolist() == [
        _signed(value, 32) for value in expected_cast32
    ]
    assert cast64.view(torch.int64).cpu().tolist() == [
        _signed(value, 64) for value in expected_cast64
    ]


@pytest.mark.parametrize("shift", [0, 1, 63])
def test_signed64_expression_paths(shift):
    values = [0, 1, 0x7FFFFFFFFFFFFFFF, -0x8000000000000000, -1]
    expected_shift = [value >> shift for value in values]
    expected_cast8 = [_signed(value, 8) for value in values]
    expected_cast16 = [_signed(value, 16) for value in values]
    expected_cast32 = [_signed(value, 32) for value in values]
    expected_cast64 = values

    device = torch.device("cuda")
    shifted = torch.zeros(len(values), dtype=torch.int64, device=device)
    cast8, cast16, cast32, cast64 = _allocate_outputs(device, len(values), signed=True)
    stream = torch.cuda.Stream()
    signed64(
        _pointer(shifted, fx.Int64),
        _pointer(cast8, fx.Int8),
        _pointer(cast16, fx.Int16),
        _pointer(cast32, fx.Int32),
        _pointer(cast64, fx.Int64),
        len(values),
        shift,
        stream=stream,
    )
    torch.cuda.synchronize()

    assert shifted.cpu().tolist() == expected_shift
    assert cast8.cpu().to(torch.int64).tolist() == expected_cast8
    assert cast16.cpu().to(torch.int64).tolist() == expected_cast16
    assert cast32.cpu().to(torch.int64).tolist() == expected_cast32
    assert cast64.cpu().tolist() == expected_cast64


@pytest.mark.parametrize("shift", [0, 1, 63])
def test_unsigned64_expression_paths(shift):
    bit_values = [
        0,
        1,
        0x7FFFFFFFFFFFFFFF,
        0x8000000000000000,
        0xFFFFFFFFFFFFFFFF,
    ]
    expected_shift = [(value >> shift) & 0xFFFFFFFFFFFFFFFF for value in bit_values]
    expected_cast8 = [value & 0xFF for value in bit_values]
    expected_cast16 = [value & 0xFFFF for value in bit_values]
    expected_cast32 = [value & 0xFFFFFFFF for value in bit_values]
    expected_cast64 = bit_values

    device = torch.device("cuda")
    shifted = torch.zeros(len(bit_values), dtype=torch.uint64, device=device)
    cast8, cast16, cast32, cast64 = _allocate_outputs(device, len(bit_values), signed=False)
    stream = torch.cuda.Stream()
    unsigned64(
        _pointer(shifted, fx.Uint64),
        _pointer(cast8, fx.Uint8),
        _pointer(cast16, fx.Uint16),
        _pointer(cast32, fx.Uint32),
        _pointer(cast64, fx.Uint64),
        len(bit_values),
        shift,
        stream=stream,
    )
    torch.cuda.synchronize()

    assert shifted.view(torch.int64).cpu().tolist() == [
        _signed(value, 64) for value in expected_shift
    ]
    assert cast8.view(torch.int8).cpu().to(torch.int64).tolist() == [
        _signed(value, 8) for value in expected_cast8
    ]
    assert cast16.view(torch.int16).cpu().to(torch.int64).tolist() == [
        _signed(value, 16) for value in expected_cast16
    ]
    assert cast32.view(torch.int32).cpu().to(torch.int64).tolist() == [
        _signed(value, 32) for value in expected_cast32
    ]
    assert cast64.view(torch.int64).cpu().tolist() == [
        _signed(value, 64) for value in expected_cast64
    ]
