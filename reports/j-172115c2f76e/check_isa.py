"""Regression predicate for the captured gfx950 SGPR staging failure."""

import re
import sys


text = open(sys.argv[1], encoding="utf-8").read()

required_copy = "s_mov_b64 s[60:61], s[80:81]"
writes = [
    f"v_writelane_b32 v254, s{reg}, {lane}"
    for reg, lane in zip(range(56, 64), range(8))
]
affected_loads = re.findall(
    r"^\s*buffer_load_dwordx4 .*s\[(?:48:51|76:79)\].*$", text, re.MULTILINE
)

errors = []
if required_copy not in text:
    errors.append(f"missing required reaching definition: {required_copy}")
for write in writes:
    if write not in text:
        errors.append(f"missing expected spill write: {write}")
if len(affected_loads) != 16:
    errors.append(f"expected 16 affected descriptor loads, found {len(affected_loads)}")

print(f"required_copy_present={required_copy in text}")
print(f"affected_descriptor_loads={len(affected_loads)}")
for error in errors:
    print(error)
sys.exit(bool(errors))
