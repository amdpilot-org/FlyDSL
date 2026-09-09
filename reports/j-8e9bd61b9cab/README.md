# `zipped_divide` lower-rank and `None` tiler validation

## Status

Early draft. This report will be updated as the bounded gfx942 validation completes.

## Environment

- Working mirror: `amdpilot-org/FlyDSL`
- Source-tree commit: `ed70142704e1a6d5563fb53e1607e3a4b85d7111` (`v0.3.2-30-ged70142`, source `__version__` 0.3.3)
- Installed wheel: FlyDSL 0.3.1 at `/opt/venv/lib/python3.10/site-packages/flydsl`
- Python: `/opt/venv/bin/python` (3.10.12)
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`
- ROCm HIP runtime reported by Torch: `7.2.26015-fc0010cf6a`
- GPU: one assigned gfx942/MI300X device visible through Torch (`torch.cuda.device_count() == 1`)

The installed wheel and working source tree are intentionally recorded separately; the installed 0.3.1 native module is not assumed to match the source-tree commit.

## Initial reproduction

Using the installed 0.3.1 wheel and layout `(64,50,80):(16000,160,1)`:

- `logical_divide` with `(32,)`, `(32,None,None)`, and `(32,None,40)` completed.
- `zipped_divide` with `(32,)` completed.
- `zipped_divide` with `(32,None,None)` aborted with the assertion from upstream issue 739:
  `intTupleZip2By expects rank-2 tuple at terminal`.
- `zipped_divide` with `(32,None,40)` aborted with the same assertion.

Raw installed-wheel output is retained in the job log and will be summarized in the final report.

## Upstream context

Read-only investigation of upstream issue 739 found upstream pull request 746, which changes divide tile handling and adds layout-algebra coverage for these cases. No upstream issue, pull request, or comment was modified.
