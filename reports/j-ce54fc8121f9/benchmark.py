#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import torch


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("cold", "warm"), required=True)
    parser.add_argument("--cache-root", required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--image-id", default="sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7")
    return parser.parse_args()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def tensor_sha256(tensor):
    raw = tensor.detach().contiguous().cpu().view(torch.uint8).numpy().tobytes()
    return sha256_bytes(raw)


def cache_entries(cache_root):
    entries = []
    for path in sorted(Path(cache_root).rglob("*.pkl")):
        entries.append(
            {
                "path": str(path),
                "size": path.stat().st_size,
                "sha256": sha256_bytes(path.read_bytes()),
            }
        )
    return entries


def git_commit(source_root):
    return subprocess.check_output(["git", "-C", source_root, "rev-parse", "HEAD"], text=True).strip()


def gpu_identity():
    properties = torch.cuda.get_device_properties(0)
    try:
        rocm_smi = subprocess.check_output(["rocm-smi", "--showproduct", "--showid"], text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        rocm_smi = ""
    return {
        "name": properties.name,
        "capability": list(torch.cuda.get_device_capability(0)),
        "multi_processor_count": properties.multi_processor_count,
        "total_memory_bytes": properties.total_memory,
        "rocm_smi": rocm_smi,
    }


def install_phase_instrumentation():
    from flydsl.compiler import jit_executor, jit_function

    phases = defaultdict(float)
    artifact_hashes = {}

    original_compile = jit_function.MlirCompiler.compile.__func__

    def timed_compile(cls, *args, **kwargs):
        start = time.perf_counter()
        result = original_compile(cls, *args, **kwargs)
        phases["frontend_lowering_code_object_s"] += time.perf_counter() - start
        return result

    jit_function.MlirCompiler.compile = classmethod(timed_compile)

    original_build_call_state = jit_function._build_call_state

    def timed_build_call_state(*args, **kwargs):
        start = time.perf_counter()
        return original_build_call_state(*args, **kwargs)

    jit_function._build_call_state = timed_build_call_state

    original_ensure_engine = jit_executor.CompiledArtifact._ensure_engine

    def timed_ensure_engine(self):
        start = time.perf_counter()
        result = original_ensure_engine(self)
        phases["code_object_load_s"] += time.perf_counter() - start
        artifact_hashes[sha256_bytes(self._ir_text.encode())] = len(artifact_hashes) + 1
        return result

    jit_executor.CompiledArtifact._ensure_engine = timed_ensure_engine

    def timed_build_wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = timed_build_call_state(*args, **kwargs)
        phases["call_state_s"] += time.perf_counter() - start
        return result

    jit_function._build_call_state = timed_build_wrapper
    return phases, artifact_hashes


def measure_call(label, function, args, phases, artifact_hashes):
    phases.clear()
    start = time.perf_counter()
    function(*args)
    total = time.perf_counter() - start
    sync_start = time.perf_counter()
    torch.cuda.synchronize()
    sync_seconds = time.perf_counter() - sync_start
    observable = dict(phases)
    residual = total - observable.get("frontend_lowering_code_object_s", 0.0)
    residual -= observable.get("code_object_load_s", 0.0)
    residual -= observable.get("call_state_s", 0.0)
    return {
        "label": label,
        "total_jit_call_s": total,
        "frontend_cache_and_host_launch_s": max(residual, 0.0),
        "frontend_lowering_code_object_s": observable.get("frontend_lowering_code_object_s", 0.0),
        "code_object_load_s": observable.get("code_object_load_s", 0.0),
        "call_state_s": observable.get("call_state_s", 0.0),
        "gpu_sync_s": sync_seconds,
        "artifact_ir_sha256": sorted(artifact_hashes),
    }


def run_gemm(source_root, phases, artifact_hashes):
    from kernels.gemm.preshuffle_gemm import compile_preshuffle_gemm
    from tests.utils import shuffle_weight

    rows, columns, depth = 16, 64, 64
    torch.manual_seed(20260910)
    a = torch.randn(rows, depth, device="cuda", dtype=torch.bfloat16)
    b = torch.randn(columns, depth, device="cuda", dtype=torch.bfloat16)
    b_shuffled = shuffle_weight(b, layout=(16, 16))
    output = torch.zeros(rows, columns, device="cuda", dtype=torch.bfloat16)
    empty_f32 = torch.empty(0, device="cuda", dtype=torch.float32)
    empty_f16 = torch.empty(0, device="cuda", dtype=torch.float16)
    stream = torch.cuda.current_stream()
    function = compile_preshuffle_gemm(
        N=columns,
        K=depth,
        tile_m=16,
        tile_n=64,
        tile_k=64,
        in_dtype="bf16",
        out_dtype="bf16",
    )
    args = (
        output.contiguous().view(-1),
        a.contiguous().view(-1),
        b_shuffled.contiguous().view(-1),
        empty_f32,
        empty_f32,
        empty_f16,
        rows,
        columns,
        stream,
    )
    measurements = [
        measure_call("cold_or_disk_warm", function, args, phases, artifact_hashes),
        measure_call("in_process_warm", function, args, phases, artifact_hashes),
    ]
    reference = torch.mm(a.float(), b.t().float()).to(torch.bfloat16)
    difference = (output.float() - reference.float()).abs()
    return {
        "kernel": "preshuffle_gemm",
        "shape": [rows, columns, depth],
        "configuration": {
            "tile": [16, 64, 64],
            "in_dtype": "bf16",
            "out_dtype": "bf16",
        },
        "input_sha256": {
            "a": tensor_sha256(a),
            "b": tensor_sha256(b),
            "b_shuffled": tensor_sha256(b_shuffled),
            "output_initial": tensor_sha256(torch.zeros_like(output)),
        },
        "reference": "torch.mm(a.float(), b.t().float()).to(bfloat16)",
        "gate": {"atol": 0.1, "rtol": 0.1},
        "max_abs_error": difference.max().item(),
        "mean_abs_error": difference.mean().item(),
        "gate_passed": torch.allclose(output, reference, atol=0.1, rtol=0.1),
        "measurements": measurements,
    }


def run_rmsnorm(source_root, phases, artifact_hashes):
    from kernels.norm.rmsnorm_kernel import build_rmsnorm_module

    rows, columns = 16, 64
    torch.manual_seed(20260910)
    input_tensor = torch.randn(rows, columns, device="cuda", dtype=torch.bfloat16)
    gamma = torch.rand(columns, device="cuda", dtype=torch.bfloat16)
    output = torch.empty_like(input_tensor)
    stream = torch.cuda.current_stream()
    function = build_rmsnorm_module(columns, dtype_str="bf16")
    args = (input_tensor, gamma, output, rows, stream)
    measurements = [
        measure_call("cold_or_disk_warm", function, args, phases, artifact_hashes),
        measure_call("in_process_warm", function, args, phases, artifact_hashes),
    ]
    input_float = input_tensor.float()
    reference = (
        input_float
        * torch.rsqrt(input_float.pow(2).mean(-1, keepdim=True) + 1e-6)
        * gamma.float()
    ).to(torch.bfloat16)
    difference = (output.float() - reference.float()).abs()
    return {
        "kernel": "rmsnorm",
        "shape": [rows, columns],
        "configuration": {"dtype": "bf16", "eps": 1e-6},
        "input_sha256": {
            "input": tensor_sha256(input_tensor),
            "gamma": tensor_sha256(gamma),
            "output_initial": tensor_sha256(torch.empty_like(output)),
        },
        "reference": "x * rsqrt(mean(x^2) + eps) * gamma in float32, cast to bfloat16",
        "gate": {"atol": 2e-2, "rtol": 0.0},
        "max_abs_error": difference.max().item(),
        "mean_abs_error": difference.mean().item(),
        "gate_passed": bool(difference.max().item() < 2e-2),
        "measurements": measurements,
    }


def main():
    args = parse_args()
    source_root = str(Path(args.source_root).resolve())
    cache_root = str(Path(args.cache_root).resolve())
    os.environ["FLYDSL_RUNTIME_CACHE_DIR"] = cache_root
    os.environ["FLYDSL_RUNTIME_ENABLE_CACHE"] = "1"
    sys.path.insert(0, source_root)

    import torch
    import triton
    import flydsl
    from flydsl.compiler.jit_executor import _resolve_runtime_libs

    cache_files = list(Path(cache_root).rglob("*.pkl"))
    if args.mode == "cold" and cache_files:
        raise RuntimeError(f"cold mode requires an empty cache, found {len(cache_files)} pickle files")
    if args.mode == "warm" and len(cache_files) < 2:
        raise RuntimeError(f"warm mode requires both cached kernels, found {len(cache_files)} pickle files")

    phases, artifact_hashes = install_phase_instrumentation()
    results = {
        "mode": args.mode,
        "image_id": args.image_id,
        "source_root": source_root,
        "source_commit": git_commit(source_root),
        "cache_root": cache_root,
        "cache_before": cache_entries(cache_root),
        "environment": {
            "python": sys.executable,
            "flydsl": flydsl.__file__,
            "flydsl_version": flydsl.__version__,
            "torch": torch.__file__,
            "torch_version": torch.__version__,
            "torch_hip": torch.version.hip,
            "triton": triton.__file__,
            "triton_version": triton.__version__,
            "native_runtime_libs": _resolve_runtime_libs(),
        },
        "gpu": gpu_identity(),
        "kernels": [],
    }
    results["kernels"].append(run_gemm(source_root, phases, artifact_hashes))
    results["kernels"].append(run_rmsnorm(source_root, phases, artifact_hashes))
    results["cache_after"] = cache_entries(cache_root)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
