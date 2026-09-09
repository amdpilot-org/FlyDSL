#!/usr/bin/env python3
"""Validate FlyDSL code-object generation and ROCm options on gfx950."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

import torch

import flydsl
import flydsl.compiler as flyc
import flydsl.expr as fx
from flydsl._mlir import ir


@flyc.kernel
def add_kernel(
    a: fx.Tensor,
    b: fx.Tensor,
    c: fx.Tensor,
    tiled_copy: fx.TiledCopy,
) -> None:
    thread_id = fx.thread_idx.x
    block_x, block_y = fx.block_idx.x, fx.block_idx.y
    rows, columns = a.shape.unpack()
    coordinates = fx.make_view((0, 0), fx.make_identity_layout((rows, columns)))
    tile = tiled_copy.tile_mn

    global_a = fx.flat_divide(a, tile)[None, None, block_x, block_y]
    global_b = fx.flat_divide(b, tile)[None, None, block_x, block_y]
    global_c = fx.flat_divide(c, tile)[None, None, block_x, block_y]
    global_coordinates = fx.flat_divide(coordinates, tile)[None, None, block_x, block_y]

    thread_copy = tiled_copy.get_slice(thread_id)
    thread_a = thread_copy.partition_S(global_a)
    thread_b = thread_copy.partition_S(global_b)
    thread_c = thread_copy.partition_D(global_c)
    thread_coordinates = thread_copy.partition_S(global_coordinates)[(0, None), None, None]

    register_a = fx.make_fragment_like(thread_a)
    register_b = fx.make_fragment_like(thread_b)
    register_c = fx.make_fragment_like(thread_c)
    predicate = fx.make_fragment_like(thread_coordinates, dtype=fx.Boolean)
    for index in fx.range_constexpr(fx.size(predicate.shape).unpack()):
        predicate[index] = fx.elem_less(thread_coordinates[index], (rows, columns))

    copy_atom = fx.make_copy_atom(fx.UniversalCopy128b(), fx.Float32)
    fx.copy(copy_atom, thread_a, register_a, pred=predicate)
    fx.copy(copy_atom, thread_b, register_b, pred=predicate)
    register_c.store(register_a.load() + register_b.load())
    fx.copy(copy_atom, register_c, thread_c, pred=predicate)


@flyc.jit
def add_launch(
    a: fx.Tensor,
    b: fx.Tensor,
    c: fx.Tensor,
    stream: fx.Stream = fx.Stream(None),
) -> None:
    copy_atom = fx.make_copy_atom(fx.UniversalCopy128b(), fx.Float32)
    tiled_copy = fx.make_tiled_copy_tv(
        copy_atom,
        fx.make_ordered_layout((8, 16), order=(1, 0)),
        fx.make_ordered_layout((1, 4), order=(0, 1)),
    )
    tile_rows, tile_columns = tiled_copy.tile_mn.unpack()
    rows, columns = a.shape.unpack()
    grid_rows = (rows + tile_rows - 1) // tile_rows
    grid_columns = (columns + tile_columns - 1) // tile_columns
    add_kernel(a, b, c, tiled_copy).launch(
        grid=(grid_rows, grid_columns, 1),
        block=(8 * 16, 1, 1),
        stream=stream,
    )


def ir_text() -> str:
    compiled = add_launch._last_compiled[1]
    return compiled._ir_text


def decode_mlir_binary(value: str) -> bytes:
    decoded = []
    index = 0
    while index < len(value):
        if value[index] != "\\":
            decoded.append(value[index])
            index += 1
            continue
        if index + 1 >= len(value):
            raise ValueError("unterminated MLIR escape")
        if value[index + 1] in {"\\", '"'}:
            decoded.append(value[index + 1])
            index += 2
            continue
        if index + 3 > len(value):
            raise ValueError("truncated MLIR hex escape")
        decoded.append(chr(int(value[index + 1 : index + 3], 16)))
        index += 3
    return "".join(decoded).encode("latin-1")


def code_objects(text: str, artifact_prefix: str) -> list[dict]:
    with ir.Context():
        module = ir.Module.parse(text)
        binary = next(operation for operation in module.body if operation.name == "gpu.binary")
        objects = []
        for index, attribute in enumerate(binary.attributes["objects"]):
            object_text = str(attribute)
            target = re.search(r"#rocdl\.target<([^>]*)>", object_text)
            binary_text = re.search(r'bin = "([^"]*)"', object_text)
            if binary_text is None:
                raise RuntimeError("gpu.object has no embedded binary")
            data = decode_mlir_binary(binary_text.group(1))
            objects.append(
                {
                    "index": index,
                    "target": target.group(1) if target else None,
                    "elf_size_bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
            (Path(__file__).parent / f"{artifact_prefix}-{index}.elf").write_bytes(data)
        return objects


def offloading_handler(text: str) -> str:
    with ir.Context():
        module = ir.Module.parse(text)
        binary = next(operation for operation in module.body if operation.name == "gpu.binary")
        return str(binary.attributes["offloadingHandler"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--artifact-prefix", default="code-object")
    parser.add_argument(
        "--omit-initial-target",
        action="store_true",
        help="omit the bare gpu.module target; rocdl-attach-target then creates the sole object",
    )
    args = parser.parse_args()

    if args.omit_initial_target:
        from flydsl.compiler.backends.rocm import RocmBackend

        RocmBackend.gpu_module_targets = lambda self: []

    torch.manual_seed(1054)
    a = torch.randn(64, 128, dtype=torch.float32, device="cuda")
    b = torch.randn(64, 128, dtype=torch.float32, device="cuda")
    c = torch.zeros_like(a)
    hints = {
        "fast_fp_math": True,
        "unsafe_fp_math": True,
        "waves_per_eu": 2,
        "maxnreg": 128,
    }

    started = time.perf_counter()
    executable = flyc.compile[hints](add_launch)
    executable(a, b, c, stream=torch.cuda.Stream())
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - started

    expected = a + b
    max_abs_error = (c - expected).abs().max().item()
    allclose = torch.allclose(c, expected, rtol=1e-6, atol=1e-6)
    text = ir_text()
    objects = code_objects(text, args.artifact_prefix)
    handler = offloading_handler(text)
    target_lines = [
        line.strip()
        for line in text.splitlines()
        if "rocdl.target" in line or "gpu.object" in line or "gpu.binary" in line
    ]
    result = {
        "flydsl_version": flydsl.__version__,
        "flydsl_module": flyc.__file__,
        "torch_version": torch.__version__,
        "torch_hip_version": torch.version.hip,
        "gpu_name": torch.cuda.get_device_name(0),
        "gpu_capability": list(torch.cuda.get_device_capability(0)),
        "compile_hints": hints,
        "initial_target_omitted": args.omit_initial_target,
        "cold_compile_and_launch_seconds": elapsed,
        "cold_compile_and_launch_milliseconds": round(elapsed * 1000, 3),
        "max_abs_error": max_abs_error,
        "allclose_rtol_1e-6_atol_1e-6": allclose,
        "target_lines": target_lines,
        "rocdl_target_count": text.count("rocdl.target"),
        "gpu_object_count": text.count("gpu.object"),
        "code_objects": objects,
        "offloading_handler": handler,
        "default_handler_selects_first_object": handler == "#gpu.select_object",
        "unique_code_object_sha256_count": len({item["sha256"] for item in objects}),
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if not allclose:
        raise SystemExit("numerical gate failed")


if __name__ == "__main__":
    main()
