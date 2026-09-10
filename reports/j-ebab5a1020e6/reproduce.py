#!/usr/bin/env python3

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import flydsl
import torch
import triton

import flydsl.compiler as flyc
import flydsl.expr as fx
from flydsl.runtime.device import get_rocm_arch
from kernels.gemm.mxfp4_preshuffle import launch_gemm
from kernels.gemm.preshuffle_gemm import compile_preshuffle_gemm
from tests.kernels.utils import gemm_common_utils
from tests.utils import shuffle_weight


M, N, K = 32, 128, 256
TILE_M, TILE_N, TILE_K = 32, 128, 256
RTOL, ATOL = 0.1, 0.1
IMAGE_ID = "sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7"
UNSUPPORTED_COMBOS = (("fp6", "fp6"), ("bf16", "fp4"), ("fp6", "bf16"))


def pointer(tensor):
    return flyc.from_c_void_p(fx.Uint8, tensor.contiguous().data_ptr())


def git_output(*args):
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()


def environment_record():
    mlir_spec = importlib.util.find_spec("flydsl._mlir")
    mlir_paths = list(mlir_spec.submodule_search_locations or [])
    properties = torch.cuda.get_device_properties(0)
    return {
        "image_identity": IMAGE_ID,
        "python_executable": sys.executable,
        "python_version": sys.version,
        "flydsl_file": str(flydsl.__file__),
        "flydsl_version": str(getattr(flydsl, "__version__", "<missing>")),
        "flydsl_mlir_paths": [str(path) for path in mlir_paths],
        "torch_version": str(torch.__version__),
        "torch_hip_version": str(torch.version.hip),
        "triton_version": str(triton.__version__),
        "repo_commit": git_output("rev-parse", "HEAD"),
        "repo_branch": git_output("branch", "--show-current"),
        "gpu_name": torch.cuda.get_device_name(0),
        "gpu_arch": str(get_rocm_arch()),
        "gpu_uuid": str(properties.uuid),
        "gpu_gcn_arch": str(properties.gcnArchName),
        "visible_device_count": torch.cuda.device_count(),
    }


def error_metrics(actual, reference):
    absolute = (actual - reference).abs()
    relative = absolute / reference.abs().clamp_min(1.0e-6)
    return {
        "max_abs_error": float(absolute.max().item()),
        "mean_abs_error": float(absolute.mean().item()),
        "max_rel_error": float(relative.max().item()),
        "allclose": bool(torch.allclose(actual, reference, rtol=RTOL, atol=ATOL)),
    }


def run_a6w4():
    device = torch.device("cuda")
    torch.manual_seed(767)
    a_float = torch.randn(M, K, device=device, dtype=torch.float32)
    b_float = torch.randn(N, K, device=device, dtype=torch.float32)

    a_padded, a_scale_original, a_unpacked = gemm_common_utils.per_1x32_f6_quant(a_float)
    a_codes = a_padded[:M]
    a_scale = gemm_common_utils.shuffle_scale_w4(a_scale_original, 1, False)
    b_codes, b_scale_original, _ = gemm_common_utils.per_1x32_f4_quant(b_float)
    b_shuffled = gemm_common_utils.shuffle_weight_w4(b_codes, 16, False, False)
    b_scale = gemm_common_utils.shuffle_scale_w4(b_scale_original, 1, False)

    a_dequantized = gemm_common_utils.fp6_e2m3_to_f32(a_unpacked) * gemm_common_utils.e8m0_to_f32(
        a_scale_original.repeat_interleave(32, dim=1)
    )
    b_dequantized = gemm_common_utils.mxfp4_to_f32(b_codes) * gemm_common_utils.e8m0_to_f32(
        b_scale_original.repeat_interleave(32, dim=1)
    )
    reference = torch.mm(a_dequantized, b_dequantized.T)

    output = torch.zeros((M, N), dtype=torch.bfloat16, device=device)
    bias = torch.empty(0, dtype=torch.bfloat16, device=device)
    started = time.monotonic()
    launch_gemm(
        pointer(output),
        pointer(a_codes),
        pointer(b_shuffled),
        pointer(a_scale),
        pointer(b_scale),
        M,
        N,
        torch.cuda.current_stream(),
        N,
        K,
        TILE_M,
        TILE_N,
        TILE_K,
        "fp6",
        "bf16",
        "fp4",
        1,
        -1,
        -1,
        -1,
        -1,
        -1,
        -1,
        0,
        0,
        1,
        "none",
    )
    torch.cuda.synchronize()
    elapsed = time.monotonic() - started
    actual = output.to(torch.float32)
    return {
        "shape": [M, N, K],
        "tile": [TILE_M, TILE_N, TILE_K],
        "a_dtype": "fp6-e2m3",
        "b_dtype": "fp4-e2m1",
        "output_dtype": "bf16",
        "encoded_a_bytes": int(a_codes.numel()),
        "encoded_b_bytes": int(b_shuffled.numel()),
        "a_scale_bytes": int(a_scale.numel()),
        "b_scale_bytes": int(b_scale.numel()),
        "elapsed_seconds": elapsed,
        **error_metrics(actual, reference),
        "kernel_sample": [float(value) for value in actual[0, :4].tolist()],
        "reference_sample": [float(value) for value in reference[0, :4].tolist()],
    }


def run_bf16_control():
    device = torch.device("cuda")
    torch.manual_seed(768)
    a = torch.randn(M, K, device=device, dtype=torch.bfloat16)
    b = torch.randn(N, K, device=device, dtype=torch.bfloat16)
    reference = torch.mm(a.to(torch.float32), b.to(torch.float32).T)
    output = torch.zeros((M, N), dtype=torch.bfloat16, device=device)
    bias = torch.empty(0, dtype=torch.bfloat16, device=device)
    empty_scale = torch.empty(0, device=device, dtype=torch.float32)
    b_shuffled = shuffle_weight(b.contiguous(), layout=(16, 16))
    started = time.monotonic()
    kernel = compile_preshuffle_gemm(
        N=N,
        K=K,
        tile_m=TILE_M,
        tile_n=TILE_N,
        tile_k=TILE_K,
        in_dtype="bf16",
        out_dtype="bf16",
        use_async_copy=True,
    )
    kernel(
        output.view(-1),
        a.contiguous().view(-1),
        b_shuffled.view(-1),
        empty_scale,
        empty_scale,
        bias,
        M,
        N,
        torch.cuda.current_stream(),
    )
    torch.cuda.synchronize()
    elapsed = time.monotonic() - started
    actual = output.to(torch.float32)
    return {
        "shape": [M, N, K],
        "tile": [TILE_M, TILE_N, TILE_K],
        "a_dtype": "bf16",
        "b_dtype": "bf16",
        "output_dtype": "bf16",
        "elapsed_seconds": elapsed,
        **error_metrics(actual, reference),
        "kernel_sample": [float(value) for value in actual[0, :4].tolist()],
        "reference_sample": [float(value) for value in reference[0, :4].tolist()],
    }


def probe_unsupported(a_dtype, b_dtype):
    device = torch.device("cuda")
    a = torch.zeros(M, K, dtype=torch.uint8, device=device)
    b = torch.zeros(N, K // 2, dtype=torch.uint8, device=device)
    a_scale = torch.zeros((M // 32) * ((K + 255) // 256) * 64, dtype=torch.uint8, device=device)
    b_scale = torch.zeros((N // 32) * ((K + 255) // 256) * 64, dtype=torch.uint8, device=device)
    output = torch.zeros(M, N, dtype=torch.bfloat16, device=device)
    bias = torch.empty(0, dtype=torch.bfloat16, device=device)
    print(f"BEGIN a_dtype={a_dtype!r} b_dtype={b_dtype!r}", flush=True)
    launch_gemm(
        pointer(output),
        pointer(a),
        pointer(b),
        pointer(a_scale),
        pointer(b_scale),
        M,
        N,
        torch.cuda.current_stream(),
        N,
        K,
        TILE_M,
        TILE_N,
        TILE_K,
        a_dtype,
        "bf16",
        b_dtype,
        1,
        -1,
        -1,
        -1,
        -1,
        -1,
        -1,
        0,
        0,
        1,
        "none",
    )
    torch.cuda.synchronize()
    print(f"END a_dtype={a_dtype!r} b_dtype={b_dtype!r}", flush=True)


def capture_unsupported(a_dtype, b_dtype):
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT), environment.get("PYTHONPATH", "")]
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--probe-unsupported",
            a_dtype,
            b_dtype,
        ],
        cwd=REPO_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "a_dtype": a_dtype,
        "b_dtype": b_dtype,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-unsupported", nargs=2, metavar=("A_DTYPE", "B_DTYPE"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.probe_unsupported:
        probe_unsupported(*args.probe_unsupported)
        return

    if not torch.cuda.is_available():
        raise RuntimeError("A CUDA/ROCm GPU is required")
    if str(get_rocm_arch()) != "gfx950":
        raise RuntimeError(f"This investigation requires gfx950, got {get_rocm_arch()}")
    if torch.cuda.device_count() != 1:
        raise RuntimeError(f"Expected one visible GPU, got {torch.cuda.device_count()}")

    result = {
        "environment": environment_record(),
        "supported_atom_table": {
            "a_dtypes": ["fp4", "fp6", "fp8"],
            "b_dtypes": ["fp4", "fp8"],
            "atom": "MFMA_Scale(16, 16, 128, A, B, opsel_a, opsel_b)",
        },
        "a6w4": run_a6w4(),
        "bf16_control": run_bf16_control(),
        "unsupported": [capture_unsupported(*combo) for combo in UNSUPPORTED_COMBOS],
    }
    result["passed"] = result["a6w4"]["allclose"] and result["bf16_control"]["allclose"]
    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n")
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
