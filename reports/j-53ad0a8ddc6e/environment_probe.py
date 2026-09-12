#!/usr/bin/env python3
"""Record the prepared interpreter, GPU identity, and Python/native import paths."""

import importlib
import json
import os
from pathlib import Path
import sys

import flydsl
import flydsl.expr
import torch


def main() -> None:
    module_paths = {}
    for name in (
        "flydsl",
        "flydsl.expr",
        "flydsl._mlir",
        "flydsl._mlir.ir",
        "flydsl._mlir.dialects._fly_ops_gen",
    ):
        try:
            module = importlib.import_module(name)
            module_paths[name] = getattr(module, "__file__", None)
        except Exception as exc:  # pragma: no cover - evidence collection
            module_paths[name] = f"IMPORT_ERROR: {exc!r}"

    native_root = Path("/opt/venv/lib/python3.12/site-packages/flydsl/_mlir")
    properties = torch.cuda.get_device_properties(0)
    print(
        json.dumps(
            {
                "python_executable": sys.executable,
                "torch_version": torch.__version__,
                "torch_hip": torch.version.hip,
                "device_count": torch.cuda.device_count(),
                "device_name": properties.name,
                "device_total_memory_bytes": properties.total_memory,
                "current_device": torch.cuda.current_device(),
                "visibility": {
                    key: os.environ.get(key)
                    for key in (
                        "CUDA_VISIBLE_DEVICES",
                        "HIP_VISIBLE_DEVICES",
                        "ROCR_VISIBLE_DEVICES",
                    )
                },
                "module_paths": module_paths,
                "prepared_native_root": str(native_root),
                "native_shared_objects": sorted(
                    str(path) for path in native_root.rglob("*.so")
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
