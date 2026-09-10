# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""GPU-free tests for the reusable profiling timer."""

import os
import importlib
import subprocess
import sys
from pathlib import Path

import pytest

import flydsl.profiling as profiling
from flydsl.profiling import _bench_batch_sizes, do_bench

pytestmark = pytest.mark.l0_backend_agnostic


class FakeEvent:
    def __init__(self, cuda, enable_timing):
        assert enable_timing
        self.cuda = cuda
        self.timestamp = None

    def record(self):
        self.timestamp = self.cuda.clock
        self.cuda.operations.append("event")

    def synchronize(self):
        self.cuda.event_synchronizes += 1

    def elapsed_time(self, other):
        return other.timestamp - self.timestamp


class FakeCuda:
    def __init__(self):
        self.clock = 0.0
        self.operations = []
        self.device_synchronizes = 0
        self.event_synchronizes = 0

    def is_available(self):
        return True

    def synchronize(self):
        self.device_synchronizes += 1

    def _sleep(self, cycles):
        assert cycles > 0
        self.operations.append("backlog")
        self.clock += 100.0

    def Event(self, enable_timing):
        return FakeEvent(self, enable_timing)


class FakeTorch:
    def __init__(self):
        self.cuda = FakeCuda()


def _install_fake_torch(monkeypatch):
    torch = FakeTorch()
    monkeypatch.setattr(profiling, "_get_torch", lambda: torch)
    return torch


def test_autotune_keeps_do_bench_compatibility_alias():
    autotune = importlib.import_module("flydsl.autotune")
    assert autotune.do_bench is profiling.do_bench


def test_importing_flydsl_does_not_import_pytorch():
    repo_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "python") + os.pathsep + env.get("PYTHONPATH", "")
    code = "import flydsl, sys; print('torch' in sys.modules)"
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "False"


def test_bench_batch_sizes_preserve_the_requested_call_count():
    assert _bench_batch_sizes(1) == [1]
    assert _bench_batch_sizes(7) == [2, 2, 1, 1, 1]
    assert sum(_bench_batch_sizes(25)) == 25
    with pytest.raises(ValueError, match="positive integer"):
        _bench_batch_sizes(0)


def test_do_bench_uses_a_backlogged_batched_event_window(monkeypatch):
    torch = _install_fake_torch(monkeypatch)
    calls = 0

    def fn():
        nonlocal calls
        calls += 1
        torch.cuda.operations.append("kernel")
        torch.cuda.clock += 2.0

    assert do_bench(fn, warmup=3, rep=7) == 2.0
    assert calls == 10
    assert torch.cuda.device_synchronizes == 1
    assert torch.cuda.event_synchronizes == 5
    assert torch.cuda.operations[3:] == [
        "backlog",
        "event",
        "kernel",
        "kernel",
        "event",
        "backlog",
        "event",
        "kernel",
        "kernel",
        "event",
        "backlog",
        "event",
        "kernel",
        "event",
        "backlog",
        "event",
        "kernel",
        "event",
        "backlog",
        "event",
        "kernel",
        "event",
    ]


def test_do_bench_quantiles_summarize_batch_averages(monkeypatch):
    torch = _install_fake_torch(monkeypatch)

    def fn():
        torch.cuda.clock += 3.0

    assert do_bench(fn, warmup=0, rep=5, quantiles=[0.0, 0.5, 0.9]) == [3.0, 3.0, 3.0]


def test_do_bench_fails_closed_without_a_gpu_backlog(monkeypatch):
    torch = _install_fake_torch(monkeypatch)
    torch.cuda._sleep = None
    with pytest.raises(RuntimeError, match="GPU-side backlog"):
        do_bench(lambda: None)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"warmup": -1, "rep": 1}, "warmup must be a non-negative integer"),
        ({"warmup": 0, "rep": 0}, "rep must be a positive integer"),
        ({"warmup": 0, "rep": 1, "quantiles": [-0.1]}, "quantiles must be between 0 and 1"),
        ({"warmup": 0, "rep": 1, "quantiles": [1.1]}, "quantiles must be between 0 and 1"),
    ],
)
def test_do_bench_rejects_invalid_arguments(kwargs, message):
    with pytest.raises(ValueError, match=message):
        do_bench(lambda: None, **kwargs)
