# gfx950 layout-divide investigation

## Scope

This report covers ROCm/FlyDSL issue 739 on one assigned AMD Instinct MI350X
(`gfx950`, serial `692517020475`). It is distinct from earlier MI300 work and
does not claim results for any later checkout change.

The qualified image was
`amdpilotv2/open-job:gbt350-20260909`, local image ID
`sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.

## Environment

- Python: `/opt/venv/bin/python` (Python 3.12.3)
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`, imported from
  `/opt/venv/lib/python3.12/site-packages/torch/__init__.py`
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`, imported from
  `/opt/venv/lib/python3.12/site-packages/triton/__init__.py`
- FlyDSL: `0.2.4`, imported from
  `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`
- FlyDSL native dialect module:
  `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/_mlirDialectsFly.cpython-312-x86_64-linux-gnu.so`
- ROCm: `7.2.26015-fc0010cf6a`

## First GPU baseline

The first successful installed-source execution was a 4096-element `f32` copy
kernel using FlyDSL buffer load/store. The command was:

```bash
/opt/venv/bin/python /job/baseline_first.py
```

The raw record is `/job/baseline-first.json`. It used `time.perf_counter()`
around the first launch followed by `torch.cuda.synchronize()`, with no warmup
or repeated work. The first GPU execution took `0.3841560585424304` seconds.
The independent Torch `arange` reference matched exactly (`torch.equal` was
true and maximum absolute error was `0.0`).

The first attempt imported AITER's vendored buffer helpers and failed before
GPU launch because `aiter.jit.module_aiter_core` was unavailable after an
unrelated 18.2-second AITER extension build. The working baseline then used
FlyDSL's own `flydsl.expr.buffer_ops`.

## Real GPU layout probe

Run the probe with:

```bash
cd /job/FlyDSL
/opt/venv/bin/python reports/j-7dc7117e7faa/probe_layout_divide_gpu.py \
  --output /job/layout-divide-gpu-results.json
```

The probe uses a `(64,50,80):(16000,160,1)` layout over a 1,016,000-element
Torch storage. Each case launches one 32-thread block, maps thread `i` through
the divided layout with `crd2idx`, performs a real buffer load and store, and
compares against an independent host map `{i: i * 16000}`. The destination is
initialized to sentinel `-739.0`; exact success requires all 32 expected values
and exactly 1,015,968 untouched sentinels.

All supported cases passed exactly:

| Case | First-launch elapsed (s) | Exact | Untouched sentinels |
| --- | ---: | --- | ---: |
| `logical_divide(..., (32,))` | 0.2524888589978218 | yes | 1015968 |
| `zipped_divide(..., (32,))` | 0.017918827012181282 | yes | 1015968 |
| `logical_divide(..., (32,None,None))` | 0.015506195835769176 | yes | 1015968 |
| `logical_divide(..., (32,None,40))` | 0.015670407563447952 | yes | 1015968 |

Both None-entry `zipped_divide` cases aborted in a bounded child process with
return code `-6` and this exact native diagnostic:

```text
python: /flydsl/include/flydsl/Dialect/Fly/Utils/IntTupleUtils.h:854:
std::pair<_FIter, _FIter> mlir::fly::detail::intTupleZip2ByImpl(...)
[with IntTuple = mlir::fly::IntTupleAttr]:
Assertion `t.rank() == 2 && "intTupleZip2By expects rank-2 tuple at terminal"' failed.
```

The same assertion reproduces the issue's reported abort for
`(32,None,None)` and `(32,None,40)`.

## Upstream context

ROCm/FlyDSL issue 739 is titled `zipped divide crashes on some cases`. Its
reported cases are lower-rank tilers and None-entry tilers. The read-only
discussion links ROCm/FlyDSL pull request 746, `fix tile syntax in divide`.

The candidate head commit was preserved locally as:

```text
bf4e651b4cb26085642c838d3526f427d2a32c5a
```

Its patch changes `IntTupleUtils.h`, `LayoutUtils.h`,
`python/flydsl/expr/primitive.py`, and layout-algebra tests. It directly
targets the assertion reproduced above. No upstream issue, pull request, or
comment was posted or modified.

## Limitation

The container has the installed FlyDSL wheel but no MLIR CMake development
install (`lib/cmake/mlir`) or `fly-opt` build tree. Rebuilding FlyDSL or LLVM
would violate this job's explicit no-compiler-rebuild constraint. Therefore,
PR 746 was inspected and its commit preserved, but its native changes were not
executed on gfx950. The GPU results above are installed-source evidence only
and are not proof for the candidate checkout.

No production fix is duplicated here. The committed probe and this report
preserve the supported gfx950 cases, the independent host index map, sentinel
checks, and the exact native failure for the unsupported cases.
