# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

"""Analyze AMDGPU assembly emitted by ``FLYDSL_DUMP_IR=1``.

The parser deliberately consumes final assembly rather than an earlier IR
stage.  Its counts therefore describe instructions that survived LLVM's
scheduler and register allocator.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

_METADATA_FIELDS = {
    ".amdhsa_next_free_vgpr": "next_free_vgpr",
    ".amdhsa_next_free_sgpr": "next_free_sgpr",
    ".amdhsa_group_segment_fixed_size": "lds_bytes",
    ".amdhsa_private_segment_fixed_size": "scratch_bytes",
    ".amdhsa_wavefront_size32": "wavefront_size32",
}


def _instruction(line: str) -> str | None:
    # AMD assembly uses both // and /* ... */ comments.  Dumped instructions
    # are one per line; discarding a trailing block comment is sufficient and
    # avoids counting examples in comments or metadata strings.
    line = line.split("//", 1)[0].split("/*", 1)[0].strip()
    if not line or line.startswith((".", "#")) or line.endswith(":"):
        return None
    token = line.split(None, 1)[0]
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.]*", token):
        return None
    return token.lower()


def _families(opcodes: Counter[str]) -> dict[str, int]:
    def count(*prefixes: str) -> int:
        return sum(n for op, n in opcodes.items() if op.startswith(prefixes))

    return {
        "mfma_wmma": count("v_mfma", "v_wmma"),
        "vmem_load": count("buffer_load", "global_load", "flat_load", "scratch_load"),
        "vmem_store": count("buffer_store", "global_store", "flat_store", "scratch_store"),
        "lds_read": count("ds_read"),
        "lds_write": count("ds_write"),
        "waitcnt": count("s_waitcnt"),
        "barrier": count("s_barrier", "s_sched_barrier"),
    }


def analyze_isa(assembly: str) -> dict:
    """Return stable, JSON-serializable metrics for AMDGPU *assembly*.

    Register values are the assembler's ``next_free`` metadata, i.e. the
    allocated register high-water marks. They are not inferred from textual
    operands, which would miss implicit and reserved registers.
    """

    opcodes: Counter[str] = Counter()
    kernels: dict[str, dict[str, int]] = {}
    current_kernel: str | None = None

    for raw_line in assembly.splitlines():
        line = raw_line.strip()
        match = re.match(r"\.amdhsa_kernel\s+([^\s]+)", line)
        if match:
            current_kernel = match.group(1)
            kernels.setdefault(current_kernel, {})
            continue
        if line.startswith(".end_amdhsa_kernel"):
            current_kernel = None
            continue
        if current_kernel:
            for directive, field in _METADATA_FIELDS.items():
                match = re.match(rf"{re.escape(directive)}\s+([^\s]+)", line)
                if match:
                    try:
                        kernels[current_kernel][field] = int(match.group(1), 0)
                    except ValueError:
                        pass
                    break

        opcode = _instruction(raw_line)
        if opcode is not None:
            opcodes[opcode] += 1

    return {
        "instruction_count": sum(opcodes.values()),
        "families": _families(opcodes),
        "opcodes": dict(sorted(opcodes.items())),
        "kernels": kernels,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize final AMDGPU ISA dumped by FlyDSL")
    parser.add_argument("isa", type=Path, nargs="+", help="one or more *_final_isa.s files")
    parser.add_argument("--pretty", action="store_true", help="indent JSON output")
    args = parser.parse_args(argv)

    reports = {str(path): analyze_isa(path.read_text(encoding="utf-8")) for path in args.isa}
    result = next(iter(reports.values())) if len(reports) == 1 else reports
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
