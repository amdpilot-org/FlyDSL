"""Compile captured MLIR to gfx950 assembly, optionally dumping greedy MachineIR."""

import argparse
import re

from flydsl._mlir import ir
from flydsl._mlir.passmanager import PassManager
from flydsl.compiler.llvm_options import llvm_options


parser = argparse.ArgumentParser()
parser.add_argument("input")
parser.add_argument("output")
parser.add_argument("--waves-per-eu", type=int)
parser.add_argument("--mir", choices=("before", "after"))
parser.add_argument("--verify", action="store_true")
args = parser.parse_args()

options = {}
if args.verify:
    options.update({"verify-machineinstrs": True, "verify-regalloc": True})
if args.mir:
    options[f"print-{args.mir}"] = "greedy"

pass_options = ""
if args.waves_per_eu is not None:
    pass_options = f' opts="--amdgpu-waves-per-eu={args.waves_per_eu}"'

with ir.Context(), llvm_options(options):
    module = ir.Module.parse(open(args.input, encoding="utf-8").read())
    PassManager.parse(
        f"builtin.module(gpu-module-to-binary{{format=isa{pass_options}}})"
    ).run(module.operation)
    text = str(module)

start = text.index('assembly = "') + len('assembly = "')
end = text.index('">]', start)
assembly = re.sub(
    r"\\([0-9A-Fa-f]{2})",
    lambda match: chr(int(match.group(1), 16)),
    text[start:end],
)
open(args.output, "w", encoding="utf-8").write(assembly)
