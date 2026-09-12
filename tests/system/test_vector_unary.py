# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

import numpy as np
import pytest
import torch

import flydsl.compiler as flyc
import flydsl.expr as fx


def _copy_unary_body(a, b, element_type, transform):
    tid = fx.thread_idx.x
    bid = fx.block_idx.x
    tile = fx.make_tile(fx.make_layout(8, 1), fx.make_layout(24, 1))
    a = fx.rocdl.make_buffer_tensor(a)
    b = fx.rocdl.make_buffer_tensor(b)
    src = fx.slice(fx.zipped_divide(a, tile), (None, bid))
    dst = fx.slice(fx.zipped_divide(b, tile), (None, bid))
    copy_atom = fx.make_copy_atom(fx.rocdl.BufferCopy128b(), element_type)
    tiled_copy = fx.make_tiled_copy(
        copy_atom,
        fx.raked_product(fx.make_layout((4, 1), (1, 1)), fx.make_layout((1, 8), (1, 1))),
        fx.make_tile(4, 8),
    )
    thread_copy = tiled_copy.get_slice(tid)
    partition_src = thread_copy.partition_S(src)
    partition_dst = thread_copy.partition_D(dst)
    fragment = fx.make_fragment_like(partition_src)
    fx.copy(copy_atom, partition_src, fragment)
    fragment.store(transform(fragment.load()))
    fx.copy(copy_atom, fragment, partition_dst)


@flyc.kernel
def invert_i32_kernel(a: fx.Tensor, b: fx.Tensor):
    _copy_unary_body(a, b, fx.Int32, lambda value: ~value)


@flyc.kernel
def negate_i32_kernel(a: fx.Tensor, b: fx.Tensor):
    _copy_unary_body(a, b, fx.Int32, lambda value: -value)


@flyc.kernel
def invert_u32_kernel(a: fx.Tensor, b: fx.Tensor):
    _copy_unary_body(a, b, fx.Uint32, lambda value: ~value)


@flyc.kernel
def negate_u32_kernel(a: fx.Tensor, b: fx.Tensor):
    _copy_unary_body(a, b, fx.Uint32, lambda value: -value)


@flyc.jit
def run_invert_i32(a: fx.Tensor, b: fx.Tensor, stream: fx.Stream = fx.Stream(None)):
    invert_i32_kernel(a, b).launch(grid=(15, 1, 1), block=(4, 1, 1), stream=stream)


@flyc.jit
def run_negate_i32(a: fx.Tensor, b: fx.Tensor, stream: fx.Stream = fx.Stream(None)):
    negate_i32_kernel(a, b).launch(grid=(15, 1, 1), block=(4, 1, 1), stream=stream)


@flyc.jit
def run_invert_u32(a: fx.Tensor, b: fx.Tensor, stream: fx.Stream = fx.Stream(None)):
    invert_u32_kernel(a, b).launch(grid=(15, 1, 1), block=(4, 1, 1), stream=stream)


@flyc.jit
def run_negate_u32(a: fx.Tensor, b: fx.Tensor, stream: fx.Stream = fx.Stream(None)):
    negate_u32_kernel(a, b).launch(grid=(15, 1, 1), block=(4, 1, 1), stream=stream)


@pytest.mark.parametrize(
    ("dtype", "values", "operation", "run"),
    [
        (
            np.int32,
            [-(2**31), -(2**31) + 1, -2, -1, 0, 1, 2, 2**31 - 2, 2**31 - 1],
            np.invert,
            run_invert_i32,
        ),
        (
            np.int32,
            [-(2**31), -(2**31) + 1, -2, -1, 0, 1, 2, 2**31 - 2, 2**31 - 1],
            np.negative,
            run_negate_i32,
        ),
        (np.uint32, [0, 1, 2, 2**31 - 1, 2**31, 2**32 - 2, 2**32 - 1], np.invert, run_invert_u32),
        (np.uint32, [0, 1, 2, 2**31 - 1, 2**31, 2**32 - 2, 2**32 - 1], np.negative, run_negate_u32),
    ],
)
def test_vector_unary_gpu_matches_numpy(dtype, values, operation, run, monkeypatch):
    if not torch.cuda.is_available():
        pytest.skip("ROCm GPU is required for vector unary execution coverage")
    monkeypatch.setenv("FLYDSL_RUNTIME_ENABLE_CACHE", "0")
    host = np.resize(np.asarray(values, dtype=dtype), (24, 24))
    expected = operation(host)
    # Torch/FlyDSL does not expose uint32 tensor arguments. Integer memrefs are
    # signless in MLIR, so pass the same bits through an int32 tensor while the
    # copy atom gives the loaded Vector its Uint32 DSL dtype.
    torch_host = host.view(np.int32) if dtype is np.uint32 else host
    source = torch.from_numpy(torch_host).cuda()
    output = torch.empty_like(source)
    run(source, output, stream=torch.cuda.Stream())
    torch.cuda.synchronize()
    actual = output.cpu().numpy().view(dtype)
    assert np.array_equal(actual, expected)
