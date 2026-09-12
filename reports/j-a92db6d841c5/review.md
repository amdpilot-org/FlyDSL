# Independent review of candidate PR 508

Upstream issue: https://github.com/ROCm/FlyDSL/issues/583

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/523

Candidate: https://github.com/amdpilot-org/FlyDSL/pull/508 at exact head
`c2a301580864ac6235af57156f4b22d61ed29edb`.

Prepared base: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`.

## Recommendation

Do not accept the candidate as a complete fix for the original issue. It fixes
a useful subset: its regression converts the reproduced composition assertion
and several other selected invalid cases into diagnostics. However, its new
composition predicate is incomplete at static boundaries that are directly in
scope for the issue.

In particular, the candidate checks each inner layout mode independently. It
therefore accepts `!fly.layout<(2,2):(4,4)>` composed with an outer domain of
size 8 even though the combined maximum coordinate is `4 + 4 = 8`, outside the
outer domain `[0, 8)`. It also returns early without checking composition when
the inner operand is a `TileType`; `!fly.tile<[9:1]>` composed with an outer
domain of size 8 is accepted. Both cases were run against the rebuilt candidate
native compiler and exited successfully, retaining invalid operations.

The result is **subset fixed** rather than fully fixed. The candidate also only
adds checks for four operations, while the source report describes the wider
absence of layout-op verification. A staged first patch can be reasonable, but
the composition checks it does claim need to cover combined coordinates and
the supported TileType path (or explicitly reject/diagnose those cases).

## Environment and revision control

The prepared interpreter was
`/tmp/amdpilot-repo-j-a92db6d841c5/venv/bin/python`. Python `flydsl` resolved
from `/job/repo/python/flydsl`, and after rebuilding, the native package path was
`/tmp/amdpilot-repo-j-a92db6d841c5/native-build/python_packages/flydsl/_mlir`.
The native rebuild used pinned LLVM revision
`e2a39f504fee836e4def9581bed817ecc327b9dc`.

The upstream issue could not be fetched through `gh` because the ROCm
organization rejected the installed fine-grained token lifetime. The supplied
issue snapshot was therefore used as problem data, and the accessible mirror
issue plus current code/candidate diff were inspected. No upstream participant
was contacted.

## Commands and results

All raw logs were preserved outside the checkout under
`/job/review-evidence-j-a92db6d841c5/` while revisions were switched.

1. Base native rebuild:

   `/tmp/amdpilot-repo-j-a92db6d841c5/venv/bin/python /opt/amdpilot/rebuild-native.py /job`

   Exit 0. The harness reported PASS and a real GPU vector-add numerical smoke
   on one AMD Instinct MI355X (`gfx950`), Torch
   `2.9.1+rocm7.2.0.git7e1940d4`, HIP `7.2.26015-fc0010cf6a`.

2. Candidate regression on the rebuilt base:

   `/tmp/amdpilot-repo-j-a92db6d841c5/native-build/bin/fly-opt /job/review-evidence-j-a92db6d841c5/invalid_structural_inputs.mlir -verify-diagnostics`

   Exit 134. The base aborted at `LayoutUtils.h:762` in `compositionImpl` with
   `restStrideVal % currShapeVal == 0 || restStrideVal < currShapeVal`,
   reproducing the reported deep assertion behavior.

3. Exact candidate checkout and native rebuild:

   `git checkout --detach c2a301580864ac6235af57156f4b22d61ed29edb`

   `/tmp/amdpilot-repo-j-a92db6d841c5/venv/bin/python /opt/amdpilot/rebuild-native.py /job`

   Both exited 0. The rebuild working-tree digest changed from
   `e766acdc4a4a5012943b7877f88e1121e5e62c686986a4b2327be1f5b3a81759`
   on base to
   `c86eb3c04bd97066918501ee33419903a8977220a29c49f19abdeec10dbb4ffd`
   on candidate. Its GPU numerical smoke also passed on the MI355X/gfx950.

4. Candidate regression on rebuilt candidate:

   `/tmp/amdpilot-repo-j-a92db6d841c5/native-build/bin/fly-opt tests/mlir/LayoutAlgebra/invalid_structural_inputs.mlir -verify-diagnostics`

   Exit 0. This measures the expected diagnostics for the candidate's four
   invalid examples and acceptance of its dynamic controls.

5. Every `RUN` line under `tests/mlir/LayoutAlgebra/*.mlir`, substituting the
   rebuilt `fly-opt` and pinned Triton `FileCheck`:

   Exit 0 for all 11 files, including the candidate regression.

6. Adversarial static composition cases:

   `/tmp/amdpilot-repo-j-a92db6d841c5/native-build/bin/fly-opt /job/review-evidence-j-a92db6d841c5/adversarial.mlir`

   Exit 0. The emitted module retained both invalid operations: the combined
   multi-mode out-of-domain layout and the oversized TileType case. Successful
   parsing here is a failing review measurement because both invalid static
   compositions should have been diagnosed.

## Remaining limitations

No LLVM change was required to build or exercise the candidate. GPU execution
was used to validate the rebuilt native library through the rebuild harness,
but the defect under review is an MLIR verification failure and the focused
adversarial evidence is compiler output rather than a GPU kernel. Dynamic SSA
extent admissibility remains unverified at compile time by design. Other layout
operations named by the issue but untouched by the candidate were not treated
as fixed.
