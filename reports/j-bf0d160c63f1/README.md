# AOT relocation and process-lifetime report

This investigation kept the qualified Torch/ROCm stack fixed and used one assigned MI350X (`gfx950`). It did not post to or modify `ROCm/FlyDSL`.

## Conclusion

The existing FlyDSL 0.2.4 AOT artifact for `examples/01-vectorAdd.py` is relocatable across two job-private cache directories and reloads in fresh Python processes. Both reloads match the independent Torch reference with zero maximum absolute error. The artifact contains no external link libraries, and the missing-artifact run-only diagnostic includes the function, manager key, cache key, cache directory, and existence state.

No runtime fix was duplicated: the observed relocation behavior already works. The delivery adds a regression test for the run-only miss diagnostic and records the evidence in `evidence.json`.

## Reproduction

The installed Aiter source baseline was attempted first and is recorded in `/job/baseline-first.json`. Its native module built in 18.1 seconds, but test collection was blocked because the installed source requires Triton 3.6.0 while the qualified image has Triton 3.5.1. A bounded Torch GPU control passed with maximum absolute error `1.14440917969e-05` and relative error `3.68217208877e-07`.

The real AOT reproduction used mirror tag `v0.2.4` (`145a87651be9b278ea05a701c14b049eecae7db3`), matching the installed native FlyDSL 0.2.4 bindings:

```bash
PYTHONPATH=/tmp/flydsl-overlay-v024-j-bf0d160c63f1-run3 \
LD_LIBRARY_PATH=/opt/venv/lib/python3.12/site-packages/flydsl.libs \
FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-v024-artifact-A-j-bf0d160c63f1-run4 \
FLYDSL_RUNTIME_ENABLE_CACHE=1 \
/opt/venv/bin/python examples/01-vectorAdd.py
```

The same pickle was copied byte-for-byte to a second private cache directory. Each reload used `FLYDSL_RUNTIME_RUN_ONLY=1` in a fresh `/opt/venv/bin/python` process. Both executions passed `torch.allclose` and had maximum absolute error zero. The artifact SHA-256 is `ac3d044a48c892ced6b14366706fb4b2522b2cb1e7c3cc102d70484b1c3ea739`, and its entry symbol is `vector_add`. Process-local engine addresses differ, as expected; symbol identity and artifact hash do not.

The deliberately empty cache control exits 1 with `RuntimeError: FLYDSL_RUNTIME_RUN_ONLY=1 but no usable AOT cache ...`, including the manager key, cache key, cache directory, and `exists=False`.

## Current-main limitation

Current `main` is version 0.3.3 and requests the `convert-rocdl-fastmath-ops` pass, which is absent from the installed 0.2.4 native bindings. Its vector-add compile therefore fails before AOT execution. No MLIR development tree is present, so rebuilding that native pass was not attempted within the bounded job. The current-main run-only miss diagnostic was independently exercised and passes the new unit test.

These results do not claim compiler, ROCm, or native-ABI portability across versions. They apply only to the fixed qualified image and gfx950 stack recorded in `evidence.json`.
