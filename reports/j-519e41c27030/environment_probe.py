#!/usr/bin/env python3

"""Record the visible GPU, software versions, and resolved import paths."""

import importlib
import json
import os
from pathlib import Path

import torch


def module_location(name):
    module = importlib.import_module(name)
    file = getattr(module, "__file__", None)
    spec = module.__spec__
    return {
        "file": file,
        "resolved_file": str(Path(file).resolve()) if file else None,
        "origin": spec.origin if spec else None,
        "search_locations": list(spec.submodule_search_locations or []) if spec else [],
    }


props = torch.cuda.get_device_properties(0)
print(
    json.dumps(
        {
            "torch_version": torch.__version__,
            "torch_hip_version": torch.version.hip,
            "cuda_available": torch.cuda.is_available(),
            "device_count_visible": torch.cuda.device_count(),
            "current_device": torch.cuda.current_device(),
            "device_name": torch.cuda.get_device_name(0),
            "device_properties": str(props),
            "ROCR_VISIBLE_DEVICES": os.environ.get("ROCR_VISIBLE_DEVICES"),
            "HIP_VISIBLE_DEVICES": os.environ.get("HIP_VISIBLE_DEVICES"),
            "CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "imports": {
                name: module_location(name)
                for name in (
                    "flydsl",
                    "flydsl.expr",
                    "flydsl.compiler",
                    "flydsl._mlir.ir",
                    "flydsl._mlir._mlir_libs._mlir",
                )
            },
        },
        indent=2,
        sort_keys=True,
    )
)
