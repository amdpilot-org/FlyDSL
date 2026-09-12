# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

from types import ModuleType, SimpleNamespace

import pytest

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


@pytest.mark.parametrize("container_type", [SimpleNamespace, ModuleType])
def test_nested_attribute_helper_rebinding_invalidates_compile_factory(container_type):
    helpers = container_type("helpers") if container_type is ModuleType else container_type()
    helpers.fn = lambda: "old"

    @flyc.dependency_lru_cache(maxsize=4)
    def compile_factory(signature):
        def traced_body():
            return helpers.fn()

        return traced_body

    old_wrapper = compile_factory("same-static-signature")
    assert compile_factory("same-static-signature") is old_wrapper

    helpers.fn = lambda: "new"
    new_wrapper = compile_factory("same-static-signature")

    assert new_wrapper is not old_wrapper
    assert new_wrapper() == "new"


def test_nested_closure_helper_rebinding_invalidates_compile_factory():
    helper = lambda: "old"

    @flyc.dependency_lru_cache(maxsize=4)
    def compile_factory(signature):
        def traced_body():
            return helper()

        return traced_body

    old_wrapper = compile_factory("same-static-signature")
    assert compile_factory("same-static-signature") is old_wrapper

    helper = lambda: "new"
    new_wrapper = compile_factory("same-static-signature")

    assert new_wrapper is not old_wrapper
    assert new_wrapper() == "new"
