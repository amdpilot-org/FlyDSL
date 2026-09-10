# Reusable profiling export validation

## Scope and source

- Campaign: `repo-e2e-20260909`; upstream context: ROCm/FlyDSL issue 304.
- Issue 304 proposes moving reusable benchmark helpers into the FlyDSL Python API.
- Tested upstream candidate: ROCm/FlyDSL PR 829, commit
  `ce8ce9c892a7f6c6fec4d93086509139e393dbf0` (`profiling: extract reusable GPU event timer`).
- Mirror base: `ed70142704e1a6d5563fb53e1607e3a4b85d7111` (`main`).
- Working clone: `/job/FlyDSL`; local package: `/job/FlyDSL/python/flydsl`.
- Job-private cache: `/tmp/flydsl-cache-j-7e092116b545`.
- No upstream issue, PR, or comment was posted or modified.

## Environment

- Image: `amdpilotv2/open-job:gbt350-20260909`, local ID
  `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.
- GPU: one AMD Instinct MI350X, `gfx950`, device ID `0x75a0`, GUID `51966`.
- Python: `/opt/venv/bin/python` (3.12.3).
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`, `/opt/venv/lib/python3.12/site-packages/torch`.
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`, `/opt/venv/lib/python3.12/site-packages/triton`.
- Installed FlyDSL: `0.2.4`, `/opt/venv/lib/python3.12/site-packages/flydsl`.
- Native FlyDSL modules include
  `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/_mlir.cpython-312-x86_64-linux-gnu.so`,
  `_mlirDialectsFly...so`, `_mlirDialectsFlyROCDL...so`, and `libfly_jit_runtime.so`.
- HIP runtime: `/opt/rocm-7.2.0/lib/libamdhip64.so.7`; `hipcc` reports HIP 7.2.26015.

## Commands

```bash
export PYTHONPATH=/job/FlyDSL/python
python -m pytest -q tests/unit/test_profiling.py tests/unit/test_autotune.py
python reports/j-7e092116b545/validate_mi350x.py
```

The upstream candidate was checked out at the preserved commit in the job-private
cache and tested with `PYTHONPATH` pointed at that worktree:

```bash
python -m pytest -q tests/unit/test_profiling.py
```

## Numerical gates

The real kernel is `torch.add(left, right, out=output)` over 8,388,608 float32
elements. The unchanged gate is `torch.allclose(..., rtol=1e-5, atol=1e-6)`.
The measured output had max absolute difference `0.0` and remained correct after
all repetitions. A copy with one output element increased by `1.0` failed the
same gate, as required.

## Units and synchronization

`do_bench` returns milliseconds. `warmup` and `rep` are iteration counts. The
callable must enqueue asynchronous work on PyTorch's current CUDA/HIP stream and
must not synchronize internally. Warmup is untimed and followed by one device
synchronization. Each measured batch queues `torch.cuda._sleep(20_000_000)` on
the current stream, records start/end events on that stream, averages the batch's
launches, and synchronizes the end event once. The default result is the median
batch average; quantiles select sorted batch averages.

## Raw results

Upstream PR 829 candidate (`ce8ce9c...`):

- Focused tests: 11 passed.
- Ordinary `import flydsl` did not load `torch`.
- Reported quantiles, in microseconds: `[19.23999935388565, 19.519999623298645,
  19.71999928355217, 19.840000197291374, 20.08100040256977, 22.80000038444996]`.
- Candidate median: `19.779999740421772 us`.
- Independent same-stream per-call event median: `19.60100047290325 us`.
- Candidate/direct median ratio: `1.0091321495433854`.

Adapted export on mirror `main`:

- Focused tests: 61 passed.
- Ordinary `import flydsl` did not load `torch`.
- Reported quantiles, in microseconds: `[17.40819960832596, 17.43199974298477,
  17.448200285434723, 17.455999553203583, 17.656199634075165,
  17.656199634075165]`.
- Reported median: `17.452099919319153 us`.
- Independent same-stream per-call event median: `19.279999658465385 us`.
- Independent same-stream batched-event median: `17.40819960832596 us`.
- Reported/independent-batched ratio: `1.0025218179927233`.
- Full direct per-call samples, in microseconds: `[19.07999999821186,
  19.120000302791595, 19.16000060737133, 19.16000060737133,
  19.16000060737133, 19.200000911951065, 19.200000911951065,
  19.200999289751053, 19.23999935388565, 19.23999935388565,
  19.23999935388565, 19.240999594330788, 19.279999658465385,
  19.279999658465385, 19.279999658465385, 19.360000267624855,
  19.40000057220459, 19.40000057220459, 19.40000057220459,
  19.40000057220459, 19.401000812649727, 19.401000812649727,
  19.440000876784325, 20.160000771284103, 20.281000062823296]`.
- Full direct batch samples, in microseconds: `[17.392200231552124,
  17.4002006649971, 17.40819960832596, 17.464199662208557,
  18.344199657440186]`.

## Boundaries

- This change does not migrate the broader `tests/test_common.py` API or any
  test folder.
- The public export intentionally preserves `main`'s backlogged batched timer
  rather than reverting to PR 829's older per-call event implementation.
- The image did not contain `ruff` or `black`; focused pytest and `git diff
  --check` were run instead.
