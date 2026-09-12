# FlyDSL GPU qualification for JobD

At source revision `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`, the prepared raw-pointer vector-add pytest passed on the single assigned AMD Instinct MI355X (`gfx950`) GPU. The independent deterministic control launched the same FlyDSL raw-pointer kernel over 1,027 FP32 elements and matched a CPU reference exactly: maximum absolute error `0.0`, output/reference sum `1303.9260690659285`, and `allclose(rtol=1e-6, atol=1e-6)` passed.

## Reproduction

From `/job/repo`, using the prepared interpreter:

```text
/tmp/amdpilot-repo-j-833dd346ed89/venv/bin/python -m pytest -vv -s tests/unit/test_pointer_argument_vec_add.py
```

This exited `0` with `1 passed in 1.00s`. The second command was an inline Python control using the same interpreter; it imported `tests/unit/test_pointer_argument_vec_add.py`, launched `pointer_vec_add` on deterministic inputs, synchronized the GPU, copied output to CPU, and compared it with a CPU reference. It also exited `0`. Complete output and exit-code files are under `raw/`.

## Environment and limits

Python FlyDSL source came from `/job/repo/python/flydsl/expr/__init__.py`; pinned native components came from `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`. Torch was `2.9.1+rocm7.2.0.git7e1940d4` with HIP `7.2.26015-fc0010cf6a`; neither Torch nor ROCm was changed.

This is a bounded observation of one kernel path, device, and revision—not an upstream FlyDSL fix or broad compatibility result. No native code was rebuilt and no wider suite was run. Platform context is [amdpilotv2 PR 438](https://github.com/amdpilot-org/amdpilotv2/pull/438). The receipt-loss fault is externally simulated after this work, so these measurements do not claim that platform recovery succeeded.
