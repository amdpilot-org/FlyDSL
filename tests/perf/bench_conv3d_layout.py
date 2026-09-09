#!/usr/bin/env python3

"""Benchmark conv3d_implicit NCDHW and NDHWC layouts on the issue's shapes."""

import argparse
import json
import sys

import torch
from torch.profiler import ProfilerActivity, profile

from kernels.conv.conv3d_implicit import conv3d_implicit


CASES = [
    ("wan_96_6_354_642", (1, 96, 6, 354, 642), (96, 96, 3, 3, 3)),
    ("wan_384_3_46_82", (1, 384, 3, 46, 82), (384, 384, 3, 3, 3)),
    ("wan2d_4_96_353_641", (4, 96, 353, 641), (96, 96, 3, 3)),
    ("h3_conv_in", (1, 3, 17, 256, 256), (128, 3, 3, 3, 3)),
    ("h3_l0", (1, 128, 17, 256, 256), (128, 128, 3, 3, 3)),
    ("h3_l4", (1, 512, 5, 16, 16), (512, 512, 3, 3, 3)),
    ("h3_l5", (1, 1024, 5, 16, 16), (1024, 1024, 3, 3, 3)),
    ("h3_conv_out", (1, 1024, 5, 16, 16), (48, 1024, 3, 3, 3)),
]


def _time_call(call, warmup, iterations):
    for _ in range(warmup):
        call()
    torch.cuda.synchronize()
    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    start.record()
    for _ in range(iterations):
        call()
    end.record()
    torch.cuda.synchronize()
    return start.elapsed_time(end) / iterations


def _profile_call(call, iterations):
    with profile(activities=[ProfilerActivity.CUDA]) as prof:
        for _ in range(iterations):
            call()
        torch.cuda.synchronize()
    kernels = []
    for event in prof.key_averages():
        device_time = getattr(event, "self_device_time_total", 0) or getattr(event, "self_cuda_time_total", 0)
        if device_time:
            kernels.append({"name": event.key, "count": event.count, "us": device_time})
    total = sum(event["us"] for event in kernels)
    conv = sum(event["us"] for event in kernels if "conv3d_implicit_kernel" in event["name"])
    transpose = sum(event["us"] for event in kernels if "transpose" in event["name"].lower())
    return {
        "total_us": total,
        "conv_us": conv,
        "transpose_us": transpose,
        "other_data_movement_us": total - conv - transpose,
        "kernels": kernels,
    }


def _make_call(x, weight, layout, splitk):
    return lambda: conv3d_implicit(
        x,
        weight,
        stride=1,
        padding=1,
        splitk=splitk,
        layout=layout,
        out_layout=layout,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Use fewer warmup/timed iterations")
    parser.add_argument(
        "--cases",
        nargs="+",
        choices=[name for name, _, _ in CASES],
        help="Run only the named benchmark cases",
    )
    parser.add_argument("--output", help="Write detailed JSON results to this path")
    args = parser.parse_args()

    warmup = 1 if args.quick else 4
    iterations = 3 if args.quick else 12
    profile_iterations = 1 if args.quick else 3
    torch.manual_seed(993)
    results = []
    for name, input_shape, weight_shape in CASES:
        if args.cases and name not in args.cases:
            continue
        rank = len(input_shape) - 2
        x_nc = torch.randn(input_shape, device="cuda", dtype=torch.bfloat16) * 0.1
        if rank == 3:
            x_cl = x_nc.permute(0, 2, 3, 4, 1).contiguous()
            nc_layout, cl_layout = "NCDHW", "NDHWC"
        else:
            x_cl = x_nc.permute(0, 2, 3, 1).contiguous()
            nc_layout, cl_layout = "NCHW", "NHWC"
        weight = torch.randn(weight_shape, device="cuda", dtype=torch.bfloat16) * 0.1
        case_result = {"name": name, "input": list(input_shape), "weight": list(weight_shape)}
        for splitk_name, splitk in (("auto", None), ("direct", 1)):
            for layout_name, x, layout in (("default", x_nc, nc_layout), ("channels_last", x_cl, cl_layout)):
                call = _make_call(x, weight, layout, splitk)
                case_result[f"{splitk_name}_{layout_name}"] = {
                    "ms": _time_call(call, warmup, iterations),
                    "profile": _profile_call(call, profile_iterations),
                }
        results.append(case_result)
        print(f"{name}: done", file=sys.stderr)
        del x_nc, x_cl, weight
        torch.cuda.empty_cache()

    payload = {
        "torch": torch.__version__,
        "hip": torch.version.hip,
        "device": torch.cuda.get_device_name(0),
        "capability": list(torch.cuda.get_device_capability(0)),
        "cases": results,
    }
    if args.output:
        with open(args.output, "w") as handle:
            json.dump(payload, handle, indent=2)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
