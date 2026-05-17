# SPDX-License-Identifier: Apache-2.0
"""Optimized fused RoPE kernel with inline sin/cos computation."""

import torch
import triton
import triton.language as tl


@triton.jit
def _fused_rope_inline_kernel(
    q_ptr,
    k_ptr,
    out_q_ptr,
    out_k_ptr,
    theta_ptr,
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

    theta = tl.load(theta_ptr).to(tl.float32)
    freq_idx = tl.where(offs_d < HALF_D, offs_d, offs_d - HALF_D).to(tl.float32)
    inv_freq = tl.exp(-freq_idx * (tl.log(theta) / HALF_D))

    # ---- K path (always active) ----
    pos_k = pid_t.to(tl.float32)
    freq_k = pos_k * inv_freq
    cos_k = tl.cos(freq_k)
    sin_k = tl.sin(freq_k)

    k_ptrs = k_ptr + pid_h * stride_kh + pid_t * stride_ks + offs_d * stride_kd
    k_val = tl.load(k_ptrs, mask=mask, other=0.0).to(tl.float32)

    pair_offs = tl.where(offs_d < HALF_D, offs_d + HALF_D, offs_d - HALF_D)
    k_pair_ptrs = k_ptr + pid_h * stride_kh + pid_t * stride_ks + pair_offs * stride_kd
    k_pair = tl.load(k_pair_ptrs, mask=mask, other=0.0).to(tl.float32)

    k_rot = tl.where(offs_d < HALF_D, -k_pair * sin_k, k_pair * sin_k)
    k_out = k_val * cos_k + k_rot
    ok_ptrs = out_k_ptr + pid_h * stride_kh + pid_t * stride_ks + offs_d * stride_kd
    tl.store(ok_ptrs, k_out.to(tl.bfloat16), mask=mask)

    # ---- Q path (only for tokens < SQ) ----
    if pid_t < SQ:
        pos_q = pid_t.to(tl.float32)
        freq_q = pos_q * inv_freq
        cos_q = tl.cos(freq_q)
        sin_q = tl.sin(freq_q)

        q_ptrs = q_ptr + pid_h * stride_qh + pid_t * stride_qs + offs_d * stride_qd
        q_val = tl.load(q_ptrs, mask=mask, other=0.0).to(tl.float32)

        q_pair_ptrs = q_ptr + pid_h * stride_qh + pid_t * stride_qs + pair_offs * stride_qd
        q_pair = tl.load(q_pair_ptrs, mask=mask, other=0.0).to(tl.float32)

        q_rot = tl.where(offs_d < HALF_D, -q_pair * sin_q, q_pair * sin_q)
        q_out = q_val * cos_q + q_rot
        oq_ptrs = out_q_ptr + pid_h * stride_qh + pid_t * stride_qs + offs_d * stride_qd
        tl.store(oq_ptrs, q_out.to(tl.bfloat16), mask=mask)


def apply_fused_rope_inline(q, k, theta=10000.0):
    B, H, SQ, D = q.shape
    SK = k.shape[2]
    HALF_D = D // 2
    BLOCK_D = 256
    theta_t = torch.tensor(theta, dtype=torch.float32, device=q.device)

    out_q = torch.empty_like(q)
    out_k = torch.empty_like(k)

    grid = (H, SK)
    _fused_rope_inline_kernel[grid](
        q,
        k,
        out_q,
        out_k,
        theta_t,
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
