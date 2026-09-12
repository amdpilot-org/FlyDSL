#!/usr/bin/env python3
"""Compile a minimal kernel and report serialized GPU objects/targets."""

import os
import re
from pathlib import Path

import flydsl.compiler as flyc
import flydsl.expr as fx


@flyc.kernel
def _noop_kernel():
    pass


@flyc.jit
def _noop_launch(stream: fx.Stream = fx.Stream(None)):
    _noop_kernel().launch(grid=(1, 1, 1), block=(32, 1, 1), stream=stream)


def main():
    _noop_launch._call_state_cache.clear()
    _noop_launch._mem_cache.clear()
    _noop_launch._last_compiled = None
    _noop_launch.manager_key = None
    _noop_launch.cache_manager = None

    flyc.compile[{"fast_fp_math": True, "unsafe_fp_math": True}](_noop_launch)()
    ir_text = _noop_launch._last_compiled[1]._ir_text
    output = Path(os.environ.get("REPRO_IR", "duplicate-targets.mlir"))
    output.write_text(ir_text)

    objects = ir_text.count("#gpu.object<")
    targets = re.findall(r"#rocdl\.target<[^>]*>", ir_text)
    print(f"arch={os.environ.get('ARCH', '<auto>')}")
    print(f"gpu_objects={objects}")
    print(f"offloading_handler={'#gpu.select_object' in ir_text or '#fly.explicit_module' in ir_text}")
    for index, target in enumerate(targets):
        print(f"target[{index}]={target}")
    print(f"ir={output.resolve()}")


if __name__ == "__main__":
    main()
