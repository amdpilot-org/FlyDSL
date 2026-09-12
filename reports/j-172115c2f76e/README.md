# Independent review: gfx950 SGPR spill-staging miscompile

Source issue: https://github.com/ROCm/FlyDSL/issues/1087

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/579

Reviewed change: https://github.com/amdpilot-org/FlyDSL/pull/497

## Verdict

The compiler diagnosis in PR 497 is independently reproduced with the exact
captured upstream MLIR. This is a review report, not a FlyDSL fix. The unsafe
kernel was never launched.

The decompressed input hashes to
`5ca5000c39324dcc4735024f587fa3c8d5b62b276acc8bd355ebab65a9f297ef`.
Codegen with the prepared interpreter and `--amdgpu-waves-per-eu=1` emits ISA
hash `1452f52355effa38e7018af519828f1902d6960c82493a410fc75684a5684cef`,
exactly matching the report. The embedded compiler identifies as LLVM
24.0.0git revision `e2a39f504fee836e4def9581bed817ecc327b9dc`; this agrees
between `thirdparty/llvm-build-info.json` and the native library's embedded
version strings. The SDK clang is a distinct LLVM 22 build and is not the
code generator under review.

## MachineIR and ISA findings

Pre-greedy MachineIR has one defined `%72:sgpr_512` from
`S_LOAD_DWORDX16_IMM_ec` at kernarg offset 248. Its `sub4` and `sub5` are
ordinary uses at 75680B--75760B, alongside uses of the other relevant
subregisters. There is no source-level undefined value.

Post-greedy MachineIR changes the value into a split interval. At 9828B the
copy into `%8004` covers `sub0_sub1_sub2_sub3` and `sub6_sub7`, but not
`sub4_sub5`; the full `%8004:sgpr_512` is then spilled. At 115896B it is
restored, and the copy-out at 115992B explicitly copies `sub4_sub5` before
they are consumed by multiply instructions. The defect is therefore
introduced by greedy allocation/live-range splitting, between the two dumps.

The final ISA has only:

```
s_mov_b64 s[56:57], s[76:77]
s_mov_b64 s[58:59], s[78:79]
s_mov_b64 s[62:63], s[82:83]
```

It lacks `s_mov_b64 s[60:61], s[80:81]`, yet writes s60/s61 to v254 lanes
4/5. No earlier ISA definition reaches those writes. The lanes are later read
into s16/s17 and propagated into descriptor base words. The retained final ISA
contains exactly 16 `buffer_load_dwordx4` operations using the two tainted
descriptor instances: eight through s[48:51] and eight through s[76:79].

## Controls

Removing the waves-per-EU option and changing it to 2 both reproduce the same
ISA byte-for-byte. A separately supplied clean sibling object was disassembled
with the same SDK objdump; its corresponding spill group writes defined
s12--s27 values rather than the missing s60/s61 pair. The affected sibling
object reproduces the reported 0x2510/0x2518 undefined writes. These objects
have distinct retained hashes and are controls, not substituted reproducers.

The `check_isa.py` regression is intentionally failing on the affected
compiler (exit 1). It requires the missing reaching definition and also checks
that the exact reproducer still exposes the reported eight staging writes and
16 affected descriptor loads. No passing-after compiler candidate exists in
this checkout, so claiming a fixed regression would be false.

LLVM print-before/print-after produced complete MachineIR dumps, including the
`# End machine code` marker, but this image's in-process Python codegen then
segfaulted while unwinding the temporary LLVM print option (exit 139). Normal
codegen and both controls exit 0. PR 497's retained post-greedy dump is
byte-identical in the key split region. This wrapper teardown issue does not
alter the complete dump, but it prevents this review from independently
claiming successful verifier exit status.

## Requirement for a valid fix

A valid compiler correction must preserve subrange liveness across the greedy
split: every lane later restored or used, specifically sub4/sub5 here, must be
defined in the split copy-in before the whole-register spill. It must make the
exact regression pass, produce a final ISA reaching definition for both
s60/s61 (the expected copy is sufficient), leave no undefined spill source,
and eliminate taint from all 16 descriptor loads. It must also preserve the
clean sibling and unrelated lanes. An ISA-text check, a startup smoke, or a
different spill destination does not establish those properties. The required
change is in the pinned LLVM AMDGPU greedy allocator/SplitKit behavior; no
FlyDSL C++ change was supported by this reproduction, so no native rebuild was
performed.

## Reproduction

```sh
gzip -dc reports/j-172115c2f76e/raw/18_reconcile_unrealized_casts.mlir.gz > /tmp/issue1087.mlir
/tmp/amdpilot-repo-j-172115c2f76e/venv/bin/python reports/j-172115c2f76e/reproduce.py /tmp/issue1087.mlir /tmp/issue1087.s --waves-per-eu 1
/tmp/amdpilot-repo-j-172115c2f76e/venv/bin/python reports/j-172115c2f76e/check_isa.py /tmp/issue1087.s
```

Raw input, generated ISA, both MachineIR dumps, control ISA/objects, stdout,
stderr, and exit codes are retained under `raw/`. Native source loaded from
`/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`; repository Python loaded
from `/job/repo/python/flydsl`.
