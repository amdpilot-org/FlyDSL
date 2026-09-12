"""Compile the issue's captured MLIR and write its embedded gfx950 ISA."""

import re
import sys

from flydsl._mlir import ir
from flydsl._mlir.passmanager import PassManager


with ir.Context():
    module = ir.Module.parse(open(sys.argv[1], encoding="utf-8").read())
    PassManager.parse(
        'builtin.module(gpu-module-to-binary{format=isa opts="--amdgpu-waves-per-eu=1"})'
    ).run(module.operation)
    text = str(module)

start = text.index('assembly = "') + len('assembly = "')
end = text.index('">]', start)
assembly = re.sub(
    r"\\([0-9A-Fa-f]{2})",
    lambda match: chr(int(match.group(1), 16)),
    text[start:end],
)
open(sys.argv[2], "w", encoding="utf-8").write(assembly)
