# Vector unary issue validation

Upstream issue: https://github.com/ROCm/FlyDSL/issues/353

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/480

The current base already lowers integer-vector `~` to `arith.xori` and integer-vector
unary `-` to `arith.subi`; the historical LLVM `cast<IntegerType>` assertion did not
reproduce. The new system regression follows the original 8-by-24 tiled-copy shape
and runs signed and unsigned 32-bit vectors on the assigned gfx950 GPU. NumPy supplies
the independent expected results, including wraparound boundary cases.

Python logical `not` is scalar truth testing and is not an elementwise Vector operator.
The implementation now diagnoses that unsupported use directly instead of allowing a
host `bool` to reach a vector store and fail later with an unrelated operand error.

Raw evidence is retained at `/job/artifacts/j-b82ca60f4cba/`. In particular,
`gpu-vector-unary-run2.log` records the four passing GPU cases, while `dumps-run2/`
contains origin MLIR, LLVM IR, and final ISA for every kernel. The origin IR contains
`arith.xori` and `arith.subi` over `vector<48xi32>`; the gfx950 ISA contains
`v_not_b32_e32` and `v_sub_u32_e32`.
