#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""BF16 and FP16 controls for the gfx942 BufferCopy GEMM path."""

import pytest

import flydsl.compiler as flyc
import flydsl.expr as fx
from flydsl.expr.typing import T
from flydsl.runtime.device import get_rocm_arch

try:
    import torch
except ImportError:
    torch = None

pytestmark = [pytest.mark.l2_device, pytest.mark.rocm_lower]

if torch is None or not torch.cuda.is_available():
    pytest.skip("CUDA/ROCm not available", allow_module_level=True)
if get_rocm_arch() != "gfx942":
    pytest.skip(f"requires gfx942, got {get_rocm_arch()}", allow_module_level=True)

M, N, K = 64, 16, 128
WAVE, NWARP = 64, 4

DTYPES = {
    "bf16": (fx.BFloat16, torch.bfloat16),
    "fp16": (fx.Float16, torch.float16),
}


def _compile_raw_mfma(dtype):
    @flyc.kernel(known_block_size=(NWARP * WAVE, 1, 1))
    def raw_mfma_kernel(A: fx.Tensor, B: fx.Tensor, C: fx.Tensor):
        tid = fx.Int32(fx.gpu.thread_id("x"))
        warp = tid // WAVE
        lane = tid - warp * WAVE
        lane16 = lane - (lane // 16) * 16
        rgroup = lane // 16

        def load8(buf, elem_offset):
            atom = fx.make_copy_atom(fx.UniversalCopy128b(), dtype)
            reg = fx.make_rmem_tensor(fx.make_layout(8, 1), dtype)
            flat = fx.Tensor(fx.make_view(fx.get_iter(buf), fx.make_layout(1 << 30, 1)))
            divided = fx.logical_divide(flat, fx.make_layout(1, 1))
            fx.copy(atom, fx.slice(divided, (None, elem_offset)), reg)
            return fx.Vector(fx.memref_load_vec(reg)).bitcast(fx.Int64)

        def operand(word):
            operand_type = fx.Int16 if dtype == fx.BFloat16 else fx.Float16
            return fx.Vector.from_elements([word], dtype=fx.Int64).bitcast(operand_type)

        acc = fx.arith.constant_vector(0.0, T.f32x4)
        for chunk in range(4):
            a_offset = (warp * 16 + lane16) * K + (chunk * 4 + rgroup) * 8
            b_offset = lane16 * K + (chunk * 4 + rgroup) * 8
            a = load8(A, a_offset)
            b = load8(B, b_offset)
            if dtype == fx.BFloat16:
                acc = fx.rocdl.mfma_f32_16x16x16bf16_1k(
                    T.f32x4, [operand(a[0]), operand(b[0]), acc, 0, 0, 0]
                )
                acc = fx.rocdl.mfma_f32_16x16x16bf16_1k(
                    T.f32x4, [operand(a[1]), operand(b[1]), acc, 0, 0, 0]
                )
            else:
                acc = fx.rocdl.mfma_f32_16x16x16f16(
                    T.f32x4, [operand(a[0]), operand(b[0]), acc, 0, 0, 0]
                )
                acc = fx.rocdl.mfma_f32_16x16x16f16(
                    T.f32x4, [operand(a[1]), operand(b[1]), acc, 0, 0, 0]
                )

        out = fx.Vector(acc)
        for r in range(4):
            row = warp * 16 + rgroup * 4 + r
            C[row, lane16] = out[r]

    @flyc.jit
    def launch(A: fx.Tensor, B: fx.Tensor, C: fx.Tensor, stream: fx.Stream = fx.Stream(None)):
        raw_mfma_kernel(A, B, C).launch(
            grid=(1, 1, 1), block=(NWARP * WAVE, 1, 1), stream=stream
        )

    return launch


def _compile_gemm(dtype, copy_kind):
    @flyc.kernel(known_block_size=(NWARP * WAVE, 1, 1))
    def gemm_kernel(A: fx.Tensor, B: fx.Tensor, C: fx.Tensor):
        tid = fx.Int32(fx.gpu.thread_id("x"))
        bid = fx.Int32(fx.gpu.block_id("x"))
        tiled_A = fx.slice(fx.zipped_divide(A, (M, K)), (None, bid))
        tiled_B = fx.slice(fx.zipped_divide(B, (N, K)), (None, bid))
        tiled_C = fx.slice(fx.zipped_divide(C, (M, N)), (None, bid))

        mma_atom = fx.make_mma_atom(fx.rocdl.MFMA(16, 16, 16, dtype))
        tiled_mma = fx.make_tiled_mma(mma_atom, fx.make_layout((NWARP, 1, 1), (1, 0, 0)))
        thr_mma = tiled_mma.get_slice(tid)

        copy_op = fx.UniversalCopy32b() if copy_kind == "universal32" else fx.rocdl.BufferCopy64b()
        copy_atom = fx.make_copy_atom(copy_op, dtype)
        copy_A = fx.make_tiled_copy_A(copy_atom, tiled_mma).get_slice(tid)
        copy_B = fx.make_tiled_copy_B(copy_atom, tiled_mma).get_slice(tid)
        copy_C = fx.make_tiled_copy_C(
            fx.make_copy_atom(fx.UniversalCopy32b(), fx.Float32), tiled_mma
        ).get_slice(tid)

        frag_A = thr_mma.make_fragment_A(tiled_A)
        frag_B = thr_mma.make_fragment_B(tiled_B)
        frag_C = thr_mma.make_fragment_C(tiled_C)
        fx.copy(copy_atom, copy_A.partition_S(tiled_A), copy_A.retile(frag_A))
        fx.copy(copy_atom, copy_B.partition_S(tiled_B), copy_B.retile(frag_B))

        frag_C.fill(0.0)
        fx.gemm(mma_atom, frag_C, frag_A, frag_B, frag_C)
        fx.copy(
            fx.make_copy_atom(fx.UniversalCopy32b(), fx.Float32),
            copy_C.retile(frag_C),
            copy_C.partition_D(tiled_C),
        )

    @flyc.jit
    def launch(A: fx.Tensor, B: fx.Tensor, C: fx.Tensor, stream: fx.Stream = fx.Stream(None)):
        gemm_kernel(A, B, C).launch(grid=(1, 1, 1), block=(NWARP * WAVE, 1, 1), stream=stream)

    return launch


def _inputs(torch_dtype):
    torch.manual_seed(822)
    A = torch.randn(M, K, device="cuda").clamp(-1.0, 1.0).to(torch_dtype)
    B = torch.randn(N, K, device="cuda").clamp(-1.0, 1.0).to(torch_dtype)
    C = torch.zeros(M, N, dtype=torch.float32, device="cuda")
    return A, B, C


def _run(launch, torch_dtype):
    A, B, C = _inputs(torch_dtype)
    launch(A, B, C, stream=torch.cuda.current_stream())
    torch.cuda.synchronize()
    return C, A, B


@pytest.mark.parametrize("dtype_name", DTYPES)
def test_gemm_matches_raw_mfma_and_torch(dtype_name):
    dtype, torch_dtype = DTYPES[dtype_name]
    raw_result, A, B = _run(_compile_raw_mfma(dtype), torch_dtype)
    reference = A.float().cpu() @ B.float().cpu().T
    torch.testing.assert_close(raw_result.cpu(), reference, atol=5e-2, rtol=5e-2)

    for copy_kind in ("universal32", "buffer64"):
        gemm_result, _, _ = _run(_compile_gemm(dtype, copy_kind), torch_dtype)
        torch.testing.assert_close(gemm_result, raw_result, atol=1e-5, rtol=1e-5)
