#!/usr/bin/env python3
"""Validate FlyDSL expression extrema on the assigned gfx950 GPU."""

from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path

import torch

import flydsl.compiler as flyc
import flydsl.expr as fx


FLOAT_OPS = ("max", "min", "maxnumf", "minnumf", "maximumf", "minimumf")
INT_OPS = ("max", "min")


@flyc.kernel
def float_extrema_kernel(a: fx.Pointer, b: fx.Pointer, out: fx.Pointer):
    out[0] = fx.max(a[0], b[0])
    out[1] = fx.min(a[0], b[0])
    out[2] = fx.maxnumf(a[0], b[0])
    out[3] = fx.minnumf(a[0], b[0])
    out[4] = fx.maximumf(a[0], b[0])
    out[5] = fx.minimumf(a[0], b[0])


@flyc.kernel
def int_extrema_kernel(a, b, out: fx.Pointer):
    out[0] = fx.max(a, b)
    out[1] = fx.min(a, b)


@flyc.jit
def float_extrema(a: fx.Pointer, b: fx.Pointer, out: fx.Pointer, stream: fx.Stream = fx.Stream(None)):
    float_extrema_kernel(a, b, out).launch(
        grid=(1, 1, 1), block=(1, 1, 1), stream=stream
    )


@flyc.jit
def signed_int_extrema(a: fx.Int32, b: fx.Int32, out: fx.Pointer, stream: fx.Stream = fx.Stream(None)):
    int_extrema_kernel(a, b, out).launch(
        grid=(1, 1, 1), block=(1, 1, 1), stream=stream
    )


@flyc.jit
def unsigned_int_extrema(a: fx.Uint32, b: fx.Uint32, out: fx.Pointer, stream: fx.Stream = fx.Stream(None)):
    int_extrema_kernel(a, b, out).launch(
        grid=(1, 1, 1), block=(1, 1, 1), stream=stream
    )


def float_bits(value: float) -> str:
    return f"0x{struct.unpack('<I', struct.pack('<f', value))[0]:08x}"


def float_from_bits(bits: int) -> float:
    return struct.unpack('<f', struct.pack('<I', bits))[0]


def float_oracle(operation: str, lhs: float, rhs: float) -> tuple[bool, str]:
    lhs_nan = math.isnan(lhs)
    rhs_nan = math.isnan(rhs)
    lhs_zero = lhs == 0.0 and math.copysign(1.0, lhs) < 0.0
    rhs_zero = rhs == 0.0 and math.copysign(1.0, rhs) < 0.0

    if operation in ("max", "maximumf"):
        if lhs_nan or rhs_nan:
            return True, "NaN"
        if lhs_zero != rhs_zero:
            return True, "+0.0"
        return True, float_bits(max(lhs, rhs))
    if operation in ("min", "minimumf"):
        if lhs_nan or rhs_nan:
            return True, "NaN"
        if lhs_zero != rhs_zero:
            return True, "-0.0"
        return True, float_bits(min(lhs, rhs))
    if operation in ("maxnumf", "minnumf"):
        if lhs_nan and rhs_nan:
            return True, "NaN"
        if lhs_nan:
            return True, float_bits(rhs)
        if rhs_nan:
            return True, float_bits(lhs)
        if lhs_zero != rhs_zero:
            return True, "either +0.0 or -0.0"
        return True, float_bits(max(lhs, rhs) if operation == "maxnumf" else min(lhs, rhs))
    raise ValueError(operation)


def check_float(operation: str, lhs: float, rhs: float, actual: float) -> tuple[bool, str, str]:
    valid, expected = float_oracle(operation, lhs, rhs)
    actual_nan = math.isnan(actual)
    actual_bits = "NaN" if actual_nan else float_bits(actual)

    if expected == "NaN":
        passed = actual_nan
    elif expected == "either +0.0 or -0.0":
        passed = actual == 0.0
    elif expected in ("+0.0", "-0.0"):
        expected_zero = 0.0 if expected == "+0.0" else -0.0
        passed = not actual_nan and actual == 0.0 and math.copysign(1.0, actual) == math.copysign(
            1.0, expected_zero
        )
    else:
        expected_value = float_from_bits(int(expected, 16))
        passed = not actual_nan and actual_bits == float_bits(expected_value)
    return passed, expected, actual_bits


def pointer(tensor: torch.Tensor, dtype):
    return flyc.from_c_void_p(dtype, tensor.data_ptr())


def run_float_cases() -> list[dict]:
    cases = [
        ("finite_ascending", -3.0, 4.0),
        ("finite_descending", 4.0, -3.0),
        ("nan_left", float("nan"), 7.0),
        ("nan_right", 7.0, float("nan")),
        ("negative_zero_left", -0.0, 0.0),
        ("positive_zero_left", 0.0, -0.0),
    ]
    results = []
    stream = torch.cuda.current_stream()
    for name, lhs, rhs in cases:
        lhs_tensor = torch.tensor([lhs], dtype=torch.float32, device="cuda")
        rhs_tensor = torch.tensor([rhs], dtype=torch.float32, device="cuda")
        out_tensor = torch.empty(6, dtype=torch.float32, device="cuda")
        float_extrema(
            pointer(lhs_tensor, fx.Float32),
            pointer(rhs_tensor, fx.Float32),
            pointer(out_tensor, fx.Float32),
            stream=stream,
        )
        torch.cuda.synchronize()
        actual = out_tensor.cpu().tolist()
        for index, operation in enumerate(FLOAT_OPS):
            passed, expected, actual_bits = check_float(operation, lhs, rhs, actual[index])
            results.append(
                {
                    "family": "float32",
                    "case": name,
                    "operation": operation,
                    "lhs_bits": float_bits(lhs),
                    "rhs_bits": float_bits(rhs),
                    "expected": expected,
                    "actual": actual_bits,
                    "pass": passed,
                }
            )
    return results


def run_int_cases() -> list[dict]:
    cases = [
        ("int32", torch.int32, fx.Int32, True, -1, 1),
        ("int32_swapped", torch.int32, fx.Int32, True, 1, -1),
        ("uint32", torch.uint32, fx.Uint32, False, 0xFFFFFFFF, 1),
        ("uint32_swapped", torch.uint32, fx.Uint32, False, 1, 0xFFFFFFFF),
    ]
    results = []
    stream = torch.cuda.current_stream()
    for name, torch_dtype, fly_dtype, signed, lhs, rhs in cases:
        lhs_tensor = torch.tensor([lhs], dtype=torch_dtype, device="cuda")
        rhs_tensor = torch.tensor([rhs], dtype=torch_dtype, device="cuda")
        out_tensor = torch.empty(2, dtype=torch_dtype, device="cuda")
        launcher = signed_int_extrema if signed else unsigned_int_extrema
        launcher(
            lhs,
            rhs,
            pointer(out_tensor, fly_dtype),
            stream=stream,
        )
        torch.cuda.synchronize()
        actual = out_tensor.cpu().tolist()
        lhs_value = lhs if signed else lhs & 0xFFFFFFFF
        rhs_value = rhs if signed else rhs & 0xFFFFFFFF
        for index, operation in enumerate(INT_OPS):
            expected = max(lhs_value, rhs_value) if operation == "max" else min(lhs_value, rhs_value)
            if not signed:
                expected &= 0xFFFFFFFF
            results.append(
                {
                    "family": name,
                    "case": "signed" if signed else "unsigned",
                    "operation": operation,
                    "lhs": lhs_value,
                    "rhs": rhs_value,
                    "expected": expected,
                    "actual": actual[index] & 0xFFFFFFFF if not signed else actual[index],
                    "pass": actual[index] == expected,
                }
            )
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA/ROCm GPU is not available")
    if torch.cuda.get_device_capability(0) != (9, 5):
        raise RuntimeError(f"expected gfx950, got {torch.cuda.get_device_capability(0)}")

    results = run_float_cases() + run_int_cases()
    report = {
        "gpu": torch.cuda.get_device_name(0),
        "capability": list(torch.cuda.get_device_capability(0)),
        "torch": torch.__version__,
        "torch_hip": torch.version.hip,
        "results": results,
        "passed": sum(result["pass"] for result in results),
        "failed": sum(not result["pass"] for result in results),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
