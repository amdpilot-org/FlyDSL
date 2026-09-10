import runpy

import torch

import flydsl.compiler as flyc
from flydsl.compiler.backends.rocm import RocmBackend


original_pipeline_parts = RocmBackend._pipeline_parts


def compatibility_pipeline_parts(self, *, compile_hints):
    pre_binary, binary = original_pipeline_parts(self, compile_hints=compile_hints)
    pre_binary = [fragment.replace("convert-rocdl-fastmath-ops,", "") for fragment in pre_binary]
    return pre_binary, binary


RocmBackend._pipeline_parts = compatibility_pipeline_parts

print("flydsl", flyc.__name__)
print("gpu", torch.cuda.get_device_name(0))
runpy.run_path("/job/FlyDSL/examples/01-vectorAdd.py", run_name="__main__")
