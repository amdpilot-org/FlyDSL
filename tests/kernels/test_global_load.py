# SPDX-License-Identifier: Apache-2.0

import pytest
import torch

import flydsl.compiler as flyc
import flydsl.expr as fx


pytestmark = [pytest.mark.l2_device, pytest.mark.rocm_lower]


@flyc.kernel
def global_load_kernel(src: fx.Tensor, scalar_out: fx.Tensor, vector_out: fx.Tensor, masked_out: fx.Tensor):
    tid = fx.thread_idx.x
    scalar_out[tid] = fx.global_load(fx.Int32, src, elem_offset=tid * 3 + 1, alignment=4)

    packed = fx.global_load(fx.Int32x4, src, byte_offset=tid * 16, alignment=16)
    for lane in fx.range_constexpr(4):
        vector_out[tid * 4 + lane] = packed[lane]

    keep = tid < fx.Int32(5)
    masked_offset = tid if keep else tid + fx.Int32(1000000)
    masked_out[tid] = fx.global_load(
        fx.Int32, src, elem_offset=masked_offset, alignment=4, mask=keep, other=-77
    )


@flyc.jit
def run_global_load(src: fx.Tensor, scalar_out: fx.Tensor, vector_out: fx.Tensor, masked_out: fx.Tensor):
    global_load_kernel(src, scalar_out, vector_out, masked_out).launch(grid=(1, 1, 1), block=(8, 1, 1))


def test_global_load_scalar_vector_offsets_alignment_and_mask():
    src = torch.arange(64, dtype=torch.int32, device="cuda") * 13 + 7
    scalar_out = torch.empty(8, dtype=torch.int32, device="cuda")
    vector_out = torch.empty(32, dtype=torch.int32, device="cuda")
    masked_out = torch.empty(8, dtype=torch.int32, device="cuda")

    run_global_load(src, scalar_out, vector_out, masked_out)
    torch.cuda.synchronize()

    scalar_indices = torch.arange(8, device="cuda") * 3 + 1
    assert torch.equal(scalar_out, src[scalar_indices])
    assert torch.equal(vector_out, src[torch.arange(32, device="cuda")])
    expected_masked = torch.full((8,), -77, dtype=torch.int32, device="cuda")
    expected_masked[:5] = src[:5]
    assert torch.equal(masked_out, expected_masked)
