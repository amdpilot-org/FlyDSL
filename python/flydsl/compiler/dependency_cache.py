# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

"""In-process caches for compile factories with Python dependency invalidation."""

from __future__ import annotations

import dis
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


def _dependency_refs(func: Callable) -> tuple[tuple, ...]:
    """Find global and closure reads, including attribute paths and nested bodies."""
    try:
        root_dir = inspect.getfile(func)
    except (TypeError, OSError):
        root_dir = ""
    root_dir = root_dir.rsplit("/", 1)[0]
    refs: dict[tuple, tuple] = {}
    visited_codes: set[int] = set()
    root_cells = dict(zip(func.__code__.co_freevars, func.__closure__ or ()))

    def walk_code(code: types.CodeType, globals_dict: dict, cells: dict) -> None:
        if id(code) in visited_codes:
            return
        visited_codes.add(id(code))
        module_name = globals_dict.get("__name__", "?")
        instructions = tuple(dis.get_instructions(code))
        for index, instruction in enumerate(instructions):
            if instruction.opname == "LOAD_GLOBAL" and instruction.argval in globals_dict:
                name = instruction.argval
                kind, source = "global", globals_dict
                value = globals_dict[name]
            elif instruction.opname in ("LOAD_DEREF", "LOAD_CLASSDEREF") and instruction.argval in cells:
                name = instruction.argval
                kind, source = "closure", cells[name]
                try:
                    value = source.cell_contents
                except ValueError:
                    continue
            else:
                continue

            attrs = []
            for following in instructions[index + 1 :]:
                if following.opname == "LOAD_ATTR":
                    attrs.append(following.argval)
                else:
                    break
            key = (kind, module_name, name, tuple(attrs))
            refs.setdefault(key, (kind, name, module_name, source, tuple(attrs)))

            underlying = getattr(value, "__func__", value)
            nested_code = getattr(underlying, "__code__", None)
            if nested_code is not None:
                try:
                    dependency_dir = inspect.getfile(underlying).rsplit("/", 1)[0]
                except (TypeError, OSError):
                    dependency_dir = ""
                if dependency_dir == root_dir:
                    nested_cells = dict(
                        zip(nested_code.co_freevars, getattr(underlying, "__closure__", None) or ())
                    )
                    walk_code(
                        nested_code,
                        getattr(underlying, "__globals__", globals_dict),
                        nested_cells,
                    )
        for constant in code.co_consts:
            if isinstance(constant, types.CodeType):
                walk_code(constant, globals_dict, cells)

    walk_code(func.__code__, func.__globals__, root_cells)
    return tuple(refs[key] for key in sorted(refs, key=repr))


def _snapshot_refs(refs: tuple[tuple, ...]) -> tuple:
    snapshots = []
    for kind, name, module, source, attrs in refs:
        try:
            value = source[name] if kind == "global" else source.cell_contents
            for attr in attrs:
                value = inspect.getattr_static(value, attr)
            snapshot = _snapshot(value)
        # Static lookup avoids invoking DSL proxy attribute hooks, which may
        # emit IR and require a live compilation context.
        except (KeyError, AttributeError, TypeError, ValueError):
            snapshot = ("missing",)
        snapshots.append(((kind, name, module, attrs), snapshot))
    return tuple(snapshots)


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
