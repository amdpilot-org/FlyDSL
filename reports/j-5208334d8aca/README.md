# Independent review of PR 651

Upstream issue: https://github.com/ROCm/FlyDSL/issues/946

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/653

Candidate: https://github.com/amdpilot-org/FlyDSL/pull/651 at `9b06389868ff475b52fcec0521b5c63ac4d43585`

Recorded base: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`

## Recommendation

Request changes. The candidate is a substantial partial fix, not a full fix for
arbitrary valid alternate ROCm roots.

The exact candidate passed its 11 focused tests and the full unit suite (1,109
passed, 17 skipped). Real `gpu-module-to-binary` compilation and numerical
vector addition passed on gfx950 for private toolkit roots containing a space,
a double quote, or a backslash. It also passed when `ld.lld` was available only
through an arbitrary process-local private-bin symlink whose resolved target
belonged to a complete toolkit. Each GPU run reported maximum error `0.00e+00`
against the independent Torch `a + b` reference and emitted compiler dumps
through final gfx950 ISA.

However, a valid private toolkit root containing both a single quote and a
double quote is rejected before compilation by
`quote_pass_option_value()` with:

```
ValueError: MLIR textual pass options cannot represent a value containing both quote types
```

The root had an executable `llvm/bin/ld.lld` symlink and a valid
`amdgcn/bitcode` symlink, so this is a remaining filesystem-path
counterexample, not a missing-tool diagnostic. The candidate itself adds a
unit test requiring this rejection, but test-only hardening of the error does
not make the alternate root usable. Consequently the original broad contract
of stable compilation across different valid ROCm locations is only partially
resolved.

## Base reproduction and interpretation

The image's `/opt/rocm` resolves to a working `/opt/rocm-7.2.0`, so the original
default-path failure could not be reproduced naturally without changing host
toolchain state, which was out of scope. On the recorded base, setting
`FLYDSL_ROCM_TOOLKIT_PATH` to a valid private root still compiled and ran vector
addition successfully. The base has no alternate-root discovery and its
pipeline contains no toolkit option, so this demonstrates silent use of the
working default `/opt/rocm`; it is not proof that the base supports the
alternate root.

## Source, native code, and environment

- Python sources loaded from `/job/repo/python/flydsl` at both revisions.
- Native MLIR modules loaded from the prepared pinned environment under
  `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir` (recorded in
  `evidence/candidate-import-paths.log`).
- Candidate changes are Python-only, so a native rebuild was not required.
- GPU validation used one AMD Instinct MI355X (`gfx950`) with Torch
  `2.9.1+rocm7.2.0.git7e1940d4` and HIP/ROCm `7.2.26015-fc0010cf6a`.
- The issue's gfx1250/ROCm 6 environment was unavailable. Compatibility and
  execution there remain unverified.

Raw command output and exit codes are retained in `evidence/`. Compiler dumps
were generated outside the checkout under
`/tmp/amdpilot-repo-j-5208334d8aca/dump-*`.
