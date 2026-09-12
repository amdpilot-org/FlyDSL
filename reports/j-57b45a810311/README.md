# FlyDSL platform qualification: j-57b45a810311

This report qualifies the prepared FlyDSL source checkout at
`acf7e67b7d22847e345938ca54fcc137bd7b2a1f` on the assigned GPU. It is a
platform qualification report, not a claim that a FlyDSL issue has been fixed.

## Initial evidence

- Prepared source: `/job/repo` on branch `amdpilot/j-57b45a810311`, based on
  `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`.
- Prepared interpreter:
  `/tmp/amdpilot-repo-j-57b45a810311/venv/bin/python`.
- Assigned GPU: `AMD Instinct MI355X` (one visible device).
- Initial PyTorch GPU smoke: PASS. Squaring `torch.arange(16)` on the GPU and
  reducing it produced the expected sum `1240.0`.
- Runtime: PyTorch `2.9.1+rocm7.2.0.git7e1940d4`, HIP
  `7.2.26015-fc0010cf6a`.
- Native rebuild and focused unit qualification: PASS (details below).

Platform context:

- https://github.com/amdpilot-org/amdpilotv2/pull/410
- https://github.com/amdpilot-org/amdpilotv2/pull/435

## Native rebuild evidence

Command:

```text
/tmp/amdpilot-repo-j-57b45a810311/venv/bin/python /opt/amdpilot/rebuild-native.py /job
```

The command exited `0` and completed the native build in `48.3654s`. Its real
numerical GPU smoke passed in `1.2209s`: FlyDSL `vector_add 100x1000`
(including predicated border blocks) on `AMD Instinct MI355X`, architecture
`gfx950`. The build used LLVM hash `e2a39f504fee836e4def9581bed817ecc327b9dc`
and the `amd-minimal` profile with 32 parallel jobs.

The prepared source package imported from `/job/repo/python/flydsl`. The active
native package symlink after rebuilding was `/job/repo/python/flydsl/_mlir`,
targeting
`/tmp/amdpilot-repo-j-57b45a810311/native-build/python_packages/flydsl/_mlir`.
The originally prepared wheel-native path was
`/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`; it was not used for the
post-rebuild qualification.

## Unit suite evidence

Command, run once after the native rebuild:

```text
/tmp/amdpilot-repo-j-57b45a810311/venv/bin/python -m pytest tests/unit
```

Result: exit code `0`; `1112` items collected plus `3` collection-time skips;
`1098 passed`, `17 skipped`, and `2 warnings` in `7.23s`. The two warnings were
expected annotation warnings from `test_kernel_dynamic_smem_types.py`.

## Scope and limitations

This validates that the prepared full toolchain can rebuild FlyDSL's native
extension, execute the rebuild script's real numerical GPU smoke, and pass the
prepared focused unit suite. No new Torch/ROCm stack was installed, no GPU was
reset, and no host state was intentionally modified. Broader integration,
performance, multi-GPU, and upstream CI qualification were not run. Platform
receipt delivery is exercised independently and is not inferred from these
results.
