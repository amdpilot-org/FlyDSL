# Independent review of PR 554

Upstream issue: https://github.com/ROCm/FlyDSL/issues/400

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/582

Candidate: https://github.com/amdpilot-org/FlyDSL/pull/554 at
`383ee41aaa252f8f081d0b6a860f2c8f051f1cb0`

Recommendation: **request changes**. The candidate is test-only hardening and
does not fully resolve the original issue.

The candidate adds a corrected, executable version of the upstream
single-`scf.if` experiment. Correcting the predicate is valuable: the original
experiment used `warp_id == 0` with a single wave, making the else arm
unreachable. The new block-parity predicate preserves both structurally
different arms, as confirmed by 160 MFMA instructions and 32 `<4 x float>` phi
nodes.

However, this test passes unchanged on the prepared base. Base and candidate
both produce 33 unique MFMA destination groups, 138 VGPRs, and zero spills for
gfx942 code generation and gfx950 code generation. The gfx950 LLVM IR and final
ISA are byte-identical between base and candidate. There is no compiler or
lowering change in the PR, so this is not a fix and not a failing-before /
passing-after regression.

The original contract is materially broader: it reports six branch instances
in the production MLA kernel, 71 unique MFMA destination groups, and 170
spills. The candidate exercises one branch instance without the production
kernel's surrounding register pressure. The current checkout does contain
`kernels/attention/mla_fwd_decode_m16x8_fp8_fp8.py`, but its test could not be
collected because the prepared `aiter` requires Triton 3.6 or newer while the
image contains Triton `3.5.1+rocm7.2.0.gita272dfa8`.

Architecture limitations are also important. The assigned GPU is an AMD
Instinct MI355X (`gfx950:sramecc+:xnack-`), so the numerical result was checked
only on gfx950. gfx942 was cross-compiled and inspected through LLVM IR and
final ISA; it was not executed.

No native rebuild was required because the candidate changes only a Python
test and report files. Python source resolved from `/job/repo/python/flydsl`;
the native MLIR libraries remained the prepared wheel under
`/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs`.

Complete raw evidence is retained outside the checkout in
`/job/review-evidence`, including base and candidate IR/ISA, logs, source
snapshots, native library hashes, and the production-test collection error.
