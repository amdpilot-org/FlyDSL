# Independent review of PR 635

Upstream issue: https://github.com/ROCm/FlyDSL/issues/946

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/638

Candidate reviewed: https://github.com/amdpilot-org/FlyDSL/pull/635 at exact
commit `156ec2dd6d4d5e6944e53fe4dab32acc57aec00a`.

## Recommendation

`request_changes`. The candidate is a substantive partial fix, not test-only
hardening: ordinary alternate roots and an MLIR-layout `ld.lld` on process-local
`PATH` reach the real `gpu-module-to-binary` pass, and the resulting kernel runs
correctly. However, the toolkit path is interpolated into an MLIR textual pass
pipeline without quoting or escaping. A valid private toolkit whose root was
`.../path-space root` passed all candidate validation and then failed in the
actual compiler with:

```text
ValueError: <Pass-Options-Parser>: no such option root
failed to add `gpu-module-to-binary` with options `format=fatbin opts="" toolkit=/tmp/.../path-space root`
```

This is directly within the issue's alternate-ROCm-root contract. The same
unescaped interpolation occurs in both fatbin compilation and ISA dumping.

## Evidence

The recorded base `acf7e67b7d22847e345938ca54fcc137bd7b2a1f` was checked out
first. With `ROCM_PATH` set to a private incomplete root, the vector-add test
failed in the real binary pass with the original opaque `lld invocation failed`.

At the exact candidate commit:

- source imports resolved to `/job/repo/python/flydsl/`;
- native MLIR imports resolved through `/job/repo/python/flydsl/_mlir/` to the
  prepared pinned native extension;
- no C++ changed, so no native rebuild was necessary or performed;
- an explicit valid private root, with an invalid lower-precedence `ROCM_PATH`,
  compiled and ran vector add on gfx950 with maximum error `0.00e+00` against
  the independent Torch `a + b` reference;
- process-local `PATH` discovery also compiled and ran the same numerical test;
- missing and non-executable explicit linkers failed early with the precise
  variable and path;
- IR dumping produced a 4,227-byte gfx950 ISA file containing
  `.amdgcn_target`, `vecAddKernel_0`, `s_endpgm`, and AMDHSA metadata;
- the complete unit suite passed: 1102 passed, 17 skipped.

Fixtures used private directories and symlinks to `/opt/rocm` tools and device
libraries. No host or system toolchain was modified. Raw logs are retained at
`/tmp/amdpilot-repo-j-5a4b570b26e5/review-evidence/`; compiler dumps are at
`/tmp/amdpilot-repo-j-5a4b570b26e5/review-dump/`.

## Limitations

The assigned GPU is an AMD Instinct MI350X with
`gfx950:sramecc+:xnack-`, using Torch 2.9.1 / ROCm 7.2. The reported gfx1250
hardware and ROCm 6 environment are unavailable, so execution and ISA behavior
there remain unverified. This review establishes the base failure, normal-path
improvement, diagnostics, precedence, and the pathname counterexample on the
available architecture; it does not claim gfx1250 compatibility.
