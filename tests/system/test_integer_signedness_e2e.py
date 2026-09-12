# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

import pytest
import torch

import flydsl.compiler as flyc
import flydsl.expr as fx


@flyc.kernel
def _pointer_shift_kernel(src: fx.Pointer, dst: fx.Pointer, expected_name: fx.Constexpr[str]):
    assert src.element_type.__name__ == expected_name
    assert dst.element_type.__name__ == expected_name
    dst[0] = src[0] >> 1


@flyc.jit
def _pointer_shift(
    src: fx.Pointer,
    dst: fx.Pointer,
    expected_name: fx.Constexpr[str],
    stream: fx.Stream = fx.Stream(None),
):
    assert src.element_type.__name__ == expected_name
    assert dst.element_type.__name__ == expected_name
    _pointer_shift_kernel(src, dst, expected_name).launch(grid=(1, 1, 1), block=(1, 1, 1), stream=stream)


@flyc.kernel
def _tensor_shift_kernel(src: fx.Tensor, dst: fx.Tensor, expected_name: fx.Constexpr[str]):
    assert src.element_type.__name__ == expected_name
    assert dst.element_type.__name__ == expected_name
    dst[0] = src[0] >> 1


@flyc.jit
def _tensor_shift(
    src: fx.Tensor,
    dst: fx.Tensor,
    expected_name: fx.Constexpr[str],
    stream: fx.Stream = fx.Stream(None),
):
    assert src.element_type.__name__ == expected_name
    assert dst.element_type.__name__ == expected_name
    _tensor_shift_kernel(src, dst, expected_name).launch(grid=(1, 1, 1), block=(1, 1, 1), stream=stream)


_CASES = [
    (fx.Uint8, torch.uint8, [0, 1, 0x7F, 0x80, 0xFF]),
    (fx.Int8, torch.int8, [0, 1, 0x7F, -0x80, -1]),
    (fx.Uint32, torch.uint32, [0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF]),
    (fx.Int32, torch.int32, [0, 1, 0x7FFFFFFF, -0x80000000, -1]),
]


@pytest.mark.parametrize("dsl_type,torch_type,values", _CASES, ids=lambda value: getattr(value, "__name__", None))
@pytest.mark.parametrize("kind", ["pointer", "tensor_torch", "tensor_dlpack"])
def test_integer_signedness_survives_jit_and_kernel_reconstruction(dsl_type, torch_type, values, kind):
    for value in values:
        src = torch.tensor([value], device="cuda", dtype=torch_type)
        dst = torch.empty_like(src)
        stream = torch.cuda.Stream()

        if kind == "pointer":
            src_arg = flyc.from_c_void_p(dsl_type, src.data_ptr())
            dst_arg = flyc.from_c_void_p(dsl_type, dst.data_ptr())
            _pointer_shift(src_arg, dst_arg, dsl_type.__name__, stream=stream)
        else:
            wrap = flyc.from_torch_tensor if kind == "tensor_torch" else flyc.from_dlpack
            src_arg = wrap(src)
            dst_arg = wrap(dst)
            _tensor_shift(src_arg, dst_arg, dsl_type.__name__, stream=stream)

        stream.synchronize()
        reference = torch.bitwise_right_shift(src.to(torch.int64), 1).to(torch_type)
        torch.testing.assert_close(dst, reference, rtol=0, atol=0)
