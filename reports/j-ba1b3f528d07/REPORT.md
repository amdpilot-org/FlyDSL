# Independent review of candidate PR 511

## Recommendation

Reject candidate commit `2c6b394d75deb3f19d660f762b2ab02fd60c4eea` as a fix for the open convolution-performance issue. It accurately reproduces a limited sample of the reported gap, but changes only report/benchmark artifacts and makes no kernel, tuning, compiler, or native-library change. The original problem therefore remains present at the candidate revision.

Upstream issue: https://github.com/ROCm/FlyDSL/issues/861

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/527

Candidate: https://github.com/amdpilot-org/FlyDSL/pull/511

## Revisions and environment

- Prepared base: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`
- Exact candidate: `2c6b394d75deb3f19d660f762b2ab02fd60c4eea`
- GPU execution: AMD Instinct MI350X, `gfx950`, device 0; ROCm SMI recorded unique ID `0x5fb42ff90866060e`.
- Interpreter: `/tmp/amdpilot-repo-j-ba1b3f528d07/venv/bin/python`
- Python import: `/job/repo/python/flydsl/__init__.py`
- Native import path: `/job/repo/python/flydsl/_mlir`, a symlink to `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir` from the pinned wheel.
- No native rebuild was needed or performed because the candidate contains no C++ or native changes. This review validates the candidate's unchanged native dependency, not a rebuilt library.

`git diff --name-status <base> <candidate>` lists only four additions under `reports/j-5916dc8d5733/`; there is no implementation change.

## Results

The base was tested before checking out the candidate. Using GPU-event medians (5 warmups, 30 samples) and independent `torch.nn.functional.conv3d` references at the unchanged `rtol=2e-2, atol=2e-2`, the three issue-derived convolution/GEMM ratios were 1.60x, 1.47x, and 1.89x. Thus the reported lower convolution throughput reproduced on the prepared base.

At the exact candidate SHA, its own benchmark (10 warmups, 100 samples) again measured ratios of 1.51x, 1.45x, and 1.66x. All three shipped tile choices passed the Torch reference, but the performance defect remained.

Independent adversarial cases exercised implicit-GEMM `M` below and above 32, output-channel tails (`N=31`, `N=33`, `N=65`), and a stride-2 spatial tail. All passed the same Torch tolerance. Their candidate convolution/GEMM ratios were 1.96x, 1.95x, and 1.76x, respectively. Correct boundary behavior does not remedy the original throughput gap.

The focused repository tile regression selected eight cases and exited 0. No compiler/ISA performance claim was made by the candidate, and none can be inferred from a Python-level benchmark alone.

## Commands

All compilation/runtime caches used the job-private `/tmp/amdpilot-repo-j-ba1b3f528d07/cache` tree.

```bash
# Base, followed by the same script at the candidate
/tmp/amdpilot-repo-j-ba1b3f528d07/venv/bin/python \
  /job/review-evidence-j-ba1b3f528d07/review_bench.py \
  /job/review-evidence-j-ba1b3f528d07/base.json

git switch --detach 2c6b394d75deb3f19d660f762b2ab02fd60c4eea
/tmp/amdpilot-repo-j-ba1b3f528d07/venv/bin/python \
  reports/j-5916dc8d5733/bench_conv_gap.py \
  --output /job/review-evidence-j-ba1b3f528d07/candidate_regression.json \
  --warmup 10 --repetitions 100
/tmp/amdpilot-repo-j-ba1b3f528d07/venv/bin/python \
  /job/review-evidence-j-ba1b3f528d07/review_bench.py \
  /job/review-evidence-j-ba1b3f528d07/candidate_boundaries.json
/tmp/amdpilot-repo-j-ba1b3f528d07/venv/bin/python -m pytest -q \
  tests/kernels/test_conv3d_implicit.py -k tile_configs
```

Raw JSON, console logs, and the independent review source are retained outside the checkout at `/job/review-evidence-j-ba1b3f528d07/` so revision switches could not alter them.

## Limitations

The source issue supplies no production shapes or target performance threshold, so the review can establish that the sampled gap persists but cannot establish coverage of a full workload. Torch GEMM has the same implicit-GEMM dimensions/FLOP count but a different memory-access pattern, so it is a compute-density reference rather than a convolution substitute. Only the available MI350X/gfx950 architecture was verified. Resolving the issue still requires actual kernel/tuning work followed by broader workload and ISA/compiler evidence where relevant.
