#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""Record synthetic gfx942 GEMM numerics, compilation status, and VGPR usage."""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("FLYDSL_DUMP_IR", "1")
os.environ.setdefault("FLYDSL_RUNTIME_ENABLE_CACHE", "0")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import flydsl
import torch
from flydsl.compiler.diagnostics import DSLCompileError

from tests.kernels.test_buffer_copy_gemm_gfx942 import (
    _compile_gemm as compile_fp8_gemm,
    _compile_raw_mfma as compile_fp8_raw,
    _inputs as fp8_inputs,
    _run_gemm as run_fp8,
)
from tests.kernels.test_buffer_copy_gemm_gfx942_dtypes import (
    DTYPES,
    _compile_gemm as compile_dtype_gemm,
    _compile_raw_mfma as compile_dtype_raw,
    _run as run_dtype,
)


def _git_commit():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def _native_paths():
    import flydsl._mlir._mlir_libs as native_libs

    native_root = Path(native_libs.__file__).parent
    return {
        "flydsl_python": Path(flydsl.__file__).resolve().as_posix(),
        "libFlyPythonCAPI": (native_root / "libFlyPythonCAPI.so").resolve().as_posix(),
        "libfly_jit_runtime": (native_root / "libfly_jit_runtime.so").resolve().as_posix(),
    }


def _environment(image_identity):
    device = torch.cuda.get_device_properties(0)
    return {
        "flydsl_version": getattr(flydsl, "__version__", "unknown"),
        "torch_version": torch.__version__,
        "hip_version": torch.version.hip,
        "gpu_name": device.name,
        "gpu_total_memory_bytes": device.total_memory,
        "gpu_count": torch.cuda.device_count(),
        "image_identity": image_identity,
        "source_commit": _git_commit(),
        "tool_paths": {
            name: shutil.which(name) for name in ("hipcc", "rocminfo", "rocm-smi", "clang++", "lld", "llvm-mc")
        },
        **_native_paths(),
    }


def _vgpr_count(dump_root):
    isa_files = sorted(Path(dump_root).rglob("21_final_isa.s"))
    if not isa_files:
        return None
    match = re.search(
        r"^\s*\.amdhsa_next_free_vgpr\s+(\d+)$", isa_files[-1].read_text(), re.MULTILINE
    )
    return int(match.group(1)) if match else None


def _fp8_result(launch, dump_root):
    os.environ["FLYDSL_DUMP_DIR"] = str(dump_root)
    result = run_fp8(launch)
    A, B, _ = fp8_inputs()
    reference = A.float().cpu() @ B.float().cpu().T
    difference = (result.cpu() - reference).abs()
    return {
        "status": "passed",
        "max_abs_error_vs_torch": float(difference.max()),
        "mean_abs_error_vs_torch": float(difference.mean()),
        "vgpr_count": _vgpr_count(dump_root),
    }


def _dtype_result(launch, dtype, dump_root):
    os.environ["FLYDSL_DUMP_DIR"] = str(dump_root)
    result, A, B = run_dtype(launch, dtype)
    reference = A.float().cpu() @ B.float().cpu().T
    difference = (result.cpu() - reference).abs()
    return {
        "status": "passed",
        "max_abs_error_vs_torch": float(difference.max()),
        "mean_abs_error_vs_torch": float(difference.mean()),
        "vgpr_count": _vgpr_count(dump_root),
    }


def _failed_result(error, dump_root):
    return {
        "status": "failed",
        "error_type": type(error).__name__,
        "error": str(error).splitlines()[0],
        "vgpr_count": _vgpr_count(dump_root),
    }


def _collect(output_root):
    results = {}

    raw_dump = output_root / "fp8_raw_mfma"
    try:
        results["fp8_raw_mfma"] = _fp8_result(compile_fp8_raw(), raw_dump)
    except DSLCompileError as error:
        results["fp8_raw_mfma"] = _failed_result(error, raw_dump)

    for copy_kind in ("universal32", "buffer32", "buffer64", "global_buffer32", "global_buffer64"):
        dump_root = output_root / f"fp8_gemm_{copy_kind}"
        try:
            launch = compile_fp8_gemm(copy_kind, use_buffer_tensor=copy_kind.startswith("buffer"))
            results[f"fp8_gemm_{copy_kind}"] = _fp8_result(launch, dump_root)
        except DSLCompileError as error:
            results[f"fp8_gemm_{copy_kind}"] = _failed_result(error, dump_root)

    for dtype_name, (dtype, torch_dtype) in DTYPES.items():
        raw_dump = output_root / f"{dtype_name}_raw_mfma"
        try:
            results[f"{dtype_name}_raw_mfma"] = _dtype_result(
                compile_dtype_raw(dtype), torch_dtype, raw_dump
            )
        except DSLCompileError as error:
            results[f"{dtype_name}_raw_mfma"] = _failed_result(error, raw_dump)

        for copy_kind in ("universal32", "buffer64"):
            dump_root = output_root / f"{dtype_name}_gemm_{copy_kind}"
            try:
                launch = compile_dtype_gemm(dtype, copy_kind)
                results[f"{dtype_name}_gemm_{copy_kind}"] = _dtype_result(
                    launch, torch_dtype, dump_root
                )
            except DSLCompileError as error:
                results[f"{dtype_name}_gemm_{copy_kind}"] = _failed_result(error, dump_root)

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dump-root", type=Path, required=True)
    parser.add_argument("--image-identity", required=True)
    arguments = parser.parse_args()

    arguments.dump_root.mkdir(parents=True, exist_ok=True)
    report = {
        "environment": _environment(arguments.image_identity),
        "shape": {"M": 64, "N": 16, "K": 128},
        "results": _collect(arguments.dump_root),
    }
    arguments.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
