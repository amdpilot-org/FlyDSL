from __future__ import annotations

import pytest

import flydsl.compiler as flyc


@flyc.jit
def _empty_launch():
    pass


def test_run_only_cache_miss_reports_relocation_identity(tmp_path, monkeypatch):
    cache_dir = tmp_path / "missing-aot-cache"

    monkeypatch.setenv("FLYDSL_RUNTIME_CACHE_DIR", str(cache_dir))
    monkeypatch.setenv("FLYDSL_RUNTIME_ENABLE_CACHE", "1")
    monkeypatch.setenv("FLYDSL_RUNTIME_RUN_ONLY", "1")

    with pytest.raises(RuntimeError) as exc_info:
        _empty_launch()

    message = str(exc_info.value)
    assert "no usable AOT cache for _empty_launch" in message
    assert "manager_key=" in message
    assert "cache_key=" in message
    assert f"cache_dir={cache_dir}/_empty_launch_" in message
    assert "(exists=False)" in message
    assert not cache_dir.exists()
