# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

import flydsl.compiler as flyc


def _helper():
    return "old"


@flyc.dependency_lru_cache(maxsize=4)
def _compile_factory(signature):
    def traced_body():
        return _helper()

    return traced_body


def test_nested_helper_rebinding_invalidates_compile_factory(monkeypatch):
    """A cache hit must not return a wrapper built around the old helper."""
    _compile_factory.cache_clear()

    old_wrapper = _compile_factory("same-static-signature")
    assert old_wrapper() == "old"
    assert _compile_factory("same-static-signature") is old_wrapper

    monkeypatch.setattr(__name__ + "._helper", lambda: "new")
    new_wrapper = _compile_factory("same-static-signature")

    assert new_wrapper is not old_wrapper
    assert new_wrapper() == "new"
