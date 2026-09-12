import json
import torch

torch.manual_seed(20260912)
device = torch.device("cuda:0")
n = 16387
x_cpu = torch.linspace(-3.0, 5.0, n, dtype=torch.float32)
y_cpu = torch.cos(torch.arange(n, dtype=torch.float32) * 0.007) + 0.25
expected = x_cpu * 1.75 + y_cpu
x = x_cpu.to(device)
y = y_cpu.to(device)
actual_gpu = x * 1.75 + y
torch.cuda.synchronize()
actual = actual_gpu.cpu()
diff = (actual - expected).abs()
print(json.dumps({
    "control": "independent deterministic torch ROCm affine vector operation",
    "device": str(device),
    "device_name": torch.cuda.get_device_name(0),
    "elements": n,
    "dtype": str(actual_gpu.dtype),
    "max_abs_error": diff.max().item(),
    "mean_abs_error": diff.mean().item(),
    "allclose_rtol_1e-6_atol_1e-6": torch.allclose(actual, expected, rtol=1e-6, atol=1e-6),
    "gpu_sum": actual_gpu.sum().item(),
    "cpu_reference_sum": expected.sum().item(),
}, indent=2))
assert torch.allclose(actual, expected, rtol=1e-6, atol=1e-6)
