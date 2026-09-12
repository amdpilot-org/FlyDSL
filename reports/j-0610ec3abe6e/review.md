# Independent review of PR 560

Reviewed exact commit `4f72a59a0306801071fee7ef2850c110d893ff33` against base `acf7e67b7d22847e345938ca54fcc137bd7b2a1f` and the original intra-kernel profiling request.

Recommendation: **accept**. The candidate fully resolves the original issue within the supported and documented scope.

The prepared base reproduced the missing capability during real kernel lowering: `flydsl.expr.rocdl` had no `global_timer`. The identical probe compiled and returned a nonzero device timestamp at the candidate commit. The candidate's real GPU vector-add regression passed with an exact independent Torch result, positive per-workgroup intervals, and a measured median overhead of 0.076 microseconds (1.002x) in this review run.

Independent checks used distinct compiler dump directories. The profiled gfx950 ISA has two `s_memrealtime` instructions, two 64-bit global timestamp stores, and the requested barrier. The plain specialization has none of those instructions. An additional uneven-work kernel independently produced exact integer outputs, preserved sentinels around its caller-owned timestamp layout, and reported intervals of 7172, 13224, 20752, and 27104 ticks for one through four units of global-load work.

No native source changed, so rebuilding the native compiler was not applicable. Python imports resolved to the candidate checkout; the native MLIR extension resolved through the checkout's prepared link to the pinned wheel native library.

Architecture limitation: the assigned device was one AMD Instinct MI350X (`gfx950`). `s_memrealtime` provides the same-device global time domain needed for cross-XCD workgroup comparisons, but this environment could not identify or pin workgroups to distinct XCDs, so placement across XCDs was not directly demonstrated. Cross-GPU timestamps do not have a guaranteed shared epoch. Timer reads are not synchronization or completion fences, and raw ticks require an independently established device timer frequency for time conversion.

Raw logs, probes, IR, and ISA are retained outside the checkout under `/job/review-evidence/j-0610ec3abe6e/`.
