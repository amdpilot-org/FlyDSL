# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

import inspect

import pytest
import torch

import flydsl.testing as testing
import tests.test_common as legacy_testing


def test_public_testing_api_is_importable_from_installed_namespace():
    expected = {
        "benchmark",
        "checkAllclose",
        "device_memory_profiling",
        "get_trace_perf",
        "log_args",
        "perftest",
        "post_process_data",
        "run_iters",
        "run_iters_rotate",
        "run_perftest",
        "tensor_dump",
        "tensor_load",
        "verify_output",
    }

    assert set(testing.__all__) == expected
    assert all(callable(getattr(testing, name)) for name in expected)


def test_legacy_test_common_reexports_public_objects_without_forking_implementation():
    for name in testing.__all__:
        assert getattr(legacy_testing, name) is getattr(testing, name)


def test_run_helpers_preserve_return_value_and_rotate_arguments():
    seen = []

    assert testing.run_iters(3, lambda value: seen.append(value) or value * 2, 4) == 8
    assert seen == [4, 4, 4]

    seen.clear()
    rotate_args = [((1,), {}), ((2,), {})]
    assert testing.run_iters_rotate(5, lambda value: seen.append(value) or value, rotate_args) == 1
    assert seen == [1, 2, 1, 2, 1]


def test_check_allclose_reports_exact_mismatch_ratio_without_logging():
    actual = torch.tensor([1.0, 2.0, 30.0, 4.0])
    reference = torch.tensor([1.0, 2.0, 3.0, 4.0])

    assert testing.checkAllclose(actual, reference, rtol=0, atol=0, printLog=False) == 0.25
    assert testing.checkAllclose(reference, reference, rtol=0, atol=0, printLog=False) == 0


@pytest.mark.parametrize("dtype", [torch.uint8, torch.float16, torch.bfloat16, torch.float32])
def test_tensor_dump_and_load_round_trip_noncontiguous_tensor(tmp_path, dtype):
    value = torch.arange(12, dtype=torch.float32).to(dtype).reshape(3, 4).T

    testing.tensor_dump(value, "value", str(tmp_path))

    loaded = testing.tensor_load(str(tmp_path / "value.bin"))
    torch.testing.assert_close(loaded, value)


def test_tensor_load_rejects_executable_metadata(tmp_path):
    data = tmp_path / "value.bin"
    data.write_bytes(b"\0\0\0\0")
    (tmp_path / "value.meta").write_text("__import__('os').system('false')\ntorch.float32\n")

    with pytest.raises(ValueError, match="invalid tensor shape metadata"):
        testing.tensor_load(str(data))


def test_public_signatures_retain_existing_keyword_contract():
    assert tuple(inspect.signature(testing.run_perftest).parameters) == (
        "func",
        "args",
        "num_iters",
        "num_warmup",
        "testGraph",
        "num_rotate_args",
        "needTrace",
        "kwargs",
    )
    assert tuple(inspect.signature(testing.checkAllclose).parameters) == (
        "a",
        "b",
        "rtol",
        "atol",
        "tol_err_ratio",
        "msg",
        "printNum",
        "printLog",
    )
