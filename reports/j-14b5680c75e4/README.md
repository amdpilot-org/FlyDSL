# JIT source-change invalidation report

This job investigated the source-change invalidation aspect of ROCm/FlyDSL issue 862. The issue is about FlyDSL JIT compile time, has no comments, and merged pull request 964 already addresses build-time defaults. That fix was not duplicated.

The added regression test creates two job-private source revisions with the same `vector_add` call signature. One computes `C = A + B`; the other computes `C = A + 2 * B`. Each revision is launched fresh and then warm on one assigned MI350X (`gfx950`). Both outputs are compared bit-for-bit with independent PyTorch references. The test also requires distinct source hashes, JIT manager keys, cache directories, and cache artifact hashes.

The image's installed FlyDSL 0.2.4 stack executed the real GPU control successfully. The current checkout's Python 0.3.3 source could not execute its full GPU pipeline with the image's 0.2.4 native MLIR libraries because `convert-rocdl-fastmath-ops` was not registered. No MLIR install was available for a bounded rebuild. Current-checkout manager-key generation was therefore validated separately without compilation, and its distinct keys are recorded in `result.json`.

All caches were kept under `/tmp/flydsl-cache-j-14b5680c75e4`; no shared cache was edited.
