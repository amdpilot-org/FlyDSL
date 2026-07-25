# Assessment — L1/093 grouped top-k MoE routing backward (AMD gfx950 / MI355X)

## Result

| metric | eager baseline | optimized (graphed) | speedup |
|---|---|---|---|
| avg kernel_ms (16 shapes) | 0.1225 | **0.0481** | 2.55x |
| correctness (max_abs_diff) | — | **0.0** (bit-identical) | < 1e-2 ✓ |
| win rate (< 0.9x eager) | — | **16/16 = 100%** | ≥ 80% ✓ |

Both acceptance gates pass: correctness max_abs_diff = 0.0 < 1e-2 on every
shape, and kernel_ms < 0.9x eager on 100% of shapes (gate requires ≥ 80%).

## Shape-by-shape win/tie/loss

All 16 workload shapes **WIN** (0 ties, 0 losses). Speedup scales inversely
with N because launch overhead (eliminated by the CUDA graph + Triton fusion)
dominates at small N, while the parity-locked `aten::mm` GEMMs dominate at
large N.

**Tier 1 — launch-bound (3.2–3.3x):** N=1376 (3.29x), N=1312 (3.28x),
N=1321 (3.23x), N=1344 (3.18x). Smallest shapes; fusion + graph capture
removes ~6 elementwise launches and collapses the remaining 3-kernel sequence
into one replay.

**Tier 2 — mixed (2.3–3.0x):** N=1280 (2.93x), N=2521 (2.83x), N=1721 (2.81x),
N=2131 (2.75x), N=1440 (2.73x), N=3072 (2.63x), N=1408 (2.58x), N=2048 (2.31x),
N=3557 (2.34x). GEMM share grows but fusion still pays.

**Tier 3 — GEMM-bound (1.6–2.2x):** N=6144 (2.19x), N=3011 (2.05x),
N=8192 (1.61x). Largest shapes; the two `[N,160]x[160,5120]` and
`[160,N]x[N,5120]` matmuls are ~87% of GPU time and parity-locked to bf16 ULP,
so the floor is `aten::mm`.

## Bottleneck

Remaining cost is the two linear-projection GEMMs (step 5), kept as
`aten::matmul` for parity. Every alternative (aiter, Triton split-K, CK) either
crashed on K=160 or broke the 1e-2 tolerance. Steps 1–4 are fused into one
Triton kernel; no further parity-safe GEMM lever remains.
