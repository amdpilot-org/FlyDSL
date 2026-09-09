# Read-only upstream context

- ROCm/FlyDSL issue 1016 is open and titled `[Proposals Welcome] Grow flydsl.extension into a library of common GPU building blocks`.
- Its description proposes cooperative collectives, including warp and block reductions, as a candidate extension-library area. It had zero comments in the read-only API snapshot used for this investigation.
- The issue timeline cross-references ROCm/FlyDSL PR 1031, `[Ext][Coop] Add cooperative warp- and block-scope collectives`.
- PR 1031 is merged. Its GitHub-reported merge commit is `c3bd00455f711bd4f8d521951e0f5d9162437d8d`, with base `27dccebdefb8a54a8573b1c38eeb32a9e384e4eb` and head `2f36fb3ffea89cf660fb5619b3b6e67059efdd33`.
- The mirror `main` commit tested here, `ed70142704e1a6d5563fb53e1607e3a4b85d7111`, contains `c3bd00455f711bd4f8d521951e0f5d9162437d8d` and therefore already contains the block-wide sum implementation.
- No upstream issue, pull request, or comment was created, edited, or posted.
