# Correction review for PR 562

Candidate: https://github.com/amdpilot-org/FlyDSL/pull/562  
Independent review: https://github.com/amdpilot-org/FlyDSL/pull/595

The review counterexamples reproduce at candidate commit
`5fad5553f7f542c723c492379e5c4e7a9f80736a`. The executable added by the
candidate fails while importing AITER because the prepared AITER checkout
requires Triton 3.6 or newer and the pinned interpreter provides Triton
`3.5.1+rocm7.2.0.gita272dfa8`. The interpreter contains neither `sglang` nor
`vllm`, and the candidate neither imports those packages nor registers its new
file in a workflow.

No candidate source was retained. The prepared base already contains the real
downstream workflows added by commit `38dad805f923728545c687d2c05304d7ebadc4ec`:
they clone SGLang and execute selected SGLang tests, and they execute vLLM's
latency CLI with the FlyDSL and AITER wheels under test. Adding an unregistered
AITER-only HGEMM executable would not improve those boundaries.

Recent public upstream run metadata was also inspected. The latest vLLM run
failed in `Checkout upstream aiter repo`, before a downstream test, while the
latest completed SGLang run failed in `Prepare SGLang workspace`. Full job logs
were unavailable (the public logs endpoint returned HTTP 403), and the prepared
environment lacks both downstream packages and their models. Those failures are
therefore recorded as limitations rather than used to justify a speculative
workflow change.

Raw command output is retained outside the checkout at
`/job/evidence-j-e35453afe93b/`. The relevant prepared paths were:

- Python: `/tmp/amdpilot-repo-j-e35453afe93b/venv/bin/python`
- FlyDSL Python source: `/job/repo/python/flydsl`
- FlyDSL native bindings: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`
- AITER source: `/opt/aiter/aiter`

There is no failing-before/passing-after regression because no executable
downstream boundary can be reached in the pinned environment and no concrete
FlyDSL defect was established. The exact failing-before output is preserved in
`raw/candidate-direct.log`.
