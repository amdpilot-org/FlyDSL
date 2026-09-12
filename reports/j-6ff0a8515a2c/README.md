# Device printf buffering correction

Candidate https://github.com/amdpilot-org/FlyDSL/pull/571 at
`c10ac5fdbcec87f83041a33bd75ee31fff9b63ff` was checked against independent
review https://github.com/amdpilot-org/FlyDSL/pull/610.

The review counterexample reproduced: a libc `printf` before importing FlyDSL
left all four later device lines buffered at `READY` despite
`torch.cuda.synchronize()`. They appeared only after the child exited. The
candidate's line-buffered `setvbuf` configuration was therefore replaced by
unbuffered stdout configuration, which passed the same live-child timing check.

Raw before/after and test outputs are in `raw/`; structured claims and commands
are in `result.json`.
