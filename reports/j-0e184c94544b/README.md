# Autotune mutating-kernel validation on MI300X

## Outcome

The qualified installed FlyDSL 0.3.1 stack **passes** all requested real-GPU
semantic checks on one AMD Instinct MI300X (`gfx942`). The working source tree is
FlyDSL 0.3.3, but it **cannot execute on this image** when paired with the
qualified 0.3.1 native bindings because the source pass pipeline requests
`convert-rocdl-fastmath-ops`, which those bindings do not register. No source
MLIR build or install prefix is available in the image. Therefore, the positive
GPU result applies to installed 0.3.1, not to source 0.3.3.

The source-only autotune unit suite passes (`55 passed`), and the source/native
GPU blocker is recorded verbatim in `source-native-mismatch.txt`.

## Validated semantics

- `restore_value=["value"]` keeps every benchmark repetition on the pristine
  caller input. The post-hook observed six exact launches: one warmup plus two
  repetitions for each of two candidates.
- `reset_to_zero=["output"]` zeroes the output before every benchmark repetition,
  the post-search final execution, and a cached execution.
- The forced-search final execution and a subsequent cache hit both produce the
  exact integer reference output. The cache hit does not search and does not add
  benchmark observations.
- A default call with `FLYDSL_AUTOTUNE=0` uses `Config(block_dim=64)` without
  searching or recording benchmark observations.
- The declared `key=["mode"]` axis separates mode `3` from mode `5`. Mode `5`
  performs its own two-candidate search and leaves two cache entries.

All numerical gates are unchanged exact `torch.equal` comparisons on `int32`
tensors. The candidate set is two configurations (`block_dim=64` and
`block_dim=128`), the tensor size is eight elements, and no model weights are
downloaded.

## Environment

- Image: `amdpilotv2/open-job-mi300:jit-config-readable-35122-260909`
- Local image ID: `sha256:dfc9419089c338b5712da4841768b38b1ab79f3da41f8c58c3cd4dfcc1147ff1`
- Working clone: `/job/FlyDSL`
- Delivery branch: `amdpilot/j-0e184c94544b`
- Source base commit: `ed70142704e1a6d5563fb53e1607e3a4b85d7111`
- Source Python version: FlyDSL `0.3.3`
- Qualified installed FlyDSL: `0.3.1` at
  `/opt/venv/lib/python3.10/site-packages/flydsl`
- Qualified native bindings:
  `/opt/venv/lib/python3.10/site-packages/flydsl/_mlir`
- No source native build directory exists in this image.
- GPU: one AMD Instinct MI300X, `gfx942`, UUID
  `GPU-b5c590cf4c10631d`, 304 compute units.
- Compiler: `hipcc` HIP `7.2.26015-fc0010cf6a`
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`, HIP runtime
  `7.2.26015-fc0010cf6a`
- Python: `/opt/venv/bin/python` (CPython 3.10.12)

## Reproduction

Commands used for setup and read-only context:

```bash
git clone https://github.com/amdpilot-org/FlyDSL.git /job/FlyDSL
git switch -c amdpilot/j-0e184c94544b
rocminfo
rocm-smi
hipcc --version
gh issue view 320 --repo amdpilot-org/FlyDSL
curl https://api.github.com/repos/ROCm/FlyDSL/issues/770
curl https://api.github.com/repos/ROCm/FlyDSL/issues/770/comments
curl https://api.github.com/repos/ROCm/FlyDSL/pulls/783
curl https://api.github.com/repos/ROCm/FlyDSL/pulls/785
```

The GitHub API reads were unauthenticated/read-only. No upstream content was
created or changed.

Run from the working clone:

```bash
CACHE_ROOT=/job/_cache/flydsl-autotune-validation-final
mkdir -p "$CACHE_ROOT"
/opt/venv/bin/python reports/j-0e184c94544b/validate_autotune_mutating_gfx942.py \
  --cache-root "$CACHE_ROOT" \
  --output reports/j-0e184c94544b/results.json
```

The command must use `/opt/venv/bin/python` without adding the source tree to
`PYTHONPATH` when reproducing the qualified installed-package result. The script
creates job-private `runtime` and `autotune` cache directories under
`--cache-root`, uses exact integer references, and exits nonzero if any phase
fails.

Source-only checks used:

```bash
PYTHONPATH=/job/FlyDSL/python /opt/venv/bin/python \
  -m pytest tests/unit/test_autotune.py -q
```

Result: `55 passed in 1.39s`.

The source/native probe used the same harness with
`PYTHONPATH=/job/FlyDSL/python`; it failed during candidate compilation as
recorded in `source-native-mismatch.txt`.

## Raw result

The complete machine-readable result is `results.json`. It records module and
native paths, GPU identity, cache paths, captured autotune output, all observed
values, selected configs, and per-phase pass flags.

Final phase summary:

| Phase | Result |
|---|---|
| Forced search and final execution | Pass |
| Cache hit | Pass |
| Declared key-axis separation | Pass |
| Default no-search call | Pass |

## Upstream context

Read-only context came from public issue `ROCm/FlyDSL#770` and mirror issue
`amdpilot-org/FlyDSL#320`. PR `ROCm/FlyDSL#783`, which introduced
`restore_value`, `reset_to_zero`, and cache-key hardening, is already merged;
PR `ROCm/FlyDSL#785`, which added explicit opt-in search and defaults, is also
merged. No separate upstream PR candidate was checked out because the relevant
fix was already merged, so duplicating it was unnecessary. No upstream issue, PR,
or comment was posted or modified.

## Limits and uncertainties

- The real-GPU result is for qualified installed FlyDSL 0.3.1, not source 0.3.3.
- Source 0.3.3 GPU execution is blocked by the missing native pass registration
  in the qualified image; building a new LLVM/MLIR stack was outside the bounded,
  node-preserving task.
- The harness intentionally does not redesign or extend the autotuner. It keeps
  the existing `restore_value`, `reset_to_zero`, `key`, `default`, and `Config`
  names and semantics.
