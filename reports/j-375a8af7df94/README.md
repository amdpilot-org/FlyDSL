# MiniMax-M3 A4W4 MoE qualification

Model metadata was read from `amd/MiniMax-M3-MXFP4` revision
`b83d14e3d64bf373a207f3c2a7e9f0b0f1e7fc3a`: hidden size 6144,
intermediate/shared-intermediate size 3072, 128 routed experts, top-k 4, one
shared expert, sigmoid routing with normalized weights scaled by 2.0, and
SwiGLU-OAI (`alpha=1.702`, `limit=7.0`). Its Quark global configuration uses
dynamic FP4 inputs, static FP4 weights, group size 32, E8M0 scales, even scale
calculation, and half-even rounding.

The existing FlyDSL source already supplied real gfx950 scaled-MFMA A4W4 MoE
stage-1/stage-2 kernels. This change adds the missing model activation as an
opt-in specialization while keeping plain SiLU as the API default. Routed and
shared experts use the same projection kernels; the shared expert is a separate
one-expert invocation whose output is added to the routed result.

The strict numerical gate is a normalized-logit difference of 0.002, alongside
finite-output checks and reported cosine/max-absolute error. This threshold is
tight enough to detect the observed broken variants (0.0084 and 0.994 normalized
error) while the qualified routed-plus-shared model-shape path is at least
0.99999648 cosine.

Raw command output is retained in `raw/`. Compiler cache artifacts remain in
`/tmp/amdpilot-repo-j-375a8af7df94/cache`; their metadata records target
`gfx950` and kernels such as
`gemm1_a4w4_port_fp4_swigluoai_a1.702_l7_h6144_i3072_ne128_bm32_cached_sep`.
No C++ source changed, so rebuilding the native compiler would not validate any
additional code in this patch and was not performed.

This is not full-model generation or distributed expert-parallel qualification.
The packed-A4 path does not accept an EP valid mask, and the pre-existing inline
quantization and BM64 interleaved variants remain unqualified rather than being
silently treated as complete.
