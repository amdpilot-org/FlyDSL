#!/usr/bin/env python3

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

import torch
import torch.nn.functional as torch_functional

import flydsl
from flydsl._mlir.dialects.fly import PointerType
from flydsl._mlir.dialects.fly_rocdl import TargetAddressSpace
from flydsl.expr import rocdl
from flydsl.expr.numeric import Int16, Int32, Int64
from flydsl.expr.primitive import make_ptr
from flydsl.expr.typing import AddressSpace, is_generic_address_space
from flydsl.runtime.device import get_rocm_arch, is_rdna_arch

from kernels.conv.conv3d_implicit import (
    _dispatch,
    _ncdhw_to_ndhwc,
    _prep_weight,
    _pick_tile,
    compile_conv3d_implicit,
    compile_transpose_ncdhw_ndhwc,
    conv3d_implicit,
)


DEFAULT_TILE = (128, 128, 2, 4)
CANDIDATES = [
    ((128, 128, 2, 4), 1),
    ((128, 128, 2, 4), 4),
    ((128, 128, 2, 4), 8),
    ((64, 128, 1, 4), 1),
    ((64, 64, 2, 2), 1),
    ((256, 128, 2, 4), 1),
]


def install_runtime_compatibility_shims():
    original_waitcnt = rocdl.s_waitcnt

    def normalize_counter(name, value, limit):
        if value is None:
            return 0
        value = int(value)
        if not 0 <= value <= limit:
            raise ValueError(f"{name} out of range: {value}")
        return value

    def compatible_waitcnt(bitfield=None, *, vmcnt=None, lgkmcnt=None, expcnt=None):
        if bitfield is not None:
            if vmcnt is not None or lgkmcnt is not None or expcnt is not None:
                raise TypeError("raw bitfield cannot be combined with named counters")
            return original_waitcnt(int(bitfield))
        vm_count = normalize_counter("vmcnt", vmcnt, 63)
        lgkm_count = normalize_counter("lgkmcnt", lgkmcnt, 15)
        exp_count = normalize_counter("expcnt", expcnt, 7)
        encoded = (vm_count & 0xF) | ((vm_count & 0x30) << 10)
        encoded |= lgkm_count << 8 | exp_count << 4
        return original_waitcnt(encoded)

    def compatible_make_buffer_ptr(pointer, num_records_bytes=None):
        if not is_generic_address_space(pointer.address_space, AddressSpace.Global):
            raise ValueError("make_buffer_ptr requires a global pointer")
        element_type = pointer.element_type
        bounds_checked = num_records_bytes is not None
        if num_records_bytes is None:
            num_records_bytes = Int64(0xFFFFFFFF)
        elif not isinstance(num_records_bytes, Int64):
            num_records_bytes = Int64(num_records_bytes)
        flags = (7 << 12) | (4 << 15)
        if is_rdna_arch(get_rocm_arch()):
            flags |= 1 << 24
            flags |= (3 if bounds_checked else 2) << 28
        pointer_type = PointerType.get(
            elem_ty=element_type.ir_type,
            address_space=TargetAddressSpace.BufferDesc,
            alignment=pointer.alignment,
        )
        return make_ptr(
            pointer_type,
            [
                pointer,
                Int16(0).ir_value(),
                num_records_bytes.ir_value(),
                Int32(flags).ir_value(),
            ],
        )

    rocdl.s_waitcnt = compatible_waitcnt
    rocdl.make_buffer_ptr = compatible_make_buffer_ptr
    return {
        "s_waitcnt_named_counters": True,
        "make_buffer_ptr": True,
        "get_buffer_rsrc": hasattr(rocdl, "get_buffer_rsrc"),
    }


def timing_statistics(times_ms):
    ordered = sorted(times_ms)
    return {
        "median_ms": statistics.median(ordered),
        "mean_ms": statistics.fmean(ordered),
        "stddev_ms": statistics.pstdev(ordered),
        "min_ms": ordered[0],
        "max_ms": ordered[-1],
        "p10_ms": ordered[max(0, int(0.10 * len(ordered)) - 1)],
        "p90_ms": ordered[min(len(ordered) - 1, int(0.90 * len(ordered)))],
        "repetitions": len(ordered),
    }


def benchmark_gpu(operation, warmup=10, repetitions=100):
    for _ in range(warmup):
        operation()
    torch.cuda.synchronize()
    times = []
    for _ in range(repetitions):
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        start.record()
        operation()
        end.record()
        torch.cuda.synchronize()
        times.append(start.elapsed_time(end))
    return timing_statistics(times)


def output_dimensions(shape):
    depth_out = (
        shape["depth"]
        + 2 * shape["padding"][0]
        - (shape["dilation"][0] * (shape["kernel"][0] - 1) + 1)
    ) // shape["stride"][0] + 1
    height_out = (
        shape["height"]
        + 2 * shape["padding"][1]
        - (shape["dilation"][1] * (shape["kernel"][1] - 1) + 1)
    ) // shape["stride"][1] + 1
    width_out = (
        shape["width"]
        + 2 * shape["padding"][2]
        - (shape["dilation"][2] * (shape["kernel"][2] - 1) + 1)
    ) // shape["stride"][2] + 1
    return depth_out, height_out, width_out


def make_shape(name, batch, channels, depth, height, width, output_channels, kernel, source_test):
    return {
        "name": name,
        "batch": batch,
        "channels": channels,
        "depth": depth,
        "height": height,
        "width": width,
        "output_channels": output_channels,
        "kernel": kernel,
        "stride": (1, 1, 1),
        "padding": (1, 1, 1) if kernel[0] == 3 else (0, 1, 1),
        "dilation": (1, 1, 1),
        "source_test": source_test,
    }


def shape_tensors(shape, seed):
    generator = torch.Generator(device="cuda")
    generator.manual_seed(seed)
    input_shape = (
        shape["batch"],
        shape["channels"],
        shape["depth"],
        shape["height"],
        shape["width"],
    )
    weight_shape = (
        shape["output_channels"],
        shape["channels"],
        *shape["kernel"],
    )
    input_tensor = torch.randn(input_shape, device="cuda", dtype=torch.bfloat16, generator=generator)
    weight_tensor = torch.randn(weight_shape, device="cuda", dtype=torch.bfloat16, generator=generator)
    return input_tensor, weight_tensor


def torch_reference(shape, input_tensor, weight_tensor):
    return torch_functional.conv3d(
        input_tensor,
        weight_tensor,
        stride=shape["stride"],
        padding=shape["padding"],
        dilation=shape["dilation"],
    )


def public_convolution(shape, input_tensor, weight_tensor, input_layout, tile=None, splitk=1):
    return conv3d_implicit(
        input_tensor,
        weight_tensor,
        stride=shape["stride"],
        padding=shape["padding"],
        dilation=shape["dilation"],
        splitk=splitk,
        tile=tile,
        input_layout=input_layout,
        output_layout="NCDHW",
    )


def compile_kernel(shape, input_ndhwc, weight_tensor, tile, wgm, splitk=1):
    return compile_conv3d_implicit(
        shape["batch"],
        shape["channels"],
        shape["depth"],
        shape["height"],
        shape["width"],
        shape["output_channels"],
        *shape["kernel"],
        *shape["stride"],
        *shape["padding"],
        *shape["dilation"],
        "zeros",
        False,
        splitk,
        tile,
        wgm,
        1,
        False,
    )


def rocm_snapshot():
    commands = [
        ["rocm-smi", "--showproductname", "--showserial", "--showuniqueid"],
        ["rocm-smi", "--showuse", "--showmemuse"],
    ]
    snapshots = {}
    for command in commands:
        label = " ".join(command[1:])
        try:
            snapshots[label] = subprocess.check_output(command, text=True, timeout=10)
        except Exception as exc:
            snapshots[label] = f"unavailable: {exc}"
    return snapshots


def native_library_paths():
    root = Path(flydsl.__file__).parent / "_mlir" / "_mlir_libs"
    return sorted(str(path) for path in root.glob("*.so*"))[:20]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="reports/j-7a07215034cb/results.json")
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--repetitions", type=int, default=100)
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(timezone.utc).isoformat()
    compatibility = install_runtime_compatibility_shims()
    torch.cuda.set_device(0)
    stream = torch.cuda.current_stream()

    shapes = [
        make_shape(
            "3d_autotune_test",
            1,
            128,
            6,
            40,
            40,
            128,
            (3, 3, 3),
            "tests/kernels/test_conv3d_implicit.py::test_conv3d_autotune",
        ),
        make_shape(
            "3d_tile_test",
            2,
            64,
            6,
            18,
            18,
            192,
            (3, 3, 3),
            "tests/kernels/test_conv3d_implicit.py::test_conv3d_tile_configs",
        ),
        make_shape(
            "2d_degenerate_test",
            2,
            64,
            1,
            24,
            28,
            128,
            (1, 3, 3),
            "tests/kernels/test_conv3d_implicit.py::test_conv2d_vs_torch",
        ),
    ]

    baseline_results = []
    for shape_index, shape in enumerate(shapes):
        seed = 4242 + shape_index
        input_tensor, weight_tensor = shape_tensors(shape, seed)
        reference = torch_reference(shape, input_tensor, weight_tensor)
        input_ndhwc = input_tensor.permute(0, 2, 3, 4, 1).contiguous()
        expected_ndhwc = input_tensor.permute(0, 2, 3, 4, 1).contiguous()
        packed_weight = _prep_weight(
            weight_tensor,
            shape["output_channels"],
            *shape["kernel"],
            shape["channels"],
        )
        bias_argument = torch.empty(1, device="cuda", dtype=torch.float32)
        depth_out, height_out, width_out = output_dimensions(shape)
        output_shape = (
            shape["batch"],
            shape["output_channels"],
            depth_out,
            height_out,
            width_out,
        )
        output_tensor = torch.empty(output_shape, device="cuda", dtype=torch.bfloat16)
        matrix_rows = shape["batch"] * depth_out * height_out * width_out
        matrix_columns = shape["output_channels"]
        matrix_inner = shape["channels"] * shape["kernel"][0] * shape["kernel"][1] * shape["kernel"][2]
        flops = 2 * matrix_rows * matrix_columns * matrix_inner

        kernel_builder = compile_kernel(shape, input_ndhwc, weight_tensor, DEFAULT_TILE, 1)
        cold_compile_start = time.perf_counter()
        kernel_builder.compile(output_tensor, input_ndhwc, packed_weight, bias_argument, stream)
        cold_compile_seconds = time.perf_counter() - cold_compile_start

        actual_default_tile = _pick_tile(
            shape["batch"] * depth_out * height_out * width_out,
            shape["output_channels"],
            1,
            torch.device("cuda"),
        )
        actual_default_builder = compile_kernel(
            shape,
            input_ndhwc,
            weight_tensor,
            actual_default_tile,
            1,
        )
        actual_default_cold_start = time.perf_counter()
        actual_default_builder.compile(
            output_tensor,
            input_ndhwc,
            packed_weight,
            bias_argument,
            stream,
        )
        actual_default_cold_seconds = time.perf_counter() - actual_default_cold_start

        def dispatch_actual_default():
            _dispatch(
                actual_default_builder,
                output_tensor,
                input_ndhwc,
                packed_weight,
                bias_argument,
                stream=stream,
            )

        dispatch_actual_default()
        torch.cuda.synchronize()
        actual_default_kernel_timing = benchmark_gpu(
            dispatch_actual_default,
            args.warmup,
            args.repetitions,
        )

        def dispatch_kernel():
            _dispatch(
                kernel_builder,
                output_tensor,
                input_ndhwc,
                packed_weight,
                bias_argument,
                stream=stream,
            )

        dispatch_kernel()
        torch.cuda.synchronize()
        kernel_timing = benchmark_gpu(dispatch_kernel, args.warmup, args.repetitions)

        transpose_builder = compile_transpose_ncdhw_ndhwc(
            shape["batch"],
            shape["channels"],
            shape["depth"] * shape["height"] * shape["width"],
        )
        transpose_output = torch.empty(
            (
                shape["batch"],
                shape["depth"],
                shape["height"],
                shape["width"],
                shape["channels"],
            ),
            device="cuda",
            dtype=torch.bfloat16,
        )
        transpose_cold_start = time.perf_counter()
        transpose_builder.compile(transpose_output, input_tensor, stream)
        transpose_cold_seconds = time.perf_counter() - transpose_cold_start

        def dispatch_transpose():
            _dispatch(transpose_builder, transpose_output, input_tensor, stream=stream)

        dispatch_transpose()
        torch.cuda.synchronize()
        transpose_timing = benchmark_gpu(dispatch_transpose, args.warmup, args.repetitions)

        def full_input_conversion():
            return _ncdhw_to_ndhwc(input_tensor, stream)

        full_input_conversion()
        torch.cuda.synchronize()
        conversion_timing = benchmark_gpu(full_input_conversion, args.warmup, args.repetitions)
        converted_input = full_input_conversion()
        conversion_exact = torch.equal(converted_input, expected_ndhwc)

        full_ncdhw_output = public_convolution(
            shape,
            input_tensor,
            weight_tensor,
            "NCDHW",
            DEFAULT_TILE,
        )
        full_ndhwc_output = public_convolution(
            shape,
            input_ndhwc,
            weight_tensor,
            "NDHWC",
            DEFAULT_TILE,
        )
        full_ncdhw_timing = benchmark_gpu(
            lambda: public_convolution(
                shape,
                input_tensor,
                weight_tensor,
                "NCDHW",
                DEFAULT_TILE,
            ),
            args.warmup,
            args.repetitions,
        )
        full_ndhwc_timing = benchmark_gpu(
            lambda: public_convolution(
                shape,
                input_ndhwc,
                weight_tensor,
                "NDHWC",
                DEFAULT_TILE,
            ),
            args.warmup,
            args.repetitions,
        )
        actual_default_full_ndhwc_output = public_convolution(
            shape,
            input_ndhwc,
            weight_tensor,
            "NDHWC",
            None,
        )
        actual_default_full_ncdhw_output = public_convolution(
            shape,
            input_tensor,
            weight_tensor,
            "NCDHW",
            None,
        )
        actual_default_full_ndhwc_timing = benchmark_gpu(
            lambda: public_convolution(
                shape,
                input_ndhwc,
                weight_tensor,
                "NDHWC",
                None,
            ),
            args.warmup,
            args.repetitions,
        )
        actual_default_full_ncdhw_timing = benchmark_gpu(
            lambda: public_convolution(
                shape,
                input_tensor,
                weight_tensor,
                "NCDHW",
                None,
            ),
            args.warmup,
            args.repetitions,
        )
        torch_conv_timing = benchmark_gpu(
            lambda: torch_reference(shape, input_tensor, weight_tensor),
            args.warmup,
            args.repetitions,
        )

        gemm_left = torch.randn(
            (matrix_rows, matrix_inner),
            device="cuda",
            dtype=torch.bfloat16,
        )
        gemm_right = torch.randn(
            (matrix_inner, matrix_columns),
            device="cuda",
            dtype=torch.bfloat16,
        )
        gemm_output = torch.empty(
            (matrix_rows, matrix_columns),
            device="cuda",
            dtype=torch.bfloat16,
        )
        gemm_timing = benchmark_gpu(
            lambda: torch.mm(gemm_left, gemm_right, out=gemm_output),
            args.warmup,
            args.repetitions,
        )
        gemm_reference = torch.mm(gemm_left.float(), gemm_right.float())
        gemm_max_difference = (gemm_output.float() - gemm_reference).abs().max().item()

        accuracy_ncdhw = torch.allclose(
            full_ncdhw_output,
            reference,
            rtol=2e-2,
            atol=2e-2,
        )
        accuracy_ndhwc = torch.allclose(
            full_ndhwc_output,
            reference,
            rtol=2e-2,
            atol=2e-2,
        )
        actual_default_accuracy_ndhwc = torch.allclose(
            actual_default_full_ndhwc_output,
            reference,
            rtol=2e-2,
            atol=2e-2,
        )
        actual_default_accuracy_ncdhw = torch.allclose(
            actual_default_full_ncdhw_output,
            reference,
            rtol=2e-2,
            atol=2e-2,
        )
        max_difference = (
            full_ndhwc_output.float() - reference.float()
        ).abs().max().item()

        actual_input_bytes = input_tensor.numel() * input_tensor.element_size()
        weight_bytes = weight_tensor.numel() * weight_tensor.element_size()
        output_bytes = reference.numel() * reference.element_size()
        gemm_logical_bytes = (
            gemm_left.numel() + gemm_right.numel() + gemm_output.numel()
        ) * gemm_left.element_size()

        baseline_results.append(
            {
                "shape": shape,
                "seed": seed,
                "implicit_gemm": {
                    "matrix_rows": matrix_rows,
                    "matrix_columns": matrix_columns,
                    "matrix_inner": matrix_inner,
                    "flops": flops,
                },
                "bytes": {
                    "actual_input": actual_input_bytes,
                    "weight": weight_bytes,
                    "output": output_bytes,
                    "gemm_logical": gemm_logical_bytes,
                },
                "accuracy": {
                    "gate": "torch.allclose(rtol=2e-2, atol=2e-2)",
                    "full_ncdhw_pass": accuracy_ncdhw,
                    "full_ndhwc_pass": accuracy_ndhwc,
                    "actual_default_full_ndhwc_pass": actual_default_accuracy_ndhwc,
                    "actual_default_full_ncdhw_pass": actual_default_accuracy_ncdhw,
                    "max_abs_difference": max_difference,
                    "layout_conversion_exact": conversion_exact,
                },
                "cold_compilation": {
                    "convolution_seconds": cold_compile_seconds,
                    "actual_default_tile_convolution_seconds": actual_default_cold_seconds,
                    "transpose_seconds": transpose_cold_seconds,
                },
                "actual_default_tile": list(actual_default_tile),
                "timings": {
                    "kernel_only": kernel_timing,
                    "actual_default_tile_kernel_only": actual_default_kernel_timing,
                    "layout_transpose_kernel": transpose_timing,
                    "full_input_conversion": conversion_timing,
                    "full_ncdhw_public_call": full_ncdhw_timing,
                    "full_ndhwc_public_call": full_ndhwc_timing,
                    "actual_default_full_ndhwc_public_call": actual_default_full_ndhwc_timing,
                    "actual_default_full_ncdhw_public_call": actual_default_full_ncdhw_timing,
                    "torch_conv3d": torch_conv_timing,
                    "torch_mm_equivalent_gemm": gemm_timing,
                },
                "tflops": {
                    "kernel_only": flops / (kernel_timing["median_ms"] / 1e3) / 1e12,
                    "full_ndhwc_public_call": flops
                    / (full_ndhwc_timing["median_ms"] / 1e3)
                    / 1e12,
                    "torch_conv3d": flops / (torch_conv_timing["median_ms"] / 1e3) / 1e12,
                    "torch_mm_equivalent_gemm": flops
                    / (gemm_timing["median_ms"] / 1e3)
                    / 1e12,
                },
                "gemm_max_abs_difference": gemm_max_difference,
            }
        )

    measured_bottleneck = max(
        baseline_results,
        key=lambda result: result["timings"]["kernel_only"]["median_ms"],
    )
    bottleneck_shape = measured_bottleneck["shape"]
    bottleneck_index = shapes.index(bottleneck_shape)
    bottleneck_seed = 4242 + bottleneck_index
    bottleneck_input, bottleneck_weight = shape_tensors(bottleneck_shape, bottleneck_seed)
    bottleneck_reference = torch_reference(bottleneck_shape, bottleneck_input, bottleneck_weight)
    bottleneck_input_ndhwc = bottleneck_input.permute(0, 2, 3, 4, 1).contiguous()
    bottleneck_packed_weight = _prep_weight(
        bottleneck_weight,
        bottleneck_shape["output_channels"],
        *bottleneck_shape["kernel"],
        bottleneck_shape["channels"],
    )
    bottleneck_bias = torch.empty(1, device="cuda", dtype=torch.float32)
    bottleneck_depth, bottleneck_height, bottleneck_width = output_dimensions(bottleneck_shape)
    bottleneck_output = torch.empty(
        (
            bottleneck_shape["batch"],
            bottleneck_shape["output_channels"],
            bottleneck_depth,
            bottleneck_height,
            bottleneck_width,
        ),
        device="cuda",
        dtype=torch.bfloat16,
    )

    candidate_results = []
    for candidate_index, (candidate_tile, candidate_wgm) in enumerate(CANDIDATES):
        candidate_record = {
            "candidate_index": candidate_index,
            "tile": list(candidate_tile),
            "wgm": candidate_wgm,
        }
        try:
            candidate_builder = compile_kernel(
                bottleneck_shape,
                bottleneck_input_ndhwc,
                bottleneck_weight,
                candidate_tile,
                candidate_wgm,
            )
            if hasattr(candidate_builder, "_cf"):
                candidate_record["cold_compilation_cached_from_baseline"] = True
            else:
                candidate_cold_start = time.perf_counter()
                candidate_builder.compile(
                    bottleneck_output,
                    bottleneck_input_ndhwc,
                    bottleneck_packed_weight,
                    bottleneck_bias,
                    stream,
                )
                candidate_record["cold_compilation_seconds"] = (
                    time.perf_counter() - candidate_cold_start
                )

            def dispatch_candidate():
                _dispatch(
                    candidate_builder,
                    bottleneck_output,
                    bottleneck_input_ndhwc,
                    bottleneck_packed_weight,
                    bottleneck_bias,
                    stream=stream,
                )

            dispatch_candidate()
            torch.cuda.synchronize()
            candidate_record["kernel_only"] = benchmark_gpu(
                dispatch_candidate,
                args.warmup,
                args.repetitions,
            )
            candidate_output = public_convolution(
                bottleneck_shape,
                bottleneck_input_ndhwc,
                bottleneck_weight,
                "NDHWC",
                candidate_tile,
            )
            candidate_record["accuracy_pass"] = torch.allclose(
                candidate_output,
                bottleneck_reference,
                rtol=2e-2,
                atol=2e-2,
            )
            candidate_record["max_abs_difference"] = (
                candidate_output.float() - bottleneck_reference.float()
            ).abs().max().item()
            candidate_record["tflops"] = (
                measured_bottleneck["implicit_gemm"]["flops"]
                / (candidate_record["kernel_only"]["median_ms"] / 1e3)
                / 1e12
            )
        except Exception as exc:
            candidate_record["error"] = f"{type(exc).__name__}: {exc}"
        candidate_results.append(candidate_record)

    successful_candidates = [
        candidate for candidate in candidate_results if "kernel_only" in candidate
    ]
    best_candidate = min(
        successful_candidates,
        key=lambda candidate: candidate["kernel_only"]["median_ms"],
    ) if successful_candidates else None

    winner_full_ndhwc_timing = None
    winner_full_ncdhw_timing = None
    if best_candidate is not None:
        winner_tile = tuple(best_candidate["tile"])

        def winner_full_ndhwc():
            return public_convolution(
                bottleneck_shape,
                bottleneck_input_ndhwc,
                bottleneck_weight,
                "NDHWC",
                winner_tile,
            )

        def winner_full_ncdhw():
            return public_convolution(
                bottleneck_shape,
                bottleneck_input,
                bottleneck_weight,
                "NCDHW",
                winner_tile,
            )

        winner_full_ndhwc()
        winner_full_ncdhw()
        torch.cuda.synchronize()
        winner_full_ndhwc_timing = benchmark_gpu(
            winner_full_ndhwc,
            args.warmup,
            args.repetitions,
        )
        winner_full_ncdhw_timing = benchmark_gpu(
            winner_full_ncdhw,
            args.warmup,
            args.repetitions,
        )

    git_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True,
        timeout=10,
    ).strip()
    device_properties = torch.cuda.get_device_properties(0)
    results = {
        "schema_version": 1,
        "started_at_utc": started_at,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "job": "j-7a07215034cb",
        "campaign": "repo-e2e-20260909",
        "upstream_context": {
            "issue": "https://github.com/ROCm/FlyDSL/issues/861",
            "issue_state": "open",
            "issue_resolution_claim": "https://github.com/ROCm/FlyDSL/pull/820",
            "pr820_head": "cb5074880aecfab5a0f85078051829eb3935c900",
            "pr820_merged": True,
            "mirror_base_commit": git_commit,
        },
        "environment": {
            "image_identity": "sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7",
            "image_identity_source": "operator-provided qualified local image ID",
            "python": sys.executable,
            "flydsl_version": flydsl.__version__,
            "flydsl_path": flydsl.__file__,
            "torch_version": torch.__version__,
            "torch_path": torch.__file__,
            "triton_version": __import__("triton").__version__,
            "triton_path": __import__("triton").__file__,
            "rocm_arch": get_rocm_arch(),
            "gpu_name": device_properties.name,
            "gpu_uuid": str(device_properties.uuid),
            "gpu_multiprocessor_count": device_properties.multi_processor_count,
            "gpu_total_memory_bytes": device_properties.total_memory,
            "native_library_paths": native_library_paths(),
            "cache_directories": {
                "flydsl_runtime": os.environ.get("FLYDSL_RUNTIME_CACHE_DIR"),
                "flydsl_autotune": os.environ.get("FLYDSL_AUTOTUNE_CACHE_DIR"),
                "triton": os.environ.get("TRITON_CACHE_DIR"),
                "torch_inductor": os.environ.get("TORCHINDUCTOR_CACHE_DIR"),
            },
            "runtime_compatibility_shims": compatibility,
            "automatic_splitk_limitation": "The source get_buffer_rsrc op is absent from installed FlyDSL 0.2.4; all measured paths force splitk=1.",
        },
        "methodology": {
            "accuracy_gate": "torch.allclose(rtol=2e-2, atol=2e-2)",
            "warmup_iterations": args.warmup,
            "timed_repetitions": args.repetitions,
            "candidate_count": len(CANDIDATES),
            "candidate_cap": 6,
            "candidates": [
                {"tile": list(tile), "wgm": wgm} for tile, wgm in CANDIDATES
            ],
            "gemm_estimate": "Torch mm on (implicit-GEMM M, output K, reduced C*K) with preallocated BF16 output",
            "cold_compilation": "Wall time for FlyDSL executable compile, separated from warm CUDA-event kernel dispatch",
        },
        "gpu_snapshots": {
            "before": rocm_snapshot(),
            "after": rocm_snapshot(),
        },
        "baseline_results": baseline_results,
        "bottleneck": {
            "shape": bottleneck_shape,
            "selection": "maximum measured kernel-only median time among the three baseline shapes",
            "candidate_results": candidate_results,
            "best_candidate": best_candidate,
            "winner_full_ndhwc_public_call": winner_full_ndhwc_timing,
            "winner_full_ncdhw_public_call": winner_full_ncdhw_timing,
        },
    }
    output_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
