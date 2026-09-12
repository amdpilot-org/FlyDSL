# ROCm linker discovery regression

Source issue: https://github.com/ROCm/FlyDSL/issues/946

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/629

## Result

The actual pre-change `gpu-module-to-binary` path was reproduced on the assigned
gfx950 GPU by setting `ROCM_PATH` to a private incomplete ROCm root. Compilation
failed with only `lld invocation failed`.

FlyDSL now discovers and validates the complete MLIR-compatible ROCm toolkit in
this order:

1. `FLYDSL_ROCM_TOOLKIT_PATH`
2. `ROCM_PATH`, `ROCM_ROOT`, then `ROCM_HOME`
3. an `ld.lld` in the required `<root>/llvm/bin` layout on process `PATH`
4. `/opt/rocm`

An explicitly selected root is authoritative: missing linkers, non-executable
linkers, and missing device libraries produce errors naming the source and exact
path instead of silently falling through. The selected toolkit is passed to
both fatbin compilation and diagnostic ISA generation.

## Environment and evidence

- Base: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`
- Python: `/tmp/amdpilot-repo-j-949d244710c6/venv/bin/python`
- FlyDSL source: `/job/repo/python/flydsl/__init__.py`
- Native bindings (unchanged wheel): `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`
- GPU: AMD Instinct MI350X, `gfx950:sramecc+:xnack-`
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`
- HIP: `7.2.26015-fc0010cf6a`
- Real linker: `/opt/rocm/llvm/bin/ld.lld`, resolving to
  `/opt/rocm-7.2.0/lib/llvm/bin/lld`, AMD LLD 22.0.0
- Private fixtures and caches: `/tmp/amdpilot-repo-j-949d244710c6/`
- Complete raw logs: `/tmp/amdpilot-repo-j-949d244710c6/evidence/`
- Compiler dumps: `/tmp/amdpilot-repo-j-949d244710c6/compiler-evidence/vecAddKernel_0/`

The two valid private toolkit roots contained only directories and symlinks to
the real `/opt/rocm` linker and device-library tree. No host path or tool was
modified.

## Reproduction and validation

Pre-change failure:

```sh
ROCM_PATH=/tmp/amdpilot-repo-j-949d244710c6/fixtures/missing-root \
FLYDSL_RUNTIME_CACHE_DIR=/tmp/amdpilot-repo-j-949d244710c6/cache-before \
/tmp/amdpilot-repo-j-949d244710c6/venv/bin/python -m pytest \
  'tests/kernels/test_vec_add.py::test_benchmark_vector_add[4]' -q -s --tb=short
```

This exited 1 in `gpu-module-to-binary` with `lld invocation failed`.

Post-change validation used the same real numerical kernel and independent
Torch expression `a_dev + b_dev` as its reference:

- explicit private `FLYDSL_ROCM_TOOLKIT_PATH`, with a deliberately invalid
  lower-precedence `ROCM_PATH`: exit 0, max error `0.00e+00`;
- valid private `ROCM_PATH`: exit 0, max error `0.00e+00`;
- all root variables unset and the second private toolkit's `llvm/bin` first on
  process `PATH`: exit 0, max error `0.00e+00`;
- missing explicit linker: exit 1 with the exact missing path;
- non-executable explicit linker: exit 1 with the exact non-executable path.

With `FLYDSL_DUMP_IR=1`, the explicit-root run produced the final fatbin MLIR,
LLVM IR, and 4,227-byte ISA. The ISA begins with
`.amdgcn_target "amdgcn-amd-amdhsa-unknown-gfx950"`, defines
`vecAddKernel_0`, and contains `s_endpgm` and AMDHSA kernel metadata. The same
run executed on the GPU and reported max error `0.00e+00`.

The full unit suite result was `1102 passed, 17 skipped` (exit 0). Focused
discovery/backend tests were `6 passed` (exit 0). `git diff --check` passed.
The prepared environment did not contain Ruff, so Ruff checks were not run.

## Limitations

The reported gfx1250/ROCm 6 system was unavailable. Tool-path behavior was
reproduced and fixed in the actual compilation path, while GPU execution and ISA
were validated only on the assigned gfx950 with ROCm 7.2. No C++ code changed,
so the native library was not rebuilt; compilation used the prepared pinned
native library and LLVM. This does not claim gfx1250 execution compatibility.
