# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""GPU regression for the two floating-point extrema contracts.

MLIR ``maximumf``/``minimumf`` follow IEEE maximum/minimum and propagate NaN,
whereas ``maxnumf``/``minnumf`` follow the non-NaN-wins ``maximumNumber`` /
``minimumNumber`` contract.  See:
https://mlir.llvm.org/docs/Dialects/ArithOps/#arithmaximumf-arithmaximumfop
https://llvm.org/docs/LangRef.html#llvm-maxnum-intrinsic
"""

import math

import pytest

import flydsl.compiler as flyc
import flydsl.expr as fx

try:
    import torch
except ImportError:
    torch = None

pytestmark = [pytest.mark.l2_device, pytest.mark.rocm_lower]

if torch is None or not torch.cuda.is_available():
    pytest.skip("CUDA/ROCm not available", allow_module_level=True)


@flyc.kernel
def extrema_semantics_kernel(src: fx.Pointer, dst: fx.Pointer):
    row = fx.Int32(fx.block_idx.x)
    base = row * 4
    values = fx.Vector.from_elements([src[base + i] for i in fx.range_constexpr(4)], fx.Float32)
    a, b = values[0], values[1]
    out = row * 6
    dst[out + 0] = a.minimumf(b)
    dst[out + 1] = a.maximumf(b)
    dst[out + 2] = fx.minnumf(a, b)
    dst[out + 3] = fx.maxnumf(a, b)
    dst[out + 4] = values.reduce("min")
    dst[out + 5] = values.reduce("max")


@flyc.jit
def run_extrema_semantics(src: fx.Pointer, dst: fx.Pointer, rows: fx.Int32):
    extrema_semantics_kernel(src, dst).launch(grid=(rows, 1, 1), block=(1, 1, 1))


def _assert_value(actual, expected):
    if math.isnan(expected):
        assert math.isnan(actual)
    else:
        assert actual == expected
        if expected == 0.0:
            assert math.copysign(1.0, actual) == math.copysign(1.0, expected)


def test_scalar_and_vector_extrema_nan_semantics_on_gpu():
    max_finite = torch.finfo(torch.float32).max
    rows = [
        [math.nan, 1.0, -math.inf, math.inf],
        [-0.0, 0.0, -0.0, 0.0],
        [math.inf, -math.inf, 1.0, -1.0],
        [max_finite, -max_finite, max_finite, -max_finite],
    ]
    src = torch.tensor(rows, dtype=torch.float32, device="cuda").flatten()
    dst = torch.empty(len(rows) * 6, dtype=torch.float32, device="cuda")

    run_extrema_semantics(
        flyc.from_c_void_p(fx.Float32, src.data_ptr()),
        flyc.from_c_void_p(fx.Float32, dst.data_ptr()),
        len(rows),
    )
    torch.cuda.synchronize()

    # Independent expected values from the documented contracts above.
    expected = [
        [math.nan, math.nan, 1.0, 1.0, math.nan, math.nan],
        [-0.0, 0.0, -0.0, 0.0, -0.0, 0.0],
        [-math.inf, math.inf, -math.inf, math.inf, -math.inf, math.inf],
        [-max_finite, max_finite, -max_finite, max_finite, -max_finite, max_finite],
    ]
    actual = dst.reshape(len(rows), 6).cpu().tolist()
    print(f"extrema GPU output: {actual}")
    for actual_row, expected_row in zip(actual, expected, strict=True):
        for actual, reference in zip(actual_row, expected_row, strict=True):
            _assert_value(actual, reference)
