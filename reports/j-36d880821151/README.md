# Early-return control-flow audit

Upstream issue: https://github.com/ROCm/FlyDSL/issues/687

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/487

The reproduced defect was semantic, not just syntactic. A `return` inside a
runtime DSL `if` was outlined into a Python branch helper. It returned from that
helper only, after which tracing continued and emitted operations following the
apparent function return. On gfx950, a kernel whose true branch returned before
`Out[0] = 9` nevertheless wrote `9` over the initial value `3`.

The supported contract after this change is:

- A return at function scope is supported.
- A return controlled entirely by `const_expr(...)` or `range_constexpr(...)`
  remains ordinary compile-time Python control flow and is supported.
- A return belonging to a nested Python function is checked in that function's
  own control-flow context and is not mistaken for an exit from the outer DSL
  region.
- A return nested anywhere beneath runtime `if`, `for`, or `while` lowered to
  `scf.if`, `scf.for`, or `scf.while` is unsupported and raises `SyntaxError` at
  the original return line. Runtime-divergent function exit is not represented
  by the current structured-control-flow lowering.

Raw outputs are retained under `/job/raw/j-36d880821151/`. Full origin MLIR,
pass-by-pass MLIR, LLVM IR, and final ISA are retained under
`/tmp/amdpilot-repo-j-36d880821151/early-return-dumps-2/`. This was a Python
front-end change; the native extension at
`/opt/venv/lib/python3.12/site-packages/flydsl/_mlir` was not modified or rebuilt.
