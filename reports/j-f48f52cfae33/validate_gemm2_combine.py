#!/usr/bin/env python3

import argparse
import hashlib
import json
import math
import os
import pickle
import platform
import re
import subprocess
import sys
import traceback
from pathlib import Path

import torch
from torch.profiler import ProfilerActivity, profile

import flydsl

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import flydsl.compiler as flyc
import flydsl.expr as fx
from flydsl.runtime.device import get_rocm_arch
from kernels.mega_moe.mega_moe_stage2 import compile_mega_moe_stage2
from kernels.moe.moe_gemm_2stage import compile_moe_gemm2
from tests.utils import pertoken_quant, shuffle_weight

LOCAL_IMAGE_ID = "sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7"
TOKENS = 7
MODEL_DIM = 256
INTER_DIM = 128
EXPERTS = 4
TOPK = 2
TILE_M = 16
TILE_N = 64
TILE_K = 128
SEED = 727
GATE = {"metric": "cosine_similarity", "operator": ">", "threshold": 0.99, "changed": False}


def build_routing(device):
    topk_ids = torch.tensor(
        [[0, 0], [1, 1], [2, 2], [3, 3], [0, 0], [1, 1], [2, 2]],
        device=device,
        dtype=torch.int32,
    )
    topk_weights = torch.full((TOKENS, TOPK), 0.25, device=device, dtype=torch.float32)
    topk_weights[:, 1] = 0.75

    max_padded = TOPK * TOKENS + EXPERTS * TILE_M - TOPK
    max_blocks = (max_padded + TILE_M - 1) // TILE_M
    sentinel = (TOPK << 24) | TOKENS
    sorted_ids = torch.full((max_padded,), sentinel, device=device, dtype=torch.int32)
    sorted_weights = torch.empty((max_padded,), device=device, dtype=torch.float32)
    sorted_expert_ids = torch.full((max_blocks,), -1, device=device, dtype=torch.int32)
    num_valid_ids = torch.empty((1,), device=device, dtype=torch.int32)

    id_begin = 0
    expert_begin = 0
    for expert in range(EXPERTS):
        token_ids, slots = torch.where(topk_ids == expert)
        count = int(token_ids.numel())
        blocks = (count + TILE_M - 1) // TILE_M
        padded = blocks * TILE_M
        sorted_ids[id_begin : id_begin + count] = (slots.to(torch.int32) << 24) | token_ids.to(torch.int32)
        sorted_weights[id_begin : id_begin + count] = topk_weights[token_ids, slots]
        sorted_expert_ids[expert_begin : expert_begin + blocks] = expert
        id_begin += padded
        expert_begin += blocks
    num_valid_ids[0] = id_begin
    return topk_ids, topk_weights, sorted_ids, sorted_weights, sorted_expert_ids, num_valid_ids


def make_case(device):
    topk_ids, topk_weights, *routing = build_routing(device)
    torch.manual_seed(SEED)
    a2_fp32 = torch.randn((TOKENS, TOPK, INTER_DIM), device=device, dtype=torch.float32)
    w2_fp32 = torch.randn((EXPERTS, MODEL_DIM, INTER_DIM), device=device, dtype=torch.float32)
    w2_fp32 *= 1.0 / math.sqrt(INTER_DIM)
    a2_q, a2_scale = pertoken_quant(a2_fp32, quant_dtype=torch.float8_e4m3fn)
    w2_q, w2_scale = pertoken_quant(w2_fp32, quant_dtype=torch.float8_e4m3fn)
    w2_kernel = shuffle_weight(w2_q).view(EXPERTS * MODEL_DIM, INTER_DIM).contiguous().view(-1)
    w2_scale_flat = w2_scale.view(EXPERTS * MODEL_DIM, 1)
    return {
        "topk_ids": topk_ids,
        "topk_weights": topk_weights,
        "routing": routing,
        "a2_q": a2_q,
        "a2_scale": a2_scale,
        "w2_q": w2_q,
        "w2_scale": w2_scale,
        "w2_kernel": w2_kernel,
        "w2_scale_flat": w2_scale_flat,
    }


def direct_reference(case):
    a2 = case["a2_q"].float() * case["a2_scale"]
    w2 = case["w2_q"].float() * case["w2_scale"]
    result = torch.zeros((TOKENS, MODEL_DIM), device=a2.device, dtype=torch.float32)
    for token in range(TOKENS):
        for slot in range(TOPK):
            expert = int(case["topk_ids"][token, slot].item())
            result[token] += case["topk_weights"][token, slot] * (a2[token, slot] @ w2[expert].t())
    return result


def launch_args(out, case):
    sorted_ids, sorted_weights, sorted_expert_ids, num_valid_ids = case["routing"]
    blocks = int(sorted_expert_ids.numel())
    return (
        out,
        case["a2_q"].view(-1),
        case["w2_kernel"],
        case["a2_scale"].view(-1).contiguous(),
        case["w2_scale_flat"].view(-1).contiguous(),
        sorted_ids,
        sorted_expert_ids,
        sorted_weights.contiguous().view(-1),
        num_valid_ids,
        TOKENS,
        MODEL_DIM,
        INTER_DIM,
        blocks,
        torch.cuda.current_stream(),
    )


def run_reduce(case):
    exe = compile_moe_gemm2(
        model_dim=MODEL_DIM,
        inter_dim=INTER_DIM,
        experts=EXPERTS,
        topk=TOPK,
        tile_m=TILE_M,
        tile_n=TILE_N,
        tile_k=TILE_K,
        doweight_stage2=True,
        out_dtype="bf16",
        accumulate=False,
        in_dtype="fp8",
    )
    out = torch.zeros((TOKENS * TOPK, MODEL_DIM), device="cuda", dtype=torch.bfloat16)
    args = launch_args(out, case)
    compiled = flyc.compile(exe, *args)
    out.zero_()
    compiled(*args)
    torch.cuda.synchronize()

    with profile(activities=[ProfilerActivity.CUDA]) as profiler:
        for _ in range(5):
            out.zero_()
            compiled(*args)
        torch.cuda.synchronize()

    kernel_events = {}
    for event in profiler.events():
        if event.device_type != torch.autograd.DeviceType.CUDA:
            continue
        entry = kernel_events.setdefault(event.name, {"count": 0, "device_time_us": 0.0})
        entry["count"] += 1
        entry["device_time_us"] += float(event.device_time)
    return out, kernel_events


def metrics(got, reference):
    got_float = got.float()
    difference = got_float - reference
    denominator = float(reference.norm())
    return {
        "cosine_similarity": float((got_float.reshape(-1) @ reference.reshape(-1)) / (got_float.norm() * reference.norm())),
        "relative_l2": float(difference.norm() / denominator),
        "max_abs_error": float(difference.abs().max()),
        "mean_abs_error": float(difference.abs().mean()),
        "reference_l2": denominator,
    }


def attempt_atomic(case):
    exe = compile_moe_gemm2(
        model_dim=MODEL_DIM,
        inter_dim=INTER_DIM,
        experts=EXPERTS,
        topk=TOPK,
        tile_m=TILE_M,
        tile_n=TILE_N,
        tile_k=TILE_K,
        doweight_stage2=True,
        out_dtype="bf16",
        accumulate=True,
        in_dtype="fp8",
    )
    out = torch.zeros((TOKENS, MODEL_DIM), device="cuda", dtype=torch.bfloat16)
    try:
        flyc.compile(exe, *launch_args(out, case))
    except Exception as exc:
        return {
            "path": "moe_gemm_2stage atomic epilogue",
            "status": "unsupported_in_installed_runtime",
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback_tail": traceback.format_exc().splitlines()[-8:],
        }
    return {"path": "moe_gemm_2stage atomic epilogue", "status": "supported"}


def attempt_fused_megamoe():
    max_tok = 16
    recv_cap = 16
    comb_inp_nbytes = max_tok * TOPK * MODEL_DIM * 2
    launch = compile_mega_moe_stage2(
        model_dim=MODEL_DIM,
        inter_dim=INTER_DIM,
        experts=EXPERTS,
        topk=TOPK,
        rank=0,
        npes=1,
        max_tok=max_tok,
        recv_cap=recv_cap,
        comb_inp_nbytes=comb_inp_nbytes,
        BM=TILE_M,
        BN=256,
        BK=256,
        HIDDEN_MAX=MODEL_DIM,
        INTER_MAX=256,
        a_dtype="fp8",
        SBM=TILE_M,
        cu_num=256,
    )
    device = torch.device("cuda")
    aq = torch.zeros(max_tok * INTER_DIM, dtype=torch.uint8, device=device)
    ascale = torch.zeros(max_tok * 4, dtype=torch.uint8, device=device)
    bq = torch.zeros(EXPERTS * MODEL_DIM * INTER_DIM, dtype=torch.uint8, device=device)
    bscale = torch.zeros(EXPERTS * MODEL_DIM * 4, dtype=torch.uint8, device=device)
    eids = torch.zeros(TILE_M, dtype=torch.int32, device=device)
    cumsum = torch.tensor([TILE_M], dtype=torch.int32, device=device)
    max_expert_tiles = torch.tensor([1], dtype=torch.int32, device=device)
    stids = torch.zeros(64, dtype=torch.int32, device=device)
    sweights = torch.zeros(64, dtype=torch.float32, device=device)
    trb = torch.zeros(64, dtype=torch.int32, device=device)
    combine = torch.zeros(comb_inp_nbytes, dtype=torch.uint8, device=device)
    p2p = torch.tensor([combine.data_ptr()], dtype=torch.int64, device=device)
    args = (
        fx.Int64(aq.data_ptr()),
        fx.Int64(ascale.data_ptr()),
        fx.Int64(bq.data_ptr()),
        fx.Int64(bscale.data_ptr()),
        fx.Int64(eids.data_ptr()),
        fx.Int64(cumsum.data_ptr()),
        fx.Int64(max_expert_tiles.data_ptr()),
        fx.Int64(stids.data_ptr()),
        fx.Int64(sweights.data_ptr()),
        fx.Int64(trb.data_ptr()),
        fx.Int64(p2p.data_ptr()),
        fx.Int32(1),
        fx.Int32(1),
        fx.Int32(INTER_DIM),
        fx.Int32(MODEL_DIM),
        fx.Int32(0),
        fx.Int32(0),
        fx.Stream(torch.cuda.current_stream()),
    )
    try:
        flyc.compile(launch, *args)
    except Exception as exc:
        return {
            "path": "MegaMoE fused GEMM2/P2P combine",
            "status": "unsupported_in_installed_runtime",
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback_tail": traceback.format_exc().splitlines()[-8:],
        }
    return {"path": "MegaMoE fused GEMM2/P2P combine", "status": "supported"}


def cache_artifacts():
    cache_root = Path(os.environ["FLYDSL_RUNTIME_CACHE_DIR"])
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
    artifacts = []
    for path in cache_root.rglob("*.pkl"):
        with path.open("rb") as handle:
            artifact = pickle.load(handle)
        source_ir = getattr(artifact, "_source_ir", "")
        ir_text = getattr(artifact, "_ir_text", "")
        if "kernels/moe/moe_gemm_2stage/gemm2.py" not in source_ir or "gpu.func @moe_gemm2" not in source_ir:
            continue
        entry = {
            "artifact_path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "gpu_function": re.search(r"gpu\.func\s+@([^\s(]+)", source_ir).group(1),
        }
        for name, pattern in patterns.items():
            match = re.search(pattern, ir_text)
            if match is not None:
                entry[name] = int(match.group(1))
        artifacts.append(entry)
    return sorted(artifacts, key=lambda entry: entry["artifact_path"])


def gpu_identity():
    properties = torch.cuda.get_device_properties(torch.cuda.current_device())
    return {
        "name": properties.name,
        "capability": list(torch.cuda.get_device_capability(0)),
        "gcn_arch_name": properties.gcnArchName,
        "multi_processor_count": properties.multi_processor_count,
        "total_memory_bytes": properties.total_memory,
        "uuid": str(properties.uuid),
    }


def rocm_snapshot():
    result = subprocess.run(
        ["rocm-smi", "--showproductname", "--showserial", "--showuniqueid", "--showdriverversion"],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}


def git_identity():
    return {
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip(),
        "branch": subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO_ROOT, text=True).strip(),
        "main_commit": subprocess.check_output(["git", "rev-parse", "origin/main"], cwd=REPO_ROOT, text=True).strip(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("gemm2_combine_results.json"))
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA/ROCm GPU is unavailable")
    arch = str(get_rocm_arch() or "")
    if not arch.startswith("gfx95"):
        raise RuntimeError(f"this validation requires gfx950, got {arch or 'unknown'}")
    if not os.environ.get("FLYDSL_RUNTIME_CACHE_DIR"):
        raise RuntimeError("FLYDSL_RUNTIME_CACHE_DIR must point outside JOB_WORKDIR")

    device = torch.device("cuda")
    case = make_case(device)
    reference = direct_reference(case)
    out, kernel_events = run_reduce(case)
    got = out.view(TOKENS, TOPK, MODEL_DIM).sum(dim=1)
    result_metrics = metrics(got, reference)
    result_metrics["gate"] = GATE
    result_metrics["gate_pass"] = result_metrics["cosine_similarity"] > GATE["threshold"]

    sorted_ids, sorted_weights, sorted_expert_ids, num_valid_ids = case["routing"]
    report = {
        "schema_version": 1,
        "scope": "GEMM2/combine only; GEMM1 dispatch/sorting and persistent scheduling excluded",
        "environment": {
            "python": sys.executable,
            "python_version": sys.version,
            "platform": platform.platform(),
            "torch_version": torch.__version__,
            "hip_version": torch.version.hip,
            "flydsl_package": str(Path(flydsl.__file__).parent),
            "flydsl_version": flydsl.__version__,
            "flydsl_native_paths": sorted(
                str(path) for path in (Path(flydsl.__file__).parent / "_mlir" / "_mlir_libs").glob("*.so")
            ),
            "flydsl_runtime_cache_dir": os.environ["FLYDSL_RUNTIME_CACHE_DIR"],
            "local_image_id": LOCAL_IMAGE_ID,
            "container_hostname": platform.node(),
            "gpu": gpu_identity(),
            "rocm_smi": rocm_snapshot(),
            "source": git_identity(),
        },
        "configuration": {
            "tokens": TOKENS,
            "model_dim": MODEL_DIM,
            "inter_dim": INTER_DIM,
            "experts": EXPERTS,
            "topk": TOPK,
            "tile_m": TILE_M,
            "tile_n": TILE_N,
            "tile_k": TILE_K,
            "seed": SEED,
            "epilogue": "reduce plus explicit top-k slot sum",
            "dtype_identities": {
                "kernel_in_dtype": "fp8",
                "activation_payload": str(case["a2_q"].dtype),
                "activation_scale": str(case["a2_scale"].dtype),
                "weight_payload": str(case["w2_q"].dtype),
                "weight_scale": str(case["w2_scale"].dtype),
                "kernel_output": str(out.dtype),
                "torch_reference": str(reference.dtype),
            },
        },
        "routing": {
            "topk_ids": case["topk_ids"].tolist(),
            "topk_weights": case["topk_weights"].tolist(),
            "expert_route_counts": torch.bincount(case["topk_ids"].reshape(-1), minlength=EXPERTS).tolist(),
            "duplicate_route_rows": int((case["topk_ids"][:, 0] == case["topk_ids"][:, 1]).sum().item()),
            "logical_routes": TOKENS * TOPK,
            "sorted_ids": sorted_ids.tolist(),
            "sorted_weights": sorted_weights.tolist(),
            "sorted_expert_ids": sorted_expert_ids.tolist(),
            "num_valid_ids": num_valid_ids.tolist(),
            "sorted_capacity": int(sorted_ids.numel()),
            "padding_rows": int(sorted_ids.numel() - num_valid_ids[0].item()),
        },
        "kernel_identity": {
            "launcher": "launch_moe_gemm2",
            "source": "kernels/moe/moe_gemm_2stage/gemm2.py",
            "profiler_events": kernel_events,
            "cache_artifacts": cache_artifacts(),
        },
        "results": result_metrics,
        "unsupported_paths": [attempt_atomic(case), attempt_fused_megamoe()],
        "related_upstream": {
            "issue": {
                "repository": "ROCm/FlyDSL",
                "number": 727,
                "title": "[Feature]: Support Mega-Moe V1",
                "state": "open",
                "url": "https://github.com/ROCm/FlyDSL/issues/727",
            },
            "candidate_pr_932": {
                "title": "fix(mega_moe): correct GEMM2 A-scale indexing for BM=16",
                "head_commit": "a59eca588a962373baede3fb4e63a4c1e9552b3c",
                "state": "closed",
                "merged": False,
                "applied": False,
                "reason": "existing upstream fix; not duplicated",
            },
        },
        "reproduction_commands": [
            "export FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-f48f52cfae33/gemm2-report",
            "export TRITON_CACHE_DIR=/tmp/flydsl-cache-j-f48f52cfae33/triton",
            "/opt/venv/bin/python -m pytest tests/kernels/test_moe_gemm_2stage.py::test_moe_gemm2_duplicate_routes_padded_reduce -q",
            "/opt/venv/bin/python reports/j-f48f52cfae33/validate_gemm2_combine.py",
        ],
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(args.output), "gate_pass": result_metrics["gate_pass"], **result_metrics}, indent=2))


if __name__ == "__main__":
    main()
