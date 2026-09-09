#!/usr/bin/env python3
"""Validate fx.coop.BlockReduce ADD on the assigned gfx942 device."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import time
from collections import Counter
from pathlib import Path

import flydsl.compiler as flyc
import flydsl.expr as fx
import flydsl
import torch


ALGORITHMS = (
    fx.coop.BlockReduceAlgorithm.WARP_REDUCTIONS,
    fx.coop.BlockReduceAlgorithm.RAKING,
)
BLOCKS = (64, 128, 256, 1024)
TAIL_LENGTHS = (65, 133, 1000, 4097)
TAIL_BLOCKS = (64, 256)
TIMING_ITERATIONS = 100


def source_root() -> Path:
    return Path(__file__).resolve().parents[2]


def git_commit() -> str:
    return subprocess.check_output(
        ["git", "-C", str(source_root()), "rev-parse", "HEAD"], text=True
    ).strip()


def tool_version(command: list[str]) -> str:
    try:
        return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        return f"unavailable: {error}"


def linear_tid(block_size: tuple[int, int, int]) -> object:
    tid = fx.thread_idx.x
    if block_size[1] > 1 or block_size[2] > 1:
        tid = tid + fx.thread_idx.y * block_size[0]
        tid = tid + fx.thread_idx.z * (block_size[0] * block_size[1])
    return tid


def make_launch(
    block: int,
    algorithm: object,
    dtype: object,
    torch_dtype: torch.dtype,
    blocks: int = 1,
):
    block_size = (block, 1, 1)

    @flyc.kernel(known_block_size=list(block_size))
    def kernel(A: fx.Tensor, Out: fx.Tensor):
        block_reduce = fx.coop.BlockReduce[dtype, block_size, algorithm]
        storage = fx.SharedAllocator().allocate(block_reduce.SharedStorage).peek()
        tid = linear_tid(block_size)
        global_tid = fx.block_idx.x * block + tid
        total = block_reduce(A[global_tid], fx.ReductionOp.ADD, storage=storage)
        if tid == 0:
            Out[fx.block_idx.x] = total

    @flyc.jit
    def launch(A: fx.Tensor, Out: fx.Tensor, stream: fx.Stream = fx.Stream(None)):
        kernel(A, Out).launch(grid=(blocks, 1, 1), block=block_size, stream=stream)

    return launch, torch_dtype


def run_blocks(
    launch, values: torch.Tensor, blocks: int, torch_dtype: torch.dtype
) -> torch.Tensor:
    out = torch.zeros(blocks, dtype=torch_dtype, device="cuda")
    stream = torch.cuda.Stream()
    launch(values, out, stream=stream)
    stream.synchronize()
    return out.cpu()


def reference(values: torch.Tensor, block: int, torch_dtype: torch.dtype) -> torch.Tensor:
    folded = values.cpu().to(torch.int64 if not torch_dtype.is_floating_point else torch.float64)
    expected = folded.reshape(-1, block).sum(1)
    if torch_dtype.is_floating_point:
        return expected.to(torch_dtype)
    bits = 8 * torch_dtype.itemsize
    wrapped = expected % (1 << bits)
    if torch_dtype.is_signed:
        wrapped = torch.where(wrapped >= (1 << (bits - 1)), wrapped - (1 << bits), wrapped)
    return wrapped.to(torch_dtype)


def difference(out: torch.Tensor, expected: torch.Tensor) -> dict[str, float]:
    if not expected.dtype.is_floating_point:
        return {
            "max_abs": float((out.to(torch.int64) - expected.to(torch.int64)).abs().max()),
            "max_rel": 0.0,
        }
    delta = (out.to(torch.float64) - expected.to(torch.float64)).abs()
    denominator = expected.to(torch.float64).abs().clamp_min(torch.finfo(torch.float32).tiny)
    return {
        "max_abs": float(delta.max()),
        "max_rel": float((delta / denominator).max()),
    }


def check(name: str, out: torch.Tensor, expected: torch.Tensor, results: list[dict]):
    if expected.dtype.is_floating_point:
        passed = torch.allclose(out, expected, rtol=2e-5, atol=1e-5)
    else:
        passed = torch.equal(out, expected)
    diff = difference(out, expected)
    results.append({"case": name, "passed": passed, **diff})
    print(f"{name:52s} {'PASS' if passed else 'FAIL'} abs={diff['max_abs']:.9g} rel={diff['max_rel']:.9g}")
    if not passed:
        raise AssertionError(f"{name}: out={out.tolist()} expected={expected.tolist()}")


def validate_full_tiles(results: list[dict]) -> None:
    for algorithm in ALGORITHMS:
        for block in BLOCKS:
            launch, dtype = make_launch(block, algorithm, fx.Int32, torch.int32)
            values = torch.arange(block, dtype=torch.int32, device="cuda")
            out = run_blocks(launch, values, 1, dtype)
            check(
                f"full-tile/{algorithm.name}/block-{block}",
                out,
                reference(values, block, dtype),
                results,
            )


def validate_tails(results: list[dict]) -> None:
    for algorithm in ALGORITHMS:
        for block in TAIL_BLOCKS:
            for length in TAIL_LENGTHS:
                blocks = math.ceil(length / block)
                padded_length = blocks * block
                values = torch.arange(length, dtype=torch.int32, device="cuda")
                padded = torch.zeros(padded_length, dtype=torch.int32, device="cuda")
                padded[:length] = values
                launch, dtype = make_launch(
                    block, algorithm, fx.Int32, torch.int32, blocks
                )
                out = run_blocks(launch, padded, blocks, dtype)
                check(
                    f"tail/{algorithm.name}/block-{block}/length-{length}",
                    out,
                    reference(padded, block, dtype),
                    results,
                )


def validate_adversarial(results: list[dict]) -> None:
    finfo = torch.finfo(torch.float32)
    float_pattern = torch.tensor(
        [
            finfo.tiny,
            -finfo.tiny,
            finfo.max / 2,
            -finfo.max / 2,
            finfo.tiny,
            -finfo.tiny,
            1.0,
            -1.0,
        ],
        dtype=torch.float32,
        device="cuda",
    )
    int_info = torch.iinfo(torch.int32)
    int_pattern = torch.tensor(
        [int_info.min, int_info.max, -1, 1, 0, 0, int_info.min, int_info.max],
        dtype=torch.int32,
        device="cuda",
    )
    for algorithm in ALGORITHMS:
        for block in (64, 256):
            float_values = float_pattern.repeat(block // float_pattern.numel())
            float_launch, float_dtype = make_launch(
                block, algorithm, fx.Float32, torch.float32
            )
            float_out = run_blocks(float_launch, float_values, 1, float_dtype)
            check(
                f"adversarial-finite/{algorithm.name}/block-{block}",
                float_out,
                reference(float_values, block, float_dtype),
                results,
            )

            int_values = int_pattern.repeat(block // int_pattern.numel())
            int_launch, int_dtype = make_launch(block, algorithm, fx.Int32, torch.int32)
            int_out = run_blocks(int_launch, int_values, 1, int_dtype)
            check(
                f"adversarial-wrap/{algorithm.name}/block-{block}",
                int_out,
                reference(int_values, block, int_dtype),
                results,
            )


def validate_barrier_reuse(results: list[dict]) -> None:
    for algorithm in ALGORITHMS:
        for block in (64, 256):
            block_size = (block, 1, 1)

            @flyc.kernel(known_block_size=list(block_size))
            def kernel(A: fx.Tensor, B: fx.Tensor, OutA: fx.Tensor, OutB: fx.Tensor):
                block_reduce = fx.coop.BlockReduce[fx.Int32, block_size, algorithm]
                storage = fx.SharedAllocator().allocate(block_reduce.SharedStorage).peek()
                tid = linear_tid(block_size)
                total_a = block_reduce(A[tid], fx.ReductionOp.ADD, storage=storage)
                fx.barrier()
                total_b = block_reduce(B[tid], fx.ReductionOp.ADD, storage=storage)
                if tid == 0:
                    OutA[fx.block_idx.x] = total_a
                    OutB[fx.block_idx.x] = total_b

            @flyc.jit
            def launch(
                A: fx.Tensor,
                B: fx.Tensor,
                OutA: fx.Tensor,
                OutB: fx.Tensor,
                stream: fx.Stream = fx.Stream(None),
            ):
                kernel(A, B, OutA, OutB).launch(
                    grid=(1, 1, 1), block=block_size, stream=stream
                )

            a = torch.arange(block, dtype=torch.int32, device="cuda")
            b = torch.arange(block, 2 * block, dtype=torch.int32, device="cuda")
            out_a = torch.zeros(1, dtype=torch.int32, device="cuda")
            out_b = torch.zeros(1, dtype=torch.int32, device="cuda")
            stream = torch.cuda.Stream()
            launch(a, b, out_a, out_b, stream=stream)
            stream.synchronize()
            expected_a = reference(a, block, torch.int32)
            expected_b = reference(b, block, torch.int32)
            check(
                f"barrier-reuse-a/{algorithm.name}/block-{block}",
                out_a.cpu(),
                expected_a,
                results,
            )
            check(
                f"barrier-reuse-b/{algorithm.name}/block-{block}",
                out_b.cpu(),
                expected_b,
                results,
            )


def validate_wave64(results: list[dict]) -> None:
    wave = int(fx.num_warp_threads())
    semantics = {"target_wave": wave, "specializations": {}}
    for algorithm in ALGORITHMS:
        for block in (32, 64, 128, 256):
            spec = fx.coop.BlockReduce[fx.Float32, block, algorithm]
            expected_warp = min(wave, block)
            expected_warps = block // expected_warp
            passed = spec.warp_threads == expected_warp and spec.num_warps == expected_warps
            semantics["specializations"][f"{algorithm.name}/block-{block}"] = {
                "warp_threads": spec.warp_threads,
                "num_warps": spec.num_warps,
                "passed": passed,
            }
            if not passed:
                raise AssertionError(f"wave64 semantics failed for {algorithm.name}/{block}")
    results.append({"case": "wave64-semantics", "passed": True, **semantics})
    print(f"wave64-semantics target={wave} PASS")


def time_cases(results: list[dict]) -> None:
    for algorithm in ALGORITHMS:
        for block in BLOCKS:
            launch, dtype = make_launch(block, algorithm, fx.Float32, torch.float32)
            values = torch.randn(block, dtype=torch.float32, device="cuda")
            out = torch.zeros(1, dtype=torch.float32, device="cuda")
            stream = torch.cuda.Stream()
            for _ in range(3):
                launch(values, out, stream=stream)
            stream.synchronize()
            start = torch.cuda.Event(enable_timing=True)
            end = torch.cuda.Event(enable_timing=True)
            start.record(stream)
            for _ in range(TIMING_ITERATIONS):
                launch(values, out, stream=stream)
            end.record(stream)
            stream.synchronize()
            milliseconds = start.elapsed_time(end) / TIMING_ITERATIONS
            result = {
                "case": f"timing/{algorithm.name}/block-{block}",
                "passed": True,
                "iterations": TIMING_ITERATIONS,
                "mean_us": milliseconds * 1000,
            }
            results.append(result)
            print(f"{result['case']:52s} {result['mean_us']:.3f} us/launch")


def environment() -> dict:
    flydsl_path = Path(flydsl.__file__).resolve()
    native_path = flydsl_path.parent / "_mlir" / "_mlir_libs"
    source_init = (source_root() / "python" / "flydsl" / "__init__.py").read_text()
    source_version = re.search(
        r"^__version__\s*=\s*[\"']([^\"']+)[\"']", source_init, re.MULTILINE
    )
    properties = torch.cuda.get_device_properties(0)
    return {
        "source_commit": git_commit(),
        "source_version": source_version.group(1) if source_version else "unknown",
        "source_path": str(source_root()),
        "native_flydsl_path": str(flydsl_path.parent),
        "native_version": flydsl.__version__,
        "native_library_path": str(native_path),
        "python": __import__("sys").executable,
        "python_version": __import__("sys").version.split()[0],
        "torch": torch.__version__,
        "torch_path": str(Path(torch.__file__).resolve()),
        "hip": torch.version.hip,
        "gpu": {
            "name": properties.name,
            "capability": f"{properties.major}.{properties.minor}",
            "device": torch.cuda.current_device(),
        },
        "hipcc": shutil.which("hipcc") or "unavailable",
        "hipcc_version": tool_version(["hipcc", "--version"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=Path("block_reduce_validation.json"))
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA/HIP device is unavailable")
    torch.cuda.set_device(0)
    started = time.monotonic()
    results: list[dict] = []
    print("environment:")
    environment_data = environment()
    print(json.dumps(environment_data, indent=2))
    print("\nvalidation:")
    validate_wave64(results)
    validate_full_tiles(results)
    validate_tails(results)
    validate_adversarial(results)
    validate_barrier_reuse(results)
    time_cases(results)
    summary = Counter("passed" if case["passed"] else "failed" for case in results)
    report = {
        "environment": environment_data,
        "tolerance": {
            "float": {"rtol": 2e-5, "atol": 1e-5},
            "integer": "exact wraparound",
        },
        "summary": {"passed": summary["passed"], "failed": summary["failed"]},
        "validation_elapsed_seconds": time.monotonic() - started,
        "results": results,
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, indent=2) + "\n")
    print(f"\nsummary: {summary['passed']} passed, {summary['failed']} failed")
    print(f"raw results: {args.json}")
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
