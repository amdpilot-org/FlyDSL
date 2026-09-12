# Correction report

Candidate: https://github.com/amdpilot-org/FlyDSL/pull/558  
Independent review: https://github.com/amdpilot-org/FlyDSL/pull/593  
Candidate commit: `d99a42f9f4a3fc755d9053ace0954f985f37e44b`

The review's concrete documentation counterexample reproduced: the candidate's
main snippet called `BlockScan.inclusive` and then `BlockScan.exclusive` with the
same shared storage but no intervening `fx.barrier()`. A static regression over
the exact snippet failed before the correction and passes after adding the
required barrier.

The candidate's valid work was preserved. Its 64 focused BlockScan GPU tests
passed before correction; after correction all 326 cooperative extension tests
and the GPU stream-compaction example passed on the assigned gfx950 device.

The candidate PR body points to mirror issue 543. This delivery instead uses
the assigned mirror issue 604. The contribution remains explicitly limited to
block-wide prefix scan and does not claim to complete the original broad
common-building-block proposal.
