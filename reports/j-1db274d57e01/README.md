# FlyDSL platform qualification: j-1db274d57e01

This report qualifies the prepared FlyDSL source checkout on the assigned AMD
GPU. It is a platform qualification record, not a claim that a FlyDSL issue has
been fixed.

## Prepared source and environment

- Source: `amdpilot-org/FlyDSL` at base commit
  `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`
- Branch: `amdpilot/j-1db274d57e01`
- Prepared checkout: `/job/repo`
- Prepared interpreter:
  `/tmp/amdpilot-repo-j-1db274d57e01/venv/bin/python`
- Prepared native module: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`
- GPU: AMD Instinct MI355X (one assigned device)
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`
- HIP: `7.2.26015-fc0010cf6a`

## Early GPU smoke

A simple Torch numerical operation on the assigned GPU passed:

```text
device=AMD Instinct MI355X
result=1576448.0 expected=1576448.0 match=True
```

This only establishes basic GPU execution. The prepared native rebuild, its
real FlyDSL numerical GPU smoke, and the focused unit suite are pending and
will be added to this same report.

## Platform context

- https://github.com/amdpilot-org/amdpilotv2/pull/410
- https://github.com/amdpilot-org/amdpilotv2/pull/435

