# RoPE for non-AR diffusion attention: pi0 LIBERO inference is RoPE-bound at 20% of GPU time, but the existing `fused_rope_cache_kernel` doesn't fit (no KV cache, head_dim=256, B=1)

## tl;dr

Profiling production inference for the [openpi `pi0` model](https://github.com/Physical-Intelligence/openpi) on the LIBERO task (single MI300X, ROCm 7.2, PyTorch 2.11+rocm7.2, `torch.compile` `max-autotune` + CUDAGraphs) shows that **a fused-RoPE Triton kernel is the #1 hotspot at 20.4 % of total GPU time** (76.3 ms / 374.5 ms over 10 timed inferences). 

This is a Gemma-family transformer used inside a flow-matching diffusion head — the attention block runs **once per denoise step** (10×) per inference, with **no autoregressive KV cache** because every denoise iteration recomputes Q/K/V from fresh action embeddings.

FlyDSL ships [`kernels/fused_rope_cache_kernel.py`](https://github.com/amdpilot-org/FlyDSL/blob/main/kernels/fused_rope_cache_kernel.py), but reading it shows two reasons it can't be a drop-in for pi0:

1. The kernel is **fused RoPE + KV cache update** (writes into paged `KeyCache` / `ValueCache`). pi0's denoise path does **not** have a paged KV cache — every step recomputes K and V.
2. The kernel asserts `head_dim ∈ {64, 96, 128}` paths in the wave-mapping comments. **pi0 uses `head_dim = 256`** (Gemma 2B + Gemma-300M action expert). I don't see a `D=256` path tested.

So the asks here are:
1. Confirm whether `fused_rope_cache_kernel` works at `head_dim=256`, batched-prefill, no-KV-cache (or document the unsupported config).
2. Either generalize that kernel to a "**plain fused RoPE**" mode (no cache writes), or add a small sibling kernel `kernels/fused_rope_kernel.py` that handles the diffusion-style use case.
3. Add the pi0 production shapes below to whatever benchmark suite tracks RoPE on MI300.

This is a real, instrumented motivating workload — happy to chase the openpi-side integration once the kernel exists.

---

## Production trace evidence

```
Model    : pi0 — paligemma 2B prefix encoder + gemma 300M action expert (bf16)
Hardware : MI300X (gfx942), ROCm 7.2
Backend  : PyTorch 2.11.0+rocm7.2, torch.compile(mode="max-autotune"),
           TunableOp on, CUDAGraphs on, hipBLASLt
Bench    : openpi benchmark_pi0_libero_rocm.py — 3 warmup + 20 timed
Real wall: ~50 ms / inf  ≈ 20 inf/s
Trace    : torch.profiler over 10 timed inferences,
           total GPU time = 374.5 ms, GPU utilization 11.9 %
```

Top kernels by self-CUDA time (full top-25 + raw trace JSON available on request):

| %GPU      | total       | calls | avg        | what it is                                                                          |
|----------:|------------:|------:|-----------:|-------------------------------------------------------------------------------------|
| **20.4 %** | **76.34 ms** | **1800**  | **42.4 µs** | **`triton_poi_fused__..._add_bmm_cat_cos_mul_neg_sin_slice_transpose_..._15`** ← this is RoPE |
| 10.6 %    | 39.79 ms    | 5400  |  7.4 µs    | `Cijk_Alik_Bljk MT16x16x512` (hipBLASLt small-K GEMM, attention proj)              |
| 10.5 %    | 39.26 ms    | 3834  | 10.2 µs    | `Cijk_Alik_Bljk MT32x32x256` (hipBLASLt)                                            |
|  3.0 %    | 11.06 ms    | 1836  |  6.0 µs    | second variant of the same RoPE pattern (`..._16`) — prefix RoPE                    |
|  2.6 %    |  9.91 ms    | 1800  |  5.5 µs    | `triton_per_fused__softmax__..._online`  (online softmax)                           |
|  2.6 %    |  9.81 ms    | 1800  |  5.5 µs    | `triton_per_fused..._mean_mm_mul_pow_rsqrt_view_21`  (RMSNorm)                       |
|  2.0 %    |  7.37 ms    |  486  | 15.2 µs    | `triton_poi_fused__scaled_dot_product_flash_attention_addmm_clone_transpose_view_4` |

**Sanity check that #1 really is RoPE:** the fused kernel name `..._cos_mul_neg_sin_slice_transpose_unsqueeze_view` is the textbook NeoX-style rotation (`x_rot = cat([-x[..., d/2:], x[..., :d/2]]); out = x*cos + x_rot*sin`). Inductor fused that into a single pointwise kernel along with the surrounding `bmm_cat_slice_transpose_unsqueeze_view`. Per-call duration 42 µs at this small shape (B=1, S=50, H=8, D=256) is heavy and consistent with the kernel being bandwidth-bound — every element touches `cos`/`sin` tables and rewrites two halves.

## What pi0's RoPE looks like (the shape FlyDSL would have to handle)

Inside the **action expert (Gemma-300M)** during one denoise step:

| param                    | value          | source                                              |
|--------------------------|----------------|-----------------------------------------------------|
| dtype                    | `bfloat16`     | `Pi0Config.dtype = "bfloat16"`                     |
| `batch_size`             | 1              | benchmark uses single-sample inference             |
| `seq_len_q` (Q)          | 50             | `action_horizon = 50`                              |
| `seq_len_kv` (K, V)      | ~1100          | image tokens (~1024) + text (≤48) + suffix (50)    |
| `num_heads`              | 8              | Gemma-300M / 2B head count                         |
| `head_dim`               | **256**        | Gemma's `head_dim` (NOT 64/128)                    |
| `position_ids`           | int64, shape `[B, S]` |                                                  |
| `cos`/`sin` table dtype  | float32        | recomputed each forward                            |
| `theta`                  | 10000.0        | Gemma default                                      |
| **KV cache**             | **none**        | denoise recomputes K/V each step — no paging      |
| variant                  | NeoX-style rotation, full rotary (rotary_dim = head_dim) |                              |

Per inference the kernel fires:
- 1× through paligemma-2B prefix forward (image+text encoder),
- 10× through gemma-300M action expert (one denoise step, 18 layers).

So 18 layers × 10 denoise = **180 RoPE calls per inference per token slice**, matches the trace's 1800 calls / 10 inf.

## Why the existing `fused_rope_cache_kernel` doesn't apply (yet)

I read [`kernels/fused_rope_cache_kernel.py`](https://github.com/amdpilot-org/FlyDSL/blob/main/kernels/fused_rope_cache_kernel.py) at HEAD. The two structural mismatches:

1. **It always writes `KeyCache` / `ValueCache`** — the kernel is built around paged-KV decoding (`flash_layout=True/False`, `block_size`, `num_blocks`, `slot_mapping`). pi0 has no cache; we'd be writing to scratch every step. Either a `cache_op="none"` mode, or a sibling builder, would let it work here.
2. **Width-of-thread-vector mapping** is encoded with comments for `D ∈ {64, 96, 128}` and `VEC_WIDTH = ceil(D / WARP_SIZE)`. For `D=256` on CDNA (`WARP_SIZE=64`), `VEC_WIDTH = ceil(256/64) = 4`, so `vecs_per_head = 64`, `vecs_per_half = 32` — those should be valid in principle, but I don't see a `D=256` test case in `tests/kernels/test_fused_rope_cache.py`. Worth confirming the config compiles and is correct.

Also: pi0 passes Q and K with shape `[B, H, S, D]` (HF Gemma convention), not `[T, QH, D]`. That's a small adapter — easy to add — but should be in scope.

## Reproducer

```bash
# 1. base image (rocm/sgl-dev with PyTorch 2.11+rocm7.2)
docker run -d --name pi0_repro --device /dev/kfd --device /dev/dri \
  --group-add video --group-add 109 --shm-size 128g \
  rocm/sgl-dev:v0.5.10rc0-rocm720-mi30x-20260420 sleep infinity

# 2. install openpi
docker exec pi0_repro bash -c '
  cd /workspace && \
  git clone https://github.com/Physical-Intelligence/openpi.git && \
  cd openpi && uv sync && \
  uv pip install --python .venv/bin/python --no-cache-dir --force-reinstall \
    --index-url https://download.pytorch.org/whl/rocm7.2 torch
'

# 3. pi0_libero checkpoint at /root/.cache/openpi/openpi-assets/checkpoints/pi0_libero_pytorch
#    (run examples/convert_jax_model_to_pytorch.py once, ~10 min on a fast disk)

# 4. canonical bench (3 warmup + 20 timed)
docker exec pi0_repro bash -c '
  cd /workspace/openpi && .venv/bin/python benchmark_pi0_libero_rocm.py \
    --config pi0_libero --device cuda:0 --num-warmup 3 --num-runs 20
'

# 5. full torch.profiler trace
docker exec pi0_repro bash -c '
  cd /workspace/openpi && .venv/bin/python run_profile.py
'
# → /workspace/traces/torch_profile.json
```

Expected output: `Throughput : 17.7 inferences/sec` on a clean MI300X. The trace will have the kernel mix above; the RoPE kernel is identifiable by the substring `cos_mul_neg_sin` in `traceEvents[].name`.

## Specific asks (in priority order)

### 1. Add a "plain fused RoPE" path (no KV cache writes)

A new builder:

```python
def build_fused_rope_module(
    head_dim: int,                  # 256 for our case
    num_q_heads: int = 8,
    num_kv_heads: int = 8,           # MHA, not GQA
    is_neox: bool = True,
    dtype_str: str = "bf16",
    rotary_dim: int = -1,            # full rotary
    reuse_freqs_front_part: bool = True,
):
    """Apply RoPE to Q and K in-place / out-of-place, no cache writes.

    Inputs (HF Gemma layout):
      Q: [B, H_q, S, D]
      K: [B, H_kv, S, D]
      cos, sin: [B, S, D] or [B, S, D//2] if reuse_freqs_front_part

    Returns:
      Q_out, K_out (same shape, same dtype)
    """
```

Same body as `fused_rope_cache_kernel` minus the `KeyCache`/`ValueCache` stores and minus the `slot_mapping` indirection. **>80 % of the existing kernel can be reused.**

### 2. Add the pi0 shapes to `tests/kernels/test_fused_rope_cache.py` (or a new `test_fused_rope.py`)

Concretely: a parametrised test case with `(B=1, H=8, S=50, D=256, dtype=bf16)` and `(B=1, H=8, S=1100, D=256, dtype=bf16)`, comparing against a reference Gemma `apply_rotary_pos_emb` call. Use `tests/kernels/conftest.py`'s existing tolerances.

### 3. Benchmark entry

In `tests/kernels/bench_preshuffle_gemm_v2.py`-style harness: a row showing FlyDSL kernel us/call vs the inductor-fused 42 µs, at the two pi0 shapes. Even one ballpark number ("FlyDSL is 8× faster at D=256, B=1, S=50") would be enough for downstream projects (openpi, sglang, vLLM-with-Gemma) to plan integration.

### 4. (Optional, lower priority) HF integration shim

A small `flydsl.adapters.gemma_rope.apply_rotary_pos_emb_flydsl(q, k, cos, sin, position_ids, unsqueeze_dim=1)` that exactly matches HF's signature, so a model file can replace `from transformers...modeling_gemma import apply_rotary_pos_emb` with a one-line import swap.

## Why this matters beyond pi0

The same fused-RoPE pattern is the top hotspot in **any** Gemma-family model running through `torch.compile` on ROCm — pi0 just happens to be a clean, small, fully-instrumented reproducer. Other workloads that would benefit:

- Any HF `Gemma*Model` / `PaliGemma` running with `_attn_implementation = "eager"` on MI300 (the SDPA fallback path)
- Diffusion / flow-matching action heads in robotics models (RT-X family, OpenVLA, pi0)
- Encoder-only Gemma fine-tunes (no AR cache)

## References

* openpi pi0_libero benchmark (canonical): https://github.com/Physical-Intelligence/openpi/blob/main/benchmark_pi0_libero_rocm.py
* Trace analysis writeup with full top-25 kernels: I can attach `READ_ME_FIRST.md` and `torch_profile.json` (25 MB) on request
* HF Gemma RoPE reference: `transformers/models/gemma/modeling_gemma.py:apply_rotary_pos_emb`
* ROCm aiter triton RoPE for comparison: `aiter/ops/triton/rope/rope.py`

cc the FlyDSL kernel maintainers — happy to test patches as they land and chase the pi0 integration once the kernel signature is stable.
