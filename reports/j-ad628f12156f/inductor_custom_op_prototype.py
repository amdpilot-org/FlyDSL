import argparse
import importlib.util
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import torch


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PATH = REPOSITORY_ROOT / "examples" / "01-vectorAdd.py"


def load_vector_add_example():
    specification = importlib.util.spec_from_file_location(
        "flydsl_vector_add_example", EXAMPLE_PATH
    )
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


vector_add_example = load_vector_add_example()


@torch.library.custom_op(
    "flydsl_prototype::vector_add",
    mutates_args={"output"},
    device_types="cuda",
)
def flydsl_vector_add(
    lhs: torch.Tensor,
    rhs: torch.Tensor,
    output: torch.Tensor,
) -> None:
    vector_add_example.vector_add(
        lhs,
        rhs,
        output,
        stream=torch.cuda.current_stream(),
    )


@torch.library.register_fake("flydsl_prototype::vector_add")
def flydsl_vector_add_fake(
    lhs: torch.Tensor,
    rhs: torch.Tensor,
    output: torch.Tensor,
) -> None:
    return None


def forward(lhs: torch.Tensor, rhs: torch.Tensor, output: torch.Tensor):
    flydsl_vector_add(lhs, rhs, output)
    return output


def check_fake_registration():
    with torch._subclasses.FakeTensorMode(allow_non_fake_inputs=True):
        lhs = torch.empty((2, 3), device="cuda", dtype=torch.float32)
        rhs = torch.empty((2, 3), device="cuda", dtype=torch.float32)
        output = torch.empty((2, 3), device="cuda", dtype=torch.float32)
        result = flydsl_vector_add(lhs, rhs, output)
    return {
        "result_type": type(result).__name__,
        "lhs_type": type(lhs).__name__,
        "passed": result is None,
    }


def timed_execution(callable, lhs, rhs, output):
    output.zero_()
    start_event = torch.cuda.Event(enable_timing=True)
    end_event = torch.cuda.Event(enable_timing=True)
    wall_start = time.perf_counter()
    start_event.record()
    result = callable(lhs, rhs, output)
    end_event.record()
    torch.cuda.synchronize()
    wall_seconds = time.perf_counter() - wall_start
    expected = lhs + rhs
    max_abs_difference = (output - expected).abs().max().item()
    return {
        "result_shape": tuple(result.shape),
        "result_dtype": str(result.dtype),
        "max_abs_difference": max_abs_difference,
        "allclose_default": bool(torch.allclose(output, expected)),
        "equal": bool(torch.equal(output, expected)),
        "gpu_milliseconds": start_event.elapsed_time(end_event),
        "wall_milliseconds": wall_seconds * 1000.0,
    }


def collect_environment():
    import flydsl
    import triton

    source_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    source_branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    torch_library = Path(torch.__file__).parent / "lib"
    flydsl_native_root = Path(flydsl.__file__).parent / "_mlir" / "_mlir_libs"
    device_properties = torch.cuda.get_device_properties(0)
    rocm_runtime = Path("/opt/rocm/lib/libamdhip64.so")

    return {
        "source_commit": source_commit,
        "source_branch": source_branch,
        "source_example": str(EXAMPLE_PATH),
        "flydsl_module": flydsl.__file__,
        "flydsl_native_modules": [
            str(path)
            for path in sorted(flydsl_native_root.glob("*.so*"))
        ],
        "torch_native_modules": [
            str(path)
            for path in sorted(torch_library.glob("libtorch*.so*"))
        ],
        "rocm_runtime_module": str(rocm_runtime.resolve()) if rocm_runtime.exists() else None,
        "python_executable": sys.executable,
        "python_version": sys.version,
        "platform": platform.platform(),
        "torch_version": torch.__version__,
        "torch_module": torch.__file__,
        "triton_version": triton.__version__,
        "triton_module": triton.__file__,
        "hip_version": torch.version.hip,
        "cuda_device_name": torch.cuda.get_device_name(),
        "cuda_device_capability": torch.cuda.get_device_capability(),
        "cuda_device_uuid": str(device_properties.uuid),
        "cuda_pci_bus_id": device_properties.pci_bus_id,
        "cuda_total_memory_bytes": device_properties.total_memory,
        "current_stream": torch.cuda.current_stream().cuda_stream,
        "compile_backend": "inductor",
        "compile_fullgraph": True,
        "compile_dynamic": False,
        "flydsl_cache_dir": __import__("os").environ.get("FLYDSL_RUNTIME_CACHE_DIR"),
        "triton_cache_dir": __import__("os").environ.get("TRITON_CACHE_DIR"),
        "inductor_cache_dir": __import__("os").environ.get("TORCHINDUCTOR_CACHE_DIR"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    arguments = parser.parse_args()

    execution_stream = torch.cuda.Stream()
    with execution_stream:
        torch.manual_seed(0)
        compiled_forward = torch.compile(
            forward,
            fullgraph=True,
            dynamic=False,
            backend="inductor",
        )
        cases = {
            "aligned": (128, 128),
            "tail": (100, 1000),
        }
        results = {
            "environment": collect_environment(),
            "fake_check": check_fake_registration(),
            "cases": {},
        }

        for case_name, shape in cases.items():
            lhs = torch.randn(shape, dtype=torch.float32, device="cuda")
            rhs = torch.randn(shape, dtype=torch.float32, device="cuda")
            output = torch.zeros(shape, dtype=torch.float32, device="cuda")
            results["cases"][case_name] = {
                "shape": shape,
                "eager": timed_execution(forward, lhs, rhs, output),
                "compiled_cold": timed_execution(compiled_forward, lhs, rhs, output),
                "compiled_warm": timed_execution(compiled_forward, lhs, rhs, output),
        }

    serialized = json.dumps(results, indent=2, sort_keys=True)
    print(serialized)
    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(serialized + "\n")


if __name__ == "__main__":
    main()
