#!/usr/bin/env python3
"""Compile and run a small AOT kernel with two valid scalar specializations."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import torch
import triton

import flydsl
import flydsl.compiler as flyc
import flydsl.expr as fx


SIZE = 1024
BLOCK_DIM = 64
VEC_WIDTH = 4
SCALARS = (2.0, 3.0)


@flyc.kernel
def scaled_add_kernel(
    a: fx.Tensor,
    b: fx.Tensor,
    out: fx.Tensor,
    block_dim: fx.Constexpr[int],
    vec_width: fx.Constexpr[int],
    scale: fx.Constexpr[float],
):
    block_idx = fx.block_idx.x
    thread_idx = fx.thread_idx.x
    tile_elems = block_dim * vec_width

    a = fx.rocdl.make_buffer_tensor(a)
    b = fx.rocdl.make_buffer_tensor(b)
    out = fx.rocdl.make_buffer_tensor(out)

    tile_a = fx.logical_divide(a, fx.make_layout(tile_elems, 1))
    tile_b = fx.logical_divide(b, fx.make_layout(tile_elems, 1))
    tile_out = fx.logical_divide(out, fx.make_layout(tile_elems, 1))
    tile_a = fx.slice(tile_a, (None, block_idx))
    tile_b = fx.slice(tile_b, (None, block_idx))
    tile_out = fx.slice(tile_out, (None, block_idx))
    tile_a = fx.logical_divide(tile_a, fx.make_layout(vec_width, 1))
    tile_b = fx.logical_divide(tile_b, fx.make_layout(vec_width, 1))
    tile_out = fx.logical_divide(tile_out, fx.make_layout(vec_width, 1))

    reg_a = fx.make_rmem_tensor(vec_width, fx.Float32)
    reg_b = fx.make_rmem_tensor(vec_width, fx.Float32)
    reg_out = fx.make_rmem_tensor(vec_width, fx.Float32)
    copy_atom = fx.make_copy_atom(
        fx.rocdl.BufferCopy(vec_width * fx.Float32.width), fx.Float32
    )

    for lane in fx.range_constexpr(1):
        element = lane * block_dim + thread_idx
        fx.copy_atom_call(copy_atom, fx.slice(tile_a, (None, element)), reg_a)
        fx.copy_atom_call(copy_atom, fx.slice(tile_b, (None, element)), reg_b)
        scaled_b = fx.memref_load_vec(reg_b) * fx.Float32(scale)
        value = fx.arith.addf(fx.memref_load_vec(reg_a), scaled_b)
        fx.memref_store_vec(value, reg_out)
        fx.copy_atom_call(copy_atom, reg_out, fx.slice(tile_out, (None, element)))


@flyc.jit
def scaled_add(
    a: fx.Tensor,
    b: fx.Tensor,
    out: fx.Tensor,
    n: fx.Int32,
    block_dim: fx.Constexpr[int],
    vec_width: fx.Constexpr[int],
    scale: fx.Constexpr[float],
    stream: fx.Stream = fx.Stream(None),
):
    tile_elems = block_dim * vec_width
    grid_x = (n + tile_elems - 1) // tile_elems
    scaled_add_kernel(
        a, b, out, block_dim, vec_width, scale
    ).launch(
        grid=(grid_x, 1, 1),
        block=(block_dim, 1, 1),
        stream=stream,
    )


def tensors(device: torch.device):
    generator = torch.Generator(device=device).manual_seed(621)
    a = torch.randn(SIZE, generator=generator, device=device, dtype=torch.float32)
    b = torch.randn(SIZE, generator=generator, device=device, dtype=torch.float32)
    out = torch.full((SIZE,), -777.0, device=device, dtype=torch.float32)
    return a, b, out


def call(compiled, a, b, out, scale):
    return compiled(
        a, b, out, SIZE, BLOCK_DIM, VEC_WIDTH, scale, fx.Stream(None)
    )


def cache_key_for(scale):
    scaled_add._ensure_sig()
    bound = scaled_add._sig.bind(
        torch.empty(0, dtype=torch.float32),
        torch.empty(0, dtype=torch.float32),
        torch.empty(0, dtype=torch.float32),
        SIZE,
        BLOCK_DIM,
        VEC_WIDTH,
        scale,
        fx.Stream(None),
    )
    bound.apply_defaults()
    return scaled_add._build_full_cache_key(bound.arguments)


def artifact_identity(cache_dir: Path, cache_key):
    path = scaled_add.cache_manager._cache_file(
        scaled_add._cache_key_to_str(cache_key)
    )
    return {
        "path": str(path),
        "exists": path.exists(),
        "size": path.stat().st_size if path.exists() else None,
        "sha256": (
            hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        ),
    }


def native_modules():
    native_dir = Path(flydsl.__file__).resolve().parent / "_mlir" / "_mlir_libs"
    return [
        str((native_dir / name).resolve())
        for name in (
            "_mlir.cpython-312-x86_64-linux-gnu.so",
            "_mlirDialectsFly.cpython-312-x86_64-linux-gnu.so",
            "libFlyPythonCAPI.so.23.0git",
            "libfly_jit_runtime.so",
        )
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("compile", "run"))
    parser.add_argument("cache_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    os.environ["FLYDSL_RUNTIME_CACHE_DIR"] = str(args.cache_dir)
    os.environ["FLYDSL_RUNTIME_ENABLE_CACHE"] = "1"
    if args.mode == "run":
        os.environ["FLYDSL_RUNTIME_RUN_ONLY"] = "1"
    else:
        os.environ["COMPILE_ONLY"] = "1"
        os.environ.pop("FLYDSL_RUNTIME_RUN_ONLY", None)

    device = torch.device("cuda", 0)
    torch.cuda.set_device(device)
    a, b, out = tensors(device)
    cases = []

    for scale in SCALARS:
        out.fill_(-777.0)
        executed = args.mode == "run"
        started = torch.cuda.Event(enable_timing=True)
        stopped = torch.cuda.Event(enable_timing=True)
        started.record()
        compiled = flyc.compile(
            scaled_add,
            a,
            b,
            out,
            SIZE,
            BLOCK_DIM,
            VEC_WIDTH,
            scale,
            fx.Stream(None),
        )
        if args.mode == "run":
            call(compiled, a, b, out, scale)
        stopped.record()
        torch.cuda.synchronize()

        expected = torch.add(a, b * scale)
        allclose = (
            bool(torch.allclose(out, expected, rtol=1e-6, atol=1e-6))
            if executed
            else None
        )
        cache_key = cache_key_for(scale)
        cases.append(
            {
                "scale": scale,
                "argument_signature": (
                    "a=float32[1024], b=float32[1024], out=float32[1024], "
                    "n=int32, block_dim=64, vec_width=4, "
                    "scale=constexpr[float], stream=fx.Stream"
                ),
                "cache_key": str(cache_key),
                "artifact": artifact_identity(args.cache_dir, cache_key),
                "allclose": allclose,
                "max_abs_error": (
                    float((out - expected).abs().max().item())
                    if allclose is not None
                    else None
                ),
                "output_checksum": hashlib.sha256(
                    out.cpu().numpy().tobytes()
                ).hexdigest(),
                "event_elapsed_ms": started.elapsed_time(stopped),
            }
        )

    result = {
        "mode": args.mode,
        "flydsl_version": flydsl.__version__,
        "flydsl_source": flydsl.__file__,
        "flydsl_expr_source": fx.__file__,
        "function_signature": str(scaled_add._sig),
        "native_modules": native_modules(),
        "torch_version": torch.__version__,
        "triton_version": triton.__version__,
        "gpu_name": torch.cuda.get_device_name(device),
        "gpu_capability": list(torch.cuda.get_device_capability(device)),
        "gpu_arch": "gfx950",
        "numerical_gate": (
            "torch.allclose(actual, a + scale*b, rtol=1e-6, atol=1e-6)"
        ),
        "cases": cases,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
