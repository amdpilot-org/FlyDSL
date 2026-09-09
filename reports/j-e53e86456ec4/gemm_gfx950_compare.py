#!/usr/bin/env python3
"""Run one M64/N16/K128 GEMM comparison case on the assigned AMD GPU."""

import argparse
import hashlib
import json
import os
import platform
import re
import sys
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument(
    "case",
    choices=[
        "fp8_raw",
        "fp8_raw_issue_store",
        "fp8_gemm_universal32",
        "fp8_gemm_buffer32",
        "fp8_gemm_buffer64",
        "fp8_gemm_buffer128",
        "bf16_raw",
        "bf16_gemm_universal64",
        "bf16_gemm_buffer32",
        "bf16_gemm_buffer64",
        "bf16_gemm_buffer128",
    ],
)
parser.add_argument("--dump-root", type=Path, default=Path("/job/artifacts/dumps"))
parser.add_argument("--seed", type=int, default=20260909)
args = parser.parse_args()

os.environ["FLYDSL_COMPILE_BACKEND"] = "rocm"
os.environ["FLYDSL_RUNTIME_KIND"] = "rocm"
os.environ["FLYDSL_COMPILE_OPT_LEVEL"] = "2"
os.environ["FLYDSL_RUNTIME_ENABLE_CACHE"] = "0"
os.environ["FLYDSL_DUMP_IR"] = "1"
os.environ["FLYDSL_DEBUG_DUMP_ASM"] = "1"
os.environ["FLYDSL_DEBUG_SHOW_STACKTRACE"] = "1"
os.environ["FLYDSL_DUMP_DIR"] = str(args.dump_root / args.case)

import torch  # noqa: E402

import flydsl  # noqa: E402
import flydsl.compiler as flyc  # noqa: E402
import flydsl.expr as fx  # noqa: E402
from flydsl._mlir import ir  # noqa: E402
from flydsl.compiler.backends import get_backend  # noqa: E402
from flydsl.expr.typing import T  # noqa: E402
from flydsl.utils import env as flydsl_env  # noqa: E402


M = 64
N = 16
K = 128
WAVE = 64
NWARP = 4
FP8 = fx.Float8E4M3FN
BF16 = fx.BFloat16


@flyc.kernel(known_block_size=(NWARP * WAVE, 1, 1))
def raw_fp8_kernel(A: fx.Tensor, B: fx.Tensor, C: fx.Tensor):
    tid = fx.Int32(fx.gpu.thread_id("x"))
    warp = tid // WAVE
    lane = tid - warp * WAVE
    lane16 = lane - (lane // 16) * 16
    rgroup = lane // 16

    def load16(buf, byte_off):
        copy_atom = fx.make_copy_atom(fx.UniversalCopy32b(), FP8)
        reg = fx.make_rmem_tensor(fx.make_layout(16, 1), FP8)
        flat = fx.Tensor(fx.make_view(fx.get_iter(buf), fx.make_layout(1 << 30, 1)))
        div = fx.logical_divide(flat, fx.make_layout(1, 1))
        fx.copy(copy_atom, fx.slice(div, (None, byte_off)), reg)
        return fx.Vector(fx.memref_load_vec(reg)).bitcast(fx.Int64)

    acc = fx.arith.constant_vector(0.0, T.f32x4)
    for qkhe in range(2):
        a_off = (warp * 16 + lane16) * K + (qkhe * 4 + rgroup) * 16
        b_off = lane16 * K + (qkhe * 4 + rgroup) * 16
        a_w = load16(A, a_off)
        b_w = load16(B, b_off)
        acc = fx.rocdl.mfma_f32_16x16x32_fp8_fp8(
            T.f32x4, [a_w[0], b_w[0], acc, 0, 0, 0]
        )
        acc = fx.rocdl.mfma_f32_16x16x32_fp8_fp8(
            T.f32x4, [a_w[1], b_w[1], acc, 0, 0, 0]
        )

    out = fx.Vector(acc)
    for r in range(4):
        row = warp * 16 + rgroup * 4 + r
        col = lane16
        C[row, col] = out[r]


@flyc.kernel(known_block_size=(NWARP * WAVE, 1, 1))
def raw_fp8_issue_store_kernel(A: fx.Tensor, B: fx.Tensor, C: fx.Tensor):
    tid = fx.Int32(fx.gpu.thread_id("x"))
    warp = tid // WAVE
    lane = tid - warp * WAVE
    lane16 = lane - (lane // 16) * 16
    rgroup = lane // 16

    def load16(buf, byte_off):
        copy_atom = fx.make_copy_atom(fx.UniversalCopy32b(), FP8)
        reg = fx.make_rmem_tensor(fx.make_layout(16, 1), FP8)
        flat = fx.Tensor(fx.make_view(fx.get_iter(buf), fx.make_layout(1 << 30, 1)))
        div = fx.logical_divide(flat, fx.make_layout(1, 1))
        fx.copy(copy_atom, fx.slice(div, (None, byte_off)), reg)
        return fx.Vector(fx.memref_load_vec(reg)).bitcast(fx.Int64)

    acc = fx.arith.constant_vector(0.0, T.f32x4)
    for qkhe in range(2):
        a_off = (warp * 16 + lane16) * K + (qkhe * 4 + rgroup) * 16
        b_off = lane16 * K + (qkhe * 4 + rgroup) * 16
        a_w = load16(A, a_off)
        b_w = load16(B, b_off)
        acc = fx.rocdl.mfma_f32_16x16x32_fp8_fp8(
            T.f32x4, [a_w[0], b_w[0], acc, 0, 0, 0]
        )
        acc = fx.rocdl.mfma_f32_16x16x32_fp8_fp8(
            T.f32x4, [a_w[1], b_w[1], acc, 0, 0, 0]
        )

    out = fx.Vector(acc)
    row = warp * 16 + lane16
    for r in range(4):
        col = rgroup * 4 + r
        C[row, col] = out[r]


@flyc.kernel(known_block_size=(NWARP * WAVE, 1, 1))
def raw_bf16_kernel(A: fx.Tensor, B: fx.Tensor, C: fx.Tensor):
    tid = fx.Int32(fx.gpu.thread_id("x"))
    warp = tid // WAVE
    lane = tid - warp * WAVE
    lane16 = lane - (lane // 16) * 16
    rgroup = lane // 16

    def load8(buf, elem_off):
        copy_atom = fx.make_copy_atom(fx.UniversalCopy128b(), BF16)
        reg = fx.make_rmem_tensor(fx.make_layout(8, 1), BF16)
        flat = fx.Tensor(fx.make_view(fx.get_iter(buf), fx.make_layout(1 << 30, 1)))
        div = fx.logical_divide(flat, fx.make_layout(1, 1))
        fx.copy(copy_atom, fx.slice(div, (None, elem_off)), reg)
        return fx.Vector(fx.memref_load_vec(reg)).bitcast(fx.Int64)

    def operand(word):
        return fx.Vector.from_elements([word], dtype=fx.Int64).bitcast(fx.Int16)

    acc = fx.arith.constant_vector(0.0, T.f32x4)
    for qkhe in range(4):
        a_off = (warp * 16 + lane16) * K + (qkhe * 4 + rgroup) * 8
        b_off = lane16 * K + (qkhe * 4 + rgroup) * 8
        a_w = load8(A, a_off)
        b_w = load8(B, b_off)
        acc = fx.rocdl.mfma_f32_16x16x16bf16_1k(
            T.f32x4, [operand(a_w[0]), operand(b_w[0]), acc, 0, 0, 0]
        )
        acc = fx.rocdl.mfma_f32_16x16x16bf16_1k(
            T.f32x4, [operand(a_w[1]), operand(b_w[1]), acc, 0, 0, 0]
        )

    out = fx.Vector(acc)
    for r in range(4):
        row = warp * 16 + rgroup * 4 + r
        col = lane16
        C[row, col] = out[r]


def make_copy_atom(case):
    if case.endswith("universal32"):
        return fx.make_copy_atom(fx.UniversalCopy32b(), FP8)
    if case.endswith("universal64"):
        return fx.make_copy_atom(fx.UniversalCopy64b(), BF16)
    if case.endswith("buffer32"):
        return fx.make_copy_atom(fx.rocdl.BufferCopy32b(), FP8 if case.startswith("fp8") else BF16)
    if case.endswith("buffer64"):
        return fx.make_copy_atom(fx.rocdl.BufferCopy64b(), FP8 if case.startswith("fp8") else BF16)
    if case.endswith("buffer128"):
        return fx.make_copy_atom(fx.rocdl.BufferCopy128b(), FP8 if case.startswith("fp8") else BF16)
    raise ValueError(case)


@flyc.kernel(known_block_size=(NWARP * WAVE, 1, 1))
def gemm_kernel(A: fx.Tensor, B: fx.Tensor, C: fx.Tensor):
    tid = fx.Int32(fx.gpu.thread_id("x"))
    bid = fx.Int32(fx.gpu.block_id("x"))

    elem_ty = FP8 if "fp8" in os.environ["FLYDSL_COMPARE_CASE"] else BF16
    mma_k = 32 if elem_ty is FP8 else 16
    copy_atom = make_copy_atom(os.environ["FLYDSL_COMPARE_CASE"])

    bA = fx.zipped_divide(A, (M, K))
    bB = fx.zipped_divide(B, (N, K))
    bC = fx.zipped_divide(C, (M, N))
    bA = fx.slice(bA, (None, bid))
    bB = fx.slice(bB, (None, bid))
    bC = fx.slice(bC, (None, bid))

    mma_atom = fx.make_mma_atom(fx.rocdl.MFMA(16, 16, mma_k, elem_ty))
    tiled_mma = fx.make_tiled_mma(mma_atom, fx.make_layout((NWARP, 1, 1), (1, 0, 0)))
    thr_mma = tiled_mma.get_slice(tid)
    tiled_copy_A = fx.make_tiled_copy_A(copy_atom, tiled_mma)
    tiled_copy_B = fx.make_tiled_copy_B(copy_atom, tiled_mma)
    tiled_copy_C = fx.make_tiled_copy_C(
        fx.make_copy_atom(fx.UniversalCopy32b(), fx.Float32), tiled_mma
    )
    thr_copy_A = tiled_copy_A.get_slice(tid)
    thr_copy_B = tiled_copy_B.get_slice(tid)
    thr_copy_C = tiled_copy_C.get_slice(tid)

    frag_A = thr_mma.make_fragment_A(bA)
    frag_B = thr_mma.make_fragment_B(bB)
    frag_C = thr_mma.make_fragment_C(bC)
    fx.copy(copy_atom, thr_copy_A.partition_S(bA), thr_copy_A.retile(frag_A), pred=None)
    fx.copy(copy_atom, thr_copy_B.partition_S(bB), thr_copy_B.retile(frag_B), pred=None)
    frag_C.fill(0.0)
    fx.gemm(mma_atom, frag_C, frag_A, frag_B, frag_C)
    fx.copy(
        fx.make_copy_atom(fx.UniversalCopy32b(), fx.Float32),
        thr_copy_C.retile(frag_C),
        thr_copy_C.partition_D(bC),
        pred=None,
    )


@flyc.jit
def launch_raw_fp8(A: fx.Tensor, B: fx.Tensor, C: fx.Tensor, stream: fx.Stream = fx.Stream(None)):
    raw_fp8_kernel(A, B, C).launch(
        grid=(1, 1, 1), block=(NWARP * WAVE, 1, 1), stream=stream
    )


@flyc.jit
def launch_raw_fp8_issue_store(
    A: fx.Tensor, B: fx.Tensor, C: fx.Tensor, stream: fx.Stream = fx.Stream(None)
):
    raw_fp8_issue_store_kernel(A, B, C).launch(
        grid=(1, 1, 1), block=(NWARP * WAVE, 1, 1), stream=stream
    )


@flyc.jit
def launch_raw_bf16(A: fx.Tensor, B: fx.Tensor, C: fx.Tensor, stream: fx.Stream = fx.Stream(None)):
    raw_bf16_kernel(A, B, C).launch(
        grid=(1, 1, 1), block=(NWARP * WAVE, 1, 1), stream=stream
    )


@flyc.jit
def launch_gemm(A: fx.Tensor, B: fx.Tensor, C: fx.Tensor, stream: fx.Stream = fx.Stream(None)):
    gemm_kernel(A, B, C).launch(
        grid=(1, 1, 1), block=(NWARP * WAVE, 1, 1), stream=stream
    )


def parse_isa(dump_dir):
    files = sorted(dump_dir.rglob("21_final_isa.s"))
    if not files:
        return None
    text = files[-1].read_text()
    patterns = {
        "vgpr": r"^\s*\.amdhsa_next_free_vgpr\s+(\d+)",
        "sgpr": r"^\s*\.amdhsa_next_free_sgpr\s+(\d+)",
        "lds_bytes": r"^\s*\.amdhsa_group_segment_fixed_size\s+(\d+)",
        "scratch_bytes": r"^\s*\.amdhsa_private_segment_fixed_size\s+(\d+)",
    }
    resources = {}
    for name, pattern in patterns.items():
        match = re.search(pattern, text, re.MULTILINE)
        resources[name] = int(match.group(1)) if match else None
    resources["isa_path"] = str(files[-1])
    resources["isa_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    return resources


def tensor_digest(tensor):
    data = tensor.detach().cpu().contiguous().numpy().tobytes()
    return hashlib.sha256(data).hexdigest()


def main():
    os.environ["FLYDSL_COMPARE_CASE"] = args.case
    torch.manual_seed(args.seed)
    device = "cuda"
    is_fp8 = args.case.startswith("fp8")
    if is_fp8:
        A = torch.randn(M, K, device=device).clamp_(-2.0, 2.0).to(torch.float8_e4m3fn)
        B = torch.randn(N, K, device=device).clamp_(-2.0, 2.0).to(torch.float8_e4m3fn)
        atol = 0.1
        rtol = 0.1
    else:
        A = torch.randn(M, K, device=device).to(torch.bfloat16)
        B = torch.randn(N, K, device=device).to(torch.bfloat16)
        atol = 0.1
        rtol = 0.1
    C = torch.zeros(M, N, dtype=torch.float32, device=device)
    reference = torch.mm(A.float(), B.float().t())

    try:
        if args.case == "fp8_raw":
            launch_raw_fp8(A, B, C)
        elif args.case == "fp8_raw_issue_store":
            launch_raw_fp8_issue_store(A, B, C)
        elif args.case == "bf16_raw":
            launch_raw_bf16(A, B, C)
        else:
            launch_gemm(A, B, C)
        torch.cuda.synchronize()
        difference = (C - reference).abs()
        tolerance = atol + rtol * reference.abs()
        result = {
            "case": args.case,
            "status": "ran",
            "shape": [M, N, K],
            "dtype": str(A.dtype),
            "seed": args.seed,
            "gates": {"atol": atol, "rtol": rtol},
            "max_abs_error": difference.max().item(),
            "mean_abs_error": difference.mean().item(),
            "mismatch_count": int((difference > tolerance).sum().item()),
            "output_sha256": tensor_digest(C),
            "reference_sha256": tensor_digest(reference),
            "output_first16": C.flatten()[:16].tolist(),
            "reference_first16": reference.flatten()[:16].tolist(),
        }
    except Exception as error:
        result = {
            "case": args.case,
            "status": "failed",
            "shape": [M, N, K],
            "dtype": str(A.dtype),
            "seed": args.seed,
            "error_type": type(error).__name__,
            "error": str(error),
        }

    result["environment"] = {
        "python": sys.executable,
        "python_version": sys.version,
        "platform": platform.platform(),
        "gpu_name": torch.cuda.get_device_name(0),
        "gpu_capability": list(torch.cuda.get_device_capability(0)),
        "torch_version": torch.__version__,
        "torch_hip": torch.version.hip,
        "triton_version": __import__("triton").__version__,
        "flydsl_version": flydsl.__version__,
        "flydsl_path": flydsl.__file__,
        "flyc_path": flyc.__file__,
        "fx_path": fx.__file__,
        "mlir_path": ir.__file__,
        "backend": type(get_backend()).__name__,
        "target_arch": get_backend().target.arch,
        "warp_size": get_backend().target.warp_size,
        "compile_options": flydsl_env.compile.to_dict(),
        "debug_options": flydsl_env.debug.to_dict(),
        "runtime_options": flydsl_env.runtime.to_dict(),
    }
    result["resources"] = parse_isa(args.dump_root / args.case)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] == "failed":
        raise SystemExit(2)
    if result["mismatch_count"] != 0:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
