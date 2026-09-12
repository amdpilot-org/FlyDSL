# Independent review of candidate PR 509

- Upstream issue: https://github.com/ROCm/FlyDSL/issues/621
- Mirror issue: https://github.com/amdpilot-org/FlyDSL/issues/529
- Prepared base: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`
- Candidate head: `262ac58265f711353c1afd7f1dd604206ebd0aac`
- Recommendation: **request changes (candidate fixes only a subset)**

## Finding

The candidate fixes the primary reproduced failure: the base accepts any pickle-valid object as an AOT cache hit, and turns corrupt cache bytes into a compile miss by deleting the file. At the exact candidate head, a versioned envelope is written, incompatible argument-derived cache keys are rejected, corrupt artifacts raise without entering the compile body, and a fresh process can execute a valid GPU artifact in run-only mode.

However, the candidate's claimed strict schema validation has adversarial boundary gaps:

1. `schema_version=True` is accepted as schema version `1`, because validation uses equality without enforcing the metadata type. A malformed envelope can therefore pass the version check.
2. `JitCacheManager.set()` adds `value` to `memory_cache` before validating or writing it. Passing a non-`CompiledArtifact` logs a failed disk write but leaves the invalid value as a successful in-process cache hit. This contradicts the new payload-type invariant at the cache-manager boundary.

These do not invalidate the successful normal compiled-artifact round trip, but they mean the proposed “schema” is not robust at all input boundaries. The original issue is broad and asks for more robust AOT/schema handling; therefore the evidence supports a subset fix rather than full acceptance. Require exact metadata types and validate before mutating the memory cache, with regressions for both cases.

## Base reproduction

Using `/tmp/amdpilot-repo-j-7c72979d9ca2/venv/bin/python` while the checkout was at the prepared base:

```text
python <independent JitCacheManager regression>
wrong_payload_accepted True dict
corrupt_becomes_compile_miss True file_removed True
```

The complete output is retained at `/job/review-evidence-j-7c72979d9ca2/base/independent-regression.txt`. The existing cache-key regression also passed: `python -m pytest -q tests/unit/test_jit_cache_key.py` -> 4 passed.

## Candidate validation

The candidate was fetched from `origin pull/509/head` and checked out detached at the exact requested SHA. Imports resolved to the candidate checkout:

```text
flydsl /job/repo/python/flydsl/__init__.py
jit_function /job/repo/python/flydsl/compiler/jit_function.py
ir /job/repo/python/flydsl/_mlir/ir.py
```

Commands and results:

```text
/tmp/amdpilot-repo-j-7c72979d9ca2/venv/bin/python -m pytest -q \
  tests/unit/test_aot_cache_schema.py tests/unit/test_jit_cache_key.py
# 9 passed

/tmp/amdpilot-repo-j-7c72979d9ca2/venv/bin/python -m pytest -q \
  tests/unit/test_jit_cache_key_completeness.py tests/unit/test_compile_hints.py \
  tests/unit/test_aot_cache_schema.py
# 35 passed, 2 skipped
```

Independent adversarial checks produced:

```text
mismatched_key_rejected RuntimeError ... cache_key metadata does not match ...
boolean_schema_accepted True
invalid_set_memory_hit {'invalid': 'payload'} disk_exists False
```

A separate corrupt-cache `compile_lock` check raised `RuntimeError` and preserved the invalid file without entering the compile body.

## GPU and compiler evidence

On the assigned `AMD Instinct MI355X` (ROCm `7.2.26015-fc0010cf6`), `examples/01-vectorAdd.py` was run first with `FLYDSL_RUNTIME_ENABLE_CACHE=1`, then in a distinct process with `FLYDSL_RUNTIME_RUN_ONLY=1` and the same private cache. Both exited 0 and printed `PASS`, which is based on `torch.allclose(A + B, C)`.

Independent inspection of the 31,838-byte pickle found a schema envelope containing a `CompiledArtifact`; its 14,687-byte MLIR text contains `gpu.binary`, `rocdl.target`, `amdgpu`, and `gfx950`. This verifies actual compiled GPU artifact creation and run-only reuse. No tolerance was changed.

The candidate changes Python only, so the prepared native rebuild command was not applicable. The imported Python modules came from `/job/repo`; the checked-in `_mlir` Python facade was used with the image's pinned native compiler. No other architecture was tested. Raw outputs and the private GPU cache remain under `/job/review-evidence-j-7c72979d9ca2/`.
