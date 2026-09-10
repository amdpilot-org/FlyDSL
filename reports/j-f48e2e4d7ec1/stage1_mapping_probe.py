#!/usr/bin/env python3

import json
import os
import platform
import subprocess
import sys

import torch

import flydsl
import flydsl.runtime.device as flydsl_device


if not hasattr(flydsl_device, "get_warp_size"):
    flydsl_device.get_warp_size = lambda arch=None: 64

from kernels.moe.moe_sorting_kernel import UNIT_SIZE, moe_sorting_flydsl


MODEL_DIM = 4096
UNIT = UNIT_SIZE


CASES = (
    ("hot_inactive_tail_1", 1, 8, 2),
    ("hot_inactive_tail_3", 3, 8, 2),
    ("hot_inactive_tail_7", 7, 8, 2),
    ("hot_inactive_tail_15", 15, 8, 2),
    ("hot_inactive_tail_16", 16, 8, 2),
    ("hot_inactive_tail_17", 17, 8, 2),
    ("hot_inactive_tail_31", 31, 8, 2),
    ("hot_inactive_tail_32", 32, 8, 2),
    ("hot_inactive_tail_33", 33, 8, 2),
    ("spread_inactive_48_tail_1", 1, 48, 8),
    ("spread_inactive_48_tail_17", 17, 48, 8),
)


def make_route(tokens, experts, topk):
    if experts == 8:
        ids = torch.empty((tokens, topk), dtype=torch.int32)
        ids[:, 0] = 0
        ids[:, 1] = 1
    else:
        ids = torch.arange(topk, dtype=torch.int32).repeat(tokens, 1)
    weights = torch.linspace(0.25, 0.75, tokens * topk, dtype=torch.float32).reshape(tokens, topk)
    weights = weights / weights.sum(dim=1, keepdim=True)
    mask = torch.ones(experts, dtype=torch.int32)
    mask[0] = 0
    if experts >= 8:
        mask[2] = 0
        mask[4] = 0
        mask[6] = 0
    return ids, weights, mask


def reference(topk_ids, topk_weights, expert_mask, num_experts):
    tokens, topk = topk_ids.shape
    max_padded = tokens * topk + num_experts * UNIT - topk
    max_blocks = (max_padded + UNIT - 1) // UNIT
    sentinel = (topk << 24) | tokens
    sorted_ids = torch.full((max_padded,), sentinel, dtype=torch.int32)
    sorted_weights = torch.zeros(max_padded, dtype=torch.float32)
    sorted_expert_ids = torch.full((max_blocks,), -1, dtype=torch.int32)
    num_valid_ids = torch.zeros(2, dtype=torch.int32)

    ids_cursor = 0
    expert_cursor = 0
    local_expert = 0
    for expert in range(num_experts):
        if not int(expert_mask[expert]):
            continue
        token, slot = torch.where(topk_ids == expert)
        count = int(token.numel())
        if count == 0:
            continue
        blocks = (count + UNIT - 1) // UNIT
        padded = blocks * UNIT
        end = ids_cursor + count
        sorted_ids[ids_cursor:end] = (slot.to(torch.int32) << 24) | token.to(torch.int32)
        sorted_weights[ids_cursor:end] = topk_weights[token, slot]
        sorted_expert_ids[expert_cursor : expert_cursor + blocks] = local_expert
        ids_cursor += padded
        expert_cursor += blocks
        local_expert += 1

    num_valid_ids[0] = ids_cursor
    num_valid_ids[1] = tokens
    return sorted_ids, sorted_weights, sorted_expert_ids, num_valid_ids


def run_case(name, tokens, experts, topk):
    device = torch.device("cuda")
    topk_ids, topk_weights, expert_mask = make_route(tokens, experts, topk)
    topk_ids = topk_ids.to(device)
    topk_weights = topk_weights.to(device)
    expert_mask = expert_mask.to(device)
    ref = reference(topk_ids, topk_weights, expert_mask, experts)

    max_padded = int(ref[0].numel())
    max_blocks = int(ref[2].numel())
    sentinel = (topk << 24) | tokens
    gpu_ids = torch.full((max_padded,), sentinel, dtype=torch.int32, device=device)
    gpu_weights = torch.zeros(max_padded, dtype=torch.float32, device=device)
    gpu_expert_ids = torch.full((max_blocks,), -1, dtype=torch.int32, device=device)
    gpu_num_valid = torch.zeros(2, dtype=torch.int32, device=device)
    moe_buf = torch.empty((tokens, MODEL_DIM), dtype=torch.bfloat16, device=device)

    moe_sorting_flydsl(
        topk_ids,
        topk_weights,
        gpu_ids,
        gpu_weights,
        gpu_expert_ids,
        gpu_num_valid,
        moe_buf,
        experts,
        UNIT,
        expert_mask,
    )
    torch.cuda.synchronize()

    valid = int(gpu_num_valid[0].item())
    valid_blocks = int((gpu_expert_ids != -1).sum().item())
    ref_valid = int(ref[3][0].item())
    ref_valid_blocks = int((ref[2] != -1).sum().item())
    checks = {
        "num_valid_ids": torch.equal(gpu_num_valid.cpu(), ref[3].cpu()),
        "sorted_token_ids": torch.equal(gpu_ids.cpu(), ref[0].cpu()),
        "sorted_weights": torch.equal(gpu_weights.cpu(), ref[1].cpu()),
        "sorted_expert_ids": torch.equal(gpu_expert_ids.cpu(), ref[2].cpu()),
        "tail_sentinel": bool(torch.all(gpu_ids[valid:] == sentinel).item()),
        "tail_zero_weights": bool(torch.all(gpu_weights[valid:] == 0).item()),
        "tail_inactive_experts": bool(torch.all(gpu_expert_ids[valid_blocks:] == -1).item()),
        "valid_bounds": valid == ref_valid and valid <= max_padded,
        "block_bounds": valid_blocks == ref_valid_blocks and valid_blocks <= max_blocks,
    }
    return {
        "case": name,
        "tokens": tokens,
        "experts": experts,
        "topk": topk,
        "unit_size": UNIT,
        "sentinel": sentinel,
        "num_valid_ids": [int(value) for value in gpu_num_valid.cpu().tolist()],
        "reference_num_valid_ids": [int(value) for value in ref[3].cpu().tolist()],
        "valid_blocks": valid_blocks,
        "reference_valid_blocks": ref_valid_blocks,
        "max_padded": max_padded,
        "max_blocks": max_blocks,
        "checks": checks,
        "passed": all(checks.values()),
    }


def main():
    if not torch.cuda.is_available():
        raise SystemExit("CUDA/ROCm GPU is required")
    torch.manual_seed(725)
    results = [run_case(*case) for case in CASES]
    properties = torch.cuda.get_device_properties(0)
    rocm_smi = subprocess.check_output(
        ["rocm-smi", "--showproductname", "--showserial", "--showuniqueid", "--json"],
        text=True,
    )
    tested_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    report = {
        "gpu": {
            "name": properties.name,
            "capability": list(torch.cuda.get_device_capability(0)),
            "multi_processor_count": properties.multi_processor_count,
            "rocm_smi": json.loads(rocm_smi),
        },
        "image_id": "sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7",
        "tested_commit": tested_commit,
        "python": sys.executable,
        "python_version": platform.python_version(),
        "torch_version": torch.__version__,
        "flydsl_python_path": flydsl.__file__,
        "kernel_source_path": os.path.abspath("kernels/moe/moe_sorting_kernel.py"),
        "native_flydsl_path": os.path.join(os.path.dirname(flydsl.__file__), "_mlir"),
        "cases": results,
        "passed": all(result["passed"] for result in results),
    }
    output = os.path.join(os.path.dirname(__file__), "stage1_mapping_results.json")
    with open(output, "w") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"{status} {result['case']} tokens={result['tokens']} "
            f"valid={result['num_valid_ids'][0]} blocks={result['valid_blocks']} "
            f"sentinel=0x{result['sentinel']:08x}"
        )
    failed = [result for result in results if not result["passed"]]
    for result in failed:
        print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if not failed else 1)


if __name__ == "__main__":
    main()
