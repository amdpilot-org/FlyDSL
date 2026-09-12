import sys

import numpy as np
import torch
from flydsl._mlir._mlir_libs import _mlirDialectsFly
from flydsl.testing import run_perftest

print(f"testing_source={sys.modules['flydsl.testing'].__file__}")
print(f"native_extension={_mlirDialectsFly.__file__}")

x_np = np.arange(1024, dtype=np.float32)
y_np = np.arange(1024, dtype=np.float32) * 0.5
x = torch.from_numpy(x_np).cuda()
y = torch.from_numpy(y_np).cuda()
result, latency_us = run_perftest(
    lambda a, b: a + b,
    x,
    y,
    num_iters=5,
    num_warmup=2,
    num_rotate_args=1,
)
max_abs_error = np.max(np.abs(result.cpu().numpy() - (x_np + y_np))).item()
assert max_abs_error == 0.0
assert latency_us > 0
print(f"max_abs_error={max_abs_error} latency_us={latency_us}")
print("default_profiler_timing=PASS")
