#!/usr/bin/env python3
"""Bounded gfx950 check of MegaMoE GEMM1 persistent grid-stride scheduling."""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import pickle
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import torch
from torch.profiler import ProfilerActivity, profile

import flydsl.expr as fx
from kernels.mega_moe.gemm1 import compile_gemm1, gemm1_kernel
from tests.kernels.utils import gemm_common_utils as gutils


if not hasattr(fx, "max"):
    fx.max = fx.maxnumf


MODEL_DIM = 256
INTER_DIM = 512
EXPERTS = 8
SORT_BLOCK_M = 32
TILE_K = 256
NUM_WAVES = 4
NUM_CU = 256
PERSISTENT_GRID_MULT = 4
WARMUP_ITERATIONS = 10
TIMED_ITERATIONS = 50
RELL2_GATE = 0.10
LOCAL_IMAGE_ID = "sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7"


@dataclass(frozen=True)
class Case:
    distribution: str
    tile_n: int
    schedule: str


def e8m0_unshuffle(shuffled: torch.Tensor, rows: int, cols: int) -> torch.Tensor:
    padded_rows, padded_cols = shuffled.shape
    original = (
        shuffled.view(padded_rows // 32, padded_cols // 8, 4, 16, 2, 2)
        .permute(0, 5, 3, 1, 4, 2)
        .contiguous()
        .view(padded_rows, padded_cols)
    )
    return original[:rows, :cols].contiguous()


def quantize_fp8(values: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    payload, scale = gutils.per_1x32_f8_quant(values)
    return payload.contiguous(), scale.view(torch.uint8).contiguous()


def quantize_fp4(values: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    payload, scale, _ = gutils.per_1x32_f4_quant(values, shuffle=False)
    return payload.contiguous(), scale.view(torch.uint8).contiguous()


def expand_scale(payload: torch.Tensor, scale: torch.Tensor, last_dim: int) -> torch.Tensor:
    scale_f32 = gutils.e8m0_to_f32(scale)
    return (
        payload.view(payload.shape[0], last_dim // 32, 32)
        * scale_f32.unsqueeze(-1)
    ).reshape(payload.shape[0], last_dim)


def make_distribution(name: str, device: torch.device) -> list[int]:
    if name == "uniform":
        return [2048] * EXPERTS
    if name == "skewed":
        return [8192, 4096, 2048, 1024, 512, 256, 128, 64]
    raise ValueError(f"unknown distribution {name}")


def make_case_data(
    distribution: list[int], device: torch.device, seed: int
) -> dict[str, object]:
    torch.manual_seed(seed)
    num_valid = sum(distribution)
    x_bf16 = torch.randn((num_valid, MODEL_DIM), device=device, dtype=torch.bfloat16) * 0.25
    w_bf16 = (
        torch.randn((EXPERTS, 2 * INTER_DIM, MODEL_DIM), device=device, dtype=torch.bfloat16) * 0.10
    )
    x_payload, x_scale = quantize_fp8(x_bf16)
    w_payload, w_scale = quantize_fp4(w_bf16)

    w_kernel = gutils.shuffle_weight_w4(w_payload, 16, True, True).view(torch.uint8).contiguous().view(-1)
    w_scale_kernel = (
        gutils.shuffle_scale_w4(
            w_scale.view(-1, MODEL_DIM // 32),
            experts_cnt=EXPERTS,
            gate_up=True,
        )
        .view(torch.uint8)
        .contiguous()
        .view(-1)
    )

    tile_row_base: list[int] = []
    expert_ids: list[int] = []
    row_base = 0
    for expert, count in enumerate(distribution):
        for tile_base in range(0, count, SORT_BLOCK_M):
            tile_row_base.append(row_base + tile_base)
            expert_ids.append(expert)
        row_base += count

    return {
        "counts": distribution,
        "num_valid": num_valid,
        "x_payload": x_payload,
        "x_scale": x_scale,
        "w_kernel": w_kernel,
        "w_scale_kernel": w_scale_kernel,
        "w_payload": w_payload,
        "w_scale": w_scale,
        "tile_row_base": torch.tensor(tile_row_base, device=device, dtype=torch.int32),
        "expert_ids": torch.tensor(expert_ids, device=device, dtype=torch.int32),
    }


def reference(data: dict[str, object]) -> torch.Tensor:
    x_payload = data["x_payload"]
    x_scale = data["x_scale"]
    w_payload = data["w_payload"]
    w_scale = data["w_scale"]
    counts = data["counts"]
    x_dequant = expand_scale(x_payload.float(), x_scale, MODEL_DIM)
    w_dequant = gutils.mxfp4_to_f32(w_payload)
    w_dequant = expand_scale(
        w_dequant.view(-1, MODEL_DIM), w_scale.view(-1, MODEL_DIM // 32), MODEL_DIM
    ).view(EXPERTS, 2 * INTER_DIM, MODEL_DIM)

    result = torch.empty((data["num_valid"], INTER_DIM), device=x_payload.device, dtype=torch.float32)
    row_base = 0
    for expert, count in enumerate(counts):
        rows = slice(row_base, row_base + count)
        activation = x_dequant[rows]
        gate = activation @ w_dequant[expert, :INTER_DIM].t()
        up = activation @ w_dequant[expert, INTER_DIM:].t()
        result[rows] = gate * torch.sigmoid(gate) * up
        row_base += count
    return result


def decode_output(
    output: torch.Tensor, output_scale: torch.Tensor, num_valid: int
) -> torch.Tensor:
    padded_rows = ((num_valid + 255) // 256) * 256
    padded_cols = ((INTER_DIM // 32 + 7) // 8) * 8
    scale = e8m0_unshuffle(
        output_scale[: padded_rows * padded_cols].view(padded_rows, padded_cols),
        num_valid,
        INTER_DIM // 32,
    )
    return expand_scale(output.float(), scale, INTER_DIM)


def run_case(
    case: Case,
    data: dict[str, object],
    ref: torch.Tensor,
    device: torch.device,
) -> dict[str, object]:
    num_valid = data["num_valid"]
    n_tiles = (2 * INTER_DIM) // case.tile_n
    total_work = (num_valid // SORT_BLOCK_M) * n_tiles
    if case.schedule == "ordinary":
        grid_mult = math.ceil(total_work / NUM_CU)
    elif case.schedule == "persistent":
        grid_mult = PERSISTENT_GRID_MULT
    else:
        raise ValueError(f"unknown schedule {case.schedule}")
    grid_x = min(total_work, NUM_CU * grid_mult)

    output = torch.empty((num_valid, INTER_DIM), device=device, dtype=torch.float8_e4m3fn)
    padded_rows = ((num_valid + 255) // 256) * 256
    padded_cols = ((INTER_DIM // 32 + 7) // 8) * 8
    output_scale = torch.empty(
        padded_rows * padded_cols + INTER_DIM, device=device, dtype=torch.uint8
    )
    stream = fx.Stream(torch.cuda.current_stream())

    def launch() -> None:
        gemm1_kernel(
            output,
            data["x_payload"],
            data["w_kernel"],
            data["x_scale"],
            data["w_scale_kernel"],
            data["tile_row_base"],
            data["expert_ids"],
            output_scale,
            num_valid,
            stream,
            model_dim=MODEL_DIM,
            inter_dim=INTER_DIM,
            sort_block_m=SORT_BLOCK_M,
            tile_n=case.tile_n,
            tile_k=TILE_K,
            num_waves=NUM_WAVES,
            grid_mult=grid_mult,
            num_cu=NUM_CU,
            a_dtype="fp8",
            out_dtype="fp8",
        )

    launch()
    torch.cuda.synchronize()
    got = decode_output(output, output_scale, num_valid)
    rel_l2 = float(torch.linalg.norm(got - ref) / torch.linalg.norm(ref))
    max_abs = float((got - ref).abs().max())

    for _ in range(WARMUP_ITERATIONS):
        launch()
    torch.cuda.synchronize()

    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    start.record()
    for _ in range(TIMED_ITERATIONS):
        launch()
    end.record()
    torch.cuda.synchronize()
    elapsed_ms = float(start.elapsed_time(end))

    with profile(activities=[ProfilerActivity.CUDA]) as profiler:
        for _ in range(5):
            launch()
        torch.cuda.synchronize()
    kernel_events = [event for event in profiler.events() if event.device_type == torch.autograd.DeviceType.CUDA]

    lds_pool_bytes = max(
        2 * SORT_BLOCK_M * TILE_K,
        SORT_BLOCK_M * (case.tile_n // 2) * 4,
    )
    lds_scale_bytes = SORT_BLOCK_M * (MODEL_DIM // 32)
    return {
        "case": case.__dict__,
        "counts": data["counts"],
        "num_valid": num_valid,
        "m_tiles": num_valid // SORT_BLOCK_M,
        "n_tiles": n_tiles,
        "total_work_tiles": total_work,
        "grid_mult": grid_mult,
        "grid_x": grid_x,
        "work_tiles_per_cta_average": total_work / grid_x,
        "rel_l2": rel_l2,
        "max_abs_error": max_abs,
        "rel_l2_gate_unchanged": RELL2_GATE,
        "passed_unchanged_gate": rel_l2 < RELL2_GATE,
        "warmup_iterations": WARMUP_ITERATIONS,
        "timed_iterations": TIMED_ITERATIONS,
        "elapsed_ms": elapsed_ms,
        "mean_us": elapsed_ms * 1000.0 / TIMED_ITERATIONS,
        "profiled_launches": 5,
        "profiled_cuda_kernel_events": len(kernel_events),
        "threads_per_cta": NUM_WAVES * 64,
        "lds_bytes_computed": lds_pool_bytes + lds_scale_bytes,
        "torch_memory_allocated_bytes": torch.cuda.memory_allocated(),
        "torch_memory_reserved_bytes": torch.cuda.memory_reserved(),
    }


def gpu_identity() -> dict[str, object]:
    properties = torch.cuda.get_device_properties(torch.cuda.current_device())
    return {
        "name": properties.name,
        "gcn_arch_name": properties.gcnArchName,
        "multi_processor_count": properties.multi_processor_count,
        "total_memory_bytes": properties.total_memory,
        "uuid": str(properties.uuid),
    }


def rocm_snapshot() -> dict[str, str]:
    result = subprocess.run(
        ["rocm-smi", "--showproductname", "--showserial", "--showmeminfo", "vram"],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}


def compiled_kernel_resources() -> dict[str, dict[str, object]]:
    cache_root = Path(os.environ.get("FLYDSL_RUNTIME_CACHE_DIR", ""))
    if not cache_root:
        raise RuntimeError("FLYDSL_RUNTIME_CACHE_DIR must point outside JOB_WORKDIR")
    artifacts: list[dict[str, object]] = []
    patterns = {
        "agpr_count": r"agpr_count = (\d+)",
        "group_segment_fixed_size": r"group_segment_fixed_size = (\d+)",
        "max_flat_workgroup_size": r"max_flat_workgroup_size = (\d+)",
        "private_segment_fixed_size": r"private_segment_fixed_size = (\d+)",
        "sgpr_count": r"sgpr_count = (\d+)",
        "sgpr_spill_count": r"sgpr_spill_count = (\d+)",
        "vgpr_count": r"vgpr_count = (\d+)",
        "vgpr_spill_count": r"vgpr_spill_count = (\d+)",
        "wavefront_size": r"wavefront_size = (\d+)",
    }
    for path in cache_root.rglob("*.pkl"):
        with path.open("rb") as handle:
            artifact = pickle.load(handle)
        ir_text = getattr(artifact, "_ir_text", "")
        source_ir = getattr(artifact, "_source_ir", "")
        if "gfx950" not in ir_text or "kernels/mega_moe/gemm1.py" not in source_ir:
            continue
        entry: dict[str, object] = {"artifact_path": str(path)}
        for name, pattern in patterns.items():
            match = re.search(pattern, ir_text)
            if match is None:
                raise RuntimeError(f"missing {name} in {path}")
            entry[name] = int(match.group(1))
        artifacts.append(entry)
    if len(artifacts) != 2:
        raise RuntimeError(f"expected two GEMM1 cache artifacts, found {len(artifacts)}")
    artifacts.sort(key=lambda entry: (entry["vgpr_count"], entry["sgpr_count"]))
    return {str(tile_n): artifact for tile_n, artifact in zip((128, 256), artifacts)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("persistent_gemm1_results.json"))
    parser.add_argument("--seed", type=int, default=726)
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA/ROCm GPU is unavailable")
    device = torch.device("cuda", torch.cuda.current_device())
    torch.cuda.reset_peak_memory_stats()

    cases = [
        Case(distribution, tile_n, schedule)
        for distribution in ("uniform", "skewed")
        for tile_n in (128, 256)
        for schedule in ("ordinary", "persistent")
    ]
    results = []
    for distribution in ("uniform", "skewed"):
        data = make_case_data(make_distribution(distribution, device), device, args.seed)
        ref = reference(data)
        for case in (case for case in cases if case.distribution == distribution):
            print(f"running {case}", flush=True)
            results.append(run_case(case, data, ref, device))

    report = {
        "schema_version": 1,
        "python": sys.executable,
        "python_version": sys.version,
        "platform": platform.platform(),
        "torch_version": torch.__version__,
        "hip_version": torch.version.hip,
        "flydsl_package": os.path.dirname(os.path.abspath(fx.__file__)),
        "source_root": str(Path(__file__).resolve().parents[2]),
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[2], text=True
        ).strip(),
        "source_branch": subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=Path(__file__).resolve().parents[2],
            text=True,
        ).strip(),
        "local_image_id": LOCAL_IMAGE_ID,
        "flydsl_runtime_cache_dir": os.environ.get("FLYDSL_RUNTIME_CACHE_DIR"),
        "flydsl_native_paths": sorted(
            str(path)
            for path in (Path(fx.__file__).parent / "_mlir" / "_mlir_libs").glob("*.so")
        ),
        "installed_flydsl_fx_max_compatibility_alias": "fx.maxnumf",
        "gpu": gpu_identity(),
        "rocm_smi": rocm_snapshot(),
        "compiled_kernel_resources": compiled_kernel_resources(),
        "constants": {
            "model_dim": MODEL_DIM,
            "inter_dim": INTER_DIM,
            "experts": EXPERTS,
            "sort_block_m": SORT_BLOCK_M,
            "tile_k": TILE_K,
            "num_waves": NUM_WAVES,
            "num_cu": NUM_CU,
            "persistent_grid_mult": PERSISTENT_GRID_MULT,
            "warmup_iterations": WARMUP_ITERATIONS,
            "timed_iterations": TIMED_ITERATIONS,
            "rel_l2_gate_unchanged": RELL2_GATE,
        },
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
