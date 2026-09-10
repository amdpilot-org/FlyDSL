#!/usr/bin/env python3
import importlib.util
import json
import math
import os
import statistics
import sys

import torch


TEST_PATH = "/opt/aiter/op_tests/flydsl_tests/test_flydsl_moe_a16wfp4.py"
OUTPUT_PATH = "/job/logs/gemm2-bench.json"


def load_test_module():
    spec = importlib.util.spec_from_file_location("flydsl_a16wfp4_test", TEST_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def timed_samples(launch, samples_per_round, rounds):
    samples_ms = []
    for _ in range(rounds):
        for _ in range(samples_per_round):
            launch()
        torch.cuda.synchronize()
        for _ in range(samples_per_round):
            launch()
            torch.cuda.synchronize()
            start = torch.cuda.Event(enable_timing=True)
            end = torch.cuda.Event(enable_timing=True)
            start.record()
            launch()
            end.record()
            end.synchronize()
            samples_ms.append(start.elapsed_time(end))
    return samples_ms


def main():
    test = load_test_module()
    from aiter.ops.flydsl.moe_kernels import flydsl_moe_stage2

    token = 2048
    model_dim = 512
    inter_dim = 256
    experts = 64
    topk = 4
    rounds = 3
    samples_per_round = 20
    warmup = 5

    candidates = [
        ("tm32_tn128_tk256_default", 32, 128, 256, None),
        ("tm64_tn128_tk256_default", 64, 128, 256, None),
        ("tm128_tn128_tk256_default", 128, 128, 256, None),
        ("tm64_tn128_tk128_persistent", 64, 128, 128, True),
    ]

    results = []
    flops = 2.0 * token * topk * inter_dim * model_dim
    for name, tile_m, tile_n, tile_k, persist in candidates:
        data = test._generate_a16wfp4_data(
            token=token,
            model_dim=model_dim,
            inter_dim=inter_dim,
            E=experts,
            topk=topk,
            block_m=tile_m,
            seed=0,
        )
        out = torch.zeros(
            (token, model_dim), dtype=torch.bfloat16, device=torch.device("cuda")
        )
        kwargs = {
            "inter_states": data["a2"],
            "w2": data["w2_qt_shuf"],
            "sorted_token_ids": data["sorted_ids"],
            "sorted_expert_ids": data["sorted_expert_ids"],
            "num_valid_ids": data["num_valid_ids"],
            "out": out,
            "topk": topk,
            "tile_m": tile_m,
            "tile_n": tile_n,
            "tile_k": tile_k,
            "a_dtype": "bf16",
            "b_dtype": "fp4",
            "out_dtype": "bf16",
            "mode": "atomic",
            "w2_scale": data["w2_scale_shuf"],
            "a2_scale": None,
            "sorted_weights": data["sorted_weights_s2"],
            "sort_block_m": tile_m,
            "persist": persist,
        }

        out.zero_()
        checked = flydsl_moe_stage2(**kwargs)
        torch.cuda.synchronize()
        passed, max_delta, close_pct = test._check_result(data["ref_stage2"], checked)

        def launch():
            out.zero_()
            flydsl_moe_stage2(**kwargs)

        for _ in range(warmup):
            launch()
        torch.cuda.synchronize()
        samples_ms = timed_samples(launch, samples_per_round, rounds)
        samples_us = [value * 1000.0 for value in samples_ms]
        mean_us = statistics.fmean(samples_us)
        result = {
            "candidate": name,
            "tile_m": tile_m,
            "tile_n": tile_n,
            "tile_k": tile_k,
            "persist": persist,
            "sort_block_m": tile_m,
            "correctness_pass": bool(passed),
            "max_delta": max_delta,
            "close_percent": close_pct,
            "rounds": rounds,
            "samples_per_round": samples_per_round,
            "warmup": warmup,
            "mean_us": mean_us,
            "median_us": statistics.median(samples_us),
            "stdev_us": statistics.stdev(samples_us),
            "cv_percent": 100.0 * statistics.stdev(samples_us) / mean_us,
            "min_us": min(samples_us),
            "max_us": max(samples_us),
            "tflops": flops / (mean_us * 1e-6) / 1e12,
            "raw_samples_us": samples_us,
        }
        results.append(result)
        print(json.dumps(result, indent=2))
        torch.cuda.empty_cache()

    report = {
        "label": "MXFP4 MoE GEMM2 large-token bounded benchmark",
        "shape": {
            "tokens": token,
            "model_dim": model_dim,
            "inter_dim": inter_dim,
            "experts": experts,
            "topk": topk,
        },
        "timing": "CUDA events; zero-fill excluded; 5 warmups then 3x20 samples",
        "reference": "torch_moe_stage2 dequantized MXFP4/E8M0 reference",
        "shuffle_semantics": {
            "weight": "shuffle_weight_a16w4(..., gate_up=False)",
            "scale": "e8m0_shuffle(...)",
        },
        "results": results,
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(f"wrote {OUTPUT_PATH}")
    if not all(result["correctness_pass"] for result in results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
