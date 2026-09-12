#!/usr/bin/env python3
"""Measure one uncached AST rewrite per fresh Python interpreter."""

import argparse
import json
import linecache
import statistics
import subprocess
import sys
import time


def measure_once():
    from flydsl.compiler.ast_rewriter import ASTRewriter, Transformer

    source = "def measured(x):\n" + "".join(f"    v{i} = x + {i}\n" for i in range(1000)) + "    return v999\n"
    filename = "/tmp/flydsl_ast_cold.py"
    linecache.cache[filename] = (len(source), None, source.splitlines(True), filename)
    namespace = {}
    exec(compile(source, filename, "exec"), namespace)

    visits = {}
    original_visit = Transformer.visit

    def counted_visit(self, node):
        name = type(self).__name__
        visits[name] = visits.get(name, 0) + 1
        return original_visit(self, node)

    Transformer.visit = counted_visit
    start = time.perf_counter_ns()
    ASTRewriter.transform(namespace["measured"])
    elapsed_ms = (time.perf_counter_ns() - start) / 1e6
    print(json.dumps({"elapsed_ms": elapsed_ms, "visits": visits, "total_visits": sum(visits.values())}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=15)
    parser.add_argument("--single", action="store_true")
    args = parser.parse_args()
    if args.single:
        measure_once()
        return

    rows = []
    for _ in range(args.samples):
        output = subprocess.check_output([sys.executable, __file__, "--single"], text=True)
        rows.append(json.loads(output))
    elapsed = [row["elapsed_ms"] for row in rows]
    print(
        json.dumps(
            {
                "samples": len(rows),
                "median_ms": statistics.median(elapsed),
                "mean_ms": statistics.mean(elapsed),
                "min_ms": min(elapsed),
                "max_ms": max(elapsed),
                "total_visits_per_sample": sorted({row["total_visits"] for row in rows}),
                "visits": rows[0]["visits"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
