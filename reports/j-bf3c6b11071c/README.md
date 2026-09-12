# gfx950 PA SWA issue 510 investigation

Upstream issue: https://github.com/ROCm/FlyDSL/issues/510

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/481

The exact reported source was recovered from GitHub's immutable commit archives:

- failing revision: `b2e0961da3be4415c09f7cbfad43dedade02f63c`
- fixed revision: `0494957dce75dd5b7c913f73273ea67174562ee3`
- upstream fix: one line in `kernels/pa_decode_swa.py`, changing `_widen_nonnegative_i32_to_i64` from `ExtUIOp` to `ExtSIOp`

The recovered `global_window_accuracy` case preserves the report exactly: FP8 e4m3fn, per-token quantization, transposed V, fixed KV lengths, partition 256, page 1024, heads `(12, 2)`, context 3000, batch 128, query length 4, head size 128, sliding window 1023, and global window 3.

The prepared main checkout at `acf7e67b7d22847e345938ca54fcc137bd7b2a1f` does not contain that test, global-window PA SWA path, or widening helper. The recovered Python code could not be paired honestly with the prepared native library: its `DLTensorAdaptor` API takes three arguments, while the pinned wheel takes one. The prescribed rebuild helper also cannot qualify this historical source because it pins LLVM `7f77ca0dbda4abbf9af06537b2c475f20ccd6007`; the image is qualified for `e2a39f504fee836e4def9581bed817ecc327b9dc`.

Consequently, the outcome is `environment_blocked`. The exact FlyDSL kernel did not launch, and this report makes no claim that the upstream zext failure or sext fix was numerically reproduced here. Raw command output is in `raw/broken-test.log`; the immutable upstream patches are retained in `raw/`.
