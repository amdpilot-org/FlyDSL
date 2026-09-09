#!/usr/bin/env python3

import argparse
import importlib.metadata
import json
import os
import subprocess
import sys
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.profiler import ProfilerActivity, profile

from flydsl.runtime.device import get_rocm_arch
from kernels.conv.conv3d_implicit import _ncdhw_to_ndhwc, conv3d_implicit


RTOL = 2e-2
ATOL = 2e-2
WARMUP_ITERATIONS = 5
TIMED_ITERATIONS = 20
PROFILE_ITERATIONS = 5


def command_output(command):
    try:
        return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as error:
        return f"unavailable: {error}"


def as_layout(tensor, layout):
    if layout == "NDHWC":
        return tensor.permute(0, 2, 3, 4, 1).contiguous()
    return tensor.contiguous()


def comparison(actual, expected):
    actual_float = actual.float()
    expected_float = expected.float()
    difference = (actual_float - expected_float).abs()
    close = torch.isclose(actual_float, expected_float, rtol=RTOL, atol=ATOL)
    return {
        "shape": list(actual.shape),
        "expected_shape": list(expected.shape),
        "allclose": bool(actual.shape == expected.shape and torch.allclose(
            actual_float, expected_float, rtol=RTOL, atol=ATOL
        )),
        "mismatch_count": int((~close).sum().item()) if actual.shape == expected.shape else None,
        "max_abs_diff": float(difference.max().item()) if actual.shape == expected.shape else None,
        "mean_abs_diff": float(difference.mean().item()) if actual.shape == expected.shape else None,
    }


def timed_call(call):
    for _ in range(WARMUP_ITERATIONS):
        call()
    torch.cuda.synchronize()
    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    start.record()
    for _ in range(TIMED_ITERATIONS):
        call()
    end.record()
    torch.cuda.synchronize()
    return start.elapsed_time(end) / TIMED_ITERATIONS


def profile_call(call):
    with profile(activities=[ProfilerActivity.CUDA]) as profiler:
        for _ in range(PROFILE_ITERATIONS):
            call()
        torch.cuda.synchronize()

    kernels = []
    for event in profiler.key_averages():
        device_time = (
            getattr(event, "self_device_time_total", 0)
            or getattr(event, "self_cuda_time_total", 0)
        )
        if device_time:
            kernels.append({
                "name": event.key,
                "count": int(event.count),
                "total_us": float(device_time),
                "per_call_us": float(device_time / PROFILE_ITERATIONS),
            })

    def total(predicate):
        return sum(event["per_call_us"] for event in kernels if predicate(event["name"]))

    conv_us = total(lambda name: "conv3d_implicit_kernel" in name)
    transpose_us = total(lambda name: "transpose" in name.lower())
    return {
        "conv_us_per_call": conv_us,
        "transpose_us_per_call": transpose_us,
        "other_data_movement_us_per_call": sum(
            event["per_call_us"] for event in kernels
        ) - conv_us - transpose_us,
        "kernels": kernels,
    }


def measure(name, call):
    return {
        "name": name,
        "event_ms_per_call": timed_call(call),
        **profile_call(call),
    }


def layer(
    x,
    weight,
    bias,
    stride,
    padding,
    input_layout,
    output_layout,
    out_layout=None,
    pass_none_out_layout=False,
):
    resolved_out_layout = None if pass_none_out_layout else (
        out_layout if out_layout is not None else output_layout
    )
    return conv3d_implicit(
        x,
        weight,
        bias=bias,
        stride=stride,
        padding=padding,
        splitk=1,
        layout=input_layout,
        out_layout=resolved_out_layout,
    )


def build_environment(args):
    candidate = Path(args.candidate).resolve()
    aiter_path = Path("/opt/aiter/aiter/__init__.py")
    properties = torch.cuda.get_device_properties(0)
    return {
        "image_id": args.image_id,
        "candidate_path": str(candidate),
        "candidate_commit": command_output(["git", "-C", str(candidate), "rev-parse", "HEAD"]),
        "candidate_status": command_output(["git", "-C", str(candidate), "status", "--short"]),
        "python_executable": os.path.abspath(sys.executable),
        "python_version": sys.version.replace("\n", " "),
        "gpu_name": torch.cuda.get_device_name(0),
        "gpu_capability": list(torch.cuda.get_device_capability(0)),
        "gpu_multiprocessor_count": properties.multi_processor_count,
        "gpu_total_memory_gib": properties.total_memory / 1024**3,
        "rocm_arch": str(get_rocm_arch()),
        "rocm_smi": command_output(["rocm-smi", "--showproductname", "--showdriverversion"]),
        "hipcc_version": command_output(["hipcc", "--version"]),
        "torch_version": torch.__version__,
        "torch_hip": torch.version.hip,
        "torch_module": torch.__file__,
        "triton_version": importlib.metadata.version("triton"),
        "triton_module": importlib.import_module("triton").__file__,
        "flydsl_version": importlib.import_module("flydsl").__version__,
        "flydsl_module": importlib.import_module("flydsl").__file__,
        "aiter_version": importlib.metadata.version("amd-aiter"),
        "aiter_module": str(aiter_path) if aiter_path.exists() else None,
        "hip_library": command_output(["bash", "-lc", "ldconfig -p | grep libamdhip64.so.7 | head -1"]),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", default="/job/FlyDSL-candidate")
    parser.add_argument("--image-id", default="sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7")
    parser.add_argument("--output", default="results.json")
    args = parser.parse_args()

    torch.manual_seed(344)
    input_shape = (2, 32, 5, 8, 10)
    x_ncdhw = torch.randn(input_shape, device="cuda", dtype=torch.bfloat16) * 0.1
    x_ndhwc = x_ncdhw.permute(0, 2, 3, 4, 1).contiguous()
    weight_1 = torch.randn((64, 32, 3, 3, 3), device="cuda", dtype=torch.bfloat16) * 0.1
    bias_1 = torch.randn((64,), device="cuda", dtype=torch.float32) * 0.1
    weight_2 = torch.randn((48, 64, 3, 3, 3), device="cuda", dtype=torch.bfloat16) * 0.1
    bias_2 = torch.randn((48,), device="cuda", dtype=torch.float32) * 0.1
    stride_1 = (1, 2, 1)
    padding_1 = (1, 0, 1)
    stride_2 = (1, 1, 2)
    padding_2 = (0, 1, 1)

    reference_1 = F.conv3d(
        x_ncdhw,
        weight_1,
        bias=bias_1.to(torch.bfloat16),
        stride=stride_1,
        padding=padding_1,
    )
    reference_2 = F.conv3d(
        reference_1,
        weight_2,
        bias=bias_2.to(torch.bfloat16),
        stride=stride_2,
        padding=padding_2,
    )

    modes = {
        "ncdhw_ncdhw": ("NCDHW", "NCDHW", "NCDHW", "NCDHW"),
        "ndhwc_ndhwc": ("NDHWC", "NDHWC", "NDHWC", "NDHWC"),
        "ncdhw_to_ndhwc_then_ncdhw": ("NCDHW", "NDHWC", "NDHWC", "NCDHW"),
        "ndhwc_to_ncdhw_then_ndhwc": ("NDHWC", "NCDHW", "NCDHW", "NDHWC"),
    }

    correctness = {}
    for name, (first_in, first_out, second_in, second_out) in modes.items():
        source = x_ndhwc if first_in == "NDHWC" else x_ncdhw
        actual_1 = layer(
            source, weight_1, bias_1, stride_1, padding_1, first_in, first_out
        )
        actual_2 = layer(
            actual_1, weight_2, bias_2, stride_2, padding_2, second_in, second_out
        )
        torch.cuda.synchronize()
        correctness[name] = {
            "layer_1_input_layout": first_in,
            "layer_1_output_layout": first_out,
            "layer_2_input_layout": second_in,
            "layer_2_output_layout": second_out,
            "intermediate": comparison(actual_1, as_layout(reference_1, first_out)),
            "final": comparison(actual_2, as_layout(reference_2, second_out)),
        }

    actual_1 = layer(x_ncdhw, weight_1, bias_1, stride_1, padding_1, "NCDHW", "NCDHW")
    converted = _ncdhw_to_ndhwc(actual_1, None)
    actual_2 = layer(converted, weight_2, bias_2, stride_2, padding_2, "NDHWC", "NDHWC")
    torch.cuda.synchronize()
    correctness["explicit_mid_conversion"] = {
        "layer_1_input_layout": "NCDHW",
        "layer_1_output_layout": "NCDHW",
        "explicit_conversion": "NCDHW_to_NDHWC",
        "layer_2_input_layout": "NDHWC",
        "layer_2_output_layout": "NDHWC",
        "intermediate": comparison(actual_1, reference_1),
        "converted_intermediate": comparison(converted, as_layout(reference_1, "NDHWC")),
        "final": comparison(actual_2, as_layout(reference_2, "NDHWC")),
    }

    actual_1 = layer(
        x_ndhwc,
        weight_1,
        bias_1,
        stride_1,
        padding_1,
        "NDHWC",
        "NDHWC",
        pass_none_out_layout=True,
    )
    actual_2 = layer(
        actual_1,
        weight_2,
        bias_2,
        stride_2,
        padding_2,
        "NDHWC",
        "NDHWC",
        pass_none_out_layout=True,
    )
    torch.cuda.synchronize()
    correctness["out_layout_none_inherits_ndhwc"] = {
        "layer_1_input_layout": "NDHWC",
        "layer_1_output_layout": "NDHWC",
        "layer_2_input_layout": "NDHWC",
        "layer_2_output_layout": "NDHWC",
        "intermediate": comparison(actual_1, as_layout(reference_1, "NDHWC")),
        "final": comparison(actual_2, as_layout(reference_2, "NDHWC")),
    }

    def single_call(source, input_layout, output_layout):
        return lambda: layer(
            source, weight_1, bias_1, stride_1, padding_1, input_layout, output_layout
        )

    def chain_call(mode):
        first_in, first_out, second_in, second_out = modes[mode]
        source = x_ndhwc if first_in == "NDHWC" else x_ncdhw

        def call():
            intermediate = layer(
                source, weight_1, bias_1, stride_1, padding_1, first_in, first_out
            )
            return layer(
                intermediate, weight_2, bias_2, stride_2, padding_2, second_in, second_out
            )

        return call

    def explicit_chain_call():
        intermediate = layer(
            x_ncdhw, weight_1, bias_1, stride_1, padding_1, "NCDHW", "NCDHW"
        )
        intermediate = _ncdhw_to_ndhwc(intermediate, None)
        return layer(
            intermediate, weight_2, bias_2, stride_2, padding_2, "NDHWC", "NDHWC"
        )

    timing = {
        "single_ncdhw_to_ndhwc": measure(
            "single_ncdhw_to_ndhwc", single_call(x_ncdhw, "NCDHW", "NDHWC")
        ),
        "single_ndhwc_to_ndhwc": measure(
            "single_ndhwc_to_ndhwc", single_call(x_ndhwc, "NDHWC", "NDHWC")
        ),
        "two_layer_ncdhw": measure("two_layer_ncdhw", chain_call("ncdhw_ncdhw")),
        "two_layer_ndhwc": measure("two_layer_ndhwc", chain_call("ndhwc_ndhwc")),
        "two_layer_mixed": measure(
            "two_layer_mixed", chain_call("ncdhw_to_ndhwc_then_ncdhw")
        ),
        "two_layer_explicit_mid_conversion": measure(
            "two_layer_explicit_mid_conversion", explicit_chain_call
        ),
        "direct_ncdhw_to_ndhwc": measure(
            "direct_ncdhw_to_ndhwc", lambda: _ncdhw_to_ndhwc(x_ncdhw, None)
        ),
    }

    payload = {
        "environment": build_environment(args),
        "numerical_gate": {"rtol": RTOL, "atol": ATOL},
        "workload": {
            "input_shape": list(input_shape),
            "weight_1_shape": list(weight_1.shape),
            "weight_2_shape": list(weight_2.shape),
            "bias_dtype": "float32",
            "reference_bias_dtype": "bfloat16",
            "layer_1_stride": list(stride_1),
            "layer_1_padding": list(padding_1),
            "layer_2_stride": list(stride_2),
            "layer_2_padding": list(padding_2),
            "splitk": 1,
            "dtype": "bfloat16",
            "seed": 344,
        },
        "correctness": correctness,
        "timing": timing,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({
        "output": str(output),
        "all_correct": all(
            result["allclose"]
            for mode in correctness.values()
            for result in [
                value for key, value in mode.items()
                if key in {"intermediate", "converted_intermediate", "final"}
            ]
        ),
        "timing_ms": {
            name: result["event_ms_per_call"] for name, result in timing.items()
        },
    }, indent=2))


if __name__ == "__main__":
    main()
