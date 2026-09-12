# ROCm toolkit path correction

Upstream issue: https://github.com/ROCm/FlyDSL/issues/946

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/642

Candidate PR: https://github.com/amdpilot-org/FlyDSL/pull/635

Independent review PR: https://github.com/amdpilot-org/FlyDSL/pull/641

## Result

The review counterexample was independently reproduced at candidate commit
`156ec2dd6d4d5e6944e53fe4dab32acc57aec00a`. A valid private ROCm toolkit at
`/tmp/amdpilot-repo-j-70daea8859a4/candidate-space root` passed the candidate's
linker and device-library validation, but the real vector-add compilation failed
while parsing the `gpu-module-to-binary` pass:

```text
ValueError: <Pass-Options-Parser>: no such option root
failed to add `gpu-module-to-binary` with options `format=fatbin opts="" toolkit=/tmp/amdpilot-repo-j-70daea8859a4/candidate-space root`
```

The candidate interpolated the toolkit path as an unquoted textual MLIR pass
option in both fatbin compilation and ISA dumping. The consolidated correction
preserves the candidate's discovery, precedence, and diagnostics, and quotes and
escapes the toolkit value for MLIR pass syntax at both call sites. Regression
coverage checks a space-containing real pipeline and MLIR parsing of spaces,
quotes, and backslashes.

## Validation

- Exact-candidate failure: the vector-add command below exited 1 before the
  correction with the parser diagnostic above. Raw output:
  `/tmp/amdpilot-repo-j-70daea8859a4/evidence/candidate-space-failing.log`.
- Focused tests:
  `/tmp/amdpilot-repo-j-70daea8859a4/venv/bin/python -m pytest tests/unit/test_rocm_toolkit_discovery.py tests/unit/test_external_llvm_codegen.py -q`
  passed 19 tests.
- Corrected real compilation and execution:
  `FLYDSL_ROCM_TOOLKIT_PATH='/tmp/amdpilot-repo-j-70daea8859a4/candidate-space root' FLYDSL_RUNTIME_CACHE_DIR=/tmp/amdpilot-repo-j-70daea8859a4/cache-after-space-v1 FLYDSL_DUMP_IR=1 FLYDSL_DUMP_DIR=/tmp/amdpilot-repo-j-70daea8859a4/dump-after-space-v1 /tmp/amdpilot-repo-j-70daea8859a4/venv/bin/python -m pytest 'tests/kernels/test_vec_add.py::test_benchmark_vector_add[4]' -q -s --tb=short`
  passed on gfx950 with maximum error `0.00e+00` against the test's independent
  Torch `a + b` reference. Raw output:
  `/tmp/amdpilot-repo-j-70daea8859a4/evidence/space-after-passing.log`.
- The same corrected run exercised ISA dumping through the second corrected
  pass string. Its 4,227-byte `21_final_isa.s` contains `.amdgcn_target
  "amdgcn-amd-amdhsa-unknown-gfx950"`, `vecAddKernel_0`, `s_endpgm`, and AMDHSA
  metadata. Dump inventory and markers are retained under
  `/tmp/amdpilot-repo-j-70daea8859a4/evidence/` and the compiler dumps under
  `/tmp/amdpilot-repo-j-70daea8859a4/dump-after-space-v1/`.
- Full unit suite:
  `/tmp/amdpilot-repo-j-70daea8859a4/venv/bin/python -m pytest tests/unit -q`
  passed 1,106 tests with 17 skipped. Raw output:
  `/tmp/amdpilot-repo-j-70daea8859a4/evidence/unit-suite.log`.

The private toolkit used symlinks to the real `/opt/rocm` linker and device
libraries. No host toolchain was modified. Source imports came from
`/job/repo/python/flydsl`; the prepared native extension remained at
`/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`. This correction changes
Python pass-string construction only, so no native rebuild was needed.

## Limitations

The assigned GPU is gfx950 with ROCm 7.2. The originally reported gfx1250 and
ROCm 6 environment is unavailable, so hardware execution and ISA validation on
that architecture/toolkit version remain unverified.
