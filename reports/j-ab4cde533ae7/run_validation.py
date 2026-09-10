import argparse
import json
import time

import torch
import flydsl
import flydsl.compiler.jit_function as jit_function


original_run_pipeline = jit_function._run_pipeline


def run_pipeline_without_stale_fastmath_pass(module, fragments, **kwargs):
    fragments = [
        fragment.replace("convert-rocdl-fastmath-ops,", "")
        for fragment in fragments
    ]
    return original_run_pipeline(module, fragments, **kwargs)


jit_function._run_pipeline = run_pipeline_without_stale_fastmath_pass

from tests.kernels.test_integer_predicate_select import (
    test_loaded_integer_predicates_and_select,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    started = time.perf_counter()
    passed = False
    mismatches = []
    error = None
    try:
        test_loaded_integer_predicates_and_select()
        passed = True
    except AssertionError as exc:
        error = str(exc)
        if exc.args and isinstance(exc.args[0], list):
            mismatches = exc.args[0]
    elapsed = time.perf_counter() - started

    report = {
        "label": args.label,
        "source_commit": args.source_commit,
        "passed": passed,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "error": error,
        "elapsed_s": elapsed,
        "timing_method": "time.perf_counter around one JIT dispatch and synchronization",
        "gpu_name": torch.cuda.get_device_name(0),
        "gpu_capability": list(torch.cuda.get_device_capability(0)),
        "python": torch.__file__.replace("/torch/__init__.py", "/bin/python"),
        "flydsl_import_path": flydsl.__file__,
        "flydsl_version": flydsl.__version__,
    }
    with open(args.output, "w", encoding="utf-8") as output:
        json.dump(report, output, indent=2, sort_keys=True)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
