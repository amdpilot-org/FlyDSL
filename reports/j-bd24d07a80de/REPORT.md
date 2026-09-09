# Early-return admission and diagnostics on gfx942

## Summary

This bounded investigation probes FlyDSL kernel `return` placement using one-thread, one-element, fixed-input kernels. Before the change, several unsupported forms compiled silently and produced wrong output; a `return` inside a dynamic `while` loop hung for the 120-second probe bound. The patch adds definition-time validation so:

- a bare top-level kernel `return` remains admitted;
- `return` inside `const_expr` control flow and `fx.range_constexpr` remains admitted;
- a valued kernel `return` is rejected with a clear `SyntaxError`;
- `return` inside dynamic `if`, `for ... range(...)`, or `while` is rejected with a clear `SyntaxError`.

No barrier was used in any probe, and the fix does not introduce divergent control flow around barriers.

## Upstream context

Read-only issue: `ROCm/FlyDSL` issue 687, `"[Feature]: [Feature]: "early return" check in control flow"`, state `open`.

The issue body asks to prevent non-standard user code that can cause hard-to-detect errors, incorrect output, or crashes. Its current comments array is empty. Its timeline contains only `labeled` and `assigned` events, with no linked pull request or referenced commit. Therefore no candidate upstream PR was tested and no candidate commit hash is recorded.

Raw API responses are retained in:

- `reports/j-bd24d07a80de/raw/issue_687.json`
- `reports/j-bd24d07a80de/raw/issue_687_comments.json`
- `reports/j-bd24d07a80de/raw/issue_687_timeline.json`

## Environment

The complete measured log is `reports/j-bd24d07a80de/raw/environment.log`.

- Qualified image: `amdpilotv2/open-job-mi300:jit-config-readable-260909-banff5`
- Operator-provided local image ID: `sha256:39fe745feda79ecf4c17f4d806d8ef12150bef720f2f07f5c63a20b3ccfd63f1`
- Container hostname (not image identity): `banff-cyxtera-cx57a-5`
- Working clone: `/job/work/FlyDSL`
- Mirror base commit: `ed70142704e1a6d5563fb53e1607e3a4b85d7111`
- Working source version: FlyDSL `0.3.3`
- Source-native Python package: `/job/build-cache/flydsl-build/python_packages`
- Source-native bindings: `/job/build-cache/flydsl-build/python_packages/flydsl/_mlir/_mlir_libs`
- Preinstalled FlyDSL: `0.3.1` at `/opt/venv/lib/python3.10/site-packages/flydsl`
- Python: `/opt/venv/bin/python`, Python `3.10.12`
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`; HIP available; one device
- GPU: AMD Instinct MI300X, `gfx942`, unique ID `0x6e8448eb6f49db1d`, serial `692440004395`
- ROCm/HIP: HIP `7.2.26015-fc0010cf6a`, AMD clang `22.0.0git`
- CMake: `4.3.4`; Ninja: `1.13.0.git.kitware-jobserver-pipe-1`
- Pinned LLVM/MLIR source commit: `e2a39f504fee836e4def9581bed817ecc327b9dc`
- Job-private MLIR cache: `/job/build-cache/llvm-project`
- Job-private FlyDSL build cache: `/job/build-cache/flydsl-build`

The preinstalled `0.3.1` bindings were not assumed to match the working `0.3.3` source. Attempting the source Python with those bindings failed with the preserved raw diagnostic:

```text
ValueError: MLIR Textual PassPipeline Parser:1:236: error: 'convert-rocdl-fastmath-ops' does not refer to a registered pass or pass pipeline
```

The repository's pinned MLIR revision was therefore built with its `amd-minimal` profile, followed by the FlyDSL native build. Build caches were kept under `/job/build-cache`, outside the delivery clone.

## Probe set

The probe harness is `reports/j-bd24d07a80de/probe_early_return.py`. It uses the source-native operation names `return`, `if`, `for ... range(...)`, `while`, `const_expr`, and `fx.range_constexpr`. Inputs are bounded to a one-element `int32` output tensor, grid `(1, 1, 1)`, block `(1, 1, 1)`, runtime flags `0` or `1`, and loop bounds `2`.

The runner is `reports/j-bd24d07a80de/run_probes.sh`. It disables the FlyDSL runtime cache and bounds each process with `timeout 30s`.

## Pre-fix behavior

Raw pre-fix logs are in `reports/j-bd24d07a80de/raw/pre_fix/`.

| Form | Inputs | Expected | Actual pre-fix | Result |
| --- | ---: | ---: | ---: | --- |
| baseline, no return | flag 1 | 1 | 1 | pass |
| top-level bare `return` | flag 1 | 1 | 1 | pass |
| top-level valued `return` | flag 1 | 1 | 99 | silent wrong output |
| dynamic `if`, return last in branch | flags 1/0 | 1/2 | 1/2 | pass |
| dynamic `if`, return then post-if store | flags 1/0 | 1/3 | 3/3 | silent wrong output for flag 1 |
| dynamic `if`, carried state then return | flags 1/0 | 1/0 | 0/0 | silent wrong output for flag 1 |
| dynamic `for ... range(2)`, return then post-loop store | n 2 | 10 | 99 | silent wrong output |
| dynamic `while`, return then post-loop store | offset 2 | 2 | no output before bound | 120-second timeout, exit 124 |
| nested dynamic `if`, return then post-if store | flags 1/0 | 1/4 | 4/4 | silent wrong output for flag 1 |
| `const_expr` `if`, return then post-if store | flags 1/0 | 1/2 | 1/2 | pass |
| `fx.range_constexpr(2)`, return then post-loop store | n 2 | 10 | 10 | pass |

Representative preserved pre-fix failures:

```text
RESULT form=top_level_value_return flag=1 flag_const=1 actual=99 expected=1
AssertionError: numerical gate failed: actual=99, expected=1
```

```text
RESULT form=dynamic_if_return_after flag=1 flag_const=1 actual=3 expected=1
AssertionError: numerical gate failed: actual=3, expected=1
```

```text
RESULT form=dynamic_if_state_return flag=1 flag_const=1 actual=0 expected=1
AssertionError: numerical gate failed: actual=0, expected=1
```

```text
RESULT form=for_return_after flag=1 flag_const=1 actual=99 expected=10
AssertionError: numerical gate failed: actual=99, expected=10
```

```text
RESULT form=nested_if_return_after flag=1 flag_const=1 actual=4 expected=1
AssertionError: numerical gate failed: actual=4, expected=1
```

The pre-fix `while_return_after.log` is empty and its probe was terminated by the 120-second bound with exit code `124`.

## Post-fix behavior

Raw post-fix logs are in `reports/j-bd24d07a80de/raw/`, with the combined run in `raw/probe_summary.log`.

| Form | Inputs | Expected | Post-fix result |
| --- | ---: | ---: | --- |
| baseline, no return | flag 1 | 1 | `actual=1`, exit 0 |
| top-level bare `return` | flag 1 | 1 | `actual=1`, exit 0 |
| top-level valued `return` | flag 1 | reject | `SyntaxError: FlyDSL kernel return must not carry a value`, exit 1 |
| dynamic `if`, return last in branch | flag 1 | reject | dynamic-control-flow `SyntaxError`, exit 1 |
| dynamic `if`, return then post-if store | flag 1 | reject | dynamic-control-flow `SyntaxError`, exit 1 |
| dynamic `if`, carried state then return | flag 1 | reject | dynamic-control-flow `SyntaxError`, exit 1 |
| dynamic `for ... range(2)` return | n 2 | reject | dynamic-control-flow `SyntaxError`, exit 1 |
| dynamic `while` return | offset 2 | reject | dynamic-control-flow `SyntaxError`, exit 1 |
| nested dynamic `if` return | flag 1 | reject | dynamic-control-flow `SyntaxError`, exit 1 |
| `const_expr` `if` return | flags 1/0 | 1/2 | `actual=1`, `actual=2`, exit 0 |
| `fx.range_constexpr(2)` return | n 2 | 10 | `actual=10`, exit 0 |

The new diagnostic for every rejected dynamic-control-flow form is:

```text
SyntaxError: FlyDSL does not support early return inside dynamic control flow; restructure the kernel to yield carried state or use const_expr control flow
```

The valued-return diagnostic is:

```text
SyntaxError: FlyDSL kernel return must not carry a value
```

## Implementation

`python/flydsl/compiler/ast_rewriter.py` adds a first-pass `ValidateReturns` transformer. It tracks dynamic control-flow nesting and rejects kernel returns in that context before the existing rewriters convert Python branches into generated helper functions. It recognizes `const_expr` conditions and `fx.range_constexpr` iterators as compile-time control flow and leaves those forms valid.

`python/flydsl/compiler/kernel_function.py` marks `@flyc.kernel` functions as `function_kind="kernel"` so valued returns are rejected only for kernels and ordinary `@flyc.jit` return behavior remains unchanged.

`tests/unit/test_early_return_validation.py` covers:

- admitted top-level bare return;
- admitted `const_expr` control-flow return;
- rejected valued kernel return;
- rejected dynamic `if`, `for`, and `while` returns;
- rejected dynamic return nested under a `const_expr` branch.

## Validation

Commands run:

```bash
PYTHONPATH=/job/build-cache/flydsl-build/python_packages:/job/build-cache/python-deps \
  /opt/venv/bin/python -m pytest \
  tests/unit/test_early_return_validation.py \
  tests/unit/test_if_dispatch_paths.py \
  tests/unit/test_for_dispatch_paths.py \
  tests/unit/test_while_dispatch_paths.py \
  tests/unit/test_dynamic_controlflow_list_carry.py -q
```

Result:

```text
57 passed in 1.31s
```

Formatting and lint used job-private pinned targets:

```text
ruff: All checks passed!
black: 4 files would be left unchanged.
```

The post-fix gfx942 probe runner exits 0. Its numerical gates are unchanged from the pre-fix expected values.

## Reproduction

From the working clone, after building pinned MLIR and FlyDSL into `/job/build-cache`:

```bash
export PYTHONPATH=/job/build-cache/flydsl-build/python_packages:/job/build-cache/python-deps
export FLYDSL_RUNTIME_ENABLE_CACHE=0
/opt/venv/bin/python reports/j-bd24d07a80de/probe_early_return.py \
  constexpr_if_return_after --flag 1 --flag-const 1 --expected 1
reports/j-bd24d07a80de/run_probes.sh
```

## Notes and limitations

- No upstream issue, PR, or comment was posted or modified.
- No full model weights were downloaded; all validation is synthetic and local.
- The preinstalled FlyDSL `0.3.1` stack remains untouched. The working `0.3.3` source was tested through the source-native build.
- The fix intentionally rejects all dynamic-control-flow returns, including the narrow branch-terminal case that happened to produce the expected value before the fix. This avoids admitting syntax whose meaning depends on whether statements follow the control-flow operation.
