#!/usr/bin/env python3
"""Bounded small-token MXFP4 MoE measurement for FlyDSL issue 708.

The benchmark intentionally keeps the production scale/weight shuffle contract.
It measures host enqueue latency and device duration separately for GEMM1 and
GEMM2. SiLU and FP4 re-quantization are fused into GEMM1, so activation is
reported as a zero-latency fused stage rather than inventing a separate launch.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_ROOT = Path(os.environ.get("FLYDSL_JOB_CACHE", "/tmp/flydsl-cache-j-2016d83e4371"))
os.environ.setdefault("FLYDSL_RUNTIME_CACHE_DIR", str(CACHE_ROOT / "runtime"))
os.environ.setdefault("TRITON_CACHE_DIR", str(CACHE_ROOT / "triton"))
os.environ.setdefault("AITER_JIT_DIR", str(CACHE_ROOT / "aiter-jit"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import torch
import triton
from flydsl.runtime.device import get_rocm_arch

from kernels.moe.mxfp_moe import flydsl_mxfp4_gemm1, flydsl_mxfp4_gemm2
from tests.kernels.utils import gemm_common_utils as gcu
from tests.utils import shuffle_weight


TOKENS = (1, 8, 32, 128)
MODEL_DIM = 1024
INTER_DIM = 256
EXPERTS = 8
TOPK = 2
SEED = 20260910
WARMUP_LAUNCHES = 10
TIMED_LAUNCHES = 50
RTOL = 2e-3
ATOL = 2e-3
LOGITS_DIFF_THRESHOLD = 2e-3

CONFIGS = (
    {
        "name": "bm16_inline_atomic",
        "bm": 16,
        "inline_quant": True,
        "interleave": False,
        "g2_epilog": "atomic",
    },
    {
        "name": "bm32_prequant_atomic",
        "bm": 32,
        "inline_quant": False,
        "interleave": False,
        "g2_epilog": "atomic",
    },
    {
        "name": "bm64_prequant_atomic",
        "bm": 64,
        "inline_quant": False,
        "interleave": False,
        "g2_epilog": "atomic",
    },
    {
        "name": "bm128_prequant_nonatomic",
        "bm": 128,
        "inline_quant": False,
        "interleave": False,
        "g2_epilog": "nonatomic",
    },
)


def quantize_mxfp4(x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Use FlyDSL's existing per-1x32 E8M0/FP4 quantization contract."""
    original_shape = x.shape
    x = x.reshape(-1, original_shape[-1]).float()
    blocks = x.view(-1, 32)
    amax = blocks.abs().amax(dim=1)
    scale_u8 = gcu.f32_to_e8m0(amax / 4.0)
    scale_f32 = gcu.e8m0_to_f32(scale_u8)
    normalized = blocks / scale_f32.unsqueeze(1)
    packed = gcu.f32_to_mxfp4(normalized)
    packed = packed.reshape(*original_shape[:-1], -1)
    scale = scale_u8.reshape(-1, original_shape[-1] // 32).view(torch.uint8)
    return packed, scale


def dequantize_mxfp4(packed: torch.Tensor, scale_u8: torch.Tensor) -> torch.Tensor:
    original_shape = packed.shape
    logical_last = int(original_shape[-1]) * 2
    packed_u8 = packed.view(torch.uint8).reshape(-1, logical_last // 2)
    values = gcu.mxfp4_to_f32(packed_u8)
    scales = gcu.e8m0_to_f32(scale_u8.view(torch.uint8).reshape(-1, logical_last // 32))
    values = values * scales.repeat_interleave(32, dim=1)
    return values.reshape(*original_shape[:-1], logical_last)


def build_routing(
    topk_ids: torch.Tensor,
    topk_weights: torch.Tensor,
    *,
    experts: int,
    tokens: int,
    topk: int,
    block_m: int,
) -> dict[str, Any]:
    max_padded = tokens * topk + experts * block_m - topk
    max_blocks = (max_padded + block_m - 1) // block_m
    sorted_ids = torch.full((max_padded,), (topk << 24) | tokens, dtype=torch.int32, device="cuda")
    sorted_weights = torch.empty(max_padded, dtype=torch.float32, device="cuda")
    sorted_expert_ids = torch.full((max_blocks,), -1, dtype=torch.int32, device="cuda")

    row_begin = 0
    block_begin = 0
    for expert in range(experts):
        token_id, slot = torch.where(topk_ids == expert)
        count = int(token_id.numel())
        if count == 0:
            continue
        blocks = (count + block_m - 1) // block_m
        padded = blocks * block_m
        sorted_ids[row_begin : row_begin + count] = (slot.to(torch.int32) << 24) | token_id.to(torch.int32)
        sorted_weights[row_begin : row_begin + count] = topk_weights[token_id, slot]
        sorted_expert_ids[block_begin : block_begin + blocks] = expert
        row_begin += padded
        block_begin += blocks

    num_valid_ids = torch.tensor([row_begin, tokens], dtype=torch.int32, device="cuda")
    return {
        "sorted_ids": sorted_ids.contiguous(),
        "sorted_weights": sorted_weights.contiguous(),
        "sorted_expert_ids": sorted_expert_ids.contiguous(),
        "num_valid_ids": num_valid_ids.contiguous(),
        "sorted_size": max_padded,
        "blocks": max_blocks,
        "total_rows": row_begin,
    }


def effective_g1_use_nt(*, bm: int, inline_quant: bool, tokens: int, topk: int, experts: int) -> bool:
    if inline_quant:
        return True
    if bm != 32:
        return False
    total_m_blocks = (tokens * topk + bm - 1) // bm
    return total_m_blocks < experts


def unshuffle_stage1_scale(
    shuffled_scale: torch.Tensor,
    *,
    total_rows: int,
    scale_cols: int,
    bm: int,
    n_blocks: int,
) -> torch.Tensor:
    """Invert the BM-dependent GEMM1 output-scale layout for validation only."""
    scale = torch.zeros(total_rows, scale_cols, dtype=torch.uint8, device=shuffled_scale.device)
    flat = shuffled_scale.view(-1)
    m_blocks = (total_rows + bm - 1) // bm
    for m_block in range(m_blocks):
        for n_block in range(n_blocks):
            for wave_grp in range(4):
                for m_lane in range(16):
                    col = n_block * 4 + wave_grp
                    if bm == 16:
                        row = m_block * 16 + m_lane
                        offset = m_block * 256 + wave_grp * 64 + m_lane * 4 + n_block * 2
                        scale[row, col] = flat[offset]
                        continue
                    for sub in range(bm // 32):
                        chunk = m_block * (bm // 32) + sub
                        for row_half in range(2):
                            row = m_block * bm + sub * 32 + row_half * 16 + m_lane
                            offset = (
                                chunk * 256
                                + wave_grp * 64
                                + m_lane * 4
                                + n_block * 2
                                + row_half
                            )
                            scale[row, col] = flat[offset]
    return scale


def timing_stats(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "median_us": float(np.median(array)),
        "p95_us": float(np.percentile(array, 95)),
        "min_us": float(np.min(array)),
        "max_us": float(np.max(array)),
        "mean_us": float(np.mean(array)),
    }


def measure_launch(
    launch: Callable[[], None],
    *,
    warmup: int = WARMUP_LAUNCHES,
    samples: int = TIMED_LAUNCHES,
) -> dict[str, Any]:
    for _ in range(warmup):
        launch()
    torch.cuda.synchronize()

    host_us: list[float] = []
    device_us: list[float] = []
    for _ in range(samples):
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        start.record()
        host_start = time.perf_counter_ns()
        launch()
        host_end = time.perf_counter_ns()
        end.record()
        torch.cuda.synchronize()
        host_us.append((host_end - host_start) / 1000.0)
        device_us.append(start.elapsed_time(end) * 1000.0)
    return {
        "host_enqueue": timing_stats(host_us),
        "device_duration": timing_stats(device_us),
        "host_samples_us": host_us,
        "device_samples_us": device_us,
        "samples": samples,
        "warmup": warmup,
    }


def validation_metrics(actual: torch.Tensor, reference: torch.Tensor) -> dict[str, Any]:
    actual = actual.float().reshape(-1)
    reference = reference.float().reshape(-1)
    diff = (actual - reference).abs()
    tolerance = ATOL + RTOL * reference.abs()
    exceed_fraction = float((diff > tolerance).float().mean().item())
    denominator = float((actual.double() ** 2).sum() + (reference.double() ** 2).sum())
    if denominator == 0:
        logits_diff = 0.0
    else:
        logits_diff = 1.0 - float(2.0 * (actual.double() * reference.double()).sum() / denominator)
        if np.isnan(logits_diff):
            logits_diff = 1.0
    passed = exceed_fraction < 0.05 or logits_diff <= LOGITS_DIFF_THRESHOLD
    return {
        "passed": passed,
        "exceed_fraction": exceed_fraction,
        "logits_diff": logits_diff,
        "max_abs": float(diff.max().item()),
        "mean_abs": float(diff.mean().item()),
        "rmse": float(diff.pow(2).mean().sqrt().item()),
        "gate": {
            "rtol": RTOL,
            "atol": ATOL,
            "logits_diff_threshold": LOGITS_DIFF_THRESHOLD,
            "existing_5_percent_early_pass": True,
        },
    }


def run_case(
    *,
    tokens: int,
    config: dict[str, Any],
    x_fp32: torch.Tensor,
    w1_fp32: torch.Tensor,
    w2_fp32: torch.Tensor,
    topk_ids: torch.Tensor,
    topk_weights: torch.Tensor,
) -> dict[str, Any]:
    bm = int(config["bm"])
    inline_quant = bool(config["inline_quant"])
    interleave = bool(config["interleave"])
    g2_epilog = str(config["g2_epilog"])
    n_out = 2 * INTER_DIM
    routing = build_routing(
        topk_ids,
        topk_weights,
        experts=EXPERTS,
        tokens=tokens,
        topk=TOPK,
        block_m=bm,
    )
    sorted_ids = routing["sorted_ids"]
    sorted_weights = routing["sorted_weights"]
    sorted_expert_ids = routing["sorted_expert_ids"]
    num_valid_ids = routing["num_valid_ids"]
    total_rows = int(routing["total_rows"])

    x_reference_fp32 = x_fp32.to(torch.bfloat16).to(torch.float32) if inline_quant else x_fp32
    x_q, x_scale = quantize_mxfp4(x_reference_fp32)
    w1_q, w1_scale = quantize_mxfp4(w1_fp32.reshape(EXPERTS * n_out, MODEL_DIM))
    w2_q, w2_scale = quantize_mxfp4(w2_fp32.reshape(EXPERTS * MODEL_DIM, INTER_DIM))
    w1_shuffled = shuffle_weight(w1_q.view(torch.float4_e2m1fn_x2)).view(torch.uint8).contiguous()
    w2_shuffled = shuffle_weight(w2_q.view(torch.float4_e2m1fn_x2)).view(torch.uint8).contiguous()
    w1_scale_shuffled = (
        gcu.e8m0_shuffle(w1_scale.view(EXPERTS * n_out, MODEL_DIM // 32)).view(torch.uint8).contiguous()
    )
    w2_scale_shuffled = (
        gcu.e8m0_shuffle(w2_scale.view(EXPERTS * MODEL_DIM, INTER_DIM // 32)).view(torch.uint8).contiguous()
    )

    if inline_quant:
        x_scale_sorted = x_scale.view(torch.uint8).contiguous()
        hidden = x_fp32.to(torch.bfloat16).contiguous()
    else:
        x_scale_sorted = (
            gcu.moe_mxfp4_sort(
                x_scale[:tokens].view(tokens, 1, -1),
                sorted_ids=sorted_ids,
                num_valid_ids=num_valid_ids,
                token_num=tokens,
                block_size=bm,
            )
            .view(torch.uint8)
            .contiguous()
        )
        hidden = torch.zeros(tokens, MODEL_DIM, dtype=torch.bfloat16, device="cuda")

    scale_cols = INTER_DIM // 32
    padded_rows = (routing["sorted_size"] + 255) // 256 * 256
    padded_cols = (scale_cols + 7) // 8 * 8
    scale_chunks = (total_rows + (16 if bm == 16 else 32) - 1) // (16 if bm == 16 else 32)
    scale_output_bytes = max(padded_rows * padded_cols, scale_chunks * 256)
    stage1_q = torch.zeros(routing["sorted_size"], INTER_DIM // 2, dtype=torch.uint8, device="cuda")
    stage1_scale_shuffled = torch.zeros(scale_output_bytes, dtype=torch.uint8, device="cuda")
    m_indices = (sorted_ids & 0x00FFFFFF).to(torch.int32).contiguous()
    g1_use_nt = effective_g1_use_nt(
        bm=bm, inline_quant=inline_quant, tokens=tokens, topk=TOPK, experts=EXPERTS
    )

    def launch_gemm1() -> None:
        flydsl_mxfp4_gemm1(
            a_quant=x_q.view(torch.uint8).contiguous(),
            a_scale_sorted_shuffled=x_scale_sorted,
            w1_u8=w1_shuffled,
            w1_scale_u8=w1_scale_shuffled,
            sorted_expert_ids=sorted_expert_ids,
            cumsum_tensor=num_valid_ids,
            m_indices=m_indices,
            inter_sorted_quant=stage1_q,
            inter_sorted_shuffled_scale=stage1_scale_shuffled,
            hidden_states=hidden,
            n_tokens=tokens,
            BM=bm,
            use_nt=g1_use_nt,
            inline_quant=inline_quant,
            interleave=interleave,
            NE=EXPERTS,
            D_HIDDEN=MODEL_DIM,
            D_INTER=INTER_DIM,
            topk=TOPK,
            a_dtype="fp4",
        )

    launch_gemm1()
    torch.cuda.synchronize()
    stage1_scale = unshuffle_stage1_scale(
        stage1_scale_shuffled,
        total_rows=total_rows,
        scale_cols=scale_cols,
        bm=bm,
        n_blocks=n_out // 256,
    )
    actual_stage1 = dequantize_mxfp4(stage1_q[:total_rows], stage1_scale)

    token_ids = sorted_ids[:total_rows] & 0x00FFFFFF
    valid_rows = token_ids < tokens
    expert_per_row = sorted_expert_ids[(torch.arange(total_rows, device="cuda") // bm).long()]
    x_dequant = dequantize_mxfp4(x_q, x_scale)
    w1_dequant = dequantize_mxfp4(w1_q, w1_scale).view(EXPERTS, n_out, MODEL_DIM)
    reference_activation = torch.zeros(total_rows, INTER_DIM, dtype=torch.float32, device="cuda")
    for expert in range(EXPERTS):
        rows = valid_rows & (expert_per_row == expert)
        if not bool(rows.any()):
            continue
        rows_token = token_ids[rows].long()
        gate = x_dequant[rows_token] @ w1_dequant[expert, :INTER_DIM].T
        up = x_dequant[rows_token] @ w1_dequant[expert, INTER_DIM:].T
        reference_activation[rows] = torch.nn.functional.silu(gate) * up
    reference_rows = valid_rows.nonzero(as_tuple=False).squeeze(1)
    reference_q, reference_scale = quantize_mxfp4(reference_activation[reference_rows])
    reference_stage1 = dequantize_mxfp4(reference_q, reference_scale)
    stage1_validation = validation_metrics(actual_stage1[reference_rows], reference_stage1)

    if g2_epilog == "atomic":
        stage2_flat = torch.zeros(tokens * MODEL_DIM, dtype=torch.bfloat16, device="cuda")
    else:
        stage2_flat = torch.zeros(routing["sorted_size"] * MODEL_DIM, dtype=torch.bfloat16, device="cuda")

    def launch_gemm2() -> None:
        flydsl_mxfp4_gemm2(
            inter_sorted_quant=stage1_q,
            inter_sorted_shuffled_scale=stage1_scale_shuffled,
            w2_u8=w2_shuffled,
            w2_scale_u8=w2_scale_shuffled,
            sorted_expert_ids=sorted_expert_ids,
            cumsum_tensor=num_valid_ids,
            sorted_token_ids=sorted_ids,
            sorted_weights=sorted_weights,
            flat_out=stage2_flat,
            M_logical=tokens,
            max_sorted=routing["sorted_size"],
            BM=bm,
            use_nt=g2_epilog == "atomic",
            epilog=g2_epilog,
            NE=EXPERTS,
            D_HIDDEN=MODEL_DIM,
            D_INTER=INTER_DIM,
            topk=TOPK,
        )

    launch_gemm2()
    torch.cuda.synchronize()
    if g2_epilog == "atomic":
        actual_stage2 = stage2_flat.view(tokens, MODEL_DIM).float()
    else:
        flat_rows = stage2_flat.view(routing["sorted_size"], MODEL_DIM).float()
        actual_stage2 = torch.zeros(tokens, MODEL_DIM, dtype=torch.float32, device="cuda")
        actual_stage2.index_add_(
            0,
            token_ids[valid_rows].long(),
            flat_rows[:total_rows][valid_rows] * sorted_weights[:total_rows][valid_rows].unsqueeze(1),
        )

    w2_dequant = dequantize_mxfp4(w2_q, w2_scale).view(EXPERTS, MODEL_DIM, INTER_DIM)
    reference_stage2 = torch.zeros(tokens, MODEL_DIM, dtype=torch.float32, device="cuda")
    for expert in range(EXPERTS):
        rows = valid_rows & (expert_per_row == expert)
        if not bool(rows.any()):
            continue
        rows_token = token_ids[rows].long()
        down = actual_stage1[:total_rows][rows] @ w2_dequant[expert].T
        reference_stage2.index_add_(
            0,
            rows_token,
            down * sorted_weights[:total_rows][rows].unsqueeze(1),
        )
    stage2_validation = validation_metrics(actual_stage2, reference_stage2)

    gemm1_timing = measure_launch(launch_gemm1)
    if g2_epilog == "atomic":
        stage2_flat.zero_()
    gemm2_timing = measure_launch(launch_gemm2)
    if g2_epilog == "atomic":
        stage2_flat.zero_()
        launch_gemm2()
        torch.cuda.synchronize()

    return {
        "tokens": tokens,
        "config": config["name"],
        "bm": bm,
        "g1_inline_quant": inline_quant,
        "g1_interleave": interleave,
        "g1_effective_use_nt": g1_use_nt,
        "g2_epilog": g2_epilog,
        "g2_use_nt": g2_epilog == "atomic",
        "total_sorted_rows": total_rows,
        "gemm1_timing": gemm1_timing,
        "activation_timing": {
            "status": "fused_into_gemm1_no_separate_launch",
            "host_enqueue_us": 0.0,
            "device_duration_us": 0.0,
        },
        "gemm2_timing": gemm2_timing,
        "stage1_validation": stage1_validation,
        "stage2_validation": stage2_validation,
    }


def collect_environment() -> dict[str, Any]:
    import flydsl

    properties = torch.cuda.get_device_properties(0)
    return {
        "source_path": str(REPO_ROOT),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip(),
        "python_path": sys.executable,
        "flydsl_python_path": flydsl.__file__,
        "torch_path": torch.__file__,
        "triton_path": triton.__file__,
        "torch_version": torch.__version__,
        "torch_hip_version": torch.version.hip,
        "triton_version": triton.__version__,
        "rocm_arch": get_rocm_arch(),
        "image": {
            "qualified_image": "amdpilotv2/open-job:gbt350-20260909",
            "local_image_id": "sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7",
            "identity_source": "operator-provided local image ID; docker CLI is unavailable inside the container",
        },
        "gpu": {
            "count": torch.cuda.device_count(),
            "name": torch.cuda.get_device_name(0),
            "capability": list(torch.cuda.get_device_capability(0)),
            "total_memory_bytes": properties.total_memory,
            "multi_processor_count": properties.multi_processor_count,
        },
        "cache": {
            "flydsl_runtime": os.environ["FLYDSL_RUNTIME_CACHE_DIR"],
            "triton": os.environ["TRITON_CACHE_DIR"],
            "aiter_jit": os.environ["AITER_JIT_DIR"],
        },
        "timing": {
            "warmup_launches": WARMUP_LAUNCHES,
            "timed_launches": TIMED_LAUNCHES,
            "method": "perf_counter_ns around host call; CUDA events around each synchronized launch",
        },
    }


def write_outputs(results: list[dict[str, Any]], environment: dict[str, Any], output: Path) -> None:
    payload = {
        "issue": "ROCm/FlyDSL issue 708",
        "scope": "bounded small-token MXFP4 MoE stage latency",
        "shape": {
            "tokens": list(TOKENS),
            "model_dim": MODEL_DIM,
            "inter_dim": INTER_DIM,
            "experts": EXPERTS,
            "topk": TOPK,
            "seed": SEED,
        },
        "configurations": [dict(config) for config in CONFIGS],
        "environment": environment,
        "results": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "reports/j-2016d83e4371/results.json",
    )
    args = parser.parse_args()
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    device = torch.device("cuda")

    results = []
    for tokens in TOKENS:
        scale = 0.2
        x_fp32 = torch.randn(tokens, MODEL_DIM, device=device, dtype=torch.float32) * scale
        w1_fp32 = torch.randn(EXPERTS, 2 * INTER_DIM, MODEL_DIM, device=device, dtype=torch.float32) * scale
        w2_fp32 = (
            torch.randn(EXPERTS, MODEL_DIM, INTER_DIM, device=device, dtype=torch.float32)
            * scale
            / (INTER_DIM**0.5)
        )
        score = torch.rand(tokens, EXPERTS, device=device, dtype=torch.float32)
        topk_values, topk_ids = torch.topk(score, k=TOPK, dim=1)
        topk_weights = torch.softmax(topk_values, dim=1).to(torch.float32)
        for config in CONFIGS:
            print(f"running {config['name']} tokens={tokens}", flush=True)
            result = run_case(
                tokens=tokens,
                config=config,
                x_fp32=x_fp32,
                w1_fp32=w1_fp32,
                w2_fp32=w2_fp32,
                topk_ids=topk_ids,
                topk_weights=topk_weights,
            )
            results.append(result)
            print(
                "  G1 host/device median "
                f"{result['gemm1_timing']['host_enqueue']['median_us']:.3f}/"
                f"{result['gemm1_timing']['device_duration']['median_us']:.3f} us; "
                "G2 host/device median "
                f"{result['gemm2_timing']['host_enqueue']['median_us']:.3f}/"
                f"{result['gemm2_timing']['device_duration']['median_us']:.3f} us; "
                f"stage1/2 gates {result['stage1_validation']['passed']}/{result['stage2_validation']['passed']}",
                flush=True,
            )
            torch.cuda.synchronize()
            torch.cuda.empty_cache()

    environment = collect_environment()
    write_outputs(results, environment, args.output)
    print(f"wrote {args.output}", flush=True)


if __name__ == "__main__":
    main()
