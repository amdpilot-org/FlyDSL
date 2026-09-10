# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""Device coverage for candidate pruning and selected-result correctness."""

import pytest
import torch

import flydsl.compiler as flyc
import flydsl.expr as fx
from flydsl.autotune import Config, autotune

pytestmark = [pytest.mark.l2_device, pytest.mark.rocm_lower]

if torch is None or not torch.cuda.is_available():
    pytest.skip("CUDA/ROCm not available. Skipping GPU tests.", allow_module_level=True)


SIZE = 1024
VALID_BLOCK_DIM = 64
INVALID_BLOCK_DIM = 0
VEC_WIDTH = 4


@flyc.kernel
def _vector_add_kernel(
    A: fx.Tensor,
    B: fx.Tensor,
    C: fx.Tensor,
    block_dim: fx.Constexpr[int],
    vec_width: fx.Constexpr[int],
):
    bid = fx.block_idx.x
    tid = fx.thread_idx.x
    tile = block_dim * vec_width

    tA = fx.slice(fx.logical_divide(A, fx.make_layout(tile, 1)), (None, bid))
    tB = fx.slice(fx.logical_divide(B, fx.make_layout(tile, 1)), (None, bid))
    tC = fx.slice(fx.logical_divide(C, fx.make_layout(tile, 1)), (None, bid))
    tA = fx.logical_divide(tA, fx.make_layout(vec_width, 1))
    tB = fx.logical_divide(tB, fx.make_layout(vec_width, 1))
    tC = fx.logical_divide(tC, fx.make_layout(vec_width, 1))

    atom = fx.make_copy_atom(fx.UniversalCopy(vec_width * 32), fx.Float32)
    rA = fx.make_rmem_tensor(vec_width, fx.Float32)
    rB = fx.make_rmem_tensor(vec_width, fx.Float32)
    rC = fx.make_rmem_tensor(vec_width, fx.Float32)

    fx.copy_atom_call(atom, fx.slice(tA, (None, tid)), rA)
    fx.copy_atom_call(atom, fx.slice(tB, (None, tid)), rB)
    fx.memref_store_vec(fx.arith.addf(fx.memref_load_vec(rA), fx.memref_load_vec(rB)), rC)
    fx.copy_atom_call(atom, rC, fx.slice(tC, (None, tid)))


@flyc.jit
def _vector_add(
    A: fx.Tensor,
    B: fx.Tensor,
    C: fx.Tensor,
    n: fx.Int32,
    block_dim: fx.Constexpr[int],
    vec_width: fx.Constexpr[int],
    stream: fx.Stream = fx.Stream(None),
):
    tile = block_dim * vec_width
    grid = (n + tile - 1) // tile
    _vector_add_kernel(A, B, C, block_dim, vec_width).launch(
        grid=(grid, 1, 1),
        block=(block_dim, 1, 1),
        stream=stream,
    )


def _default_config(*_args, **_kwargs):
    return Config(block_dim=VALID_BLOCK_DIM, vec_width=VEC_WIDTH)


def _candidate_configs(*_args, **_kwargs):
    return [
        Config(block_dim=VALID_BLOCK_DIM, vec_width=VEC_WIDTH),
        Config(block_dim=INVALID_BLOCK_DIM, vec_width=VEC_WIDTH),
    ]


def _prune_candidates(configs, _sig_args):
    return [config for config in configs if 0 < config.kwargs["block_dim"] <= 256]


_tuner = autotune(
    configs=_candidate_configs,
    key=["n"],
    default=_default_config,
    prune_configs_by=_prune_candidates,
)(_vector_add)


@pytest.fixture(autouse=True)
def _isolated_tuner(tmp_path, monkeypatch):
    _tuner.cache.clear()
    _tuner._artifact_cache.clear()
    monkeypatch.setattr(_tuner, "_cache_file", tmp_path / "vector-add.json")
    monkeypatch.setenv("FLYDSL_AUTOTUNE_CACHE_DIR", str(tmp_path / "autotune-cache"))
    monkeypatch.setenv("FLYDSL_AUTOTUNE_CONFIG_DIR", str(tmp_path / "artifacts"))
    monkeypatch.delenv("FLYDSL_AUTOTUNE", raising=False)
    yield
    _tuner.cache.clear()
    _tuner._artifact_cache.clear()


def _inputs():
    generator = torch.Generator(device="cuda").manual_seed(0)
    a = torch.randn(SIZE, device="cuda", dtype=torch.float32, generator=generator)
    b = torch.randn(SIZE, device="cuda", dtype=torch.float32, generator=generator)
    return a, b, torch.empty_like(a)


def test_default_path_skips_search_and_matches_reference(monkeypatch):
    monkeypatch.setenv("FLYDSL_AUTOTUNE", "0")
    monkeypatch.setattr(_tuner, "_bench_one", lambda *_args, **_kwargs: pytest.fail("unexpected search"))

    a, b, output = _inputs()
    _tuner(a, b, output, SIZE, stream=torch.cuda.current_stream())
    torch.cuda.synchronize()

    torch.testing.assert_close(output, a + b, rtol=0, atol=0)


def test_pruning_selects_valid_candidate_and_matches_reference(monkeypatch):
    monkeypatch.setenv("FLYDSL_AUTOTUNE", "1")
    benchmarked = []

    def bench_once(config, *_args, **_kwargs):
        benchmarked.append(config)
        return 1.0

    monkeypatch.setattr(_tuner, "_bench_one", bench_once)
    a, b, output = _inputs()
    stream = torch.cuda.current_stream()
    _tuner(a, b, output, SIZE, stream=stream)
    stream.synchronize()

    assert [config.kwargs for config in benchmarked] == [{"block_dim": VALID_BLOCK_DIM, "vec_width": VEC_WIDTH}]
    key = _tuner._make_key((a, b, output, SIZE), {"stream": stream})
    assert _tuner.cache[key].kwargs == {"block_dim": VALID_BLOCK_DIM, "vec_width": VEC_WIDTH}
    torch.testing.assert_close(output, a + b, rtol=0, atol=0)


def test_all_invalid_candidates_retain_the_real_error(monkeypatch):
    monkeypatch.setenv("FLYDSL_AUTOTUNE", "1")
    monkeypatch.setattr(_tuner, "configs", [Config(block_dim=INVALID_BLOCK_DIM, vec_width=VEC_WIDTH)])
    monkeypatch.setattr(_tuner, "prune_configs_by", None)
    a, b, output = _inputs()

    with pytest.raises(RuntimeError, match="All autotune configs failed") as excinfo:
        _tuner(a, b, output, SIZE, stream=torch.cuda.current_stream())

    assert isinstance(excinfo.value.__cause__, ValueError)
    assert "known_block_size[0] must be positive, got 0" in str(excinfo.value.__cause__)
    assert not _tuner.cache
