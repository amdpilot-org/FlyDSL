# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

"""Fused RoPE + KV Cache kernel builder using the @flyc.kernel API.

Fuses 3 operations into two kernel launches:
  Kernel 1 (Q RoPE):     Q → rotate → Q_out
  Kernel 2 (K+V cache):  K → rotate → K_out + key_cache;  V → value_cache

Input shapes:
  Q: [T, QH, D],  K: [T, KH, D],  V: [T, KH, D]
  CosCache/SinCache: [max_pos, D//2]  (must be 2-D contiguous)
  Positions: [T] int32,  SlotMapping: [T] int32

KV cache layouts:
  flash_layout=True:
    KeyCache:   [num_blocks, block_size, KH, D]
    ValueCache: [num_blocks, block_size, KH, D]
  flash_layout=False (ATOM default):
    KeyCache:   [num_blocks, KH, D//x, block_size, x]  (x=16, x-packed)
    ValueCache: [num_blocks, KH, D, block_size]         (dim-major)


"""

import flydsl.compiler as flyc
import flydsl.expr as fx

from flydsl.expr import arith, vector, range_constexpr
from flydsl.expr.arith import ArithValue
from flydsl.expr.typing import T
from flydsl.expr import buffer_ops
from kernels.kernels_common import dtype_to_elem_type
from kernels.mfma_preshuffle_pipeline import crd2idx


WARP_SIZE = 64
VEC_WIDTH = 8


def _layout_to_dword_off(coord, layout, elem_bytes):
    """Coordinate → dword offset for buffer_load/buffer_store.

    crd2idx(coord, layout) → element offset (index) → byte offset (i32) → dword offset (i32).
    """
    elem_off = arith.index_cast(T.i32, crd2idx(coord, layout))
    return (ArithValue(elem_off) * elem_bytes) >> fx.Int32(2)


def _apply_neox_rope(qk_rsrc, qk_dw, cos_rsrc, sin_rsrc, cos_dw,
                     pair_rsrc, pair_dw, is_first_half,
                     vec_dwords, vec_type_e, i32_vec_ty):
    """Load, rotate (NeoX), and return the rotated vector as i32.

    Performs:
      out[first_half]  = qk * cos - pair * sin
      out[second_half] = qk * cos + pair * sin

    Args:
        qk_rsrc:       buffer resource for Q or K
        qk_dw:         dword offset of the current thread's vec in qk_rsrc
        cos_rsrc:      buffer resource for CosCache
        sin_rsrc:      buffer resource for SinCache
        cos_dw:        dword offset into cos/sin (shared for both halves)
        pair_rsrc:     buffer resource for the paired-half vec (same as qk_rsrc)
        pair_dw:       dword offset of the partner vec in pair_rsrc
        is_first_half: i1 predicate — true when tid < vecs_per_half
        vec_dwords:    number of i32 dwords per vector load
        vec_type_e:    MLIR vector type in element dtype (e.g. vec<8xbf16>)
        i32_vec_ty:    MLIR vector type in i32 (e.g. vec<4xi32>)

    Returns:
        rot_i32: rotated vector as i32 vector, ready for buffer_store
    """
    def _load_e(rsrc, dw):
        raw = buffer_ops.buffer_load(rsrc, dw, vec_width=vec_dwords, dtype=T.i32)
        return vector.bitcast(vec_type_e, raw)

    qk_e   = _load_e(qk_rsrc,   qk_dw)
    cos_e  = _load_e(cos_rsrc,  cos_dw)
    sin_e  = _load_e(sin_rsrc,  cos_dw)
    pair_e = _load_e(pair_rsrc, pair_dw)

    # NeoX sign: first half uses -sin, second half uses +sin
    qk_cos   = ArithValue(qk_e) * ArithValue(cos_e)
    pair_sin = ArithValue(pair_e) * ArithValue(sin_e)
    sin_term = arith.select(is_first_half, arith.negf(pair_sin), pair_sin)
    rot_e    = ArithValue(qk_cos) + ArithValue(sin_term)

    return vector.bitcast(i32_vec_ty, rot_e)


def build_fused_rope_cache_module(
    head_dim: int = 64,
    rotary_dim: int = -1,
    num_q_heads: int = 8,
    num_kv_heads: int = 1,
    block_size: int = 16,
    is_neox: bool = True,
    flash_layout: bool = True,
    dtype_str: str = "bf16",
):
    """Build fused RoPE + KV cache kernel.

    Args:
        head_dim: dimension per attention head
        rotary_dim: dimensions to rotate (== head_dim for full rotation)
        num_q_heads: query heads per rank
        num_kv_heads: KV heads per rank
        block_size: paged attention block size
        is_neox: True for NeoX-style rotation
        flash_layout: True for [num_blocks, block_size, KH, D] cache layout
        dtype_str: element dtype ("bf16" or "f16")

    Returns:
        launch_fn(Q, K, V, Positions, CosCache, SinCache, SlotMapping,
                  KeyCache, ValueCache, Q_out, K_out, num_tokens, stream)
    """
    if rotary_dim == -1:
        rotary_dim = head_dim
    if not is_neox:
        raise NotImplementedError("Only NeoX-style RoPE is supported")
    if rotary_dim != head_dim:
        raise NotImplementedError("Partial rotation not yet supported")
    if dtype_str not in ("bf16", "f16"):
        raise ValueError(
            f"dtype_str must be 'bf16' or 'f16', got {dtype_str!r} "
            f"(f32 is not supported: kernel uses 2-byte elem_bytes and vec8 vectorization)"
        )
    half_dim = rotary_dim // 2
    elem_bytes = 2  # bf16 and f16 are both 2 bytes
    vec_dwords = (VEC_WIDTH * elem_bytes) // 4  # 4 dwords for vec8 of 2-byte elements
    vecs_per_half = half_dim // VEC_WIDTH   # number of VEC_WIDTH-wide vectors covering half_dim
    vecs_per_head = head_dim // VEC_WIDTH   # number of VEC_WIDTH-wide vectors covering head_dim
    x_size = 16  # x-packing factor for non-flash key_cache

    # Validate vectorization and layout assumptions to avoid silent truncation.
    if head_dim % VEC_WIDTH != 0:
        raise ValueError(
            f"head_dim must be a multiple of VEC_WIDTH ({VEC_WIDTH}), "
            f"got head_dim={head_dim}"
        )
    if rotary_dim % 2 != 0:
        raise ValueError(
            f"rotary_dim must be even so that half_dim=rotary_dim//2 is integral, "
            f"got rotary_dim={rotary_dim}"
        )
    if half_dim % VEC_WIDTH != 0:
        raise ValueError(
            f"half_dim (rotary_dim//2) must be a multiple of VEC_WIDTH "
            f"({VEC_WIDTH}), got half_dim={half_dim} (rotary_dim={rotary_dim})"
        )
    if not flash_layout and head_dim % x_size != 0:
        raise ValueError(
            f"With flash_layout=False, head_dim must be a multiple of the "
            f"key_cache packing factor x_size ({x_size}), got head_dim={head_dim}"
        )
    if vecs_per_head > WARP_SIZE:
        max_head_dim = WARP_SIZE * VEC_WIDTH
        raise ValueError(
            f"Unsupported head_dim={head_dim}: with WARP_SIZE={WARP_SIZE} and "
            f"VEC_WIDTH={VEC_WIDTH}, head_dim must satisfy "
            f"head_dim <= {max_head_dim} to avoid incomplete coverage "
            f"(got vecs_per_head={vecs_per_head} > WARP_SIZE)"
        )
    BLOCK_THREADS = WARP_SIZE

    # Layout shape/stride tuples (plain Python ints) — materialized as
    # fx.make_layout inside each kernel where an MLIR context is active.
    # None is used for dynamic/unknown extents (token count, position range,
    # block count) so the layout shape matches the actual indexing domain.
    _q_shape = (None, num_q_heads, vecs_per_head)
    _q_stride = (num_q_heads * head_dim, head_dim, VEC_WIDTH)
    _kv_shape = (None, num_kv_heads, vecs_per_head)
    _kv_stride = (num_kv_heads * head_dim, head_dim, VEC_WIDTH)
    _cos_shape = (None, vecs_per_half)
    _cos_stride = (half_dim, VEC_WIDTH)

    # ----- Fused Kernel: Q RoPE + K RoPE + KV cache write -----
    # Grid: (max(QH, KH), T, 1), one program per (head, token)
    # Each program: vecs_per_head threads process head_dim elements.
    # Threads conditionally do Q work, K work, or both (when head_idx < QH/KH).
    @flyc.kernel
    def fused_rope_cache_kernel(
        Q: fx.Tensor,            # [T, QH, D]
        K: fx.Tensor,            # [T, KH, D]
        V: fx.Tensor,            # [T, KH, D]
        Positions: fx.Tensor,    # [T] int32
        CosCache: fx.Tensor,     # [max_pos, half_dim]
        SinCache: fx.Tensor,     # [max_pos, half_dim]
        SlotMapping: fx.Tensor,  # [T] int32
        KeyCache: fx.Tensor,     # flash: [num_blocks, BS, KH, D]
        ValueCache: fx.Tensor,   # flash: [num_blocks, BS, KH, D]
        Q_out: fx.Tensor,        # [T, QH, D]
        K_out: fx.Tensor,        # [T, KH, D]
    ):
        pid_h = fx.block_idx.x   # head index 0..max(QH,KH)-1
        pid_t = fx.block_idx.y   # token index 0..T-1
        tid = fx.thread_idx.x    # 0..63

        elem_type = dtype_to_elem_type(dtype_str)
        vec_type_e = T.vec(VEC_WIDTH, elem_type)
        i32_vec_ty = T.vec(vec_dwords, T.i32)

        # Buffer resources at top level
        q_rsrc = buffer_ops.create_buffer_resource(Q, max_size=True)
        k_rsrc = buffer_ops.create_buffer_resource(K, max_size=True)
        v_rsrc = buffer_ops.create_buffer_resource(V, max_size=True)
        pos_rsrc = buffer_ops.create_buffer_resource(Positions, max_size=True)
        cos_rsrc = buffer_ops.create_buffer_resource(CosCache, max_size=True)
        sin_rsrc = buffer_ops.create_buffer_resource(SinCache, max_size=True)
        slot_rsrc = buffer_ops.create_buffer_resource(SlotMapping, max_size=True)
        kc_rsrc = buffer_ops.create_buffer_resource(KeyCache, max_size=True)
        vc_rsrc = buffer_ops.create_buffer_resource(ValueCache, max_size=True)
        qo_rsrc = buffer_ops.create_buffer_resource(Q_out, max_size=True)
        ko_rsrc = buffer_ops.create_buffer_resource(K_out, max_size=True)

        # Layouts (materialized inside kernel where MLIR context is active)
        q_layout = fx.make_layout(_q_shape, _q_stride)
        kv_layout = fx.make_layout(_kv_shape, _kv_stride)
        cos_sin_layout = fx.make_layout(_cos_shape, _cos_stride)

        if arith.cmpi(arith.CmpIPredicate.ult, tid, fx.Int32(vecs_per_head)):
            # Load position once per (token, head) block
            pos_val = buffer_ops.buffer_load(pos_rsrc, pid_t, vec_width=1, dtype=T.i32)

            # -- Shared cos/sin address via crd2idx (same for both Q and K) --
            cos_vec_idx = tid % vecs_per_half
            cos_coord = (pos_val, fx.Int32(cos_vec_idx))
            cos_dw = _layout_to_dword_off(cos_coord, cos_sin_layout, elem_bytes)

            is_first_half = arith.cmpi(arith.CmpIPredicate.ult, tid, fx.Int32(vecs_per_half))
            pair_tid = arith.select(is_first_half, tid + vecs_per_half, tid - vecs_per_half)

            # --- Q RoPE (conditional on pid_h < num_q_heads) ---
            is_q_head = arith.cmpi(
                arith.CmpIPredicate.ult, pid_h, fx.Int32(num_q_heads)
            )
            if is_q_head:
                q_coord = (pid_t, pid_h, tid)
                q_dw = _layout_to_dword_off(q_coord, q_layout, elem_bytes)
                pair_coord_q = (pid_t, pid_h, pair_tid)
                pair_dw_q = _layout_to_dword_off(pair_coord_q, q_layout, elem_bytes)
                rot_i32 = _apply_neox_rope(
                    q_rsrc, q_dw, cos_rsrc, sin_rsrc, cos_dw,
                    q_rsrc, pair_dw_q, is_first_half,
                    vec_dwords, vec_type_e, i32_vec_ty,
                )
                buffer_ops.buffer_store(rot_i32, qo_rsrc, q_dw)

            # --- K RoPE + KV cache write (conditional on pid_h < num_kv_heads) ---
            is_kv_head = arith.cmpi(
                arith.CmpIPredicate.ult, pid_h, fx.Int32(num_kv_heads)
            )
            if is_kv_head:
                kv_coord = (pid_t, pid_h, tid)
                k_dw = _layout_to_dword_off(kv_coord, kv_layout, elem_bytes)
                pair_coord_k = (pid_t, pid_h, pair_tid)
                pair_dw_k = _layout_to_dword_off(pair_coord_k, kv_layout, elem_bytes)
                k_rot_i32 = _apply_neox_rope(
                    k_rsrc, k_dw, cos_rsrc, sin_rsrc, cos_dw,
                    k_rsrc, pair_dw_k, is_first_half,
                    vec_dwords, vec_type_e, i32_vec_ty,
                )
                buffer_ops.buffer_store(k_rot_i32, ko_rsrc, k_dw)

                # KV Cache write
                slot_val = buffer_ops.buffer_load(slot_rsrc, pid_t, vec_width=1, dtype=T.i32)

                if arith.cmpi(arith.CmpIPredicate.sge, slot_val, fx.Int32(0)):
                    pid_t_slot = ArithValue(slot_val) // block_size
                    pid_b = ArithValue(slot_val) % block_size

                    v_raw = buffer_ops.buffer_load(v_rsrc, k_dw, vec_width=vec_dwords, dtype=T.i32)

                    if flash_layout:
                        kc_flash_layout = fx.make_layout(
                            (None, block_size, num_kv_heads, vecs_per_head),
                            (block_size * num_kv_heads * head_dim,
                             num_kv_heads * head_dim,
                             head_dim,
                             VEC_WIDTH),
                        )
                        kc_coord = (pid_t_slot, pid_b, pid_h, tid)
                        kc_dw = _layout_to_dword_off(kc_coord, kc_flash_layout, elem_bytes)

                        buffer_ops.buffer_store(k_rot_i32, kc_rsrc, kc_dw)
                        buffer_ops.buffer_store(v_raw, vc_rsrc, kc_dw)
                    else:
                        d_start = ArithValue(tid) * VEC_WIDTH
                        dim_group = d_start // x_size
                        dim_within = d_start % x_size

                        kc_nf_layout = fx.make_layout(
                            (None, num_kv_heads, head_dim // x_size, block_size, x_size),
                            (num_kv_heads * (head_dim // x_size) * block_size * x_size,
                             (head_dim // x_size) * block_size * x_size,
                             block_size * x_size,
                             x_size,
                             1),
                        )
                        kc_coord_nf = (pid_t_slot, pid_h, dim_group, pid_b, dim_within)
                        kc_dw_nf = _layout_to_dword_off(kc_coord_nf, kc_nf_layout, elem_bytes)

                        buffer_ops.buffer_store(k_rot_i32, kc_rsrc, kc_dw_nf)

                        v_e = vector.bitcast(vec_type_e, v_raw)
                        vc_nf_layout = fx.make_layout(
                            (None, num_kv_heads, head_dim, block_size),
                            (num_kv_heads * head_dim * block_size,
                             head_dim * block_size,
                             block_size,
                             1),
                        )
                        for vi in range_constexpr(VEC_WIDTH):
                            v_scalar = vector.extract(v_e, static_position=[vi])
                            d_idx = ArithValue(tid) * VEC_WIDTH + vi
                            vc_coord = (pid_t_slot, pid_h, d_idx, pid_b)
                            vc_elem_off = arith.index_cast(T.i32, crd2idx(vc_coord, vc_nf_layout))
                            buffer_ops.buffer_store(v_scalar, vc_rsrc, vc_elem_off)

    @flyc.jit
    def launch_fused_rope_cache(
        Q: fx.Tensor,
        K: fx.Tensor,
        V: fx.Tensor,
        Positions: fx.Tensor,
        CosCache: fx.Tensor,
        SinCache: fx.Tensor,
        SlotMapping: fx.Tensor,
        KeyCache: fx.Tensor,
        ValueCache: fx.Tensor,
        Q_out: fx.Tensor,
        K_out: fx.Tensor,
        num_tokens: fx.Int32,
        stream: fx.Stream = fx.Stream(None),
    ):
        n_h = max(num_q_heads, num_kv_heads)
        fused_launcher = fused_rope_cache_kernel(
            Q, K, V,
            Positions, CosCache, SinCache,
            SlotMapping, KeyCache, ValueCache,
            Q_out, K_out,
        )
        fused_launcher.launch(
            grid=(n_h, num_tokens, 1),
            block=(BLOCK_THREADS, 1, 1),
            stream=stream,
        )

    # Pre-compile with dummy tensors inside the builder to eliminate JIT
    # dispatch overhead from the timed path (~100 us -> ~20 us).
    import torch as _torch
    _dummy_tok = 50
    _dummy_pos = 8192
    _dummy_dtype = _torch.bfloat16 if dtype_str == "bf16" else _torch.float16
    _dummy_Q = _torch.empty(_dummy_tok, num_q_heads, head_dim, device="cuda", dtype=_dummy_dtype)
    _dummy_K = _torch.empty(_dummy_tok, num_kv_heads, head_dim, device="cuda", dtype=_dummy_dtype)
    _dummy_V = _torch.empty(_dummy_tok, num_kv_heads, head_dim, device="cuda", dtype=_dummy_dtype)
    _dummy_Pos = _torch.empty(_dummy_tok, device="cuda", dtype=_torch.int32)
    _dummy_Cos = _torch.empty(_dummy_pos, half_dim, device="cuda", dtype=_dummy_dtype)
    _dummy_Sin = _torch.empty(_dummy_pos, half_dim, device="cuda", dtype=_dummy_dtype)
    _dummy_Slot = _torch.empty(_dummy_tok, device="cuda", dtype=_torch.int32)
    _dummy_nb = max(32, (_dummy_tok + block_size - 1) // block_size + 4)
    _dummy_KC = _torch.empty(_dummy_nb, block_size, num_kv_heads, head_dim, device="cuda", dtype=_dummy_dtype)
    _dummy_VC = _torch.empty(_dummy_nb, block_size, num_kv_heads, head_dim, device="cuda", dtype=_dummy_dtype)
    _dummy_Qo = _torch.empty_like(_dummy_Q)
    _dummy_Ko = _torch.empty_like(_dummy_K)

    _compiled = flyc.compile(
        launch_fused_rope_cache,
        _dummy_Q, _dummy_K, _dummy_V,
        _dummy_Pos, _dummy_Cos, _dummy_Sin,
        _dummy_Slot, _dummy_KC, _dummy_VC,
        _dummy_Qo, _dummy_Ko, _dummy_tok,
        _torch.cuda.current_stream(),
    )

    def launch_fused_rope_cache_fast(
        Q, K, V, Positions, CosCache, SinCache,
        SlotMapping, KeyCache, ValueCache,
        Q_out, K_out, num_tokens, stream=None,
    ):
        s = stream if stream is not None else _torch.cuda.current_stream()
        return _compiled(Q, K, V, Positions, CosCache, SinCache,
                         SlotMapping, KeyCache, ValueCache,
                         Q_out, K_out, num_tokens, s)

    return launch_fused_rope_cache_fast
