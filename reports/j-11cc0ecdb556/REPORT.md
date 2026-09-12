# JobD FlyDSL qualification: j-11cc0ecdb556

This bounded run completed real FlyDSL work on the single visible GPU. The prepared raw-pointer vector-add test passed, and a separate deterministic Torch control confirmed the device's vector-add output against a CPU float64 reference.

## Measurements

- Device: AMD Instinct MI355X, GPU 0 of 1 visible, `gfx950`, unique ID `0x89e8c5cd3767811a`.
- Prepared test: `tests/unit/test_pointer_argument_vec_add.py` passed (`1 passed in 1.04s`, exit 0). It launches FlyDSL JIT code over 4,099 float32 elements and requires maximum error below `1e-5`.
- Independent control: 4,099 float32 GPU additions were finite; maximum absolute error versus a CPU float64 addition of the copied inputs was `2.384185791015625e-07`; checksum `38.46857421845198` (exit 0).
- Stack retained as supplied: Torch `2.9.1+rocm7.2.0.git7e1940d4`, HIP `7.2.26015-fc0010cf6a`.

## Reproduction

From `/job/repo`:

```text
/tmp/amdpilot-repo-j-11cc0ecdb556/venv/bin/python -m pytest -q tests/unit/test_pointer_argument_vec_add.py
/tmp/amdpilot-repo-j-11cc0ecdb556/venv/bin/python reports/j-11cc0ecdb556/numerical_control.py
rocm-smi --showproductname --showuniqueid --showserial --showdriverversion
```

Source revision: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`. FlyDSL Python sources loaded from `/job/repo/python/flydsl`; the pinned native wheel directory was `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`, including `_mlir.cpython-312-x86_64-linux-gnu.so`. Raw command output and separate exit-code files are preserved under `raw/`.

## Limitations

This is evidence for the platform qualification described by [amdpilotv2 PR 438](https://github.com/amdpilot-org/amdpilotv2/pull/438), not an upstream FlyDSL fix. The prepared pytest reports only pass/fail against its `<1e-5` assertion; the exact error above belongs to the independent control. No native rebuild was needed because no native source changed. The simulated receipt-loss fault happens after the real work, so this report neither compensates for it nor claims that PR-receipt recovery succeeded.
