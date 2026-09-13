# Independent review of PR 698

Reviewed exact candidate `8f8d9aaffdcf57ce573a96609134690f24639f31` against the recorded base `acf7e67b7d22847e345938ca54fcc137bd7b2a1f` and the original MiniMax-M3 A4W4 MoE request.

## Verdict

Recommendation: **accept**. The candidate fully resolves the kernel-level original issue on the supported gfx950 packed-A4/static-W4 path. It adds the MiniMax `swigluoai` activation without changing the legacy SiLU default, retains genuine FP4 activations and FP4 weights with per-32 E8M0 scales, and exposes the selection through the existing host launcher.

The prepared base did not expose an activation selector, had no MiniMax regression, and quarantined the packed A4W4 correctness case without executing it. At the candidate commit, the focused seven-case suite passed, the exact 6144x3072/E128/top-k-4 routed-plus-shared sweep passed at 1/2/4/16/32/256 tokens, and a reviewer-authored adversarial case passed with a non-tile-aligned batch, four duplicate routes, zero and extreme activation blocks, and non-default activation constants.

## Evidence and boundaries

- Hardware: one AMD Instinct MI350X, `gfx950:sramecc+:xnack-`.
- Software: Python from `/tmp/amdpilot-repo-j-a003b400bea7/venv`, Torch `2.9.1+rocm7.2.0.git7e1940d4`, HIP `7.2.26015-fc0010cf6a`.
- Source imports came from `/job/repo/python/flydsl`; native MLIR libraries came from the pinned wheel under `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs`.
- No C++ changed, so no native rebuild was required or performed.
- The exact model-shape run produced cosine `0.99999654..0.99999821`, max absolute error `0.00155360..0.00260985`, and finite outputs.
- The independent adversarial run produced cosine `0.99999702`, max absolute error `0.046875`, mean absolute error `0.00181039`, and finite outputs. The larger pointwise error is consistent with the BF16 final output and block-FP4 requantization; the normalized-logit error printed by the strict shared verifier was `0.000003`, below its `0.002` threshold.

This review does not claim full MiniMax generation, model-weight loading, multi-rank expert parallel dispatch, or a packed-A4 valid-mask/non-local-slot interface. The candidate explicitly leaves inline BF16-to-FP4 quantization and BM64 interleaving unqualified; those are neighboring variants rather than counterexamples to the supported packed-A4 entry point.

Raw commands and output are retained under `raw/`.
