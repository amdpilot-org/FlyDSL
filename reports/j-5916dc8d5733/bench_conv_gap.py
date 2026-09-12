#!/usr/bin/env python3
"""Measure FlyDSL conv throughput against equivalent BF16 GEMM work on MI350."""

import argparse
import json
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
import torch.nn.functional as F

import flydsl
import flydsl._mlir
from flydsl.runtime.device import get_rocm_arch
from kernels.conv.conv3d_implicit import _pick_tile, conv3d_implicit


SHAPES = [
    ("conv3d_medium", (1, 128, 6, 40, 40), (128, 128, 3, 3, 3), 1, 1),
    ("conv3d_tail", (2, 64, 6, 18, 18), (192, 64, 3, 3, 3), 1, 1),
    ("conv2d_common", (2, 64, 1, 24, 28), (128, 64, 1, 3, 3), 1, (0, 1, 1)),
]
TILES = [(32, 32, 1, 2), (64, 64, 2, 2), (128, 128, 2, 4)]


def run(command):
    return subprocess.run(command, text=True, capture_output=True, check=False).stdout.strip()


def timing(operation, warmup, repetitions):
    for _ in range(warmup):
        operation()
    torch.cuda.synchronize()
    samples = []
    for _ in range(repetitions):
        begin = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        begin.record()
        operation()
        end.record()
        end.synchronize()
        samples.append(begin.elapsed_time(end))
    ordered = sorted(samples)
    return {
        "samples_ms": samples,
        "median_ms": statistics.median(ordered),
        "mean_ms": statistics.fmean(ordered),
        "stddev_ms": statistics.pstdev(ordered),
        "min_ms": ordered[0],
        "max_ms": ordered[-1],
        "p10_ms": ordered[max(0, int(0.10 * len(ordered)) - 1)],
        "p90_ms": ordered[min(len(ordered) - 1, int(0.90 * len(ordered)))],
    }


def output_dims(x_shape, w_shape, stride, padding):
    n, c, d, h, w = x_shape
    k, _, kt, kh, kw = w_shape
    if isinstance(padding, int):
        pt = ph = pw = padding
    else:
        pt, ph, pw = padding
    return (
        n,
        c,
        k,
        (d + 2 * pt - kt) // stride + 1,
        (h + 2 * ph - kh) // stride + 1,
        (w + 2 * pw - kw) // stride + 1,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--repetitions", type=int, default=100)
    args = parser.parse_args()

    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "methodology": {
            "clock": "torch.cuda.Event on the current stream; end event synchronized for every sample",
            "warmup": args.warmup,
            "repetitions": args.repetitions,
            "conv_scope": "full public call including output allocation/dispatch; packed weights are memoized after warmup",
            "gemm_scope": "torch.mm with a preallocated BF16 output",
            "accuracy": "torch.nn.functional.conv3d, torch.allclose(rtol=2e-2, atol=2e-2)",
        },
        "environment": {
            "torch_version": torch.__version__,
            "torch_path": torch.__file__,
            "flydsl_version": getattr(flydsl, "__version__", ""),
            "flydsl_path": flydsl.__file__,
            "native_path": list(flydsl._mlir.__path__),
            "arch": get_rocm_arch(),
            "gpu_name": torch.cuda.get_device_name(),
            "gpu_index": torch.cuda.current_device(),
            "rocm_smi_before": run(["rocm-smi", "--showproductname", "--showuniqueid", "--showuse"]),
        },
        "shapes": [],
    }

    for index, (name, x_shape, w_shape, stride, padding) in enumerate(SHAPES):
        torch.manual_seed(9100 + index)
        x = torch.randn(x_shape, device="cuda", dtype=torch.bfloat16)
        weight = torch.randn(w_shape, device="cuda", dtype=torch.bfloat16)
        reference = F.conv3d(x, weight, stride=stride, padding=padding)
        n, c, k, do, ho, wo = output_dims(x_shape, w_shape, stride, padding)
        gemm_m = n * do * ho * wo
        gemm_k = c * w_shape[2] * w_shape[3] * w_shape[4]
        chosen = tuple(_pick_tile(gemm_m, k, 1, x.device))
        item = {
            "name": name,
            "input_shape": x_shape,
            "weight_shape": w_shape,
            "stride": stride,
            "padding": padding,
            "implicit_gemm": {"m": gemm_m, "n": k, "k": gemm_k, "flops": 2 * gemm_m * k * gemm_k},
            "heuristic_tile": chosen,
            "tiles": {},
        }
        for tile in TILES:
            actual = conv3d_implicit(x, weight, stride=stride, padding=padding, tile=tile, output_layout="NDHWC")
            actual_ncdhw = actual.permute(0, 4, 1, 2, 3).contiguous()
            torch.cuda.synchronize()
            item["tiles"][str(tile)] = {
                "accuracy_pass": bool(torch.allclose(actual_ncdhw, reference, rtol=2e-2, atol=2e-2)),
                "max_abs_error": float((actual_ncdhw - reference).abs().max()),
                "timing": timing(
                    lambda tile=tile: conv3d_implicit(
                        x, weight, stride=stride, padding=padding, tile=tile, output_layout="NDHWC"
                    ),
                    args.warmup,
                    args.repetitions,
                ),
            }
        lhs = torch.randn((gemm_m, gemm_k), device="cuda", dtype=torch.bfloat16)
        rhs = torch.randn((gemm_k, k), device="cuda", dtype=torch.bfloat16)
        gemm_out = torch.empty((gemm_m, k), device="cuda", dtype=torch.bfloat16)
        item["torch_mm"] = timing(
            lambda: torch.mm(lhs, rhs, out=gemm_out), args.warmup, args.repetitions
        )
        conv_ms = item["tiles"][str(chosen)]["timing"]["median_ms"]
        gemm_ms = item["torch_mm"]["median_ms"]
        item["heuristic_vs_gemm"] = {
            "time_ratio": conv_ms / gemm_ms,
            "conv_tflops": item["implicit_gemm"]["flops"] / conv_ms / 1.0e9,
            "gemm_tflops": item["implicit_gemm"]["flops"] / gemm_ms / 1.0e9,
        }
        result["shapes"].append(item)
        print(f"{name}: conv={conv_ms:.5f} ms gemm={gemm_ms:.5f} ms ratio={conv_ms / gemm_ms:.2f}x")

    result["environment"]["rocm_smi_after"] = run(
        ["rocm-smi", "--showproductname", "--showuniqueid", "--showuse"]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
