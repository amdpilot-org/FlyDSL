#!/usr/bin/env python3
"""Minimal kernel launcher for rocprofv3 external profiling."""
import sys, torch, os
sys.path.insert(0, "/workspace/FlyDSL/python")
sys.path.insert(0, "/workspace/FlyDSL")

from tests.kernels.test_fused_rope_cache import MAX_POS, BLOCK_SIZE
from kernels.fused_rope_cache_kernel import build_fused_rope_cache_module

device = torch.device("cuda")
num_tokens, num_q_heads, num_kv_heads, head_dim = 50, 8, 8, 256
torch_dtype = torch.bfloat16
launch_fn = build_fused_rope_cache_module(
    head_dim=head_dim, num_q_heads=num_q_heads, num_kv_heads=num_kv_heads,
    block_size=BLOCK_SIZE, is_neox=True, flash_layout=True, dtype_str="bf16",
    apply_scale=False, reuse_freqs_front_part=True, pos_dtype="i32",
)

torch.manual_seed(42)
q = torch.randn(num_tokens, num_q_heads, head_dim, device=device, dtype=torch_dtype)
k = torch.randn(num_tokens, num_kv_heads, head_dim, device=device, dtype=torch_dtype)
v = torch.randn(num_tokens, num_kv_heads, head_dim, device=device, dtype=torch_dtype)
half_dim = head_dim // 2
cos_cache = torch.randn(MAX_POS, half_dim, device=device, dtype=torch_dtype)
sin_cache = torch.randn(MAX_POS, half_dim, device=device, dtype=torch_dtype)
positions = torch.randint(0, MAX_POS, (num_tokens,), device=device, dtype=torch.int32)
slot_mapping = torch.arange(num_tokens, device=device, dtype=torch.int32)
num_blocks = max(32, (num_tokens + BLOCK_SIZE - 1) // BLOCK_SIZE + 4)
key_cache = torch.zeros(num_blocks, BLOCK_SIZE, num_kv_heads, head_dim, device=device, dtype=torch_dtype)
value_cache = torch.zeros(num_blocks, BLOCK_SIZE, num_kv_heads, head_dim, device=device, dtype=torch_dtype)
q_out = torch.empty_like(q)
k_out = torch.empty_like(k)
k_scale = torch.ones(1, dtype=torch.float32, device=device)
v_scale = torch.ones(1, dtype=torch.float32, device=device)

for _ in range(30):
    launch_fn(q, k, v, positions, cos_cache, sin_cache, slot_mapping,
              key_cache, value_cache, q_out, k_out, num_tokens,
              k_scale, v_scale, stream=torch.cuda.current_stream())
