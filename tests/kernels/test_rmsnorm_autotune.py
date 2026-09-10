# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

"""GPU contracts for the direct RMSNorm autotune adopter."""

import json
import os
import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.l2_device, pytest.mark.rocm_lower]

try:
    import torch
except ImportError:
    torch = None
if torch is None or not torch.cuda.is_available():
    pytest.skip("CUDA/ROCm not available. Skipping GPU tests.", allow_module_level=True)

import flydsl.compiler as flyc  # noqa: E402
from flydsl.autotune import Config  # noqa: E402
from kernels.norm.rmsnorm_autotune import _SEARCH_CONFIGS, _rmsnorm_tuner, rmsnorm_autotuned  # noqa: E402
from kernels.norm.rmsnorm_kernel import rmsnorm_direct  # noqa: E402

EPS = 1e-5


@pytest.fixture(autouse=True)
def _isolated_tuner(tmp_path, monkeypatch):
    _rmsnorm_tuner.cache.clear()
    _rmsnorm_tuner._artifact_cache.clear()
    monkeypatch.setattr(_rmsnorm_tuner, "_cache_file", tmp_path / "rmsnorm.json")
    monkeypatch.setenv("FLYDSL_AUTOTUNE_CONFIG_DIR", str(tmp_path / "artifacts"))
    monkeypatch.delenv("FLYDSL_AUTOTUNE", raising=False)
    yield
    _rmsnorm_tuner.cache.clear()
    _rmsnorm_tuner._artifact_cache.clear()


def _reference(x, g):
    xf = x.float()
    return xf * torch.rsqrt((xf * xf).mean(-1, keepdim=True) + EPS) * g.float()


def _inputs(M=32, N=8192, weight_dtype=torch.bfloat16):
    generator = torch.Generator(device="cuda").manual_seed(0)
    x = torch.randn(M, N, device="cuda", dtype=torch.bfloat16, generator=generator)
    g = torch.rand(N, device="cuda", dtype=weight_dtype, generator=generator)
    return x, g, _reference(x, g)


def _assert_close(out, ref):
    torch.testing.assert_close(out.float(), ref, rtol=0, atol=2e-2)


def _strided_inputs(M, N, row_stride, dtype, weight_dtype):
    generator = torch.Generator(device="cuda").manual_seed(0)
    input_storage = torch.randn(M, row_stride, device="cuda", dtype=dtype, generator=generator)
    input_t = input_storage[:, :N]
    gamma = torch.rand(N, device="cuda", dtype=weight_dtype, generator=generator)
    output_storage = torch.empty(M, row_stride, device="cuda", dtype=dtype)
    output = output_storage[:, :N]
    return input_t, gamma, output, _reference(input_t, gamma)


def _tuner_key(input_t, gamma, output, M, N, dtype_str, weight_dtype_str, stream):
    return _rmsnorm_tuner._make_key(
        (input_t, gamma, output, M),
        {
            "N": N,
            "dtype_str": dtype_str,
            "weight_dtype_str": weight_dtype_str,
            "stream": stream,
        },
    )


def _artifact_ref(input_t, gamma, output, M, N, dtype_str, weight_dtype_str, stream):
    return _rmsnorm_tuner._artifact_ref(
        (input_t, gamma, output, M),
        {
            "N": N,
            "dtype_str": dtype_str,
            "weight_dtype_str": weight_dtype_str,
            "stream": stream,
        },
        required=True,
    )


def _jit_key(input_t, gamma, output, M, N, dtype_str, weight_dtype_str, stream):
    bound = rmsnorm_direct._sig.bind(
        input_t,
        gamma,
        output,
        M,
        N,
        dtype_str,
        256,
        stream,
        weight_dtype_str,
    )
    return rmsnorm_direct._build_full_cache_key(bound.arguments)


@pytest.mark.parametrize(
    "weight_dtype,weight_dtype_str",
    ((torch.bfloat16, "bf16"), (torch.float32, "f32")),
)
def test_rmsnorm_direct_specializes_known_block_size(weight_dtype, weight_dtype_str):
    x, g, ref = _inputs(M=1, weight_dtype=weight_dtype)
    out = torch.empty_like(x)
    stream = torch.cuda.current_stream()

    compile_args = (x, g, out, x.shape[0], x.shape[1], "bf16", 512, stream)
    if weight_dtype == torch.float32:
        compile_args += (weight_dtype_str,)
    compiled = flyc.compile(rmsnorm_direct, *compile_args)
    stream.synchronize()
    artifact = compiled._keepalive

    assert "known_block_size = array<i32: 512, 1, 1>" in artifact.source_ir
    match = re.search(r"max_flat_workgroup_size\\CD\\([0-9A-Fa-f]{2})\\([0-9A-Fa-f]{2})", artifact.ir)
    assert match is not None and int("".join(match.groups()), 16) == 512
    if weight_dtype == torch.float32:
        weight_copy_type = "!fly.copy_atom<!fly_rocdl.cdna3.buffer_copy<128>, 32>"
        assert artifact.source_ir.count(weight_copy_type) >= 3
    _assert_close(out, ref)


def test_rmsnorm_autotuned_default_uses_current_stream_and_skips_search(monkeypatch):
    monkeypatch.setattr(_rmsnorm_tuner, "_bench_one", lambda *args, **kwargs: pytest.fail("unexpected search"))
    x, g, ref = _inputs()
    out = torch.empty_like(x)
    stream = torch.cuda.Stream()
    stream.wait_stream(torch.cuda.current_stream())
    observed_streams = []
    original_run_config = _rmsnorm_tuner._run_config

    def checked_run_config(config, args, kwargs):
        observed_streams.append(kwargs["stream"].cuda_stream)
        return original_run_config(config, args, kwargs)

    monkeypatch.setattr(_rmsnorm_tuner, "_run_config", checked_run_config)

    with torch.cuda.stream(stream):
        rmsnorm_autotuned(x, g, out, x.shape[0])
    stream.synchronize()

    assert observed_streams == [stream.cuda_stream]
    _assert_close(out, ref)


def test_rmsnorm_autotuned_search_then_cache_hit(monkeypatch):
    completed = 0
    target = next(
        index
        for index, config in enumerate(_SEARCH_CONFIGS, start=1)
        if config.kwargs["BLOCK_THREADS"] == 128 and config.waves_per_eu == 2
    )
    x, g, ref = _inputs(M=8)
    out = torch.empty_like(x)
    stream = torch.cuda.Stream()
    stream.wait_stream(torch.cuda.current_stream())
    raw_stream = stream.cuda_stream

    def bench_once(call, warmup, rep):
        nonlocal completed
        assert torch.cuda.current_stream().cuda_stream == stream.cuda_stream
        call()
        stream.synchronize()
        completed += 1
        return 0.0 if completed == target else float(completed)

    monkeypatch.setattr(_rmsnorm_tuner, "_do_bench", bench_once)
    monkeypatch.setenv("FLYDSL_AUTOTUNE", "1")
    rmsnorm_autotuned(x, g, out, x.shape[0], stream=raw_stream)
    stream.synchronize()

    assert completed == len(_SEARCH_CONFIGS)
    _assert_close(out, ref)

    artifacts = list(Path(os.environ["FLYDSL_AUTOTUNE_CONFIG_DIR"]).glob("*.json"))
    assert len(artifacts) == 1
    payload = json.loads(artifacts[0].read_text())
    assert payload["identity"]["key"] == {
        "m_in": x.shape[0],
        "N": x.shape[1],
        "dtype_str": "bf16",
        "weight_dtype_str": "bf16",
    }
    assert payload["identity"]["device"]["name"] == torch.cuda.get_device_name(x.device)
    assert payload["config"]["BLOCK_THREADS"] == 128
    assert payload["config"]["waves_per_eu"] == 2

    call_kwargs = {
        "N": x.shape[1],
        "dtype_str": "bf16",
        "weight_dtype_str": "bf16",
        "stream": raw_stream,
    }
    winner_key = _rmsnorm_tuner._make_key((x, g, out, x.shape[0]), call_kwargs)
    assert winner_key in _rmsnorm_tuner.cache
    other_m_key = _rmsnorm_tuner._make_key((x, g, out, x.shape[0] + 1), call_kwargs)
    assert other_m_key != winner_key

    monkeypatch.delenv("FLYDSL_AUTOTUNE")
    monkeypatch.setattr(
        _rmsnorm_tuner,
        "default",
        lambda *args, **kwargs: pytest.fail("cached winner should take precedence over default"),
    )
    cached = torch.empty_like(x)
    rmsnorm_autotuned(x, g, cached, x.shape[0], stream=raw_stream)
    stream.synchronize()

    assert completed == len(_SEARCH_CONFIGS)
    _assert_close(cached, ref)

    # A fresh serving decision with no winner cache must load the emitted
    # artifact without evaluating the default or search space.
    _rmsnorm_tuner.cache.clear()
    _rmsnorm_tuner._artifact_cache.clear()
    monkeypatch.setattr(
        _rmsnorm_tuner,
        "default",
        lambda *args, **kwargs: pytest.fail("offline artifact should take precedence over default"),
    )
    monkeypatch.setattr(
        _rmsnorm_tuner,
        "configs",
        lambda *args, **kwargs: pytest.fail("offline hit should not construct search configs"),
    )
    offline = torch.empty_like(x)
    rmsnorm_autotuned(x, g, offline, x.shape[0], stream=raw_stream)
    stream.synchronize()

    assert completed == len(_SEARCH_CONFIGS)
    _assert_close(offline, ref)


def test_rmsnorm_weight_dtype_has_distinct_tuning_identity():
    x, g, _ = _inputs(M=1)
    _, g_fp32, mixed_ref = _inputs(M=1, weight_dtype=torch.float32)
    out = torch.empty_like(x)
    common = {"N": x.shape[1], "dtype_str": "bf16", "stream": torch.cuda.current_stream().cuda_stream}

    same_dtype_key = _rmsnorm_tuner._make_key(
        (x, g, out, x.shape[0]),
        {**common, "weight_dtype_str": "bf16"},
    )
    mixed_dtype_key = _rmsnorm_tuner._make_key(
        (x, g_fp32, out, x.shape[0]),
        {**common, "weight_dtype_str": "f32"},
    )

    assert "weight_dtype_str" in _rmsnorm_tuner.key
    assert mixed_dtype_key != same_dtype_key

    rmsnorm_autotuned(x, g_fp32, out, x.shape[0])
    torch.cuda.synchronize()
    _assert_close(out, mixed_ref)


def test_equal_shape_specialization_and_incompatible_artifact_rejection(monkeypatch):
    searches = 0

    def bench_once(call, warmup, rep):
        nonlocal searches
        searches += 1
        call()
        return 1.0

    monkeypatch.setattr(_rmsnorm_tuner, "_do_bench", bench_once)
    monkeypatch.setattr(
        _rmsnorm_tuner,
        "configs",
        lambda *_args, **_kwargs: [Config(BLOCK_THREADS=256)],
    )

    M, N = 4, 4096
    stream = torch.cuda.current_stream().cuda_stream
    cases = [
        ("contiguous", N, torch.bfloat16, "bf16", torch.bfloat16, "bf16", True),
        ("stride-2", 2 * N, torch.bfloat16, "bf16", torch.bfloat16, "bf16", False),
        ("stride-3", 3 * N, torch.bfloat16, "bf16", torch.bfloat16, "bf16", False),
        ("f16", N, torch.float16, "f16", torch.float16, "f16", True),
        ("fp32-weight", N, torch.bfloat16, "bf16", torch.float32, "f32", True),
    ]
    tuner_keys = []
    artifact_paths = []
    artifact_identities = []
    jit_keys = []

    for _name, row_stride, dtype, dtype_str, weight_dtype, weight_dtype_str, force in cases:
        if force:
            monkeypatch.setenv("FLYDSL_AUTOTUNE", "1")
        else:
            monkeypatch.delenv("FLYDSL_AUTOTUNE", raising=False)

        input_t, gamma, output, reference = _strided_inputs(M, N, row_stride, dtype, weight_dtype)
        rmsnorm_autotuned(input_t, gamma, output, M, stream=stream)
        torch.cuda.synchronize()
        _assert_close(output, reference)

        tuner_keys.append(_tuner_key(input_t, gamma, output, M, N, dtype_str, weight_dtype_str, stream))
        artifact_path, artifact_identity = _artifact_ref(
            input_t, gamma, output, M, N, dtype_str, weight_dtype_str, stream
        )
        artifact_paths.append(artifact_path)
        artifact_identities.append(artifact_identity)
        jit_keys.append(_jit_key(input_t, gamma, output, M, N, dtype_str, weight_dtype_str, stream))

    assert searches == 3
    assert len(_rmsnorm_tuner.cache) == 3
    assert tuner_keys[0] == tuner_keys[1] == tuner_keys[2]
    assert len({tuner_keys[0], tuner_keys[3], tuner_keys[4]}) == 3
    assert artifact_paths[0] == artifact_paths[1] == artifact_paths[2]
    assert artifact_identities[0] == artifact_identities[1] == artifact_identities[2]
    assert len(set(artifact_paths)) == 3
    assert jit_keys[0] == jit_keys[1] == jit_keys[2]
    assert len({jit_keys[0], jit_keys[3], jit_keys[4]}) == 3

    compiled = [rmsnorm_direct._mem_cache[key] for key in jit_keys]
    assert compiled[0] is compiled[1] is compiled[2]
    assert len({id(compiled[0]), id(compiled[3]), id(compiled[4])}) == 3

    artifacts = list(Path(os.environ["FLYDSL_AUTOTUNE_CONFIG_DIR"]).glob("rmsnorm-*.json"))
    assert len(artifacts) == 3
    incompatible = json.loads(artifact_paths[0].read_text())
    artifact_paths[3].write_text(json.dumps(incompatible))
    _rmsnorm_tuner.cache.clear()
    _rmsnorm_tuner._artifact_cache.clear()

    served_defaults = []

    def default_config(*_args, **_kwargs):
        config = Config(BLOCK_THREADS=128)
        served_defaults.append(config)
        return config

    monkeypatch.setattr(_rmsnorm_tuner, "default", default_config)
    monkeypatch.delenv("FLYDSL_AUTOTUNE", raising=False)
    input_t, gamma, output, reference = _strided_inputs(M, N, N, torch.float16, torch.float16)
    rmsnorm_autotuned(input_t, gamma, output, M, stream=stream)
    torch.cuda.synchronize()

    assert searches == 3
    assert [config.kwargs["BLOCK_THREADS"] for config in served_defaults] == [128]
    _assert_close(output, reference)
