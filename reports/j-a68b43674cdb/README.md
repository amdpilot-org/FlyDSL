# ISA analysis candidate report

This contribution implements the ISA dump/analysis portion of the proposal in
https://github.com/ROCm/FlyDSL/issues/515 and its mirror
https://github.com/amdpilot-org/FlyDSL/issues/669. It does not claim to
implement physical register pinning, exact scheduler-region preservation,
additional instruction wrappers, or exact immediate-offset buffer operations.

The analyzer consumes the final `*.s` output produced by `FLYDSL_DUMP_IR=1`,
not an earlier compiler stage. See `raw/gfx950-final-isa.s` for the retained
MI350X/gfx950 compiler output, `raw/gfx950-isa-analysis.json` for its report,
and the two pytest logs for unit and GPU evidence.

The prepared native library was loaded from
`/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`. No native source changed,
so `/opt/amdpilot/rebuild-native.py` was not invoked.

Direct `gh issue view` access to the upstream repository was rejected by the
ROCm organization's token-lifetime policy. No credential or host setting was
changed; intake used the provided issue snapshot, the mirror, current source,
and git history.
