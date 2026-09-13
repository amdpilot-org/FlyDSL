"""Reproduce and attribute the gfx950 BF16-to-MXFP4 inline MoE discrepancy.

Run from the repository root with the interpreter recorded in REPOSITORY.md.
This deliberately bypasses only the historical pytest.xfail control flow; the
kernel correctness threshold remains unchanged.
"""

import json
import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.kernels.test_moe_gemm import (
    _per_1x32_fp4_quant,
    test_mxfp_moe_variants,
)
from tests.kernels.utils.gemm_common_utils import e8m0_to_f32, mxfp4_to_f32


def snapshot(label: str, values: torch.Tensor) -> None:
    q32, s32 = _per_1x32_fp4_quant(values.float())
    bf16 = values.to(torch.bfloat16).float()
    qb, sb = _per_1x32_fp4_quant(bf16)
    dq = mxfp4_to_f32(qb).reshape(values.shape) * e8m0_to_f32(sb).repeat_interleave(32, dim=1)
    print(json.dumps({
        "case": label,
        "fp32_vs_bf16_input_max_abs": (values.float() - bf16).abs().max().item(),
        "packed_byte_mismatches": (q32.view(torch.uint8) != qb.view(torch.uint8)).sum().item(),
        "scale_byte_mismatches": (s32.view(torch.uint8) != sb.view(torch.uint8)).sum().item(),
        "bf16_packed_hex": qb.view(torch.uint8).cpu().tolist(),
        "bf16_scale_u8": sb.view(torch.uint8).cpu().tolist(),
        "bf16_dequantized": dq.cpu().tolist(),
    }))


def main() -> None:
    dev = "cuda"
    snapshot("exact_and_signed_zero", torch.tensor(
        [[0.0, -0.0, 0.5, -0.5, 1.0, -1.0, 1.5, -1.5] * 4], device=dev))
    snapshot("ties_and_padding", torch.tensor(
        [[0.25, 0.75, 1.25, 1.75, 2.5, 3.5, 5.0, 7.0] * 3 + [0.0] * 8], device=dev))
    snapshot("zero_block", torch.zeros((1, 32), device=dev))
    snapshot("extreme_dynamic_range", torch.tensor(
        [[1e-30, -1e-30, 1e-6, -1e-6, 1.0, -1.0, 1e3, -1e3] * 4], device=dev))

    torch.manual_seed(717)
    torch.cuda.manual_seed_all(717)
    pytest.xfail = lambda reason: print("BYPASS_XFAIL:", reason)
    test_mxfp_moe_variants("fp4", "inline_bm16")


if __name__ == "__main__":
    main()
