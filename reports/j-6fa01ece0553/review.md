# Independent review of PR 494 for MXFP6 A support

- Upstream issue: https://github.com/ROCm/FlyDSL/issues/767
- Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/520
- Prepared base: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`
- Candidate reviewed: `9bf7434049ef10ebc0329f1f3567b961aee73f0b`
- Hardware: one AMD Instinct MI355X (`gfx950`), ROCm 7.2, Torch `2.9.1+rocm7.2.0.git7e1940d4`

## Recommendation

The original missing-support problem is **not reproducible on the prepared base**. The base already implements `a_dtype="fp6"` in `kernels/gemm/mxfp4_preshuffle.py`, and its existing A6W4 GPU regression passed all 10 parameterized cases. The candidate does not restore kernel functionality or alter production code; it makes the existing test oracle more independent by decoding packed MXFP6/MXFP4 and E8M0 locally.

The candidate change is sound and useful as test hardening, but it should not be described as the fix for the original issue. I recommend accepting it only with that scope understood. Relative to this base, the appropriate issue outcome is `not_reproduced`, not `fixed`.

## Evidence

All commands used `/tmp/amdpilot-repo-j-6fa01ece0553/venv/bin/python`. Python sources resolved to `/job/repo/python/flydsl/__init__.py` and `/job/repo/kernels/gemm/mxfp4_preshuffle.py`. Native MLIR libraries remained the pinned wheel under `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`; no native rebuild was required because the candidate changes only a Python test and report artifacts.

1. Base regression:

   `python -m pytest tests/kernels/test_preshuffle_gemm.py -k 'a6w4' -vv -s`

   Result: exit 0, 10 passed and 160 deselected on gfx950. This includes bf16/fp16 outputs, M=32 through 1024, K=8192 and K=14336.

2. Exact candidate regression, after detached checkout of `9bf7434049ef10ebc0329f1f3567b961aee73f0b`:

   `python -m pytest tests/kernels/test_preshuffle_gemm.py -k 'a6w4' -vv -s`

   Result: exit 0, 10 passed and 160 deselected. The candidate's independent local decoder therefore agrees with real GPU output for every existing A6W4 case without changing the `rtol=0.1, atol=0.1` tolerances.

3. Adversarial decode check:

   A standalone script packed all 64 E2M3 codes into the kernel's 24-data-byte plus 8-padding-byte layout, decoded them with the candidate helper, compared against a direct mathematical E2M3 definition, and then changed every padding byte to `0xff`.

   Result: exit 0; all 64 codes were exact (`max_abs=0.0`) and padding changes did not affect decoded values.

4. Adversarial GPU row boundaries:

   Direct calls to `test_mfma_a6w4_preshuffle` used N=128, K=256 and M values 1, 31, 32, and 33, for both bf16 and fp16 output, with tile M selected as 32 or 64.

   Result: exit 0; all 8 GPU cases passed. This exercises the first row, immediately below/at a 32-row boundary, and immediately above it. A seeded M=33 bf16 measurement reported max absolute error 0.125, max relative error 0.0038910506, and mean absolute error 0.0173192 against the independent decoded FP32 matmul reference; the original tolerance was unchanged.

5. Fresh compiler/ISA evidence:

   `FLYDSL_DUMP_IR=1 FLYDSL_DUMP_DIR=/job/review-evidence/candidate/isa FLYDSL_RUNTIME_ENABLE_CACHE=0 python <focused A6W4 runner>`

   Result: exit 0 and a real GPU pass. `21_final_isa.s` targets `amdgcn-amd-amdhsa-unknown-gfx950` and contains `v_mfma_scale_f32_16x16x128_f8f6f4` instructions, confirming the compiled path uses the scaled f8/f6/f4 MFMA instruction family.

Raw output produced during review is retained under `/job/review-evidence/{base,candidate,meta}`. Selected copies are included beside this report under `raw/`.

## Limitations

Only the assigned MI355X/gfx950 architecture was verified. No other architecture was claimed by the issue or exercised. The candidate's local reference still shares the quantizers and scale/weight shufflers with the kernel setup; the value decoding itself is independent and was exhaustively checked. The original historical failure immediately after upstream change `f5c50f45334cba1136c6c47598b336898d228678` was not reconstructed because the prepared review base is much newer and already contains restored MXFP6-A support.
