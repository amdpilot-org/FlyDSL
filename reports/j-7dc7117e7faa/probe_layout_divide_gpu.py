#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import tempfile
import time

import torch
import flydsl
import flydsl.compiler as flyc
import flydsl.expr as fx
from flydsl._mlir.extras import types as T
from flydsl.expr import buffer_ops


SHAPE = (64, 50, 80)
STRIDES = (16000, 160, 1)
TILE = (32,)
SENTINEL = -739.0
NONE_TILE = (32, None, None)
PARTIAL_NONE_TILE = (32, None, 40)


@flyc.kernel
def logical_copy_kernel(source: fx.Tensor, destination: fx.Tensor):
    source_resource = buffer_ops.create_buffer_resource(source, max_size=True)
    destination_resource = buffer_ops.create_buffer_resource(destination, max_size=True)
    layout = fx.make_layout(SHAPE, STRIDES)
    divided = fx.logical_divide(layout, TILE)
    offset = fx.get_scalar(fx.crd2idx((fx.thread_idx.x, (0, 0, 0)), divided))
    value = buffer_ops.buffer_load(
        source_resource, offset, vec_width=1, dtype=T.f32()
    )
    buffer_ops.buffer_store(value, destination_resource, offset)


@flyc.kernel
def zipped_copy_kernel(source: fx.Tensor, destination: fx.Tensor):
    source_resource = buffer_ops.create_buffer_resource(source, max_size=True)
    destination_resource = buffer_ops.create_buffer_resource(destination, max_size=True)
    layout = fx.make_layout(SHAPE, STRIDES)
    divided = fx.zipped_divide(layout, TILE)
    offset = fx.get_scalar(fx.crd2idx((fx.thread_idx.x, (0, 0, 0)), divided))
    value = buffer_ops.buffer_load(
        source_resource, offset, vec_width=1, dtype=T.f32()
    )
    buffer_ops.buffer_store(value, destination_resource, offset)


@flyc.kernel
def logical_none_copy_kernel(source: fx.Tensor, destination: fx.Tensor):
    source_resource = buffer_ops.create_buffer_resource(source, max_size=True)
    destination_resource = buffer_ops.create_buffer_resource(destination, max_size=True)
    layout = fx.make_layout(SHAPE, STRIDES)
    divided = fx.logical_divide(layout, NONE_TILE)
    offset = fx.get_scalar(fx.crd2idx(((fx.thread_idx.x, 0), 0, 0), divided))
    value = buffer_ops.buffer_load(
        source_resource, offset, vec_width=1, dtype=T.f32()
    )
    buffer_ops.buffer_store(value, destination_resource, offset)


@flyc.kernel
def logical_partial_none_copy_kernel(source: fx.Tensor, destination: fx.Tensor):
    source_resource = buffer_ops.create_buffer_resource(source, max_size=True)
    destination_resource = buffer_ops.create_buffer_resource(destination, max_size=True)
    layout = fx.make_layout(SHAPE, STRIDES)
    divided = fx.logical_divide(layout, PARTIAL_NONE_TILE)
    offset = fx.get_scalar(fx.crd2idx(((fx.thread_idx.x, 0), 0, (0, 0)), divided))
    value = buffer_ops.buffer_load(
        source_resource, offset, vec_width=1, dtype=T.f32()
    )
    buffer_ops.buffer_store(value, destination_resource, offset)


@flyc.jit
def launch_logical_none(source, destination, stream: fx.Stream):
    logical_none_copy_kernel(source, destination).launch(
        grid=(1, 1, 1), block=(32, 1, 1), stream=stream
    )


@flyc.jit
def launch_logical_partial_none(source, destination, stream: fx.Stream):
    logical_partial_none_copy_kernel(source, destination).launch(
        grid=(1, 1, 1), block=(32, 1, 1), stream=stream
    )


@flyc.jit
def launch_logical(source, destination, stream: fx.Stream):
    logical_copy_kernel(source, destination).launch(
        grid=(1, 1, 1), block=(32, 1, 1), stream=stream
    )


@flyc.jit
def launch_zipped(source, destination, stream: fx.Stream):
    zipped_copy_kernel(source, destination).launch(
        grid=(1, 1, 1), block=(32, 1, 1), stream=stream
    )


def as_layout_tensor(values):
    return torch.as_strided(values, SHAPE, STRIDES)


def run_case(name, launcher):
    source_storage = torch.full((1016000,), SENTINEL, device="cuda", dtype=torch.float32)
    destination_storage = torch.full_like(source_storage, SENTINEL)
    source = as_layout_tensor(source_storage)
    destination = as_layout_tensor(destination_storage)
    for index in range(32):
        source[index, 0, 0] = index + 1

    started = time.perf_counter()
    launcher(source, destination, torch.cuda.current_stream())
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - started

    host_map = {index: index * STRIDES[0] for index in range(32)}
    observed = [float(destination_storage[offset]) for offset in host_map.values()]
    expected = [float(index + 1) for index in range(32)]
    untouched = int((destination_storage == SENTINEL).sum().item())
    exact = observed == expected and untouched == destination_storage.numel() - 32
    return {
        "case": name,
        "elapsed_seconds": elapsed,
        "host_index_map": host_map,
        "observed": observed,
        "expected": expected,
        "untouched_sentinel_count": untouched,
        "exact_match": exact,
    }


def run_diagnostic_case(name, operation, tile, shape, strides):
    child = f"""import flydsl.compiler as flyc
import flydsl.expr as fx

@flyc.jit
def probe():
    layout = fx.make_layout({shape!r}, {strides!r})
    print({operation}(layout, {tile!r}))

probe()
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as child_file:
        child_file.write(child)
        child_path = child_file.name
    command = ["sh", "-c", "ulimit -c 0; exec /opt/venv/bin/python \"$1\"", "python", child_path]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    os.unlink(child_path)
    return {
        "case": name,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="layout-divide-gpu-results.json")
    args = parser.parse_args()

    results = {
        "label": "installed-source gfx950 probe; not proof for checkout changes",
        "python": "/opt/venv/bin/python",
        "flydsl_module": flydsl.__file__,
        "flydsl_version": flydsl.__version__,
        "torch_version": torch.__version__,
        "rocm_version": torch.version.hip,
        "gpu": subprocess.run(
            ["rocm-smi", "--showproductname", "--showserial"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout,
        "cases": [],
        "diagnostics": [],
    }
    results["cases"].append(run_case("logical_divide((64,50,80):(16000,160,1), (32,))", launch_logical))
    results["cases"].append(run_case("zipped_divide((64,50,80):(16000,160,1), (32,))", launch_zipped))
    results["cases"].append(
        run_case(
            "logical_divide((64,50,80):(16000,160,1), (32,None,None))",
            launch_logical_none,
        )
    )
    results["cases"].append(
        run_case(
            "logical_divide((64,50,80):(16000,160,1), (32,None,40))",
            launch_logical_partial_none,
        )
    )
    results["diagnostics"].append(
        run_diagnostic_case(
            "zipped_divide((64,50,80):(16000,160,1), (32,None,None))",
            "fx.zipped_divide",
            (32, None, None),
            (64, 50, 80),
            (16000, 160, 1),
        )
    )
    results["diagnostics"].append(
        run_diagnostic_case(
            "zipped_divide((64,50,80):(16000,160,1), (32,None,40))",
            "fx.zipped_divide",
            (32, None, 40),
            (64, 50, 80),
            (16000, 160, 1),
        )
    )
    results["diagnostics"].append(
        run_diagnostic_case(
            "invalid rank: logical_divide((64,):(1,), (32,None))",
            "fx.logical_divide",
            (32, None),
            (64,),
            (1,),
        )
    )

    with open(args.output, "w") as handle:
        json.dump(results, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(results, indent=2, sort_keys=True))
    assert all(case["exact_match"] for case in results["cases"])


if __name__ == "__main__":
    main()
