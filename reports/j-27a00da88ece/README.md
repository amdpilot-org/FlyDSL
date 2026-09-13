# MiniMax-M3 inline A4W4 follow-up

Upstream issue: https://github.com/ROCm/FlyDSL/issues/717

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/701

This follow-up starts from PR698 commit
`8f8d9aaffdcf57ce573a96609134690f24639f31`.  The reported BM16 inline
failure reproduced on an MI350X/gfx950: normalized output error was
`0.007878099790699977` at the unchanged `0.002` gate.  The first mismatch was
not in the on-device nibble packing or scale-consumer layout: the kernel
quantizes a BF16 `hidden_states` input, while the test reference quantized the
pre-cast FP32 generator tensor.  Re-quantizing the exact BF16 values consumed
by the kernel reduced the same deterministic regression to `0.001035` and it
passed without changing tolerances or kernel source.

`probe_inline_quant.py` is the standalone reproduction/attribution probe.  It
records raw packed bytes, E8M0 bytes, and independently dequantized FP32 values
for exact values, ties, signed zero, a zero block, extreme dynamic range, and
padding.  It then launches the actual BM16 inline fused MoE kernel.  The exact
production-shape tests cover tokens 1/2/4/16/32/256, hidden 6144,
intermediate 3072, 128 routed experts, top-k 4, and a separate one-expert
shared projection for both SiLU and SwiGLU-OAI.  Output references start from
BF16, independently quantize/dequantize MXFP4 in Torch, and perform FP32
reference projection math.

The executed stage-1 dispatch is BM16 inline BF16-to-FP4 (`inline_quant=True`,
`use_nt=True`); the preserved candidate path is BM32 packed A4.  Raw logs name
these dispatches.  The BM64 interleaved variant remains xfailed and is not
claimed.  This is one-GPU kernel validation only: no full-model inference,
multi-rank EP, serving integration, or automatic AITER/SGLang adoption is
claimed.  The packed path still has no EP valid mask.

No C++ changed, so no native rebuild was required.  The run used the source at
`/job/repo`, Python `/tmp/amdpilot-repo-j-27a00da88ece/venv/bin/python`, and
the pinned native package under
`/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`.  Device/compiler details
and the initially observed private cache variables are retained under `raw/`.
