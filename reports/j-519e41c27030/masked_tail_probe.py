#!/usr/bin/env python3

"""Independent masked-tail GPU check for the pointer-argument vector add."""

import importlib.util
import json
from pathlib import Path

import torch


REPO = Path(__file__).resolve().parents[2]
TEST_PATH = REPO / "tests/unit/test_pointer_argument_vec_add.py"
spec = importlib.util.spec_from_file_location("pointer_argument_vec_add", TEST_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

torch.manual_seed(51941)
length = 1003
capacity = 1280
sentinel = -9876.5

a = torch.randn(capacity, device="cuda", dtype=torch.float32)
b = torch.randn(capacity, device="cuda", dtype=torch.float32)
out = torch.full((capacity,), sentinel, device="cuda", dtype=torch.float32)
reference = torch.add(a[:length], b[:length])

module.pointer_vec_add(
    module.flyc.from_c_void_p(module.fx.Float32, a.data_ptr()),
    module.flyc.from_c_void_p(module.fx.Float32, b.data_ptr()),
    module.flyc.from_c_void_p(module.fx.Float32, out.data_ptr()),
    length,
    stream=torch.cuda.current_stream(),
)
torch.cuda.synchronize()

active = out[:length]
tail = out[length:]
max_abs_error = torch.max(torch.abs(active - reference)).item()
mismatch_count = torch.count_nonzero(active != reference).item()
tail_changed_count = torch.count_nonzero(tail != sentinel).item()
result = {
    "length": length,
    "capacity": capacity,
    "tail_elements": capacity - length,
    "sentinel": sentinel,
    "max_abs_error": max_abs_error,
    "exact_mismatch_count": mismatch_count,
    "tail_changed_count": tail_changed_count,
    "passed": max_abs_error < 1e-5 and tail_changed_count == 0,
}
print(json.dumps(result, indent=2, sort_keys=True))
if not result["passed"]:
    raise SystemExit(1)
