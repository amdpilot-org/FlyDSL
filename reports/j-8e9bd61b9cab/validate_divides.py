#!/usr/bin/env python3

import sys

import numpy as np
import torch

import flydsl.compiler as flyc
import flydsl.expr as fx


SHAPE = (64, 50, 80)
STRIDE = (16000, 160, 1)
THREADS_PER_BLOCK = 128
SENTINEL = -12345
TILERS = {
    0: (32,),
    1: (32, None, None),
    2: (32, None, 40),
}


def original_coordinates(linear):
    linear = np.asarray(linear, dtype=np.int64)
    i = linear // (SHAPE[1] * SHAPE[2])
    remainder = linear % (SHAPE[1] * SHAPE[2])
    j = remainder // SHAPE[2]
    k = remainder % SHAPE[2]
    return i, j, k


def oracle_indices(linear, tiler):
    coordinates = original_coordinates(linear)
    result = np.zeros_like(np.asarray(linear, dtype=np.int64))
    for mode, (coordinate, stride) in enumerate(zip(coordinates, STRIDE)):
        tile = tiler[mode] if mode < len(tiler) else None
        if tile is None:
            result += coordinate * stride
        else:
            result += (coordinate % tile) * stride + (coordinate // tile) * (tile * stride)
    return result


def oracle_layout(tiler, operation):
    logical_shape = []
    logical_stride = []
    for mode, (shape, stride) in enumerate(zip(SHAPE, STRIDE)):
        tile = tiler[mode] if mode < len(tiler) else None
        if tile is None:
            logical_shape.append(shape)
            logical_stride.append(stride)
        else:
            logical_shape.append((tile, shape // tile))
            logical_stride.append((stride, tile * stride))

    if operation == "logical_divide":
        return tuple(logical_shape), tuple(logical_stride)

    first_shape = []
    first_stride = []
    second_shape = []
    second_stride = []
    for mode, (shape, stride) in enumerate(zip(SHAPE, STRIDE)):
        if mode >= len(tiler):
            second_shape.append(shape)
            second_stride.append(stride)
            continue
        tile = tiler[mode]
        if tile is None:
            first_shape.append(1)
            first_stride.append(0)
            second_shape.append(shape)
            second_stride.append(stride)
        else:
            first_shape.append(tile)
            first_stride.append(stride)
            second_shape.append(shape // tile)
            second_stride.append(tile * stride)
    return (tuple(first_shape), tuple(second_shape)), (tuple(first_stride), tuple(second_stride))


@flyc.kernel
def divide_load_store_kernel(
    Input: fx.Pointer,
    Output: fx.Pointer,
    operation_id: fx.Constexpr[int],
    case_id: fx.Constexpr[int],
):
    linear = fx.block_idx.x * THREADS_PER_BLOCK + fx.thread_idx.x
    i = linear // (50 * 80)
    remainder = linear % (50 * 80)
    j = remainder // 80
    k = remainder % 80

    layout = fx.make_layout(SHAPE, STRIDE)
    tiler = (32,) if case_id == 0 else (32, None, None) if case_id == 1 else (32, None, 40)

    divided = (
        fx.logical_divide(layout, tiler)
        if operation_id == 0
        else fx.zipped_divide(layout, tiler)
    )
    coord = (
        (
            fx.make_coord((i % 32, i // 32), j, k)
            if case_id == 0
            else fx.make_coord((i % 32, i // 32), j, k)
            if case_id == 1
            else fx.make_coord((i % 32, i // 32), j, (k % 40, k // 40))
        )
        if operation_id == 0
        else (
            fx.make_coord((i % 32,), (i // 32, j, k))
            if case_id == 0
            else fx.make_coord((i % 32, 0, 0), (i // 32, j, k))
            if case_id == 1
            else fx.make_coord((i % 32, 0, k % 40), (i // 32, j, k // 40))
        )
    )

    index = fx.get_scalar(fx.crd2idx(coord, divided))
    value = (Input + index).load()
    (Output + index).store(value)


@flyc.jit
def launch_divide_load_store(
    Input: fx.Pointer,
    Output: fx.Pointer,
    operation_id: fx.Constexpr[int],
    case_id: fx.Constexpr[int],
    stream: fx.Stream = fx.Stream(None),
):
    element_count = SHAPE[0] * SHAPE[1] * SHAPE[2]
    grid_x = (element_count + THREADS_PER_BLOCK - 1) // THREADS_PER_BLOCK
    divide_load_store_kernel(Input, Output, operation_id, case_id).launch(
        grid=(grid_x, 1, 1),
        block=(THREADS_PER_BLOCK, 1, 1),
        stream=stream,
    )


@flyc.jit
def check_layouts():
    layout = fx.make_layout(SHAPE, STRIDE)
    for case_id, tiler in TILERS.items():
        logical = fx.logical_divide(layout, tiler)
        zipped = fx.zipped_divide(layout, tiler)
        expected_logical_shape, expected_logical_stride = oracle_layout(tiler, "logical_divide")
        expected_zipped_shape, expected_zipped_stride = oracle_layout(tiler, "zipped_divide")
        expected_logical = fx.make_layout(expected_logical_shape, expected_logical_stride)
        expected_zipped = fx.make_layout(expected_zipped_shape, expected_zipped_stride)
        assert str(logical) == str(expected_logical)
        assert str(zipped) == str(expected_zipped)
        print("layout", case_id, tiler)
        print("  logical_divide", logical)
        print("  zipped_divide", zipped)


def main():
    if torch.cuda.device_count() != 1:
        raise RuntimeError(f"expected one assigned GPU, found {torch.cuda.device_count()}")

    print("python", sys.executable)
    print("flydsl", fx.__name__, fx.__file__)
    print("torch", torch.__version__, torch.__file__)
    print("hip", torch.version.hip)
    print("gpu", torch.cuda.get_device_name(0))
    check_layouts()

    element_count = SHAPE[0] * SHAPE[1] * SHAPE[2]
    linear = np.arange(element_count, dtype=np.int64)
    expected_indices = oracle_indices(linear, TILERS[0])
    for tiler in TILERS.values():
        np.testing.assert_array_equal(oracle_indices(linear, tiler), expected_indices)

    cosize = int(expected_indices.max()) + 1
    buffer_size = cosize + 1024
    input_tensor = torch.arange(buffer_size, dtype=torch.int32, device="cuda")
    expected_values = input_tensor[torch.from_numpy(expected_indices).cuda()]

    for operation_id, operation_name in enumerate(("logical_divide", "zipped_divide")):
        for case_id, tiler in TILERS.items():
            output_tensor = torch.full((buffer_size,), SENTINEL, dtype=torch.int32, device="cuda")
            stream = torch.cuda.Stream()
            launch_divide_load_store(
                flyc.from_c_void_p(fx.Int32, input_tensor.data_ptr()),
                flyc.from_c_void_p(fx.Int32, output_tensor.data_ptr()),
                operation_id,
                case_id,
                stream=stream,
            )
            stream.synchronize()

            actual_values = output_tensor[torch.from_numpy(expected_indices).cuda()]
            mismatches = torch.count_nonzero(actual_values != expected_values).item()
            written_count = torch.count_nonzero(output_tensor[:cosize] != SENTINEL).item()
            sentinel_untouched = torch.count_nonzero(output_tensor[cosize:] == SENTINEL).item()
            print(
                "device",
                operation_name,
                tiler,
                "elements",
                element_count,
                "cosize",
                cosize,
                "mismatches",
                mismatches,
                "written",
                written_count,
                "sentinel_untouched",
                sentinel_untouched,
            )
            if mismatches != 0:
                raise AssertionError(f"{operation_name}({tiler}) produced incorrect indices")
            if written_count != element_count:
                raise AssertionError(f"{operation_name}({tiler}) did not write every element uniquely")
            if sentinel_untouched != buffer_size - cosize:
                raise AssertionError(f"{operation_name}({tiler}) wrote out of bounds")


if __name__ == "__main__":
    main()
