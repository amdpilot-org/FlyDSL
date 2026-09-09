#!/usr/bin/env python3
"""Validate FlyDSL autotune mutation semantics on one gfx950 GPU."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_ID = f"run-{os.getpid()}"
AUTOTUNE_CACHE = Path("/job/flydsl-autotune-cache-j-54d968ba6fd6") / RUN_ID
RUNTIME_CACHE = Path("/job/flydsl-runtime-cache-j-54d968ba6fd6") / RUN_ID

os.environ["FLYDSL_AUTOTUNE_CACHE_DIR"] = str(AUTOTUNE_CACHE)
os.environ["FLYDSL_RUNTIME_CACHE_DIR"] = str(RUNTIME_CACHE)
os.environ["FLYDSL_RUNTIME_ENABLE_CACHE"] = "1"
os.environ["FLYDSL_AUTOTUNE_CONFIG_DIR"] = ""

AUTOTUNE_CACHE.mkdir(parents=True, exist_ok=True)
RUNTIME_CACHE.mkdir(parents=True, exist_ok=True)

import torch  # noqa: E402
import triton  # noqa: E402
import flydsl  # noqa: E402
import flydsl.compiler as flyc  # noqa: E402
import flydsl.expr as fx  # noqa: E402
from flydsl.autotune import Config, autotune  # noqa: E402

autotune_module = importlib.import_module("flydsl.autotune")


SIZE = 4096
VEC_WIDTH = 4
CONFIG_BLOCKS = (64, 128, 256)
DEFAULT_BLOCK = 128


@flyc.kernel
def mutating_add_kernel(
    A: fx.Tensor,
    B: fx.Tensor,
    C: fx.Tensor,
    BLOCK: fx.Constexpr[int],
    VEC: fx.Constexpr[int],
):
    bid = fx.block_idx.x
    tid = fx.thread_idx.x
    tile = BLOCK * VEC

    tA = fx.slice(fx.logical_divide(A, fx.make_layout(tile, 1)), (None, bid))
    tB = fx.slice(fx.logical_divide(B, fx.make_layout(tile, 1)), (None, bid))
    tC = fx.slice(fx.logical_divide(C, fx.make_layout(tile, 1)), (None, bid))

    tA = fx.logical_divide(tA, fx.make_layout(VEC, 1))
    tB = fx.logical_divide(tB, fx.make_layout(VEC, 1))
    tC = fx.logical_divide(tC, fx.make_layout(VEC, 1))

    atom = fx.make_copy_atom(fx.UniversalCopy(VEC * fx.Float32.width), fx.Float32)
    rA = fx.make_rmem_tensor(VEC, fx.Float32)
    rB = fx.make_rmem_tensor(VEC, fx.Float32)
    rC = fx.make_rmem_tensor(VEC, fx.Float32)

    fx.copy_atom_call(atom, fx.slice(tA, (None, tid)), rA)
    fx.copy_atom_call(atom, fx.slice(tB, (None, tid)), rB)
    fx.memref_store_vec(fx.arith.addf(fx.memref_load_vec(rA), fx.memref_load_vec(rB)), rC)
    fx.copy_atom_call(atom, rC, fx.slice(tA, (None, tid)))
    fx.copy_atom_call(atom, rC, fx.slice(tC, (None, tid)))


@flyc.jit
def mutating_add(
    A: fx.Tensor,
    B: fx.Tensor,
    C: fx.Tensor,
    n: fx.Int32,
    BLOCK: fx.Constexpr[int],
    stream: fx.Stream = fx.Stream(None),
):
    tile = BLOCK * VEC_WIDTH
    grid_x = (n + tile - 1) // tile
    mutating_add_kernel(A, B, C, BLOCK, VEC_WIDTH).launch(
        grid=(grid_x, 1, 1), block=(BLOCK, 1, 1), stream=stream
    )


search_calls = 0


def counting_bench(kernel_call, warmup: int, rep: int) -> float:
    global search_calls
    search_calls += 1
    return autotune_module.do_bench(kernel_call, warmup=warmup, rep=rep)


tuned_add = autotune(
    configs=[Config(BLOCK=block) for block in CONFIG_BLOCKS],
    key=["n"],
    warmup=1,
    rep=3,
    reset_to_zero=["C"],
    restore_value=["A"],
    default=lambda *args, **kwargs: Config(BLOCK=DEFAULT_BLOCK),
    do_bench=counting_bench,
)(mutating_add)


@contextmanager
def force_autotune(value: str | None) -> Iterator[None]:
    old = os.environ.get("FLYDSL_AUTOTUNE")
    try:
        if value is None:
            os.environ.pop("FLYDSL_AUTOTUNE", None)
        else:
            os.environ["FLYDSL_AUTOTUNE"] = value
        yield
    finally:
        if old is None:
            os.environ.pop("FLYDSL_AUTOTUNE", None)
        else:
            os.environ["FLYDSL_AUTOTUNE"] = old


def make_inputs() -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    A = torch.arange(SIZE, dtype=torch.float32, device="cuda")
    B = torch.full_like(A, 2.0)
    C = torch.full_like(A, 777.0)
    A0 = A.clone()
    return A, B, C, A0


def direct_reference(block: int) -> tuple[torch.Tensor, torch.Tensor]:
    A, B, C, A0 = make_inputs()
    C.zero_()
    mutating_add(A, B, C, SIZE, BLOCK=block, stream=torch.cuda.Stream())
    torch.cuda.synchronize()
    return A, C


def compare_exact(label: str, actual: torch.Tensor, expected: torch.Tensor) -> dict:
    exact = torch.equal(actual.detach().cpu(), expected.detach().cpu())
    if not exact:
        raise AssertionError(f"{label}: exact comparison failed")
    return {"phase": label, "exact": True}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    torch.cuda.set_device(0)
    source_autotune = REPO_ROOT / "python/flydsl/autotune.py"
    source_init = REPO_ROOT / "python/flydsl/__init__.py"
    source_version_match = re.search(
        r"^__version__\s*=\s+[\"']([^\"']+)[\"']",
        source_init.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()

    phase_results = []

    # Normal default call: no explicit search, no cache entry yet.
    A, B, C, A0 = make_inputs()
    with force_autotune(None):
        tuned_add(A, B, C, SIZE, stream=torch.cuda.Stream())
    torch.cuda.synchronize()
    refA, refC = direct_reference(DEFAULT_BLOCK)
    phase_results.append(compare_exact("default_call_A", A, refA))
    phase_results.append(compare_exact("default_call_C", C, refC))
    default_search_calls = search_calls
    if default_search_calls != 0:
        raise AssertionError(f"default call unexpectedly searched {default_search_calls} times")

    # Explicit search only. This leaves A restored and C as one clean run.
    A, B, C, A0 = make_inputs()
    with force_autotune("1"):
        chosen = tuned_add.resolve_config(A, B, C, SIZE, stream=torch.cuda.Stream())
    torch.cuda.synchronize()
    chosen_block = chosen.kwargs["BLOCK"]
    refA, refC = direct_reference(chosen_block)
    phase_results.append(compare_exact("explicit_search_A_restored", A, A0))
    phase_results.append(compare_exact("explicit_search_C_clean_run", C, refC))
    explicit_search_calls = search_calls - default_search_calls
    if explicit_search_calls != len(CONFIG_BLOCKS):
        raise AssertionError(f"expected {len(CONFIG_BLOCKS)} searches, saw {explicit_search_calls}")

    # Final execution with the chosen config, served from the scratch cache.
    A, B, C, A0 = make_inputs()
    with force_autotune(None):
        tuned_add(A, B, C, SIZE, stream=torch.cuda.Stream())
    torch.cuda.synchronize()
    refA, refC = direct_reference(chosen_block)
    phase_results.append(compare_exact("final_execution_A", A, refA))
    phase_results.append(compare_exact("final_execution_C", C, refC))

    # Repeated cache hit on fresh inputs.
    A, B, C, A0 = make_inputs()
    with force_autotune(None):
        tuned_add(A, B, C, SIZE, stream=torch.cuda.Stream())
    torch.cuda.synchronize()
    refA, refC = direct_reference(chosen_block)
    phase_results.append(compare_exact("cache_hit_A", A, refA))
    phase_results.append(compare_exact("cache_hit_C", C, refC))

    # A second call on the same A must accumulate; restore_value is search-only.
    with force_autotune(None):
        tuned_add(A, B, C, SIZE, stream=torch.cuda.Stream())
    torch.cuda.synchronize()
    expected_accumulated = A0 + 2 * B
    phase_results.append(compare_exact("repeated_call_accumulated_A", A, expected_accumulated))
    phase_results.append(compare_exact("repeated_call_accumulated_C", C, expected_accumulated))

    final_search_calls = search_calls
    if final_search_calls != explicit_search_calls:
        raise AssertionError("final/cache calls unexpectedly triggered additional searches")

    properties = torch.cuda.get_device_properties(0)
    results = {
        "status": "PASS",
        "source_commit": commit,
        "source_version": source_version_match.group(1) if source_version_match else None,
        "hybrid_package_version": flydsl.__version__,
        "source_autotune_path": str(source_autotune),
        "hybrid_autotune_path": str(autotune_module.__file__),
        "source_autotune_sha256": sha256(source_autotune),
        "hybrid_autotune_sha256": sha256(Path(autotune_module.__file__)),
        "torch_version": torch.__version__,
        "torch_hip_version": torch.version.hip,
        "torch_path": str(Path(torch.__file__).resolve()),
        "triton_version": triton.__version__,
        "triton_path": str(Path(triton.__file__).resolve()),
        "native_mlir_path": str(Path(flydsl._mlir.__path__[0]).resolve()),
        "gpu": {
            "name": torch.cuda.get_device_name(0),
            "architecture": flydsl.runtime.device.get_rocm_arch(),
            "compute_capability": torch.cuda.get_device_capability(0),
            "compute_units": properties.multi_processor_count,
        },
        "cache": {
            "autotune_dir": str(AUTOTUNE_CACHE),
            "runtime_dir": str(RUNTIME_CACHE),
            "autotune_file": str(tuned_add._cache_file),
        },
        "candidate_blocks": list(CONFIG_BLOCKS),
        "default_block": DEFAULT_BLOCK,
        "chosen_block": chosen_block,
        "search_calls": {
            "default": default_search_calls,
            "explicit": explicit_search_calls,
            "final_total": final_search_calls,
        },
        "phases": phase_results,
    }
    output = Path(__file__).with_name("results.json")
    output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
