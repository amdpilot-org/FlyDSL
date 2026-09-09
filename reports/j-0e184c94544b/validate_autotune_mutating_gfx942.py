#!/usr/bin/env python3

import argparse
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

import torch


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cache-root",
        type=Path,
        default=None,
        help="Job-private cache root (default: a fresh temporary directory)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="JSON result path (default: print JSON to stdout)",
    )
    return parser.parse_args()


def configure_caches(cache_root):
    runtime_cache = cache_root / "runtime"
    autotune_cache = cache_root / "autotune"
    runtime_cache.mkdir(parents=True, exist_ok=True)
    autotune_cache.mkdir(parents=True, exist_ok=True)
    os.environ["FLYDSL_RUNTIME_CACHE_DIR"] = str(runtime_cache)
    os.environ["FLYDSL_AUTOTUNE_CACHE_DIR"] = str(autotune_cache)
    os.environ["FLYDSL_RUNTIME_ENABLE_CACHE"] = "1"
    os.environ["FLYDSL_AUTOTUNE"] = "0"
    return runtime_cache, autotune_cache


def make_inputs(mode, size=8):
    value = torch.arange(size, dtype=torch.int32, device="cuda")
    output = torch.full((size,), 99, dtype=torch.int32, device="cuda")
    expected = (torch.arange(size, dtype=torch.int32, device="cuda") + mode).to(torch.int32)
    return value, output, expected


def tensor_lists(observations):
    return [
        {
            "value": entry["value"].detach().cpu().tolist(),
            "output": entry["output"].detach().cpu().tolist(),
        }
        for entry in observations
    ]


def exact_observation(observations, expected):
    return bool(observations) and all(
        torch.equal(entry["value"], expected) and torch.equal(entry["output"], expected)
        for entry in observations
    )


def main():
    args = parse_args()
    cache_root = args.cache_root
    if cache_root is None:
        cache_root = Path(tempfile.mkdtemp(prefix="flydsl-autotune-gfx942-"))
    cache_root = cache_root.resolve()
    runtime_cache, autotune_cache = configure_caches(cache_root)

    import flydsl
    import flydsl.compiler as flyc
    import flydsl.expr as fx
    from flydsl import Config, autotune
    from flydsl.runtime.device import get_rocm_arch

    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("this validation requires exactly one CUDA/ROCm device")

    @flyc.kernel
    def mutating_kernel(
        value: fx.Tensor,
        output: fx.Tensor,
        mode: fx.Constexpr[int],
        block_dim: fx.Constexpr[int],
    ):
        tid = fx.thread_idx.x
        bid = fx.block_idx.x

        value_tile = fx.logical_divide(value, fx.make_layout(block_dim, 1))
        value_tile = fx.slice(value_tile, (None, bid))
        value_tile = fx.logical_divide(value_tile, fx.make_layout(1, 1))

        output_tile = fx.logical_divide(output, fx.make_layout(block_dim, 1))
        output_tile = fx.slice(output_tile, (None, bid))
        output_tile = fx.logical_divide(output_tile, fx.make_layout(1, 1))

        atom = fx.make_copy_atom(fx.UniversalCopy32b(), fx.Int32)
        register = fx.make_rmem_tensor(1, fx.Int32)
        fx.copy_atom_call(atom, fx.slice(value_tile, (None, tid)), register)
        updated = fx.memref_load_vec(register) + fx.Int32(mode)
        fx.memref_store_vec(updated, register)
        fx.copy_atom_call(atom, register, fx.slice(value_tile, (None, tid)))
        fx.copy_atom_call(atom, register, fx.slice(output_tile, (None, tid)))

    @flyc.jit
    def mutating_entry(
        value: fx.Tensor,
        output: fx.Tensor,
        n: fx.Int32,
        mode: fx.Constexpr[int],
        block_dim: fx.Constexpr[int],
        stream: fx.Stream = fx.Stream(None),
    ):
        grid_x = (n + block_dim - 1) // block_dim
        mutating_kernel(value, output, mode, block_dim).launch(
            grid=(grid_x, 1, 1),
            block=(block_dim, 1, 1),
            stream=stream,
        )

    configs = [Config(block_dim=64), Config(block_dim=128)]

    def make_tuner(*, default=None, post_hook=None):
        return autotune(
            configs=configs,
            key=["mode"],
            warmup=1,
            rep=2,
            restore_value=["value"],
            reset_to_zero=["output"],
            default=default,
            post_hook=post_hook,
        )(mutating_entry)

    def make_recorder():
        observations = []
        current = {}

        def bind(value, output):
            current["value"] = value
            current["output"] = output

        def post_hook(_kwargs):
            observations.append(
                {
                    "value": current["value"].detach().clone(),
                    "output": current["output"].detach().clone(),
                }
            )

        return observations, bind, post_hook

    search_observations, search_bind, search_post_hook = make_recorder()
    search_tuner = make_tuner(post_hook=search_post_hook)

    os.environ["FLYDSL_AUTOTUNE"] = "1"
    value, output, expected = make_inputs(3)
    search_bind(value, output)
    stream = torch.cuda.Stream()
    search_stdout = io.StringIO()
    try:
        with redirect_stdout(search_stdout):
            search_tuner(value, output, len(value), 3, stream=stream)
    except Exception as error:
        print(search_stdout.getvalue(), file=sys.stderr)
        raise
    torch.cuda.synchronize()

    selected_config = next(iter(search_tuner.cache.values()))
    forced_search = {
        "candidate_count": len(configs),
        "warmup": 1,
        "rep": 2,
        "expected_kernel_observations": len(configs) * (1 + 2),
        "kernel_observation_count": len(search_observations),
        "observations": tensor_lists(search_observations),
        "selected_config": selected_config.to_dict(),
        "final_value": value.detach().cpu().tolist(),
        "final_output": output.detach().cpu().tolist(),
        "expected": expected.detach().cpu().tolist(),
        "stdout": search_stdout.getvalue(),
    }
    forced_search["search_repetitions_exact"] = exact_observation(search_observations, expected)
    forced_search["final_execution_exact"] = torch.equal(value, expected) and torch.equal(output, expected)
    forced_search["pass"] = (
        forced_search["kernel_observation_count"] == forced_search["expected_kernel_observations"]
        and forced_search["search_repetitions_exact"]
        and forced_search["final_execution_exact"]
        and "[autotune] tuning" in forced_search["stdout"]
    )

    os.environ["FLYDSL_AUTOTUNE"] = "0"
    cache_value, cache_output, cache_expected = make_inputs(3)
    cache_stream = torch.cuda.Stream()
    cache_stdout = io.StringIO()
    cache_entries_before = len(search_tuner.cache)
    with redirect_stdout(cache_stdout):
        search_tuner(
            cache_value,
            cache_output,
            len(cache_value),
            3,
            stream=cache_stream,
        )
    torch.cuda.synchronize()

    cache_hit = {
        "observation_count_before": forced_search["kernel_observation_count"],
        "observation_count_after": len(search_observations),
        "cache_entry_count_before": cache_entries_before,
        "cache_entry_count_after": len(search_tuner.cache),
        "selected_config": selected_config.to_dict(),
        "value": cache_value.detach().cpu().tolist(),
        "output": cache_output.detach().cpu().tolist(),
        "expected": cache_expected.detach().cpu().tolist(),
        "stdout": cache_stdout.getvalue(),
    }
    cache_hit["output_exact"] = torch.equal(cache_value, cache_expected) and torch.equal(
        cache_output, cache_expected
    )
    cache_hit["searched"] = "[autotune] tuning" in cache_hit["stdout"]
    cache_hit["pass"] = (
        not cache_hit["searched"]
        and cache_hit["cache_entry_count_after"] == cache_hit["cache_entry_count_before"]
        and cache_hit["observation_count_after"] == cache_hit["observation_count_before"]
        and cache_hit["output_exact"]
    )

    key_value, key_output, key_expected = make_inputs(5)
    search_bind(key_value, key_output)
    key_stream = torch.cuda.Stream()
    key_stdout = io.StringIO()
    with redirect_stdout(key_stdout):
        search_tuner(key_value, key_output, len(key_value), 5, stream=key_stream)
    torch.cuda.synchronize()

    key_axis = {
        "mode_3_config": selected_config.to_dict(),
        "cache_entry_count": len(search_tuner.cache),
        "observation_count": len(search_observations),
        "value": key_value.detach().cpu().tolist(),
        "output": key_output.detach().cpu().tolist(),
        "expected": key_expected.detach().cpu().tolist(),
        "stdout": key_stdout.getvalue(),
    }
    key_axis["separate_mode_5_searched"] = "[autotune] tuning" in key_axis["stdout"]
    key_axis["output_exact"] = torch.equal(key_value, key_expected) and torch.equal(
        key_output, key_expected
    )
    key_axis["pass"] = (
        key_axis["cache_entry_count"] == 2
        and key_axis["separate_mode_5_searched"]
        and key_axis["output_exact"]
    )

    default_observations, default_bind, default_post_hook = make_recorder()
    default_calls = []

    def default(value, output, n, mode, stream):
        config = Config(block_dim=64)
        default_calls.append(config)
        return config

    default_tuner = make_tuner(default=default, post_hook=default_post_hook)
    default_value, default_output, default_expected = make_inputs(7)
    default_bind(default_value, default_output)
    default_stream = torch.cuda.Stream()
    default_stdout = io.StringIO()
    with redirect_stdout(default_stdout):
        default_tuner(
            default_value,
            default_output,
            len(default_value),
            7,
            stream=default_stream,
        )
    torch.cuda.synchronize()

    default_config = default_calls[0]
    default_call = {
        "default_config": default_config.to_dict(),
        "observation_count": len(default_observations),
        "value": default_value.detach().cpu().tolist(),
        "output": default_output.detach().cpu().tolist(),
        "expected": default_expected.detach().cpu().tolist(),
        "stdout": default_stdout.getvalue(),
    }
    default_call["searched"] = "[autotune] tuning" in default_call["stdout"]
    default_call["output_exact"] = torch.equal(default_value, default_expected) and torch.equal(
        default_output, default_expected
    )
    default_call["pass"] = (
        default_config.kwargs["block_dim"] == 64
        and not default_call["searched"]
        and default_call["observation_count"] == 0
        and default_call["output_exact"]
    )

    import flydsl._mlir.ir as mlir_ir

    device = torch.cuda.current_device()
    properties = torch.cuda.get_device_properties(device)
    result = {
        "pass": all(
            (
                forced_search["pass"],
                cache_hit["pass"],
                key_axis["pass"],
                default_call["pass"],
            )
        ),
        "flydsl": {
            "version": flydsl.__version__,
            "python_path": str(Path(flydsl.__file__).resolve()),
            "native_bindings_path": str(Path(mlir_ir.__file__).resolve()),
        },
        "torch": {
            "version": torch.__version__,
            "hip": torch.version.hip,
            "path": str(Path(torch.__file__).resolve()),
        },
        "gpu": {
            "arch": get_rocm_arch(),
            "name": properties.name,
            "compute_capability": torch.cuda.get_device_capability(device),
            "compute_units": properties.multi_processor_count,
            "device_count": torch.cuda.device_count(),
        },
        "cache": {
            "root": str(cache_root),
            "runtime": str(runtime_cache),
            "autotune": str(autotune_cache),
        },
        "phases": {
            "forced_search_final_execution": forced_search,
            "cache_hit": cache_hit,
            "declared_key_axis": key_axis,
            "default_no_search": default_call,
        },
    }

    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
