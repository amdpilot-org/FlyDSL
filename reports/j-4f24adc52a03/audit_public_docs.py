#!/usr/bin/env python3
"""Audit syntactically public Python symbols at a Git revision."""

import ast
import json
import subprocess
import sys
from collections import Counter


revision = sys.argv[1]
paths = subprocess.check_output(
    ["git", "ls-tree", "-r", "--name-only", revision, "python/flydsl/expr", "python/flydsl/compiler", "python/flydsl/utils"],
    text=True,
).splitlines()
counts = Counter()
symbols = {}
for path in paths:
    if not path.endswith(".py"):
        continue
    source = subprocess.check_output(["git", "show", f"{revision}:{path}"], text=True)
    tree = ast.parse(source, filename=path)
    area = path.split("/")[2]
    module = path.removeprefix("python/").removesuffix(".py").replace("/", ".")
    candidates = [(node, node.name) for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))]
    for parent in (node for node in tree.body if isinstance(node, ast.ClassDef)):
        candidates.extend(
            (node, f"{parent.name}.{node.name}")
            for node in parent.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
    for node, name in candidates:
        if name.rsplit(".", 1)[-1].startswith("_"):
            continue
        doc = ast.get_docstring(node)
        key = f"{module}.{name}"
        if not doc:
            counts[f"{area}_missing_docstring"] += 1
            symbols[key] = "missing_docstring"
        elif "Example:" not in doc:
            counts[f"{area}_missing_example"] += 1
            symbols[key] = "missing_example"

reviewed = {
    key: symbols.get(key, "complete")
    for key in (
        "flydsl.compiler.backends.base.GPUTarget",
        "flydsl.compiler.backends.base.BaseBackend",
        "flydsl.utils.env.EnvOption",
        "flydsl.utils.env.EnvManager",
    )
}
print(json.dumps({"revision": revision, "counts": dict(sorted(counts.items())), "reviewed": reviewed}, indent=2))
