# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

"""Fused RoPE + KV Cache kernel builder using the @flyc.kernel API.

Fuses 3 operations into a **single kernel launch**:
  Q -> RoPE rotation -> Q_out
  K -> RoPE rotation -> K_out + key_cache
  V -> value_cache

Grid: (max(QH, KH), T, 1)  -- shared blocks for Q and K
  block_idx.x = head_idx in [0, max(QH, KH))
  block_idx.y = token_idx

  Each block conditionally does Q work (if head_idx < QH) and/or K work
  (if head_idx < KH).  For GQA (QH >> KH) blocks beyond KH only do Q;
  for MQA-like configs where KH <= QH every block does both.

  Cos/sin are loaded ONCE per block (before branching) and shared by both
  the Q and K paths, saving buffer descriptor SGPRs.

Input shapes:
  Q: [T, QH, D],  K: [T, KH, D],  V: [T, KH, D]
  CosCache/SinCache: [max_pos, D//2] if reuse_freqs_front_part else [max_pos, D]
  Positions/SlotMapping:
    - pos_dtype="i32": [T] int32
    - pos_dtype="i64": [T] int64, accessed via stride-2 int32 indexing (.view(int32))

KV cache layouts:
  flash_layout=True:
  flash_layout=False (ATOM default):

"""

import flydsl.compiler as flyc
import flydsl.expr as fx
from flydsl.expr import arith, buffer_ops, const_expr, range_constexpr, vector
from flydsl.expr.arith import ArithValue
from flydsl.expr.typing import T, Vector as Vec
from kernels.kernels_common import get_warp_size

# WARP_SIZE is 32 on RDNA (wave32: gfx10xx/gfx11xx/gfx12xx) and 64 on CDNA (wave64: gfx9xx).
# All derived values (VEC_WIDTH, vecs_per_half, BLOCK_THREADS) flow from this automatically.
WARP_SIZE = get_warp_size()


def build_fused_rope_cache_module(
    head_dim: int = 64,
    rotary_dim: int = -1,
    num_q_heads: int = 8,
    num_kv_heads: int = 1,
    block_size: int = 16,
    is_neox: bool = True,
    flash_layout: bool = True,
    dtype_str: str = "bf16",
    apply_scale: bool = False,
    reuse_freqs_front_part: bool = True,
    pos_dtype: str = "i32",
):
    if rotary_dim == -1:
        rotary_dim = head_dim
    if not is_neox:
        raise NotImplementedError("Only NeoX-style RoPE is supported")
    if rotary_dim != head_dim:
        raise NotImplementedError("Partial rotation not yet supported")
    if dtype_str not in ("bf16", "f16"):
        raise ValueError(
            f"dtype_str must be 'bf16' or 'f16', got {dtype_str!r}"
        )
    half_dim = rotary_dim // 2

    # VEC_WIDTH: elements per thread. Use ceil division so vecs_per_head never
    # exceeds WARP_SIZE for the fixed one-thread-per-vector mapping below.
    # For D=64:  VEC_WIDTH=1 -> vecs_per_head=64 (full wavefront, 16-bit loads).
    # For D=96:  VEC_WIDTH=2 -> vecs_per_head=48 (fits within one wavefront).
    # For D=128: VEC_WIDTH=2 -> vecs_per_head=64 (32-bit loads, unchanged).
    VEC_WIDTH = max(1, (head_dim + WARP_SIZE - 1) // WARP_SIZE)

    vecs_per_half = half_dim // VEC_WIDTH
    vecs_per_head = head_dim // VEC_WIDTH
    x_size = 16

    # elem_bits for copy atom (bf16/f16 = 16 bits)
    elem_bits = 16
    # Copy atom bits: VEC_WIDTH * elem_bits
    copy_bits = VEC_WIDTH * elem_bits  # e.g. 2*16=32 for VEC_WIDTH=2

    if head_dim % VEC_WIDTH != 0:
        raise ValueError(f"head_dim must be a multiple of VEC_WIDTH ({VEC_WIDTH}), got {head_dim}")
    if rotary_dim % 2 != 0:
        raise ValueError(f"rotary_dim must be even, got {rotary_dim}")
    if half_dim % VEC_WIDTH != 0:
        raise ValueError(f"half_dim must be a multiple of VEC_WIDTH ({VEC_WIDTH}), got {half_dim}")
    if not flash_layout and head_dim % x_size != 0:
        raise ValueError(f"head_dim must be a multiple of x_size ({x_size}), got {head_dim}")

    BLOCK_THREADS = WARP_SIZE
    num_q_heads_val = num_q_heads
    num_kv_heads_val = num_kv_heads
    max_heads = max(num_q_heads, num_kv_heads)

    @flyc.kernel
    def fused_qk_rope_reshape_and_cache(
        Q: fx.Tensor,
        K: fx.Tensor,
        V: fx.Tensor,
        Positions: fx.Tensor,
        CosCache: fx.Tensor,
        SinCache: fx.Tensor,
        Q_out: fx.Tensor,
        K_out: fx.Tensor,
    ):
        head_idx = fx.block_idx.x
        pid_t = fx.block_idx.y
        tid = fx.thread_idx.x

        elem_type = T.bf16 if dtype_str == "bf16" else T.f16
        elem_dtype = fx.BFloat16 if dtype_str == "bf16" else fx.Float16

        # --- Layout API setup ---
        copy_atom = fx.make_copy_atom(fx.rocdl.BufferCopy(copy_bits), elem_bits)
        vec_reg_ty = fx.MemRefType.get(
            elem_type, fx.LayoutType.get(VEC_WIDTH, 1), fx.AddressSpace.Register
        )
        # Single layout used for both register alloca and logical_divide (same shape).
        vec_reg_lay = fx.make_layout(VEC_WIDTH, 1)
        vec_div_lay = vec_reg_lay

        # f32 scalar copy atom for KScale/VScale loads (1 x f32 = 32 bits).
        f32_copy_atom = fx.make_copy_atom(fx.rocdl.BufferCopy32b(), 32)
        f32_reg_ty = fx.MemRefType.get(T.f32, fx.LayoutType.get(1, 1), fx.AddressSpace.Register)
        f32_reg_lay = fx.make_layout(1, 1)

        # Helper: load a VEC_WIDTH vector from a divided 1D tensor at given index
        def load_vec(div_tensor, idx, atom=None):
            r = fx.memref_alloca(vec_reg_ty, vec_reg_lay)
            fx.copy_atom_call(atom or copy_atom, fx.slice(div_tensor, (None, idx)), r)
            return fx.memref_load_vec(r)

        # Helper: store a VEC_WIDTH vector to a divided 1D tensor at given index
        def store_vec(val, div_tensor, idx, atom=None):
            r = fx.memref_alloca(vec_reg_ty, vec_reg_lay)
            fx.memref_store_vec(val, r)
            fx.copy_atom_call(atom or copy_atom, r, fx.slice(div_tensor, (None, idx)))

        # Helper: get the rotary-pair element via ds_bpermute (LDS cross-lane shuffle).
        # For NeoX RoPE, the pair of thread tid is tid XOR vecs_per_half.
        # ds_bpermute: thread tid reads the VGPR value held by thread (pair_byte_addr/4).
        # pair_byte_addr = (tid XOR vecs_per_half) * 4.
        # Handles VEC_WIDTH=1 (vector<1xbf16/f16>, 16-bit) and VEC_WIDTH=2 (vector<2xbf16/f16>, 32-bit).
        def ds_bpermute_pair(vec_val, pair_byte_addr):
            """Return the copy of vec_val held by the rotary-pair thread, via ds_bpermute."""
            if const_expr(VEC_WIDTH == 1):
                # vector<1xf16/bf16> → extract scalar → bitcast to i16 → zero-extend i32
                elem_val = vec_val[0]
                i16_val = ArithValue(elem_val).bitcast(T.i16)
                i32_val = ArithValue(i16_val).extui(T.i32)
                # Cross-lane shuffle: get pair thread's 32-bit VGPR (pair elem in low 16 bits)
                peer_i32 = fx.rocdl.ds_bpermute(T.i32, pair_byte_addr, i32_val)
                # Truncate back to i16, bitcast to elem_type, reconstruct vector<1xelem_type>
                peer_i16 = ArithValue(peer_i32).trunci(T.i16)
                peer_elem = ArithValue(peer_i16).bitcast(elem_type)
                return Vec.from_elements([peer_elem], elem_dtype)
            else:
                # VEC_WIDTH>=2: VEC_WIDTH bf16/f16 elements → n_i32 x i32, one ds_bpermute per chunk.
                # VEC_WIDTH=2 → n_i32=1 (32 bits); VEC_WIDTH=4 → n_i32=2 (64 bits), etc.
                n_i32 = VEC_WIDTH // 2
                v_i32 = Vec(vec_val).bitcast(fx.Int32)
                peer_chunks = []
                for ci in range_constexpr(n_i32):
                    chunk = v_i32[ci]
                    peer_chunks.append(fx.rocdl.ds_bpermute(T.i32, pair_byte_addr, chunk))
                peer_v_i32 = Vec.from_elements(peer_chunks, fx.Int32)
                return peer_v_i32.bitcast(elem_dtype)

        if tid < vecs_per_head:
            # --- Load position (scalar i32) ---
            pos_rsrc = buffer_ops.create_buffer_resource(Positions, max_size=True)
            if const_expr(pos_dtype == "i64"):
                pos_elem_off = pid_t * 2
            else:
                pos_elem_off = pid_t
            pos_val = buffer_ops.buffer_load(pos_rsrc, pos_elem_off, vec_width=1, dtype=T.i32)

            is_first_half = tid < vecs_per_half
            cos_vec_idx = tid % vecs_per_half if reuse_freqs_front_part else tid

            # Pair lane for ds_bpermute: tid XOR vecs_per_half (symmetric, works for both halves).
            # pair_byte_addr = pair_lane * 4 (ds_bpermute address unit is bytes, VGPR = 4 bytes).
            pair_lane = tid ^ vecs_per_half
            pair_byte_addr = pair_lane * 4

            # --- Shared cos/sin (loaded once, used by both Q and K) ---
            Cos_buf = fx.rocdl.make_buffer_tensor(CosCache)
            Sin_buf = fx.rocdl.make_buffer_tensor(SinCache)
            cos_row = fx.slice(Cos_buf, (pos_val, None))
            sin_row = fx.slice(Sin_buf, (pos_val, None))
            cos_div = fx.logical_divide(cos_row, vec_div_lay)
            sin_div = fx.logical_divide(sin_row, vec_div_lay)
            cos_e = load_vec(cos_div, cos_vec_idx)
            sin_e = load_vec(sin_div, cos_vec_idx)

            # --- Q RoPE (head_idx < num_q_heads) ---
            if head_idx < num_q_heads_val:
                Q_buf = fx.rocdl.make_buffer_tensor(Q)
                Q_out_buf = fx.rocdl.make_buffer_tensor(Q_out)

                q_row = fx.slice(Q_buf, (pid_t, head_idx, None))
                q_div = fx.logical_divide(q_row, vec_div_lay)
                qo_row = fx.slice(Q_out_buf, (pid_t, head_idx, None))
                qo_div = fx.logical_divide(qo_row, vec_div_lay)

                q_e_vec = load_vec(q_div, tid)
                q_e = q_e_vec
                # Use ds_bpermute to get pair element via LDS cross-lane shuffle (no VMEM).
                q_pair_e = ds_bpermute_pair(q_e_vec, pair_byte_addr)

                q_cos = q_e * cos_e
                q_pair_sin = q_pair_e * sin_e
                q_sin_term = is_first_half.select(-q_pair_sin, q_pair_sin)
                q_rot_e = q_cos + q_sin_term

                store_vec(q_rot_e.ir_value(), qo_div, tid)

            # --- K RoPE + KV cache (head_idx < num_kv_heads) ---
            if head_idx < num_kv_heads_val:
                K_buf = fx.rocdl.make_buffer_tensor(K)
                K_out_buf = fx.rocdl.make_buffer_tensor(K_out)

                k_row = fx.slice(K_buf, (pid_t, head_idx, None))
                k_div = fx.logical_divide(k_row, vec_div_lay)
                ko_row = fx.slice(K_out_buf, (pid_t, head_idx, None))
                ko_div = fx.logical_divide(ko_row, vec_div_lay)

                k_e_vec = load_vec(k_div, tid)
                k_e = k_e_vec
                # Use ds_bpermute to get pair element via LDS cross-lane shuffle (no VMEM).
                k_pair_e = ds_bpermute_pair(k_e_vec, pair_byte_addr)

                k_cos = k_e * cos_e
                k_pair_sin = k_pair_e * sin_e
                k_sin_term = is_first_half.select(-k_pair_sin, k_pair_sin)
                k_rot_e = k_cos + k_sin_term

                store_vec(k_rot_e.ir_value(), ko_div, tid)
                # K_buf, K_out_buf now dead — 8 SGPRs freed

    def _mark_token_layout_dynamic(tensor):
        if hasattr(tensor, "mark_layout_dynamic"):
            shape = getattr(tensor, "_orig_shape", None)
            leading_dim = len(shape) - 1 if shape is not None else -1
            return tensor.mark_layout_dynamic(leading_dim=leading_dim)
        return flyc.from_dlpack(tensor).mark_layout_dynamic(leading_dim=tensor.ndim - 1)

    @flyc.jit
    def _jit_launch_fused_rope_cache(
        Q: fx.Tensor,
        K: fx.Tensor,
        V: fx.Tensor,
        Positions: fx.Tensor,
        CosCache: fx.Tensor,
        SinCache: fx.Tensor,
        Q_out: fx.Tensor,
        K_out: fx.Tensor,
        num_tokens: fx.Int32,
        stream: fx.Stream = fx.Stream(None),
    ):
        launcher = fused_qk_rope_reshape_and_cache(
            Q, K, V, Positions, CosCache, SinCache, SlotMapping,
        )
        launcher.launch(
            grid=(max_heads, num_tokens, 1),
            block=(BLOCK_THREADS, 1, 1),
            stream=stream,
        )

    def launch_fused_rope_cache(
        Q,
        K,
        V,
        Positions,
        CosCache,
        SinCache,
        SlotMapping,
        Q_out,
        K_out,
        num_tokens,
        stream=fx.Stream(None),
    ):
        return _jit_launch_fused_rope_cache(
            _mark_token_layout_dynamic(Q),
            _mark_token_layout_dynamic(K),
            _mark_token_layout_dynamic(V),
            _mark_token_layout_dynamic(Positions),
            CosCache,
            SinCache,
            _mark_token_layout_dynamic(Q_out),
            num_tokens,
            stream=stream,
        )

    return launch_fused_rope_cache
