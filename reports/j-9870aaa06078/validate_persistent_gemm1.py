#!/usr/bin/env python3
"""Validate and time standard MoE GEMM1 default vs persistent execution on gfx950."""

import json
import statistics
import subprocess
import sys
from pathlib import Path

import torch

import flydsl.compiler as flyc
from kernels.moe.moe_gemm_2stage import compile_moe_gemm1
from tests.kernels.test_moe_gemm_2stage import _cosine_sim, _prep_gemm1


CASES = [
    # Masked decode tails and >256 logical work tiles (two N tiles per M block).
    dict(tokens=2051, model_dim=256, inter_dim=128, experts=4, topk=2, tile_m=16, tile_n=64, tile_k=128),
    # A larger prefill-style tile and masked tail, also exceeding the persistent grid.
    dict(tokens=8193, model_dim=256, inter_dim=128, experts=4, topk=2, tile_m=64, tile_n=64, tile_k=128),
]
DTYPES = ("fp8", "int8", "int8smooth", "int4")
WARMUP = 20
BATCHES = 7
ITERATIONS = 100


def launch_args(data, out, case):
    sorted_token_ids, sorted_weights, sorted_expert_ids, num_valid_ids, blocks = data["routing"]
    return (
        out,
        data["x_q"].view(-1),
        data["w"].view(-1),
        data["scale_x"].view(-1).contiguous(),
        data["scale_w"].view(-1).contiguous(),
        sorted_token_ids,
        sorted_expert_ids,
        sorted_weights.contiguous().view(-1),
        num_valid_ids,
        case["tokens"],
        case["inter_dim"],
        case["model_dim"],
        int(blocks),
        torch.cuda.current_stream(),
    )


def measure(compiled, args):
    for _ in range(WARMUP):
        compiled(*args)
    torch.cuda.synchronize()
    samples = []
    for _ in range(BATCHES):
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        start.record()
        for _ in range(ITERATIONS):
            compiled(*args)
        end.record()
        torch.cuda.synchronize()
        samples.append(float(start.elapsed_time(end)) * 1000.0 / ITERATIONS)
    return {
        "samples_us": samples,
        "mean_us": statistics.mean(samples),
        "median_us": statistics.median(samples),
        "stdev_us": statistics.stdev(samples),
        "min_us": min(samples),
        "max_us": max(samples),
        "warmup": WARMUP,
        "batches": BATCHES,
        "iterations_per_batch": ITERATIONS,
    }


def main():
    torch.manual_seed(726)
    results = []
    for shape_index, case in enumerate(CASES):
        for in_dtype in DTYPES:
            data = _prep_gemm1(
                tokens=case["tokens"],
                model_dim=case["model_dim"],
                inter_dim=case["inter_dim"],
                experts=case["experts"],
                topk=case["topk"],
                tile_m=case["tile_m"],
                seed=726 + shape_index,
                in_dtype=in_dtype,
                out_dtype="bf16",
            )
            common = dict(
                model_dim=case["model_dim"],
                inter_dim=case["inter_dim"],
                experts=case["experts"],
                topk=case["topk"],
                tile_m=case["tile_m"],
                tile_n=case["tile_n"],
                tile_k=case["tile_k"],
                doweight_stage1=False,
                out_dtype="bf16",
                in_dtype=in_dtype,
            )
            outputs = {}
            timings = {}
            for mode, persistent in (("default", False), ("persistent", True)):
                out = torch.full(
                    (case["tokens"], case["topk"], case["inter_dim"]),
                    float("nan"),
                    device="cuda",
                    dtype=torch.bfloat16,
                )
                exe = compile_moe_gemm1(**common, persistent=persistent)
                args = launch_args(data, out, case)
                compiled = flyc.compile(exe, *args)
                compiled(*args)
                torch.cuda.synchronize()
                outputs[mode] = out.clone()
                timings[mode] = measure(compiled, args)

            sorted_blocks = int(data["routing"][-1])
            logical_tiles = sorted_blocks * (case["inter_dim"] // 64)
            result = {
                "shape": case,
                "in_dtype": in_dtype,
                "sorted_m_blocks": sorted_blocks,
                "logical_tiles": logical_tiles,
                "persistent_grid_ctas": min(logical_tiles, torch.cuda.get_device_properties(0).multi_processor_count),
                "default_cosine_vs_torch": _cosine_sim(outputs["default"], data["ref"]),
                "persistent_cosine_vs_torch": _cosine_sim(outputs["persistent"], data["ref"]),
                "persistent_cosine_vs_default": _cosine_sim(outputs["persistent"], outputs["default"]),
                "default": timings["default"],
                "persistent": timings["persistent"],
                "persistent_over_default_mean": timings["persistent"]["mean_us"] / timings["default"]["mean_us"],
            }
            print(json.dumps(result), flush=True)
            results.append(result)

    props = torch.cuda.get_device_properties(0)
    report = {
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "python": sys.executable,
        "torch": torch.__version__,
        "hip": torch.version.hip,
        "gpu": {
            "name": props.name,
            "arch": props.gcnArchName,
            "compute_units": props.multi_processor_count,
        },
        "results": results,
    }
    output = Path(__file__).with_name("persistent-gemm1-validation.json")
    output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
