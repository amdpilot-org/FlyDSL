# Commands and operations

The following bounded commands were used for setup, validation, and evidence
collection. Exploratory searches used `rg`, `find`, `sed`, and `git diff`; no
node-wide state was modified.

```bash
git clone --depth 1 https://github.com/amdpilot-org/FlyDSL.git /job/FlyDSL
gh issue view 831 --repo ROCm/FlyDSL
curl -fL https://api.github.com/repos/ROCm/FlyDSL/issues/831
curl -fL https://api.github.com/repos/ROCm/FlyDSL/issues/831/comments
curl -fL https://api.github.com/repos/ROCm/FlyDSL/issues/831/timeline
/opt/venv/bin/python -m pytest tests/kernels/test_intra_kernel_timing.py -q
FLYDSL_GPU_ARCH=gfx942 /opt/venv/bin/python examples/06-intra_kernel_timing.py
FLYDSL_GPU_ARCH=gfx942 /opt/venv/bin/python examples/06-intra_kernel_timing.py \
  --grid-blocks 16 --work-multiplier 64 --repetitions 50
FLYDSL_GPU_ARCH=gfx942 /opt/venv/bin/python examples/06-intra_kernel_timing.py \
  --grid-blocks 1 --work-multiplier 4096 --repetitions 30
rocm-smi -c -m -p -t --showdriverversion --showproductname --showserial --showuniqueid
rocminfo
hipcc --version
/opt/venv/bin/python -m pip show flydsl torch
/opt/venv/bin/python -m compileall -q examples/06-intra_kernel_timing.py \
  tests/kernels/test_intra_kernel_timing.py
```
