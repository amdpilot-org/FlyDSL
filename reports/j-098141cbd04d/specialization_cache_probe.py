#!/usr/bin/env python3
import argparse
import enum
import json
import os
import time

import torch

import flydsl.compiler as flyc
import flydsl.expr as fx
from flydsl.compiler.backends.rocm import RocmBackend


original_pipeline_parts = RocmBackend._pipeline_parts


def compatibility_pipeline_parts(self, *, compile_hints):
    pre_binary, binary = original_pipeline_parts(self, compile_hints=compile_hints)
    pre_binary = [fragment.replace("convert-rocdl-fastmath-ops,", "") for fragment in pre_binary]
    return pre_binary, binary


RocmBackend._pipeline_parts = compatibility_pipeline_parts



class Mode(enum.Enum):
    ADD = 0
    MAX = 1



def make_launcher(scale, mode):
    @flyc.kernel
    def kernel(A: fx.Pointer, B: fx.Pointer, C: fx.Pointer, n: fx.Int32):
        idx = fx.block_idx.x * fx.block_dim.x + fx.thread_idx.x
        if idx < n:
            if mode is Mode.ADD:
                C[idx] = A[idx] * fx.Float32(scale) + B[idx]
            else:
                C[idx] = fx.max(A[idx], B[idx]) * fx.Float32(scale)

    @flyc.jit
    def launch(A: fx.Pointer, B: fx.Pointer, C: fx.Pointer, n: fx.Int32, stream: fx.Stream = fx.Stream(None)):
        block_dim = 256
        grid_x = (n + block_dim - 1) // block_dim
        kernel(A, B, C, n).launch(grid=(grid_x, 1, 1), block=[block_dim, 1, 1], stream=stream)

    return launch


def run_case(case, size, seed):
    torch.manual_seed(seed)
    a = torch.randn(size, device="cuda", dtype=torch.float32)
    b = torch.randn(size, device="cuda", dtype=torch.float32)
    c = torch.empty_like(a)
    stream = torch.cuda.Stream()
    launcher = make_launcher(case["scale"], case["mode"])

    def call():
        c.zero_()
        start = time.perf_counter()
        launcher(
            flyc.from_c_void_p(fx.Float32, a.data_ptr()),
            flyc.from_c_void_p(fx.Float32, b.data_ptr()),
            flyc.from_c_void_p(fx.Float32, c.data_ptr()),
            size,
            stream=stream,
        )
        torch.cuda.synchronize()
        return time.perf_counter() - start

    cold_seconds = call()
    cache_key = (
        launcher._last_compiled[0]
        if launcher._last_compiled is not None
        else next(iter(launcher._call_state_cache))
    )
    manager_key = launcher.manager_key
    warm_seconds = call()
    if case["mode"] is Mode.ADD:
        expected = a * case["scale"] + b
    else:
        expected = torch.maximum(a, b) * case["scale"]
    max_abs_error = float((c - expected).abs().max().item())
    return {
        **case,
        "cache_key": str(cache_key),
        "manager_key": manager_key,
        "cold_seconds": cold_seconds,
        "warm_seconds": warm_seconds,
        "max_abs_error": max_abs_error,
        "allclose": bool(torch.allclose(c, expected, rtol=1e-5, atol=1e-5)),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("populate", "load"))
    parser.add_argument("output")
    args = parser.parse_args()

    cases = [
        {"scale": 2.0, "mode": Mode.ADD},
        {"scale": 3.0, "mode": Mode.ADD},
        {"scale": 2.0, "mode": Mode.MAX},
        {"scale": 3.0, "mode": Mode.MAX},
    ]
    if args.phase == "load":
        cases.reverse()

    results = [run_case(case, size=1024, seed=862 + index) for index, case in enumerate(cases)]
    keys = [result["manager_key"] for result in results]
    report = {
        "phase": args.phase,
        "source_commit": os.environ.get("FLYDSL_SOURCE_COMMIT", ""),
        "python": os.sys.executable,
        "gpu": torch.cuda.get_device_name(0),
        "cache_dir": os.environ.get("FLYDSL_RUNTIME_CACHE_DIR", ""),
        "cases": [{**result, "mode": result["mode"].name} for result in results],
        "distinct_manager_keys": len(keys) == len(set(keys)),
        "all_outputs_correct": all(result["allclose"] for result in results),
    }
    with open(args.output, "w", encoding="utf-8") as output:
        json.dump(report, output, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
