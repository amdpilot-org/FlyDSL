#!/usr/bin/env python3

import argparse
import importlib.metadata
import json
import os
import platform
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PYTHON = REPO_ROOT / "python"
NATIVE_PACKAGE = Path(os.environ["FLYDSL_NATIVE_MLIR_PACKAGE"])

sys.path.insert(0, str(SOURCE_PYTHON))

import flydsl  # noqa: E402

flydsl.__path__.append(str(NATIVE_PACKAGE))

import torch  # noqa: E402

import flydsl.compiler as flyc  # noqa: E402
import flydsl.expr as fx  # noqa: E402


@flyc.kernel
def if_liveout_kernel(Out: fx.Tensor, selector: fx.Int32):
    value = fx.Int32(1)
    if selector > fx.Int32(0):
        value = fx.Int32(2)
    post = value + fx.Int32(7)
    Out[0] = post


@flyc.jit
def if_liveout_launch(
    Out: fx.Tensor,
    selector: fx.Int32,
    stream: fx.Stream = fx.Stream(None),
):
    if_liveout_kernel(Out, selector).launch(
        grid=(1, 1, 1), block=(1, 1, 1), stream=stream.value
    )


@flyc.kernel
def nested_if_kernel(Out: fx.Tensor, selector: fx.Int32):
    value = fx.Int32(1)
    if selector > fx.Int32(0):
        value = value + fx.Int32(10)
        if selector > fx.Int32(1):
            value = value + fx.Int32(5)
        else:
            value = value - fx.Int32(2)
    else:
        value = value + fx.Int32(3)
    post = value + fx.Int32(7)
    Out[0] = post


@flyc.jit
def nested_if_launch(
    Out: fx.Tensor,
    selector: fx.Int32,
    stream: fx.Stream = fx.Stream(None),
):
    nested_if_kernel(Out, selector).launch(
        grid=(1, 1, 1), block=(1, 1, 1), stream=stream.value
    )


@flyc.kernel
def for_carry_kernel(Out: fx.Tensor, count: fx.Int32):
    accumulator = fx.Int32(0)
    for index in range(count):
        accumulator = accumulator + index + fx.Int32(1)
    post = accumulator + fx.Int32(100)
    Out[0] = post


@flyc.jit
def for_carry_launch(
    Out: fx.Tensor,
    count: fx.Int32,
    stream: fx.Stream = fx.Stream(None),
):
    for_carry_kernel(Out, count).launch(
        grid=(1, 1, 1), block=(1, 1, 1), stream=stream.value
    )


@flyc.kernel
def while_carry_kernel(Out: fx.Tensor, count: fx.Int32):
    offset = count
    accumulator = fx.Int32(0)
    while offset > fx.Int32(0):
        if offset > fx.Int32(2):
            accumulator = accumulator + fx.Int32(10)
        else:
            accumulator = accumulator + fx.Int32(1)
        offset = offset - fx.Int32(1)
    post = accumulator + fx.Int32(100)
    Out[0] = post


@flyc.jit
def while_carry_launch(
    Out: fx.Tensor,
    count: fx.Int32,
    stream: fx.Stream = fx.Stream(None),
):
    while_carry_kernel(Out, count).launch(
        grid=(1, 1, 1), block=(1, 1, 1), stream=stream.value
    )


@flyc.kernel
def for_nested_branch_kernel(Out: fx.Tensor, count: fx.Int32):
    accumulator = fx.Int32(0)
    for index in range(count):
        if index > fx.Int32(1):
            accumulator = accumulator + fx.Int32(2)
        else:
            accumulator = accumulator + fx.Int32(1)
    post = accumulator + fx.Int32(100)
    Out[0] = post


@flyc.jit
def for_nested_branch_launch(
    Out: fx.Tensor,
    count: fx.Int32,
    stream: fx.Stream = fx.Stream(None),
):
    for_nested_branch_kernel(Out, count).launch(
        grid=(1, 1, 1), block=(1, 1, 1), stream=stream.value
    )


@flyc.kernel
def float_branch_kernel(Out: fx.Tensor, selector: fx.Int32):
    value = fx.Float32(1.0)
    if selector > fx.Int32(0):
        value = value + fx.Float32(0.25)
    else:
        value = value - fx.Float32(0.125)
    post = value + fx.Float32(0.5)
    Out[0] = post


@flyc.jit
def float_branch_launch(
    Out: fx.Tensor,
    selector: fx.Int32,
    stream: fx.Stream = fx.Stream(None),
):
    float_branch_kernel(Out, selector).launch(
        grid=(1, 1, 1), block=(1, 1, 1), stream=stream.value
    )


@dataclass
class Case:
    name: str
    dtype: torch.dtype
    argument: int
    launch: Callable
    reference: Callable



def reference_if_liveout(selector):
    value = 1
    if selector > 0:
        value = 2
    return value + 7



def reference_nested_if(selector):
    value = 1
    if selector > 0:
        value += 10
        if selector > 1:
            value += 5
        else:
            value -= 2
    else:
        value += 3
    return value + 7


def reference_for_carry(count):
    accumulator = 0
    for index in range(count):
        accumulator += index + 1
    return accumulator + 100


def reference_while_carry(count):
    offset = count
    accumulator = 0
    while offset > 0:
        if offset > 2:
            accumulator += 10
        else:
            accumulator += 1
        offset -= 1
    return accumulator + 100



def reference_for_nested_branch(count):
    accumulator = 0
    for index in range(count):
        if index > 1:
            accumulator += 2
        else:
            accumulator += 1
    return accumulator + 100



def reference_float_branch(selector):
    value = 1.0
    if selector > 0:
        value += 0.25
    else:
        value -= 0.125
    return value + 0.5


def make_output(dtype):
    output = torch.zeros(1, device="cuda", dtype=dtype)
    tensor = flyc.from_torch_tensor(output).mark_layout_dynamic(
        leading_dim=0, divisibility=1
    )
    return output, tensor



def run_case(case):
    output, tensor = make_output(case.dtype)
    case.launch(tensor, fx.Int32(case.argument))
    torch.cuda.synchronize()
    expected = torch.tensor(
        [case.reference(case.argument)], device="cuda", dtype=case.dtype
    )
    passed = torch.equal(output, expected)
    difference = (output.to(torch.float64) - expected.to(torch.float64)).abs()
    return {
        "name": case.name,
        "argument": case.argument,
        "actual": output.tolist(),
        "expected": expected.tolist(),
        "max_abs_error": difference.max().item(),
        "gate": "torch.equal (rtol=0, atol=0)",
        "passed": passed,
    }


def run_none_diagnostic():
    try:
        @flyc.kernel
        def none_initialized_kernel(Out: fx.Tensor, selector: fx.Int32):
            value = None
            if selector > fx.Int32(0):
                value = fx.Int32(2)
            Out[0] = value.ir_value()

        @flyc.jit
        def none_initialized_launch(
            Out: fx.Tensor,
            selector: fx.Int32,
            stream: fx.Stream = fx.Stream(None),
        ):
            none_initialized_kernel(Out, selector).launch(
                grid=(1, 1, 1), block=(1, 1, 1), stream=stream.value
            )

        output, tensor = make_output(torch.int32)
        none_initialized_launch(tensor, fx.Int32(1))
        torch.cuda.synchronize()
    except TypeError as error:
        return {
            "name": "none_initialized_dynamic_if",
            "status": "pass",
            "diagnostic": str(error),
        }
    return {
        "name": "none_initialized_dynamic_if",
        "status": "fail",
        "diagnostic": "Expected a TypeError diagnostic, but execution succeeded.",
        "actual": output.tolist(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError("A CUDA/ROCm GPU is required")

    cases = [
        Case("if_liveout", torch.int32, 1, if_liveout_launch, reference_if_liveout),
        Case("nested_if", torch.int32, 2, nested_if_launch, reference_nested_if),
        Case("for_carry", torch.int32, 5, for_carry_launch, reference_for_carry),
        Case("while_carry", torch.int32, 5, while_carry_launch, reference_while_carry),
        Case(
            "for_nested_branch",
            torch.int32,
            5,
            for_nested_branch_launch,
            reference_for_nested_branch,
        ),
        Case(
            "float_branch",
            torch.float32,
            0,
            float_branch_launch,
            reference_float_branch,
        ),
    ]

    results = {
        "schema_version": 1,
        "source_commit": os.environ.get("FLYDSL_SOURCE_COMMIT", "unknown"),
        "source_python_path": str(SOURCE_PYTHON),
        "native_mlir_package": str(NATIVE_PACKAGE),
        "flydsl_source_version": flydsl.__version__,
        "installed_flydsl_version": importlib.metadata.version("flydsl"),
        "native_flydsl_version": re.search(
            r'^__version__\s*=\s*["\']([^"\']+)',
            (NATIVE_PACKAGE / "__init__.py").read_text(),
            re.MULTILINE,
        ).group(1),
        "image_identity": os.environ.get("FLYDSL_IMAGE_ID", "unknown"),
        "torch_version": torch.__version__,
        "torch_hip_version": torch.version.hip,
        "gpu_name": torch.cuda.get_device_name(0),
        "gpu_arch": os.environ.get("FLYDSL_GPU_ARCH", "unknown"),
        "python_version": platform.python_version(),
        "cases": [run_case(case) for case in cases],
        "diagnostics": [run_none_diagnostic()],
    }
    results["all_numeric_cases_passed"] = all(
        case["passed"] for case in results["cases"]
    )
    results["all_diagnostics_passed"] = all(
        diagnostic["status"] == "pass" for diagnostic in results["diagnostics"]
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
    if not results["all_numeric_cases_passed"] or not results["all_diagnostics_passed"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
