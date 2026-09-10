#!/usr/bin/env python3
"""Compile, reload, and probe a tiny FlyDSL elementwise AOT kernel."""

import argparse
import hashlib
import json
import os
from pathlib import Path

import torch

import flydsl
import flydsl.compiler as flyc
import flydsl.expr as fx
import triton


SIZE = 1024
BLOCK_DIM = 64
VEC_WIDTH = 4


@flyc.kernel
def vec_add_kernel(
    a: fx.Tensor,
    b: fx.Tensor,
    out: fx.Tensor,
    block_dim: fx.Constexpr[int],
    vec_width: fx.Constexpr[int],
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
        fx.rocdl.BufferCopy(vec_width * fx.Float32.width),
        fx.Float32,
    )

    for lane in fx.range_constexpr(1):
        element = lane * block_dim + thread_idx
        fx.copy_atom_call(copy_atom, fx.slice(tile_a, (None, element)), reg_a)
        fx.copy_atom_call(copy_atom, fx.slice(tile_b, (None, element)), reg_b)
        value = fx.arith.addf(fx.memref_load_vec(reg_a), fx.memref_load_vec(reg_b))
        fx.memref_store_vec(value, reg_out)
        fx.copy_atom_call(copy_atom, reg_out, fx.slice(tile_out, (None, element)))


@flyc.jit
def vec_add(
    a: fx.Tensor,
    b: fx.Tensor,
    out: fx.Tensor,
    n: fx.Int32,
    const_n: fx.Constexpr[int],
    block_dim: fx.Constexpr[int],
    vec_width: fx.Constexpr[int],
    stream: fx.Stream = fx.Stream(None),
):
    tile_elems = block_dim * vec_width
    grid_x = (n + tile_elems - 1) // tile_elems
    vec_add_kernel(a, b, out, block_dim, vec_width).launch(
        grid=(grid_x, 1, 1),
        block=(block_dim, 1, 1),
        stream=stream,
    )


def artifact_identity(cache_dir: Path):
    files = sorted(cache_dir.rglob("*.pkl"))
    return [
        {
            "path": str(path),
            "size": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in files
    ]


def tensors(device):
    generator = torch.Generator(device=device).manual_seed(621)
    a = torch.randn(SIZE, generator=generator, device=device, dtype=torch.float32)
    b = torch.randn(SIZE, generator=generator, device=device, dtype=torch.float32)
    out = torch.full((SIZE,), -777.0, device=device, dtype=torch.float32)
    return a, b, out


def call_compiled(compiled, a, b, out, n):
    return compiled(a, b, out, n, SIZE, BLOCK_DIM, VEC_WIDTH, fx.Stream(None))


def probe_wrong_dtype(compiled, device):
    a, b, out = tensors(device)
    wrong_b = b.to(torch.float64)
    out.fill_(-777.0)
    raw_error = None
    try:
        call_compiled(compiled, a, wrong_b, out, SIZE)
        torch.cuda.synchronize()
    except BaseException as error:
        raw_error = f"{type(error).__name__}: {error}"
    return {
        "case": "wrong_dtype",
        "argument_signature": "a=float32[1024], b=float64[1024], out=float32[1024], n=int32",
        "raw_error": raw_error,
        "rejected_before_launch": raw_error is not None,
        "output_allclose_to_torch": bool(
            torch.allclose(out, torch.add(a, b.to(torch.float32)), rtol=1e-6, atol=1e-6)
        ),
        "output_checksum": hashlib.sha256(out.cpu().numpy().tobytes()).hexdigest(),
    }


def probe_wrong_rank(compiled, device):
    a, b, out = tensors(device)
    wrong_b = b.reshape(1, SIZE)
    out.fill_(-777.0)
    raw_error = None
    try:
        call_compiled(compiled, a, wrong_b, out, SIZE)
        torch.cuda.synchronize()
    except BaseException as error:
        raw_error = f"{type(error).__name__}: {error}"
    return {
        "case": "wrong_rank",
        "argument_signature": "a=float32[1024], b=float32[1,1024], out=float32[1024], n=int32",
        "raw_error": raw_error,
        "rejected_before_launch": raw_error is not None,
        "output_allclose_to_torch": bool(
            torch.allclose(out, torch.add(a, b.reshape(SIZE)), rtol=1e-6, atol=1e-6)
        ),
        "output_checksum": hashlib.sha256(out.cpu().numpy().tobytes()).hexdigest(),
    }


def probe_wrong_scalar(compiled, device):
    a, b, out = tensors(device)
    out.fill_(-777.0)
    raw_error = None
    try:
        call_compiled(compiled, a, b, out, float(SIZE))
        torch.cuda.synchronize()
    except BaseException as error:
        raw_error = f"{type(error).__name__}: {error}"
    return {
        "case": "wrong_scalar",
        "argument_signature": "a=float32[1024], b=float32[1024], out=float32[1024], n=float",
        "raw_error": raw_error,
        "rejected_before_launch": raw_error is not None,
        "output_allclose_to_torch": bool(
            torch.allclose(out, torch.add(a, b), rtol=1e-6, atol=1e-6)
        ),
        "output_checksum": hashlib.sha256(out.cpu().numpy().tobytes()).hexdigest(),
    }


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
        os.environ.pop("FLYDSL_RUNTIME_RUN_ONLY", None)

    device = torch.device("cuda", 0)
    native_dir = Path(flydsl.__file__).resolve().parent / "_mlir" / "_mlir_libs"
    native_modules = [
        str((native_dir / name).resolve())
        for name in (
            "_mlir.cpython-312-x86_64-linux-gnu.so",
            "_mlirDialectsFly.cpython-312-x86_64-linux-gnu.so",
            "libFlyPythonCAPI.so.23.0git",
            "libfly_jit_runtime.so",
        )
    ]
    native_modules.append(
        str((Path(triton.__file__).parent / "backends" / "amd" / "lib" / "libamdhip64.so").resolve())
    )
    torch.cuda.set_device(device)
    a, b, out = tensors(device)
    compiled = flyc.compile(
        vec_add,
        a,
        b,
        out,
        SIZE,
        SIZE,
        BLOCK_DIM,
        VEC_WIDTH,
        fx.Stream(None),
    )
    call_compiled(compiled, a, b, out, SIZE)
    torch.cuda.synchronize()
    expected = torch.add(a, b)

    result = {
        "mode": args.mode,
        "python": "/opt/venv/bin/python",
        "flydsl_source": flyc.__file__,
        "flydsl_expr_source": fx.__file__,
        "flydsl_version": getattr(flydsl, "__version__", None),
        "native_modules": native_modules,
        "torch_version": torch.__version__,
        "triton_version": __import__("triton").__version__,
        "gpu_name": torch.cuda.get_device_name(device),
        "gpu_capability": list(torch.cuda.get_device_capability(device)),
        "gpu_arch": "gfx950",
        "argument_signature": (
            "a=float32[1024], b=float32[1024], out=float32[1024], "
            "n=int32, const_n=1024, block_dim=64, vec_width=4, stream=fx.Stream"
        ),
        "numerical_gate": "torch.allclose(actual, expected, rtol=1e-6, atol=1e-6)",
        "valid_output_allclose_to_torch": bool(
            torch.allclose(out, expected, rtol=1e-6, atol=1e-6)
        ),
        "valid_output_max_abs_error": float((out - expected).abs().max().item()),
        "valid_output_checksum": hashlib.sha256(out.cpu().numpy().tobytes()).hexdigest(),
        "artifacts": artifact_identity(args.cache_dir),
    }

    if args.mode == "run":
        result["wrong_arguments"] = [
            probe_wrong_dtype(compiled, device),
            probe_wrong_rank(compiled, device),
            probe_wrong_scalar(compiled, device),
        ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
