# AOT module/symbol isolation investigation

## Scope

This report covers upstream issue 621, specifically whether two tiny AOT kernels with distinct arithmetic but compatible signatures can be exported, loaded in one process, alternately launched, and compared against exact references without module, symbol, or code-object aliasing. It deliberately does not cover stream ordering or argument-schema design.

## Environment

- GPU: one AMD Instinct MI350X, `gfx950`, UUID `GPU-5fb42ff90866060e`.
- Image: `amdpilotv2/open-job:gbt350-20260909`, local ID `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.
- Python: `/opt/venv/bin/python`.
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`.
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`.
- Installed FlyDSL: `0.2.4`, Python path `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`, native path `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/_mlir.cpython-312-x86_64-linux-gnu.so`.
- Persistent mirror base: `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.

## Installed-source baseline

The first GPU execution used the preinstalled FlyDSL wheel and the upstream `examples/01-vectorAdd.py` kernel. The command was:

```bash
FLYDSL_CACHE_DIR=/tmp/flydsl-cache-j-0e4562ca5c0b \
FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-0e4562ca5c0b \
/opt/venv/bin/python /tmp/baseline-vector-add.py
```

Results:

- Shape: `100 x 1000`, `float32`.
- Reference: `A + B`.
- Comparison: `torch.allclose(A + B, C)`.
- Result: `PASS`.
- One-shot process wall time: `2699 ms`.
- A second bounded run using `torch.equal(A + B, C)` also passed in `2107 ms`.
- Total GPU runs: `2`; no loops, sleeps, or synthetic burn.

This baseline is installed-source evidence only and is not proof for later checkout changes.

## Candidate

The only relevant upstream export/load candidate found was PR 414, exact head commit `5445af52ab018caf16e1c615a3d6fd71b1579f04`. It adds:

- `dump_to_object`
- `load_module`
- `BinaryKernelModule`
- symbol prefixing for exported LLVM and GPU symbols

The candidate is not present in current `main`.

## Findings

1. Current `main` has no AOT export/load API.
2. PR 414's Python sources are incompatible with the installed native ABI:
   - `DLTensorAdaptor` is called with three arguments, while the installed binding accepts only a DLPack capsule.
   - The candidate also expects an older MLIR pass set.
3. A v0.2.4 control using the installed native stack can compile the two tiny kernels and export distinct ELF objects.
4. Linking those objects into `.so` files and loading them with `ctypes.CDLL` does not execute correctly:
   - the ORC initializer is `GLOBAL HIDDEN`
   - the standard ELF loader does not call it
   - the first launch reaches `hipModuleGetFunction` with an invalid module handle
5. A diagnostic manual call to the hidden ORC initializer showed that the exported modules themselves are isolated:
   - add and multiply function pointers were distinct
   - ELF object SHA-256 hashes were distinct
   - object sizes were both `8760` bytes
   - `nm` showed distinct prefixed host and metadata symbols
6. That manual initializer is not a supported fix. It also exposed an input mutation when using `from_torch_tensor`, and module unload still reported `hipErrorInvalidHandle`.

## Isolation evidence

The diagnostic control produced:

- Add pointer: distinct from multiply pointer.
- Add object SHA-256: `24cf28d94b170976d040bb5c967cc5fc040ba944b5a53464951ac3420f3161b1`.
- Multiply object SHA-256: `2b85ec6fcc911386ed6f887eeb4bb7fd33433d1dd3af222977c0165fea84ccc1`.
- Add symbols included `_mlir_add_iso_add_launch` and `add_iso_add_launch`.
- Multiply symbols included `_mlir_mul_iso_mul_launch` and `mul_iso_mul_launch`.
- No host or metadata symbol names overlapped.

## Conclusion

The bounded investigation did not produce a safe code change. The candidate's symbol-prefixing design is promising, but its `.so` load path is not executable in the qualified stack because the required ORC initializer is hidden and is not invoked by `ctypes.CDLL`. A production fix needs either:

- a loader that invokes the ORC initializer, or
- an export path that emits a standard ELF constructor.

No code change is included in this report-only PR.

## Reproduction outline

1. Use the installed interpreter and wheel to run the vector-add baseline.
2. Fetch PR 414 at `5445af52ab018caf16e1c615a3d6fd71b1579f04`.
3. Overlay its Python sources on a v0.2.4 checkout and the installed `_mlir` native package.
4. Compile two tiny add and multiply kernels with compatible signatures.
5. Export each to a distinct ELF object and link each to a `.so`.
6. Load both `.so` files in one process and inspect `nm`, object hashes, and function pointers.
7. Attempt alternate launches and compare against exact Torch references.

The raw diagnostic output is in `raw-results.json`.
