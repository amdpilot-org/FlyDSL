# Independent review of PR 558

Candidate: `d99a42f9f4a3fc755d9053ace0954f985f37e44b`

Recommendation: **request changes**.

The candidate is test-only/documentation hardening on top of a `BlockScan`
implementation already present at the prepared base. Its new multi-block test
is relevant and passes on the assigned gfx950 GPU, as do the full cooperative
suite and real stream-compaction example. It does not establish a
failing-before/passing-after implementation fix: the same base implementation
already passed 62 focused GPU tests and the example.

## Blocking finding

The primary example in `docs/extension/coop_scan.md` calls `inclusive` and then
`exclusive` using the same `storage` without an intervening `fx.barrier()`.
That conflicts with both the implementation's documented contract and the
candidate's own later instruction: shared storage must not be reused for a
second collective until all threads have completed the last reads from the
first collective. The example should either show one form at a time, allocate
separate storage, or insert the barrier.

An independent kernel copied this reuse pattern and compared both outputs to
host `torch.cumsum` references for 8 blocks of 256 threads over 100 launches.
It happened to pass on gfx950 both with and without the barrier, which shows
only that the race did not manifest on this architecture/run; it does not make
the unsupported synchronization pattern valid. Raw code and output are in
`raw/adversarial_reuse.py` and `raw/adversarial-reuse-output.txt`.

## Scope assessment

- The scoped block-wide prefix-scan building block is implemented on the base,
  with explicit inclusive/exclusive APIs, independent numerical coverage, and
  a real GPU example.
- This candidate adds useful multi-block/wave-boundary regression coverage and
  public documentation, but changes no implementation or native source.
- It does not and should not claim the whole common-building-block proposal is
  complete. Therefore it does not fully resolve the broad original issue.
- Only gfx950 was available. Wave32 and other AMD architectures remain
  unverified.
- No native rebuild was run because the candidate changes no C++ or native
  compiler source. Python imports resolved from `/job/repo/python/flydsl`; the
  prepared native MLIR libraries remained under
  `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs`.

The candidate PR body also names mirror issue 543 rather than the assigned
mirror issue 583. This does not affect scan correctness, but its provenance
should be corrected.
