# Consolidated ROCm linker discovery correction

Upstream issue: https://github.com/ROCm/FlyDSL/issues/946

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/648

Candidate parent PR: https://github.com/amdpilot-org/FlyDSL/pull/644

Independent review parent PR: https://github.com/amdpilot-org/FlyDSL/pull/647

Candidate commit: `cace24273ede0742f57b4ef6d716485384721a9b`

Recorded base: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`

## Result

All three review counterexamples were independently reproduced on the exact
candidate before changing code. Valid private toolkit roots containing a double
quote or backslash passed validation and textual pipeline parsing, but real
`gpu-module-to-binary` compilation failed with `lld invocation failed`. A real
`ld.lld` symlink in an arbitrary private PATH bin was found by `shutil.which`
but ignored, and discovery returned `/opt/rocm`.

The quote and backslash failures came from the MLIR pass-option parser retaining
escape sequences literally. The candidate therefore passed a different path to
the serializer. The correction selects a quote delimiter absent from the path,
which preserves double quotes and backslashes exactly. Values containing both
quote types, which the textual option grammar cannot represent without changing
the value, now receive an explicit error rather than a later linker failure.

PATH discovery now checks both an MLIR-layout lexical linker location and the
resolved linker's ancestors, accepting a root only after the candidate's full
linker/device-library validation. This preserves explicit-root precedence and
diagnostics while supporting process-local private-bin symlinks to packaged
ROCm linkers.

## Failing before / passing after

At exact candidate commit `cace24273ede0742f57b4ef6d716485384721a9b`:

- the real vector-add compile using a quote-containing valid private root exited
  1 with `lld invocation failed`;
- the same compile using a backslash-containing valid private root exited 1 with
  `lld invocation failed`;
- the arbitrary private-bin probe printed its private `shutil.which` result but
  returned `toolkit=/opt/rocm`.

After the correction, both special-character roots compiled and ran vector add
on gfx950 with maximum error `0.00e+00` against Torch `a + b`. The arbitrary-bin
probe resolved its toolchain to `/opt/rocm-7.2.0`; a fresh real compilation
through that PATH-only layout also ran with maximum error `0.00e+00` and emitted
a 4,227-byte gfx950 ISA containing `vecAddKernel_0` and `s_endpgm`.

Focused coverage passed 22 tests. The complete unit suite passed 1,109 tests
with 17 skipped. Raw logs are retained in
`/job/evidence-j-bc8e2100a9ba/`, and compiler dumps are retained in
`/tmp/amdpilot-repo-j-bc8e2100a9ba/dump-after-arbitrary/`.

## Environment and limitations

Python sources loaded from `/job/repo/python/flydsl`; the native extension was
the prepared pinned artifact under `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`.
The correction changes Python only, so no native rebuild was required.

GPU validation used one AMD Instinct MI355X (`gfx950`) with Torch
`2.9.1+rocm7.2.0.git7e1940d4` and HIP/ROCm 7.2. The reported gfx1250/ROCm 6
environment was unavailable and remains unverified.
