# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest


pytestmark = [pytest.mark.l2_device, pytest.mark.rocm_lower]


_SOURCE = r'''
import flydsl.compiler as flyc
import flydsl.expr as fx


@flyc.kernel
def vector_add_kernel(
    A: fx.Tensor,
    B: fx.Tensor,
    C: fx.Tensor,
    tiled_copy: fx.TiledCopy,
):
    tid = fx.thread_idx.x
    bid_x, bid_y = fx.block_idx.x, fx.block_idx.y
    M, N = A.shape.unpack()
    idC = fx.make_view((0, 0), fx.make_identity_layout((M, N)))
    TileMN = tiled_copy.tile_mn
    gA = fx.flat_divide(A, TileMN)[None, None, bid_x, bid_y]
    gB = fx.flat_divide(B, TileMN)[None, None, bid_x, bid_y]
    gC = fx.flat_divide(C, TileMN)[None, None, bid_x, bid_y]
    cC = fx.flat_divide(idC, TileMN)[None, None, bid_x, bid_y]
    thr_copy = tiled_copy.get_slice(tid)
    thr_gA = thr_copy.partition_S(gA)
    thr_gB = thr_copy.partition_S(gB)
    thr_gC = thr_copy.partition_D(gC)
    thr_cC = thr_copy.partition_S(cC)[(0, None), None, None]
    thr_rA = fx.make_fragment_like(thr_gA)
    thr_rB = fx.make_fragment_like(thr_gB)
    thr_rC = fx.make_fragment_like(thr_gC)
    thr_pC = fx.make_fragment_like(thr_cC, dtype=fx.Boolean)
    for index in fx.range_constexpr(fx.size(thr_pC.shape).unpack()):
        thr_pC[index] = fx.elem_less(thr_cC[index], (M, N))
    copy_atom = fx.make_copy_atom(fx.UniversalCopy128b(), fx.Float32)
    fx.copy(copy_atom, thr_gA, thr_rA, pred=thr_pC)
    fx.copy(copy_atom, thr_gB, thr_rB, pred=thr_pC)
    thr_rC.store(ARITHMETIC)
    fx.copy(copy_atom, thr_rC, thr_gC, pred=thr_pC)


@flyc.jit
def vector_add(
    A: fx.Tensor,
    B: fx.Tensor,
    C: fx.Tensor,
    stream: fx.Stream = fx.Stream(None),
):
    copy_atom = fx.make_copy_atom(fx.UniversalCopy128b(), fx.Float32)
    tiled_copy = fx.make_tiled_copy_tv(
        copy_atom,
        fx.make_ordered_layout((8, 16), order=(1, 0)),
        fx.make_ordered_layout((1, 4), order=(0, 1)),
    )
    tile_m, tile_n = tiled_copy.tile_mn.unpack()
    M, N = A.shape.unpack()
    grid_m = (M + tile_m - 1) // tile_m
    grid_n = (N + tile_n - 1) // tile_n
    vector_add_kernel(A, B, C, tiled_copy).launch(
        grid=(grid_m, grid_n, 1), block=(8 * 16, 1, 1), stream=stream
    )
'''


def _load_revision(path: Path, arithmetic: str):
    source = _SOURCE.replace("ARITHMETIC", arithmetic)
    path.write_text(source)
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_source_change_invalidates_jit_cache(tmp_path, monkeypatch):
    torch = pytest.importorskip("torch")
    if not torch.cuda.is_available():
        pytest.skip("A GPU is required for JIT source-change invalidation")

    cache_root = tmp_path / "flydsl-cache"
    monkeypatch.setenv("FLYDSL_RUNTIME_CACHE_DIR", str(cache_root))

    revisions = {
        "add": _load_revision(
            tmp_path / "revision_add.py", "thr_rA.load() + thr_rB.load()"
        ),
        "add_plus_two_b": _load_revision(
            tmp_path / "revision_add_plus_two_b.py",
            "thr_rA.load() + 2 * thr_rB.load()",
        ),
    }

    a = torch.arange(0, 512, dtype=torch.float32, device="cuda").reshape(8, 64)
    b = torch.arange(100, 612, dtype=torch.float32, device="cuda").reshape(8, 64)
    stream = torch.cuda.Stream()
    references = {
        "add": a + b,
        "add_plus_two_b": a + 2 * b,
    }

    identities = {}
    for label, module in revisions.items():
        output = torch.zeros_like(a)
        module.vector_add(a, b, output, stream=stream)
        torch.cuda.synchronize()
        assert torch.equal(output, references[label])

        warm_output = torch.zeros_like(a)
        module.vector_add(a, b, warm_output, stream=stream)
        torch.cuda.synchronize()
        assert torch.equal(warm_output, references[label])

        cache_dir = cache_root / f"vector_add_{module.vector_add.manager_key}"
        artifacts = sorted(cache_dir.glob("*.pkl"))
        assert len(artifacts) == 1
        identities[label] = {
            "source": _sha256(tmp_path / f"revision_{label}.py"),
            "manager_key": module.vector_add.manager_key,
            "artifact": _sha256(artifacts[0]),
        }

    assert identities["add"]["source"] != identities["add_plus_two_b"]["source"]
    assert identities["add"]["manager_key"] != identities["add_plus_two_b"]["manager_key"]
    assert identities["add"]["artifact"] != identities["add_plus_two_b"]["artifact"]
