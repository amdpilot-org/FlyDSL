# FlyDSL native-development environment qualification

Status: **QUALIFIED**

The default repository image was qualified as shipped on one AMD Instinct MI350X (`gfx950`) from base commit `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`. No packages, shims, `.pth` changes, build-helper edits, source fixes, retries, or environment repairs were made.

The exact rebuild command was run once:

`/tmp/amdpilot-repo-j-52acf7d48c3e/venv/bin/python /opt/amdpilot/rebuild-native.py /job`

Results:

- Exactly one `native-build-attempts` result exists; state is `passed`.
- The rebuilt package is `/tmp/amdpilot-repo-j-52acf7d48c3e/native-build/python_packages/flydsl/_mlir`.
- The source import is `/job/repo/python/flydsl/expr/__init__.py` and the post-build native import resolves to the rebuilt package above.
- The documented real-GPU smoke passed: FlyDSL vector-add `100x1000` with predicated border blocks, on AMD Instinct MI350X (`gfx950`), one device.
- `tests/unit/test_typed_arith_ops.py` and `tests/unit/test_arith_ops.py` passed with the recorded interpreter: 53 passed.
- `patchelf` is version 0.17.2 and all recursive submodules remained at their prepared revisions.

Evidence is preserved alongside this report in `evidence.md`, `native-build.log`, `native-build.json`, `native-attempt-result.json`, and `repository-smoke.json`.

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/472

Upstream issue: https://github.com/ROCm/FlyDSL/issues/934
