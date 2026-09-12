# Cold JIT report for issue 862

The maintained in-tree RMSNorm and gfx950 GEMM examples were compiled from empty, distinct private cache directories and executed on one AMD Instinct MI350X. Both were checked against independent Torch expressions.

The cold path generated `original_ir` for `CompiledArtifact.source_ir`, then `MlirCompiler.compile()` immediately called `get_asm()` again before parsing an isolated module for lowering. The parse copy is required: lowering the freshly constructed module directly produced an MLIR duplicate-attribute assertion. This change passes the already-retained `original_ir` into `MlirCompiler.compile()`, eliminating only the duplicate serialization.

| Kernel | Baseline cold call | Changed cold call | Baseline / changed compiler pipeline | Required parse reference | Numerical result |
|---|---:|---:|---:|---:|---:|
| RMSNorm bf16 16x4096 | 148.51 ms | 141.49 ms | 83.84 / 81.32 ms | 2.67 / 2.56 ms | max abs 0.0009765625 |
| GEMM bf16-to-fp32 1024³ | 712.20 ms | 710.80 ms | 229.79 / 225.21 ms | 8.91 / 8.63 ms | max abs 0.4954681396484375 |

These are cold-cache observations, not a statistical speedup claim. Each side used a different empty cache. For both examples the logical cache-key SHA-256, source IR SHA-256, compiled IR SHA-256, and IR byte counts are identical before and after. Full output, including cache directories and architecture evidence, is under `raw/`.

The issue-linked external RMSNorm script currently fails to import because it references `flydsl.expr.vector`, which is absent from this checkout. The repository-maintained examples were therefore used; the failed import is retained in `raw/baseline/rmsnorm.log`.
