# AMDPilot interrupted-stream qualification j-4b56b067d03b

This report records qualification evidence against FlyDSL revision
`acf7e67b7d22847e345938ca54fcc137bd7b2a1f`. It is not an upstream bug fix or
a claim that the qualification platform recovered. Platform context:
https://github.com/amdpilot-org/amdpilotv2/pull/439.

The initial unit test ran before the interruption checkpoint. Continuity was
confirmed from nonce `9d5491fa-c39f-4470-a5e4-c69bfc6eaa30`; the initial test
was not repeated after continuation.

Reproduce the independent control from the repository root with:

```console
/tmp/amdpilot-repo-j-4b56b067d03b/venv/bin/python reports/j-4b56b067d03b/probes/raw_pointer_masked_tail.py
```

The control constructs deterministic device inputs, passes their raw pointers
to FlyDSL, and launches blocks over non-aligned logical sizes. Output padding is
initialized to a sentinel so the report checks both exact active values and
that masked tail lanes remain untouched.
