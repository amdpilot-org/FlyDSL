# gfx950 warp-sort validation

## Scope

- Added a minimal, stable warp-scope sorting primitive to `flydsl.extension.coop`.
- Validated distinct keys, ties, a 13-active/64-lane partial tail, and independent 32-lane groups on one AMD Instinct MI350X (`gfx950`).
- Compared every GPU result against an exact host ordering oracle; no scans, vote, exchange, or RNG were added or exercised.

## Evidence

- `baseline-first.json` records the installed-source baseline and the concrete AITER import blocker.
- `warp-sort-results.json` records the checkout-source GPU validation, exact expected/actual keys and payloads, sentinel bounds, and bounded elapsed times.
- The stable-tie contract is documented in `warp_sort`: ties preserve original lane order.

## Environment

- Image: `amdpilotv2/open-job:gbt350-20260909`
- Local image ID: `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`
- GPU: AMD Instinct MI350X, `gfx950`
- Python: `/opt/venv/bin/python`
- Installed FlyDSL: `/opt/venv/lib/python3.12/site-packages/flydsl`
- Installed native MLIR: `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir`
- Checkout sort source: `python/flydsl/extension/coop/warp/sort.py`

## Reproduction

The installed wheel is older than this checkout and cannot run the checkout’s full compiler pipeline. The validation harness therefore loads the checkout’s `warp/sort.py` into the installed qualified FlyDSL namespace and uses the installed ROCm/MLIR runtime. This preserves the qualified stack while exercising the checkout’s sort source on the real GPU.

```bash
export FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-d2e89e81f386/flydsl-runtime-cache
/opt/venv/bin/python /tmp/flydsl-cache-j-d2e89e81f386/validate_warp_sort.py
```

## Related context

- ROCm/FlyDSL issue 1016 proposes reusable `flydsl.extension` building blocks.
- Related changes already present in `main` include PR 907’s extension infrastructure and PR 1031’s cooperative reduce/scan work.
- Issue 1016 currently has no comments; no upstream issue, PR, or comment was modified.
