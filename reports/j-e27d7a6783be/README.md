# gfx950 SGPR spill-staging investigation

Source issue: https://github.com/ROCm/FlyDSL/issues/1087

Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/475

## Outcome

The exact attached `18_reconcile_unrealized_casts.mlir.gz` reproduces the
reported miscompile with the compiler embedded in this image. The decompressed
input SHA-256 is
`5ca5000c39324dcc4735024f587fa3c8d5b62b276acc8bd355ebab65a9f297ef`.
The generated ISA SHA-256 is
`1452f52355effa38e7018af519828f1902d6960c82493a410fc75684a5684cef`,
matching the issue.

The image compiler identifies itself as LLVM 24.0.0git at
`e2a39f504fee836e4def9581bed817ecc327b9dc`. This is recorded independently in
the repository's `thirdparty/llvm-build-info.json`, the installed
`llvm/Support/VCSRevision.h`, and the embedded library's version string. The
ROCm SDK clang is a different compiler (22.0.0git at
`7b800a19466229b8479a78de19143dc33c3ab9b5`) and was used only to inspect the
generated object.

## Compiler and ISA evidence

The compiler's post-greedy MachineIR shows the faulty live-range split directly:

```text
9828B  undef %8004.sub0_sub1_sub2_sub3:sgpr_512 = lr-split COPY ... {
          internal %8004.sub6_sub7:sgpr_512 = lr-split COPY ...
9836B  }
       SI_SPILL_S512_SAVE %8004:sgpr_512, %stack.3, ...

115896B %7901:sgpr_512 = SI_SPILL_S512_RESTORE %stack.3, ...
115992B undef %7900.sub8_..._sub15:sgpr_512 = lr-split COPY ... {
           internal %7900.sub4_sub5:sgpr_512 = lr-split COPY ...
116000B }
         %2659:sreg_32 = S_MUL_I32 ... %7900.sub5
116016B  %2661:sreg_32 = S_MUL_HI_U32 ... %7900.sub4
```

Thus the copy-in mask omits `sub4_sub5`, while the copy-out mask restores and
uses those lanes. `-verify-machineinstrs` and `-verify-regalloc` both accepted
this output. The complete dump is in `raw/greedy-mir.stderr`.

The final object has the reported resource counts and instruction addresses.
At `0x24d8`, `0x24dc`, and `0x24e0` it copies the first, second, and fourth i64
values, but there is no `s_mov_b64 s[60:61], s[80:81]`. Nevertheless, `s60` and
`s61` are written to `v254` lanes 4 and 5 at `0x2510` and `0x2518`. Their first
definitions are only at `0x3ce0` and `0x3ce8`, after the spill. The lanes are
reloaded at `0x3f68` and `0x3f70`. A CFG reaching-definition/taint analysis of
the generated HSACO finds 16 buffer accesses whose descriptor base derives from
the lost definition, beginning at `0x41ec`.

The unsafe kernel was not executed.

## Controls and mitigation assessment

- Omitting `--amdgpu-waves-per-eu` and setting it to 2 both produce the exact
  same failing ISA hash as the original setting of 1.
- `-amdgpu-spill-sgpr-to-vgpr=false` changes spill lowering to scratch, but the
  same staging copy remains absent. This demonstrates that spill storage choice
  is downstream of the lost definition and is not a safe mitigation.
- The issue attachment's affected and clean sibling HSACOs were run through the
  same reaching-definition predicate. The affected object has undefined
  writelane sources at `0x2510`/`0x2518`; the clean control has none.

No FlyDSL-side code mitigation was implemented. The self-contained input is
already pure LLVM/GPU/ROCDL immediately before `gpu-module-to-binary`, and all
tested FlyDSL-accessible codegen controls either preserve the failure exactly or
move the already-undefined value to a different spill mechanism. Adding an ISA
text heuristic to FlyDSL would be an incomplete compiler verifier, would require
an extra codegen pass for every kernel, and is not supported as a correctness
fix by the controls above.

The precise dependency is LLVM's greedy register allocator / SplitKit handling
of `sgpr_512` subranges. The pinned `SplitKit.cpp` contains the two relevant
paths introduced by LLVM commit `83dca924c250bc6bf2e1b1b930dcc0e2a2939009`:
`addDeadDef` skips child lane masks absent from the parent, and
`defFromParent` derives its copy lane mask from the parent interval. The same
code is present on LLVM main at the recorded read-only check
`25fe99bf939c50c7064e714a7edcbeb445bb9dc1`. The commit is a well-supported
suspect, not a proven root-cause attribution; validating an LLVM patch remains
outside this FlyDSL-only checkout and pinned rebuild contract.

## Reproduction

The commands and complete outputs are retained under `raw/`. The principal
commands used the required interpreter:

```sh
gzip -dc reports/j-e27d7a6783be/raw/18_reconcile_unrealized_casts.mlir.gz \
  > /tmp/18_reconcile_unrealized_casts.mlir
/tmp/amdpilot-repo-j-e27d7a6783be/venv/bin/python \
  reports/j-e27d7a6783be/reproduce.py \
  /tmp/18_reconcile_unrealized_casts.mlir /tmp/baseline-out.s

ROCM_PATH=/opt/rocm /tmp/amdpilot-repo-j-e27d7a6783be/venv/bin/python \
  <fatbin driver for the same MLIR>

/opt/rocm/llvm/bin/llvm-objdump -d --mcpu=gfx950 baseline.hsaco
```

The original attachment driver and analysis utilities were used from
`/job/artifacts-j-e27d7a6783be/tooling/llvm-lostcopy/`. The native compiler was
loaded from
`/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/libFlyPythonCAPI.so.24.0git`.
No FlyDSL C++ source changed, so a native rebuild was neither required nor
performed.
