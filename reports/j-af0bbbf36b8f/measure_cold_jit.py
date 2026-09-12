#!/usr/bin/env python3
"""Cold-JIT measurements for issue 862 using maintained GEMM/RMSNorm kernels."""

import argparse
import hashlib
import json
import time

import torch

import flydsl.compiler as flyc
from flydsl._mlir import ir
from flydsl.compiler import jit_function


def _timed_compiler():
    samples = []
    original = jit_function.MlirCompiler.compile.__func__

    def measured(cls, module, **kwargs):
        start = time.perf_counter()
        result = original(cls, module, **kwargs)
        samples.append(time.perf_counter() - start)
        return result

    jit_function.MlirCompiler.compile = classmethod(measured)
    return samples


def _artifact_identity(jit_fn):
    cache_key, artifact = jit_fn._last_compiled
    return {
        "cache_key_sha256": hashlib.sha256(repr(cache_key).encode()).hexdigest(),
        "source_ir_sha256": hashlib.sha256(artifact.source_ir.encode()).hexdigest(),
        "compiled_ir_sha256": hashlib.sha256(artifact._ir_text.encode()).hexdigest(),
        "source_ir_bytes": len(artifact.source_ir.encode()),
        "compiled_ir_bytes": len(artifact._ir_text.encode()),
    }


def _parse_cost(source_ir):
    with ir.Context() as ctx:
        ctx.load_all_available_dialects()
        start = time.perf_counter()
        ir.Module.parse(source_ir)
        return time.perf_counter() - start


def rmsnorm():
    from kernels.norm.rmsnorm_kernel import EPS, build_rmsnorm_module

    m, n = 16, 4096
    torch.manual_seed(42)
    x = torch.randn((m, n), device="cuda", dtype=torch.bfloat16)
    weight = torch.rand((n,), device="cuda", dtype=torch.bfloat16)
    out = torch.empty_like(x)
    stream = torch.cuda.current_stream()
    build_start = time.perf_counter()
    launch = build_rmsnorm_module(n, "bf16")
    build_s = time.perf_counter() - build_start
    compiler_s = _timed_compiler()
    torch.cuda.synchronize()
    start = time.perf_counter()
    compiled = flyc.compile(launch, x, weight, out, m, stream)
    torch.cuda.synchronize()
    cold_s = time.perf_counter() - start
    compiled(x, weight, out, m, stream)
    torch.cuda.synchronize()
    ref = (
        x.float()
        * torch.rsqrt(x.float().square().mean(1, keepdim=True) + EPS)
        * weight.float()
    ).to(x.dtype)
    torch.testing.assert_close(out, ref, atol=2e-2, rtol=1e-2)
    ident = _artifact_identity(launch)
    ident.update({"max_abs_error": (out.float() - ref.float()).abs().max().item()})
    return launch, {
        "kernel": "rmsnorm",
        "shape": [m, n],
        "build_s": build_s,
        "cold_first_call_s": cold_s,
        "compiler_pipeline_s": compiler_s,
        **ident,
    }


def gemm():
    from kernels.gemm.gemm_a16w16_gfx950 import gemm_a16w16, gemm_a16w16_gfx950

    m = n = k = 1024
    torch.manual_seed(42)
    a = torch.randn((m, k), device="cuda", dtype=torch.bfloat16)
    b = torch.randn((n, k), device="cuda", dtype=torch.bfloat16).t()
    out = torch.empty((m, n), device="cuda", dtype=torch.float32)
    compiler_s = _timed_compiler()
    torch.cuda.synchronize()
    start = time.perf_counter()
    config = {
        "block_m": 128,
        "block_n": 128,
        "block_k": 64,
        "stages": 4,
        "m_waves": 2,
        "n_waves": 4,
        "k_waves": 1,
        "group_m": 4,
        "use_half_tile_interleaved": False,
        "split_k": 1,
    }
    gemm_a16w16(a, b, out=out, layout="nt", out_dtype=torch.float32, user_kwargs=config)
    torch.cuda.synchronize()
    cold_s = time.perf_counter() - start
    ref = a.float() @ b.float()
    torch.testing.assert_close(out, ref, atol=3e-1, rtol=3e-2)
    ident = _artifact_identity(gemm_a16w16_gfx950)
    ident.update({"max_abs_error": (out - ref).abs().max().item()})
    return gemm_a16w16_gfx950, {
        "kernel": "gemm",
        "shape": [m, n, k],
        "cold_first_call_s": cold_s,
        "compiler_pipeline_s": compiler_s,
        **ident,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("kernel", choices=("gemm", "rmsnorm"))
    args = parser.parse_args()
    torch.cuda.init()
    torch.cuda.synchronize()
    jit_fn, result = globals()[args.kernel]()
    result["removed_text_parse_reference_s"] = _parse_cost(jit_fn._last_compiled[1].source_ir)
    result["device"] = torch.cuda.get_device_name()
    result["arch"] = torch.cuda.get_device_properties(0).gcnArchName
    result["cache_dir"] = str(jit_fn.cache_manager.cache_dir)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
