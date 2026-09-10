#!/usr/bin/env python3

import argparse
import hashlib
import inspect
import json
import os
import pathlib
import sys
import time


CASES = {
    "opt0-debug0-verifier1": {"opt_level": "0", "debug_info": "0", "verifier": "1"},
    "opt2-debug0-verifier1": {"opt_level": "2", "debug_info": "0", "verifier": "1"},
    "opt3-debug0-verifier1": {"opt_level": "3", "debug_info": "0", "verifier": "1"},
    "opt2-debug1-verifier1": {"opt_level": "2", "debug_info": "1", "verifier": "1"},
    "opt2-debug0-verifier0": {"opt_level": "2", "debug_info": "0", "verifier": "0"},
    "arch-gfx942-mismatch": {"opt_level": "2", "debug_info": "0", "verifier": "1", "arch": "gfx942"},
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True, choices=sorted(CASES))
    parser.add_argument("--mode", required=True, choices=("cold", "warm"))
    parser.add_argument("--cache-root", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def sha256_text(text):
    return hashlib.sha256(text.encode()).hexdigest()


def sha256_file(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def main():
    args = parse_args()
    case = CASES[args.case]
    os.environ["FLYDSL_COMPILE_OPT_LEVEL"] = case["opt_level"]
    os.environ["FLYDSL_DEBUG_ENABLE_DEBUG_INFO"] = case["debug_info"]
    os.environ["FLYDSL_DEBUG_ENABLE_VERIFIER"] = case["verifier"]
    os.environ["ARCH"] = case.get("arch", "")
    os.environ["FLYDSL_RUNTIME_CACHE_DIR"] = args.cache_root

    import torch
    import flydsl
    import flydsl.compiler as flyc
    import flydsl.expr as fx
    from flydsl.compiler.backends.rocm import RocmBackend
    import flydsl._mlir._mlir_libs as mlir_libs

    original_pipeline_parts = RocmBackend._pipeline_parts

    def compatible_pipeline_parts(self, *, compile_hints):
        fragments, binary_fragment = original_pipeline_parts(self, compile_hints=compile_hints)
        fragments = [fragment.replace("convert-rocdl-fastmath-ops,", "") for fragment in fragments]
        return fragments, binary_fragment

    RocmBackend._pipeline_parts = compatible_pipeline_parts

    @flyc.kernel
    def int_vec_add_kernel(
        A: fx.Pointer,
        B: fx.Pointer,
        C: fx.Pointer,
        n: fx.Int32,
    ):
        idx = fx.block_idx.x * fx.block_dim.x + fx.thread_idx.x
        if idx < n:
            C[idx] = A[idx] + B[idx]

    @flyc.jit
    def int_vec_add(
        A: fx.Pointer,
        B: fx.Pointer,
        C: fx.Pointer,
        n: fx.Int32,
        stream: fx.Stream = fx.Stream(None),
    ):
        block_dim = 64
        grid_x = (n + block_dim - 1) // block_dim
        int_vec_add_kernel(A, B, C, n).launch(
            grid=(grid_x, 1, 1), block=[block_dim, 1, 1], stream=stream
        )

    size = 257
    torch.manual_seed(862)
    a = torch.randint(0, 100, (size,), device="cuda", dtype=torch.int32)
    b = torch.randint(0, 100, (size,), device="cuda", dtype=torch.int32)
    c = torch.full((size,), -2147483648, device="cuda", dtype=torch.int32)
    reference = (a.cpu() + b.cpu()).to(torch.int32)
    input_min = int(a.min().item())
    input_max = int(a.max().item())
    pointers = (
        flyc.from_c_void_p(fx.Int32, a.data_ptr()),
        flyc.from_c_void_p(fx.Int32, b.data_ptr()),
        flyc.from_c_void_p(fx.Int32, c.data_ptr()),
    )

    int_vec_add._ensure_sig()
    bound = int_vec_add._sig.bind(*pointers, size, stream=torch.cuda.Stream())
    bound.apply_defaults()
    cache_key = int_vec_add._build_full_cache_key(bound.arguments)
    cache_key_text = int_vec_add._cache_key_to_str(cache_key)

    started = time.perf_counter()
    error = None
    output_cpu = None
    try:
        int_vec_add(*pointers, size, stream=torch.cuda.Stream())
        torch.cuda.synchronize()
        output_cpu = c.cpu()
    except Exception as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
    elapsed = time.perf_counter() - started

    artifact = int_vec_add._mem_cache.get(cache_key)
    if artifact is None and int_vec_add._last_compiled is not None:
        last_key, last_artifact = int_vec_add._last_compiled
        if last_key == cache_key:
            artifact = last_artifact

    cache_file = None
    if int_vec_add.cache_manager is not None:
        cache_file = int_vec_add.cache_manager._cache_file(cache_key_text)

    result = {
        "case": args.case,
        "mode": args.mode,
        "options": {
            "FLYDSL_COMPILE_OPT_LEVEL": case["opt_level"],
            "FLYDSL_DEBUG_ENABLE_DEBUG_INFO": case["debug_info"],
            "FLYDSL_DEBUG_ENABLE_VERIFIER": case["verifier"],
            "ARCH": case.get("arch", ""),
        },
        "environment": {
            "python": sys.executable,
            "flydsl_python": flydsl.__file__,
            "flydsl_version": flydsl.__version__,
            "flydsl_native_root": str(pathlib.Path(mlir_libs.__file__).parent),
            "torch": torch.__file__,
            "torch_version": torch.__version__,
            "gpu": torch.cuda.get_device_name(0),
            "gpu_capability": torch.cuda.get_device_capability(0),
        },
        "source": {
            "probe": str(pathlib.Path(__file__).resolve()),
            "kernel": inspect.getsource(int_vec_add_kernel._original_func),
            "launcher": inspect.getsource(int_vec_add.func),
            "kernel_sha256": sha256_text(inspect.getsource(int_vec_add_kernel._original_func)),
            "launcher_sha256": sha256_text(inspect.getsource(int_vec_add.func)),
        },
        "sentinels": {
            "size": size,
            "input_min": input_min,
            "input_max": input_max,
            "expected_min": 0,
            "expected_max": 198,
            "initial_output": -2147483648,
        },
        "timing": {
            "method": "one perf_counter interval around one dispatch and final synchronize",
            "elapsed_seconds": elapsed,
        },
        "identity": {
            "manager_key": int_vec_add.manager_key,
            "cache_key": cache_key_text,
            "cache_root": args.cache_root,
            "cache_file": str(cache_file) if cache_file is not None else None,
            "cache_file_exists": bool(cache_file and cache_file.exists()),
            "cache_file_sha256": sha256_file(cache_file) if cache_file and cache_file.exists() else None,
            "compiled_ir_sha256": sha256_text(artifact._ir_text) if artifact else None,
            "source_ir_sha256": sha256_text(artifact._source_ir) if artifact else None,
        },
        "comparison": None,
        "error": error,
    }

    if error is None:
        result["comparison"] = {
            "reference": "independent CPU torch.add before GPU dispatch",
            "torch_equal": bool(torch.equal(output_cpu, reference)),
            "max_abs_diff": int((output_cpu - reference).abs().max().item()),
            "output_min": int(output_cpu.min().item()),
            "output_max": int(output_cpu.max().item()),
            "first_16": output_cpu[:16].tolist(),
            "last_16": output_cpu[-16:].tolist(),
        }

    output_path = pathlib.Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))

    expected_mismatch = args.case == "arch-gfx942-mismatch"
    if expected_mismatch:
        return 0 if error is not None or not result["comparison"]["torch_equal"] else 2
    return 0 if error is None and result["comparison"]["torch_equal"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
