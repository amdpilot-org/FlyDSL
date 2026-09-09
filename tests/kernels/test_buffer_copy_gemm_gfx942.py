#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""gfx942 BufferCopy and MFMA fragment boundary tests."""

import pytest

import flydsl.compiler as flyc
import flydsl.expr as fx
from flydsl.compiler.diagnostics import DSLCompileError
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
FP8 = fx.Float8E4M3FNUZ


def _copy_op(kind):
    return {
        "universal32": fx.UniversalCopy32b,
        "buffer32": fx.rocdl.BufferCopy32b,
        "buffer64": fx.rocdl.BufferCopy64b,
        "global_buffer32": fx.rocdl.BufferCopy32b,
        "global_buffer64": fx.rocdl.BufferCopy64b,
        "buffer128": fx.rocdl.BufferCopy128b,
    }[kind]()


def _compile_raw_mfma():
    @flyc.kernel(known_block_size=(NWARP * WAVE, 1, 1))
    def kernel(A: fx.Tensor, B: fx.Tensor, C: fx.Tensor):
        tid = fx.Int32(fx.gpu.thread_id("x"))
        warp = tid // WAVE
        lane = tid - warp * WAVE
        lane16 = lane - (lane // 16) * 16
        rgroup = lane // 16

        def load16(buf, byte_offset):
            atom = fx.make_copy_atom(fx.UniversalCopy32b(), FP8)
            reg = fx.make_rmem_tensor(fx.make_layout(16, 1), FP8)
            flat = fx.Tensor(fx.make_view(fx.get_iter(buf), fx.make_layout(1 << 30, 1)))
            divided = fx.logical_divide(flat, fx.make_layout(1, 1))
            fx.copy(atom, fx.slice(divided, (None, byte_offset)), reg)
            return fx.Vector(fx.memref_load_vec(reg)).bitcast(fx.Int64)

        acc = fx.arith.constant_vector(0.0, T.f32x4)
        for chunk in range(2):
            a_offset = (warp * 16 + lane16) * K + (chunk * 4 + rgroup) * 16
            b_offset = lane16 * K + (chunk * 4 + rgroup) * 16
            a = load16(A, a_offset)
            b = load16(B, b_offset)
            acc = fx.rocdl.mfma_f32_16x16x32_fp8_fp8(T.f32x4, [a[0], b[0], acc, 0, 0, 0])
            acc = fx.rocdl.mfma_f32_16x16x32_fp8_fp8(T.f32x4, [a[1], b[1], acc, 0, 0, 0])

        out = fx.Vector(acc)
        for r in range(4):
            row = warp * 16 + rgroup * 4 + r
            C[row, lane16] = out[r]

    @flyc.jit
    def launch(A: fx.Tensor, B: fx.Tensor, C: fx.Tensor, stream: fx.Stream = fx.Stream(None)):
        kernel(A, B, C).launch(grid=(1, 1, 1), block=(NWARP * WAVE, 1, 1), stream=stream)

    return launch


def _compile_gemm(copy_kind, use_buffer_tensor):
    @flyc.kernel(known_block_size=(NWARP * WAVE, 1, 1))
    def kernel(A: fx.Tensor, B: fx.Tensor, C: fx.Tensor):
        tid = fx.Int32(fx.gpu.thread_id("x"))
        bid = fx.Int32(fx.gpu.block_id("x"))

        if use_buffer_tensor:
            A = fx.rocdl.make_buffer_tensor(A)
            B = fx.rocdl.make_buffer_tensor(B)
        tiled_A = fx.slice(fx.zipped_divide(A, (M, K)), (None, bid))
        tiled_B = fx.slice(fx.zipped_divide(B, (N, K)), (None, bid))
        tiled_C = fx.slice(fx.zipped_divide(C, (M, N)), (None, bid))

        mma_atom = fx.make_mma_atom(fx.rocdl.MFMA(16, 16, 32, FP8))
        tiled_mma = fx.make_tiled_mma(mma_atom, fx.make_layout((NWARP, 1, 1), (1, 0, 0)))
        thr_mma = tiled_mma.get_slice(tid)

        copy_atom = fx.make_copy_atom(_copy_op(copy_kind), FP8)
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
        kernel(A, B, C).launch(grid=(1, 1, 1), block=(NWARP * WAVE, 1, 1), stream=stream)

    return launch


def _inputs():
    torch.manual_seed(821)
    A = torch.randn(M, K, device="cuda").clamp(-1.0, 1.0).to(torch.float8_e4m3fnuz)
    B = torch.randn(N, K, device="cuda").clamp(-1.0, 1.0).to(torch.float8_e4m3fnuz)
    C = torch.zeros(M, N, dtype=torch.float32, device="cuda")
    return A, B, C


def _run_gemm(launch):
    A, B, C = _inputs()
    launch(A, B, C, stream=torch.cuda.current_stream())
    torch.cuda.synchronize()
    return C


@pytest.fixture(scope="module")
def raw_result():
    return _run_gemm(_compile_raw_mfma())


def _assert_gemm(launch, raw_result):
    C = _run_gemm(launch)
    A, B, _ = _inputs()
    torch.testing.assert_close(C, A.float() @ B.float().T, atol=1e-5, rtol=1e-5)
    torch.testing.assert_close(C, raw_result, atol=0.0, rtol=0.0)


def test_raw_mfma_matches_fp32_reference(raw_result):
    A, B, _ = _inputs()
    torch.testing.assert_close(raw_result, A.float() @ B.float().T, atol=1e-5, rtol=1e-5)


@pytest.mark.parametrize(
    "copy_kind", ["universal32", "buffer32", "buffer64", "global_buffer32", "global_buffer64"]
)
def test_gemm_legal_copy_widths_match_references(copy_kind, raw_result):
    _assert_gemm(
        _compile_gemm(copy_kind, use_buffer_tensor=copy_kind.startswith("buffer")), raw_result
    )


def test_buffer_copy_rejects_fragment_width_mismatch(monkeypatch):
    monkeypatch.setenv("FLYDSL_RUNTIME_ENABLE_CACHE", "0")
    A, B, C = _inputs()
    with pytest.raises(DSLCompileError, match="128 bits.*64-bit"):
        _compile_gemm("buffer128", use_buffer_tensor=False)(
            A, B, C, stream=torch.cuda.current_stream()
        )
