# Independent review of PR 702

Upstream issue: https://github.com/ROCm/FlyDSL/issues/717

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/703

Candidate: https://github.com/amdpilot-org/FlyDSL/pull/702 at
`bec00d1619c7e2cc818f23526157315efca2885d`.

Recommendation: **accept**. The candidate fully resolves the original issue within
its approved one-GPU kernel scope. The historical inline-BM16 failure reproduced
on the recorded base at normalized logits difference `0.007878099790699977`
(threshold `0.002`, max absolute difference `0.117442`). The same kernel probe at
the exact candidate passed at `0.001035` without relaxed tolerances.

The candidate correctly attributes the first mismatch to the test reference:
the kernel consumes BF16 `hidden_states`, but the old reference quantized the
pre-cast FP32 generator tensor. The repair quantizes the BF16 values actually
consumed by the kernel. Kernel quantization and packing code did not change.
Exact values, ties, signed zero, zero blocks, padding, and extreme dynamic range
had identical packed bytes and E8M0 bytes in the FP32/BF16 reference comparison;
raw bytes and independently dequantized FP32 values are in the probe logs.

Real MI350X/gfx950 execution passed the candidate's six-token routed-plus-shared
SwiGLU-OAI regression and all production-shape packed-SwiGLU, inline-SiLU, and
inline-SwiGLU cases at tokens 1/2/4/16/32/256, hidden 6144, intermediate 3072,
128 routed experts, top-k 4, and a separate one-expert shared projection. Logs
identify the actual `packed-bm32` and `inline-bm16` dispatches. An independent
review driver additionally sent zero blocks, signed/exact values, extreme
dynamic range, duplicate routes, and nonuniform route weights through the real
inline kernel for both activations and all six token counts; all strict checks
passed.

This is a full original-issue fix, not merely an unrelated smoke. It combines
the already-qualified packed A4/static W4 path with the newly verified inline
BF16-to-A4 path and opt-in MiniMax SwiGLU-OAI activation. BM64 interleaved,
FP8 activation, full-model inference, multi-rank EP, serving integration, and
automatic AITER/SGLang adoption remain explicitly outside the approved contract.
The packed path also still lacks an EP valid mask. No counterexample remains
within the original approved scope.

The source import was `/job/repo/python/flydsl/__init__.py`; native libraries
came from `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs`.
No C++ changed, so rebuilding native code would not validate additional candidate
code and was not performed. The device was one AMD Instinct MI350X (`gfx950`),
Torch `2.9.1+rocm7.2.0.git7e1940d4`, HIP `7.2.26015-fc0010cf6a`, and ROCm clang
`22.0.0git` from ROCm 7.2. NUMA balancing was enabled and warned about, but no
observed test failed or became unstable because of it. Direct `gh issue view` of
the upstream ROCm repository was denied by the mirror credential policy; the
provided issue snapshot was therefore used, while candidate and mirror issue
metadata were retained directly.

