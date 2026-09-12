# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

from __future__ import annotations

import pickle

import pytest

from flydsl.compiler.jit_executor import CompiledArtifact
from flydsl.compiler.jit_function import JitCacheManager


def _artifact() -> CompiledArtifact:
    artifact = object.__new__(CompiledArtifact)
    artifact._ir_text = "module {}"
    artifact._entry = "kernel"
    artifact._source_ir = None
    artifact._post_load_processors = []
    artifact._link_libs = []
    artifact._uses_explicit_module = False
    return artifact


def test_aot_cache_schema_round_trip(tmp_path):
    manager = JitCacheManager(tmp_path)
    manager.set("argument-schema", _artifact())

    fresh_manager = JitCacheManager(tmp_path)
    loaded = fresh_manager.get("argument-schema")

    assert isinstance(loaded, CompiledArtifact)
    assert loaded._entry == "kernel"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"not": "an envelope"}, "missing metadata fields"),
        (
            {
                "format": "flydsl.compiled-artifact",
                "schema_version": True,
                "cache_key": "argument-schema",
                "artifact": _artifact(),
            },
            "schema_version metadata must be an integer",
        ),
        (
            {
                "format": "flydsl.compiled-artifact",
                "schema_version": 999,
                "cache_key": "argument-schema",
                "artifact": None,
            },
            "unsupported schema version 999",
        ),
        (
            {
                "format": "flydsl.compiled-artifact",
                "schema_version": 1,
                "cache_key": "different-arguments",
                "artifact": None,
            },
            "cache_key metadata does not match the requested arguments",
        ),
    ],
)
def test_malformed_or_incompatible_aot_artifact_fails_without_cache_miss(
    tmp_path, payload, message
):
    manager = JitCacheManager(tmp_path)
    cache_file = manager._cache_file("argument-schema")
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with cache_file.open("wb") as output:
        pickle.dump(payload, output)

    with pytest.raises(RuntimeError, match=message):
        manager.get("argument-schema")


def test_corrupt_aot_artifact_fails_without_compile_fallback(tmp_path):
    manager = JitCacheManager(tmp_path)
    cache_file = manager._cache_file("argument-schema")
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_bytes(b"not a pickle")

    with pytest.raises(RuntimeError, match="could not deserialize pickle"):
        with manager.compile_lock("argument-schema"):
            pytest.fail("invalid cache was treated as a compile miss")


def test_failed_set_does_not_contaminate_memory_cache(tmp_path):
    manager = JitCacheManager(tmp_path)

    manager.set("argument-schema", {"not": "a compiled artifact"})

    assert "argument-schema" not in manager.memory_cache
    assert manager.get("argument-schema") is None
