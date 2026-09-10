# Backend autodetection runtime slice

## Scope

This report records a bounded runtime investigation for ROCm/FlyDSL issue 813. It does **not** claim an SDK-free wheel build, a replacement for the qualified ROCm stack, or validation of CUDA/NVVM.

## Environment

- Image: `amdpilotv2/open-job:gbt350-20260909`
- Local image ID: `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7`
- GPU: one assigned AMD Instinct MI350X, `gfx950`
- Python: `/opt/venv/bin/python3`
- FlyDSL source: `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py`
- FlyDSL version: `0.2.4`
- Torch: `2.9.1+rocm7.2.0.git7e1940d4`
- Triton: `3.5.1+rocm7.2.0.gita272dfa8`

## Runtime resolution

The installed FlyDSL runtime probes these HIP sonames with `ctypes.CDLL`:

1. `libamdhip64.so`
2. `libamdhip64.so.6`
3. `libamdhip64.so.5`

On this image, the first successful probe resolves to:

```text
/opt/rocm-7.2.0/lib/libamdhip64.so.7.2.70200
```

The active compile backend is `RocmBackend`, the runtime kind is `rocm`, and the detected target architecture is `gfx950`.

## GPU smoke test

A fresh Python process ran a 100 x 1000 float32 vector-add kernel on the assigned MI350X. The FlyDSL result was compared with the equivalent Torch operation.

- `torch.equal(expected, C)`: `true`
- Maximum absolute difference: `0.0`

## Backend override diagnostics

Only process-local environment overrides were used. No node libraries or global state were modified.

### Missing compile backend

Command:

```bash
FLYDSL_COMPILE_BACKEND=missing FLYDSL_RUNTIME_KIND=rocm \
  /opt/venv/bin/python3 -c 'import flydsl; from flydsl.runtime.device_runtime import get_device_runtime; get_device_runtime()'
```

Diagnostic:

```text
ValueError: No device-runtime kind mapped for compile backend 'missing'. Register a mapping with register_compile_runtime_mapping().
```

### Invalid runtime kind

Command:

```bash
FLYDSL_COMPILE_BACKEND=rocm FLYDSL_RUNTIME_KIND=invalid \
  /opt/venv/bin/python3 -c 'import flydsl; from flydsl.runtime.device_runtime import get_device_runtime; get_device_runtime()'
```

Diagnostic:

```text
RuntimeError: Compile backend 'rocm' requires device runtime kind 'rocm', but FLYDSL_RUNTIME_KIND (and registration) resolve to 'invalid'. Align FLYDSL_COMPILE_BACKEND with FLYDSL_RUNTIME_KIND (and extension mappings), or use a matching pair of register_backend / register_device_runtime.
```

## Observed issue

`RocmDeviceRuntime.device_count()` returned `2` on this single-GPU node. `rocm_agent_enumerator -name` reports both:

```text
gfx950:sramecc+:xnack-
gfx9-4-generic:sramecc+:xnack-
```

The current implementation counts every `gfx*` name other than `gfx000`, so it also counts the generic fallback agent. This does not affect the valid kernel run or backend selection, but it is a real autodetection inaccuracy.

## Upstream context

- ROCm/FlyDSL issue 813 is open and has no comments.
- The issue timeline cross-references PR 829, which is an unrelated profiling helper draft.
- PR 595 is merged and added `current_device_id()` through HIP `hipGetDevice`; it is already present in the tested runtime.
- No upstream PR that directly implements issue 813 was found.

## Untested packaging step

No wheel build, `auditwheel repair`, or SDK-free packaging path was exercised. The qualified ROCm stack was preserved and used as installed.
