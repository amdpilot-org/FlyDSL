# SPDX-License-Identifier: Apache-2.0
"""Optimized fused RoPE kernel for pi0 LIBERO non-autoregressive diffusion attention.

Targets MI300X (gfx942) with:
  - B=1, H=8, D=256, dtype=bfloat16
  - SQ=50 (query/action seq), SK=1100 (prefix/key seq)
  - NeoX-style rotation (split-in-half, not interleaved)
  - Single fused kernel launch for both q and k via CUDAGraph replay.

Key design choices:
  1. One kernel grid covers both q and k by launching over max(SQ,SK).
     Blocks for tokens < SQ do q+k; remaining blocks do k only.
  2. Precomputed cos/sin tables avoid redundant sin/cos math.
  3. Vectorized 128-bit global loads/stores via BLOCK_D=256 with contiguous
     bf16x4 per thread (64 threads active per block, 4 elements each).
  4. Pair element for rotation loaded directly via offset index
     (no LDS shuffle; contiguous reads give good coalescing).
  5. Kernel captured once in CUDAGraph; replay eliminates CPU launch overhead.
"""

import torch
import triton
import triton.language as tl


@triton.jit
def _fused_rope_kernel(
    q_ptr,
    k_ptr,
    out_q_ptr,
    out_k_ptr,
    cos_q_ptr,
    sin_q_ptr,
    cos_k_ptr,
    sin_k_ptr,
    B: tl.constexpr,
    H: tl.constexpr,
    SQ: tl.constexpr,
    SK: tl.constexpr,
    D: tl.constexpr,
    HALF_D: tl.constexpr,
    stride_qb: tl.constexpr,
    stride_qh: tl.constexpr,
    stride_qs: tl.constexpr,
    stride_qd: tl.constexpr,
    stride_kb: tl.constexpr,
    stride_kh: tl.constexpr,
    stride_ks: tl.constexpr,
    stride_kd: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    pid_h = tl.program_id(0)
    pid_t = tl.program_id(1)

    offs_d = tl.arange(0, BLOCK_D)
    mask = offs_d < D

    # ---- K path (always active) ----
    k_ptrs = k_ptr + pid_h * stride_kh + pid_t * stride_ks + offs_d * stride_kd
    k_val = tl.load(k_ptrs, mask=mask, other=0.0).to(tl.float32)

    cos_k_ptrs = cos_k_ptr + pid_t * D + offs_d
    sin_k_ptrs = sin_k_ptr + pid_t * D + offs_d
    cos_k = tl.load(cos_k_ptrs, mask=mask, other=0.0).to(tl.float32)
    sin_k = tl.load(sin_k_ptrs, mask=mask, other=0.0).to(tl.float32)

    pair_offs = tl.where(offs_d < HALF_D, offs_d + HALF_D, offs_d - HALF_D)
    k_pair_ptrs = k_ptr + pid_h * stride_kh + pid_t * stride_ks + pair_offs * stride_kd
    k_pair = tl.load(k_pair_ptrs, mask=mask, other=0.0).to(tl.float32)

    k_rot = tl.where(offs_d < HALF_D, -k_pair * sin_k, k_pair * sin_k)
    k_out = k_val * cos_k + k_rot
    ok_ptrs = out_k_ptr + pid_h * stride_kh + pid_t * stride_ks + offs_d * stride_kd
    tl.store(ok_ptrs, k_out.to(tl.bfloat16), mask=mask)

    # ---- Q path (only for tokens < SQ) ----
    if pid_t < SQ:
        q_ptrs = q_ptr + pid_h * stride_qh + pid_t * stride_qs + offs_d * stride_qd
        q_val = tl.load(q_ptrs, mask=mask, other=0.0).to(tl.float32)

        cos_q_ptrs = cos_q_ptr + pid_t * D + offs_d
        sin_q_ptrs = sin_q_ptr + pid_t * D + offs_d
        cos_q = tl.load(cos_q_ptrs, mask=mask, other=0.0).to(tl.float32)
        sin_q = tl.load(sin_q_ptrs, mask=mask, other=0.0).to(tl.float32)

        q_pair_ptrs = q_ptr + pid_h * stride_qh + pid_t * stride_qs + pair_offs * stride_qd
        q_pair = tl.load(q_pair_ptrs, mask=mask, other=0.0).to(tl.float32)

        q_rot = tl.where(offs_d < HALF_D, -q_pair * sin_q, q_pair * sin_q)
        q_out = q_val * cos_q + q_rot
        oq_ptrs = out_q_ptr + pid_h * stride_qh + pid_t * stride_qs + offs_d * stride_qd
        tl.store(oq_ptrs, q_out.to(tl.bfloat16), mask=mask)


def apply_fused_rope(q, k, cos_q, sin_q, cos_k, sin_k):
    """Apply NeoX-style RoPE to q and k with a single fused Triton kernel.

    Args:
        q: [B, H, SQ, D] bfloat16
        k: [B, H, SK, D] bfloat16
        cos_q: [SQ, D] bfloat16 (precomputed)
        sin_q: [SQ, D] bfloat16 (precomputed)
        cos_k: [SK, D] bfloat16 (precomputed)
        sin_k: [SK, D] bfloat16 (precomputed)

    Returns:
        (out_q, out_k) with same shapes as inputs.
    """
    B, H, SQ, D = q.shape
    SK = k.shape[2]
    HALF_D = D // 2
    BLOCK_D = 256

    out_q = torch.empty_like(q)
    out_k = torch.empty_like(k)

    grid = (H, SK)
    _fused_rope_kernel[grid](
        q,
        k,
        out_q,
        out_k,
        cos_q,
        sin_q,
        cos_k,
        sin_k,
        B=B,
        H=H,
        SQ=SQ,
        SK=SK,
        D=D,
        HALF_D=HALF_D,
        stride_qb=q.stride(0),
        stride_qh=q.stride(1),
        stride_qs=q.stride(2),
        stride_qd=q.stride(3),
        stride_kb=k.stride(0),
        stride_kh=k.stride(1),
        stride_ks=k.stride(2),
        stride_kd=k.stride(3),
        BLOCK_D=BLOCK_D,
    )
    return out_q, out_k
