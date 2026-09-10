# MI350X AOT scalar specialization evidence

This report covers ROCm/FlyDSL issue 621's stronger-AOT request, narrowed to two
legitimate `Constexpr[float]` values (`2.0` and `3.0`). It does not test invalid
schemas, artifact relocation, or cross-version ABI portability.

## Result

The installed FlyDSL `0.2.4` wheel and a job-private FlyDSL `0.3.2` wheel both
compile distinct artifacts for the two scalar values. Fresh-process
`FLYDSL_RUNTIME_RUN_ONLY=1` launches load the matching artifact and pass:

```text
torch.allclose(actual, a + scale*b, rtol=1e-6, atol=1e-6)
```

Both cases have max absolute error `0.0`. The exact cache keys, artifact paths,
SHA-256 identities, event timings, wall timings, source paths, and native paths
are in `raw-results/scalar-aot.json`.
The installed-source baseline and its concrete pre-launch error are summarized
in `raw-results/installed-baseline.json`.

The upstream history already contains scalar and tuple `Constexpr` support and
value-aware cache signatures (ROCm/FlyDSL PR 559). No direct upstream AOT-schema
PR was found, and no core change is needed for this valid-scalar case.

## Reproduction

The probe is `aot_scalar_probe.py`. Run from the repository root:

```bash
CACHE=/tmp/flydsl-cache-j-d9a618efabd6/scalar-installed-0.2.4-v5
PYTHON=/opt/venv/bin/python

$PYTHON reports/j-d9a618efabd6/aot_scalar_probe.py compile \
  "$CACHE" /tmp/flydsl-cache-j-d9a618efabd6/logs/compile.json
$PYTHON reports/j-d9a618efabd6/aot_scalar_probe.py run \
  "$CACHE" /tmp/flydsl-cache-j-d9a618efabd6/logs/run.json
```

For the private `0.3.2` control, install without replacing the image stack and
put that directory first on `PYTHONPATH`:

```bash
WHEEL=/tmp/flydsl-cache-j-d9a618efabd6/wheel-0.3.2
CACHE=/tmp/flydsl-cache-j-d9a618efabd6/scalar-wheel-0.3.2
PYTHON=/opt/venv/bin/python

$PYTHON -m pip install --no-deps --target "$WHEEL" flydsl==0.3.2
PYTHONPATH="$WHEEL" $PYTHON reports/j-d9a618efabd6/aot_scalar_probe.py compile \
  "$CACHE" /tmp/flydsl-cache-j-d9a618efabd6/logs/wheel-compile.json
PYTHONPATH="$WHEEL" $PYTHON reports/j-d9a618efabd6/aot_scalar_probe.py run \
  "$CACHE" /tmp/flydsl-cache-j-d9a618efabd6/logs/wheel-run.json
```

## Boundaries

- `compile` sets `COMPILE_ONLY=1`; it persists artifacts but does not execute,
  so its numerical comparison is intentionally `null`.
- `run` sets `FLYDSL_RUNTIME_RUN_ONLY=1` in a fresh process, loads the cached
  artifact, launches it, synchronizes, and compares against Torch.
- The delivery checkout supplies the probe, but its unbuilt `main` Python tree
  was not paired with a matching native build. The `0.3.2` result is therefore
  an exact-release control, not a claim about `main` or cross-version ABI.
- The installed AIter source baseline failed before launch because its newer
  Python source was paired with FlyDSL `0.2.4`; the concrete error is recorded
  in `/job/baseline-first.json`.
