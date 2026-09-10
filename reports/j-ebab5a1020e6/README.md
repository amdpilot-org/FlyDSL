# gfx950 A-MXFP6 investigation

## Result

The reported regression is already fixed on current `main`. Upstream issue 767 was
resolved by commit `927959cd98efada6eb6e4f19eb76bfed8a643246` (upstream issue/PR 780),
which restored MXFP6 operand-A support and `test_mfma_a6w4_preshuffle`. This report
validates that existing fix on one assigned MI350X (`gfx950`); it does not duplicate it.

The minimal real-input test uses `M=32, N=128, K=256` with tile `32x128x256`:

- A-MXFP6 E2M3 x B-MXFP4 E2M1, BF16 output: passes the unchanged numerical gate
  `torch.allclose(..., rtol=0.1, atol=0.1)`. Maximum absolute error was `0.125`
  and mean absolute error was `0.017217636108398438`.
- BF16 x BF16 control at the same shape: passes the same gate.
  Maximum absolute error was `0.1947784423828125` and mean absolute error was
  `0.018257617950439453`.
- Unsupported combinations are probed without substitution and their complete
  compile diagnostics are retained in `result.json`.

## Reproduction

From the repository root, using the image's `/opt/venv/bin/python`:

```bash
PYTHONPATH="$PWD" /opt/venv/bin/python reports/j-ebab5a1020e6/reproduce.py \
  --output /tmp/a6w4-result.json
```

The script asserts one visible `gfx950` GPU, preserves the real encoded operands and
E8M0 scales, dequantizes them independently for the reference, and records the
environment, source/native paths, numerical metrics, and unsupported tracebacks.
The exact captured execution is retained in `result.json`.

## Scope and limitations

- Tested only on the assigned AMD Instinct MI350X (`gfx950`); no other architecture
  was tested or inferred.
- Tested current `main` commit `ed70142704e1a6d5563fb53e1607e3a4b85d7111`, which
  contains the already-merged fix commit `927959cd98efada6eb6e4f19eb76bfed8a643246`.
- The image identity is the operator-qualified local image
  `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`.
  The runtime does not expose an independently checkable image-ID marker.
- The current mixed-precision atom table permits A FP4/FP6/FP8 and B FP4/FP8.
  B FP6 and BF16 operands are intentionally unsupported in this MX kernel.
