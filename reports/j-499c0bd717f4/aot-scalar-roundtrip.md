# AOT runtime-scalar round-trip evidence

Pinned revision: `acf7e67b7d22847e345938ca54fcc137bd7b2a1f`

Environment receipt interpreter: `/tmp/amdpilot-repo-j-499c0bd717f4/venv/bin/python`

GPU: `AMD Instinct MI350X` (`gfx950` in the prepared smoke receipt)

## Finding

No scalar round-trip defect reproduced at the pinned revision. FlyDSL's AOT
interface in this checkout is its disk cache: `COMPILE_ONLY=1` exports a
serialized `CompiledArtifact`, and `FLYDSL_RUNTIME_RUN_ONLY=1` reloads it without
allowing JIT fallback. Runtime `fx.Int32` values share a cache schema, so one
export successfully handled both `-7` and `11` in a fresh process.

The cache API embeds the generated native GPU binary in the pickle; it does not
emit a separate native file. The retained artifact is:

`/job/evidence-j-499c0bd717f4/aot-cache/_scalar_launch_822d07ac109274e74fcf90c7e9eb3f8b/62c098b994374b46.pkl`

## Commands

Caches unrelated to the AOT artifact were redirected below
`/tmp/flydsl-j-499c0bd717f4-cache` for every command.

```text
FLYDSL_RUNTIME_CACHE_DIR=/job/evidence-j-499c0bd717f4/aot-cache COMPILE_ONLY=1 /tmp/amdpilot-repo-j-499c0bd717f4/venv/bin/python tests/system/test_aot_scalar_roundtrip.py --worker export /job/evidence-j-499c0bd717f4/aot-cache

FLYDSL_RUNTIME_CACHE_DIR=/job/evidence-j-499c0bd717f4/aot-cache FLYDSL_RUNTIME_RUN_ONLY=1 /tmp/amdpilot-repo-j-499c0bd717f4/venv/bin/python tests/system/test_aot_scalar_roundtrip.py --worker reload /job/evidence-j-499c0bd717f4/aot-cache

/tmp/amdpilot-repo-j-499c0bd717f4/venv/bin/python -m pytest -s -q tests/system/test_aot_scalar_roundtrip.py
```

## Raw result

```text
mode=export
gpu=AMD Instinct MI350X
cache_root=/job/evidence-j-499c0bd717f4/aot-cache
artifact=/job/evidence-j-499c0bd717f4/aot-cache/_scalar_launch_822d07ac109274e74fcf90c7e9eb3f8b/62c098b994374b46.pkl
native_artifact=embedded in serialized CompiledArtifact
mode=reload
gpu=AMD Instinct MI350X
cache_root=/job/evidence-j-499c0bd717f4/aot-cache
scalar=-7 actual=52 torch_reference=52 comparison=exact
scalar=11 actual=124 torch_reference=124 comparison=exact
invalid_schema=torch.float32 rejection=FLYDSL_RUNTIME_RUN_ONLY=1 but no usable AOT cache for _scalar_launch: ... cache_dir=/job/evidence-j-499c0bd717f4/aot-cache/_scalar_launch_822d07ac109274e74fcf90c7e9eb3f8b (exists=True)
```

The reference is independently evaluated on the GPU with Torch tensor
operations (`square().add(3)`), not by reusing the kernel's output or host-side
expected constants. The schema rejection changes the output tensor from
`torch.int32` to `torch.float32`; run-only mode rejects it because no artifact
with that argument schema was exported.

Complete raw logs and the serialized/native artifact remain under
`/job/evidence-j-499c0bd717f4/`.
