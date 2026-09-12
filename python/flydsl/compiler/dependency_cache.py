# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

"""In-process caches for compile factories with Python dependency invalidation."""

from __future__ import annotations

import functools
import inspect
import threading
import types
from typing import Any, Callable, Optional


def _snapshot(value: Any, seen: tuple[int, ...] = ()) -> Any:
    if isinstance(value, (str, bytes, int, float, bool, type(None))):
        return (type(value), value)
    if isinstance(value, (tuple, list, set, frozenset, dict)):
        if id(value) in seen:
            return ("cycle", type(value))
        seen += (id(value),)
        if isinstance(value, dict):
            items = ((_snapshot(k, seen), _snapshot(v, seen)) for k, v in value.items())
            return (dict, tuple(sorted(items, key=repr)))
        items = (_snapshot(item, seen) for item in value)
        if isinstance(value, (set, frozenset)):
            items = sorted(items, key=repr)
        return (type(value), tuple(items))
    if callable(value):
        code = getattr(value, "__code__", None)
        code_identity = None if code is None else (code.co_code, repr(code.co_consts))
        return ("callable", id(value), code_identity)
    return (type(value), id(value))


def _dependency_refs(func: Callable) -> tuple[tuple[str, str, dict], ...]:
    """Find globals read by a function, including its nested function bodies."""
    try:
        root_dir = inspect.getfile(func)
    except (TypeError, OSError):
        root_dir = ""
    root_dir = root_dir.rsplit("/", 1)[0]
    refs: dict[tuple[str, str], dict] = {}
    visited_codes: set[int] = set()

    def walk_code(code: types.CodeType, globals_dict: dict) -> None:
        if id(code) in visited_codes:
            return
        visited_codes.add(id(code))
        module_name = globals_dict.get("__name__", "?")
        for name in code.co_names:
            if name not in globals_dict:
                continue
            refs.setdefault((name, module_name), globals_dict)
            value = globals_dict[name]
            underlying = getattr(value, "__func__", value)
            nested_code = getattr(underlying, "__code__", None)
            if nested_code is not None:
                try:
                    dependency_dir = inspect.getfile(underlying).rsplit("/", 1)[0]
                except (TypeError, OSError):
                    dependency_dir = ""
                if dependency_dir == root_dir:
                    walk_code(nested_code, getattr(underlying, "__globals__", globals_dict))
        for constant in code.co_consts:
            if isinstance(constant, types.CodeType):
                walk_code(constant, globals_dict)

    walk_code(func.__code__, func.__globals__)
    return tuple((name, module, refs[(name, module)]) for name, module in sorted(refs))


def _snapshot_refs(refs: tuple[tuple[str, str, dict], ...]) -> tuple:
    return tuple(
        ((name, module), _snapshot(globals_dict[name]) if name in globals_dict else ("missing",))
        for name, module, globals_dict in refs
    )


def dependency_lru_cache(maxsize: Optional[int] = 128, typed: bool = False):
    """Like :func:`functools.lru_cache`, invalidating when Python dependencies change.

    This is intended for compile factories that define a ``@flyc.jit`` or
    ``@flyc.kernel`` function inside the cached function. A normal ``lru_cache``
    returns the old wrapper before FlyDSL can retrace it; this decorator also
    watches globals referenced by nested function bodies and clears the cache
    when one is rebound or mutated.
    """

    def decorate(func: Callable) -> Callable:
        cached = functools.lru_cache(maxsize=maxsize, typed=typed)(func)
        refs = _dependency_refs(func)
        lock = threading.RLock()
        baseline = None

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal baseline
            current = _snapshot_refs(refs)
            with lock:
                if baseline is None:
                    baseline = current
                elif current != baseline:
                    cached.cache_clear()
                    baseline = current
                return cached(*args, **kwargs)

        def cache_clear() -> None:
            nonlocal baseline
            with lock:
                cached.cache_clear()
                baseline = None

        wrapper.cache_clear = cache_clear
        wrapper.cache_info = cached.cache_info
        wrapper.cache_parameters = cached.cache_parameters
        return wrapper

    return decorate
