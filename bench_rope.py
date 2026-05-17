#!/usr/bin/env python3
"""Benchmark entrypoint for fused RoPE kernel — pi0 diffusion attention shapes.

Outputs ``iters_per_second: <value>`` for the orchestrator.
"""
import sys
import os
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tests.kernels.test_fused_rope_cache import _bench_gpu_us, MAX_POS, BLOCK_SIZE
from kernels.fused_rope_cache_kernel import build_fused_rope_cache_module

# pi0 production shape from issue #2
def benchmark(
    num_tokens=50,
    num_q_heads=8,
    num_kv_heads=8,
    head_dim=256,
    flash_layout=True,
    dtype_str="bf16",
    warmup=20,
    iters=200,
):
    device = torch.device("cuda")
    torch_dtype = torch.bfloat16 if dtype_str == "bf16" else torch.float16

    # Build kernel (with KV cache writes — current production code)
    launch_fn = build_fused_rope_cache_module(
        head_dim=head_dim,
        num_q_heads=num_q_heads,
        num_kv_heads=num_kv_heads,
        block_size=BLOCK_SIZE,
        is_neox=True,
        flash_layout=flash_layout,
        dtype_str=dtype_str,
        apply_scale=False,
        reuse_freqs_front_part=True,
        pos_dtype="i32",
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

    def _run():
        launch_fn(
            q, k, v,
            positions, cos_cache, sin_cache,
            slot_mapping,
            key_cache, value_cache,
            q_out, k_out,
            num_tokens,
            k_scale, v_scale,
            stream=torch.cuda.current_stream(),
        )

    # Measure
    for _ in range(warmup):
        _run()
    torch.cuda.synchronize()
    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    start.record()
    for _ in range(iters):
        _run()
    end.record()
    torch.cuda.synchronize()
    elapsed_ms = start.elapsed_time(end)
    us_per_call = elapsed_ms * 1e3 / iters
    iters_per_second = iters / (elapsed_ms * 1e-3)

    print(f"num_tokens={num_tokens} num_q_heads={num_q_heads} head_dim={head_dim}")
    print(f"us_per_call: {us_per_call:.2f}")
    print(f"iters_per_second: {iters_per_second:.2f}")
    return iters_per_second

if __name__ == "__main__":
    # Default: pi0 action-expert shape (T=50)
    benchmark()
