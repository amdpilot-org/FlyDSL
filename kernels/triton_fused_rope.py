"""Fused bf16 NeoX RoPE Triton kernel for AMD MI300X (gfx942).

Processes q and k in a SINGLE kernel launch to halve launch overhead.
Grid: one block per sequence position (q first, then k).
Block: D=256 threads, loops over H heads.
"""

import torch
import triton
import triton.language as tl

_out_cache: dict = {}


def _get_out_like(x: torch.Tensor) -> torch.Tensor:
    key = (x.shape, x.dtype, x.device)
    out = _out_cache.get(key)
    if out is None or out.shape != x.shape:
        out = torch.empty_like(x)
        _out_cache[key] = out
    return out


@triton.jit
def _fused_rope_neox_kernel_qk_merged(
    q_ptr,
    k_ptr,
    cos_q_ptr,
    sin_q_ptr,
    cos_k_ptr,
    sin_k_ptr,
    q_out_ptr,
    k_out_ptr,
    Sq: tl.constexpr,
    Sk: tl.constexpr,
    H: tl.constexpr,
    D: tl.constexpr,
    HALF_D: tl.constexpr,
    q_stride_b: tl.constexpr,
    q_stride_h: tl.constexpr,
    q_stride_s: tl.constexpr,
    k_stride_b: tl.constexpr,
    k_stride_h: tl.constexpr,
    k_stride_s: tl.constexpr,
):
    """One block per seq position; first Sq positions = q, rest = k."""
    pid = tl.program_id(0)
    tid = tl.arange(0, D)

    if pid < Sq:
        # --- Q path ---
        s = pid
        for h in tl.static_range(H):
            offsets = 0 * q_stride_b + h * q_stride_h + s * q_stride_s + tid
            x_val = tl.load(q_ptr + offsets).to(tl.float32)
            cos_val = tl.load(cos_q_ptr + s * D + tid).to(tl.float32)
            sin_val = tl.load(sin_q_ptr + s * D + tid).to(tl.float32)
            is_first = tid < HALF_D
            pair_tid = tl.where(is_first, tid + HALF_D, tid - HALF_D)
            pair_offsets = 0 * q_stride_b + h * q_stride_h + s * q_stride_s + pair_tid
            pair_val = tl.load(q_ptr + pair_offsets).to(tl.float32)
            rotated_val = tl.where(is_first, -pair_val, pair_val)
            out_val = x_val * cos_val + rotated_val * sin_val
            tl.store(q_out_ptr + offsets, out_val.to(tl.bfloat16))
    else:
        # --- K path ---
        s = pid - Sq
        for h in tl.static_range(H):
            offsets = 0 * k_stride_b + h * k_stride_h + s * k_stride_s + tid
            x_val = tl.load(k_ptr + offsets).to(tl.float32)
            cos_val = tl.load(cos_k_ptr + s * D + tid).to(tl.float32)
            sin_val = tl.load(sin_k_ptr + s * D + tid).to(tl.float32)
            is_first = tid < HALF_D
            pair_tid = tl.where(is_first, tid + HALF_D, tid - HALF_D)
            pair_offsets = 0 * k_stride_b + h * k_stride_h + s * k_stride_s + pair_tid
            pair_val = tl.load(k_ptr + pair_offsets).to(tl.float32)
            rotated_val = tl.where(is_first, -pair_val, pair_val)
            out_val = x_val * cos_val + rotated_val * sin_val
            tl.store(k_out_ptr + offsets, out_val.to(tl.bfloat16))


def fused_rope_qk_triton(
    q: torch.Tensor,
    k: torch.Tensor,
    cos_q: torch.Tensor,
    sin_q: torch.Tensor,
    cos_k: torch.Tensor,
    sin_k: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    B, H, Sq, D = q.shape
    Bk, Hk, Sk, Dk = k.shape
    assert B == Bk and H == Hk and D == Dk
    assert D == 256, f"This kernel targets D=256, got {D}"
    assert cos_q.shape == (1, 1, Sq, D) and sin_q.shape == (1, 1, Sq, D)
    assert cos_k.shape == (1, 1, Sk, D) and sin_k.shape == (1, 1, Sk, D)

    q_out = _get_out_like(q)
    k_out = _get_out_like(k)
    total_blocks = Sq + Sk

    _fused_rope_neox_kernel_qk_merged[(total_blocks,)](
        q, k, cos_q, sin_q, cos_k, sin_k, q_out, k_out,
        Sq, Sk, H, D, D // 2,
        q.stride(0), q.stride(1), q.stride(2),
        k.stride(0), k.stride(1), k.stride(2),
        num_warps=4,
    )
    return q_out, k_out
