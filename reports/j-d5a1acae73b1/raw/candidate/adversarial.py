import importlib.abc
import sys


class BlockPandas(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "pandas" or fullname.startswith("pandas."):
            raise ModuleNotFoundError("pandas intentionally blocked", name="pandas")
        return None


sys.meta_path.insert(0, BlockPandas())

import numpy as np
import torch
from flydsl._mlir import ir
from flydsl.testing import checkAllclose, run_perftest

print(f"testing_source={sys.modules['flydsl.testing'].__file__}")
print(f"native_ir={ir.__file__}")
print(f"torch={torch.__version__} hip={torch.version.hip}")
print(f"device={torch.cuda.get_device_name(0)} capability={torch.cuda.get_device_capability(0)}")
assert "pandas" not in sys.modules

actual_cpu = torch.tensor([1.0, 2.0, 3.0])
reference_cpu = torch.from_numpy(np.array([1.0, 2.0, 3.0], dtype=np.float32))
assert checkAllclose(actual_cpu, reference_cpu, rtol=0, atol=0, printLog=False) == 0

x_np = np.linspace(-2.0, 2.0, 4096, dtype=np.float32)
y_np = np.linspace(5.0, 7.0, 4096, dtype=np.float32)
x = torch.from_numpy(x_np).cuda()
y = torch.from_numpy(y_np).cuda()
result, latency_us = run_perftest(
    lambda a, b: a + b,
    x,
    y,
    num_iters=8,
    num_warmup=2,
    num_rotate_args=1,
)
expected = x_np + y_np
max_abs_error = np.max(np.abs(result.cpu().numpy() - expected)).item()
assert max_abs_error == 0.0
assert latency_us > 0
assert "pandas" not in sys.modules
print(f"max_abs_error={max_abs_error} latency_us={latency_us}")
print("blocked_pandas_primary_helpers_and_event_timing=PASS")
