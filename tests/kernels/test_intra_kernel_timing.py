#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

import importlib.util
from pathlib import Path

import pytest

_EXAMPLE_PATH = Path(__file__).resolve().parents[2] / "examples" / "06-intra_kernel_timing.py"
_SPEC = importlib.util.spec_from_file_location("imbalanced_copy", _EXAMPLE_PATH)
imbalanced_copy = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(imbalanced_copy)

pytestmark = [pytest.mark.l2_device, pytest.mark.rocm_lower]


def test_imbalanced_copy_timing_preserves_exact_result():
    result = imbalanced_copy.run_case(work_multiplier=4, block_dim=64, grid_blocks=4, warmup=1, repetitions=3)
    assert result["uninstrumented_exact"]
    assert result["instrumented_exact"]
    assert result["block_cycles"][-1] > result["block_cycles"][0]
