# Convolution performance gap investigation on MI350X/gfx950

## Executive summary

This investigation measures three small convolution shapes already covered by the repository's convolution tests, compares them with equivalent implicit-GEMM work, separates layout conversion, kernel dispatch, and cold compilation, and tests exactly six supported tile/pipeline candidates on the measured bottleneck.

The current no-`tile` path selects `(32, 32, 1, 2)` for all three shapes. On the measured 3D bottleneck, its kernel-only median time is `0.03502 ms` and its full NDHWC public-call median time is `0.05032 ms`. The best tested candidate, `(64, 64, 2, 2)` with `wgm=1`, reduces kernel-only median time to `0.03202 ms` (`1.09x`) and full NDHWC public-call median time to `0.04496 ms` (`1.12x`). All tested outputs pass the unchanged BF16 accuracy gate.

For these small shapes, the convolution kernel itself is already faster than the equivalent Torch `mm` estimate. The remaining public-call gap is dominated by layout conversion and per-call output allocation/dispatch overhead, not by the MFMA kernel. Cold compilation is also much larger than steady-state kernel time: `5.09 s` for the current tile and `5.69 s` for the winning candidate.

## Scope and upstream context

- Upstream issue: `ROCm/FlyDSL` issue 861, `[Issue]: Tune conv perf`.
- Issue state: open, with a comment stating it is resolved by `ROCm/FlyDSL` PR 820.
- PR 820 head: `cb5074880aecfab5a0f85078051829eb3935c900`; merged upstream.
- Mirror base tested: `ed70142704e1a6d5563fb53e1607e3a4b85d7111`.
- PR 820's tile parameterization and autotuner are already present in this mirror base. No already-working fix was duplicated or re-applied.
- This task concerns convolution compute efficiency. It does not retest the previous conv3d NDHWC chaining feature, run a full model, fetch model weights, or rebuild LLVM.
- No upstream issue, PR, or comment was posted or changed.

## Environment

| Item | Value |
|---|---|
| Qualified image | `sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7` |
| Image identity source | Operator-provided qualified local image ID |
| GPU | One assigned AMD Instinct MI350X, gfx950 |
| GPU UUID | `39633630-6435-3836-6166-613834643530` |
| GPU unique ID | `0x9c60d586afa84d50` |
| GPU serial | `692517020509` |
| Compute units | 256 |
| Python | `/opt/venv/bin/python3` |
| Torch | `2.9.1+rocm7.2.0.git7e1940d4`, `/opt/venv/lib/python3.12/site-packages/torch/__init__.py` |
| Triton | `3.5.1+rocm7.2.0.gita272dfa8`, `/opt/venv/lib/python3.12/site-packages/triton/__init__.py` |
| FlyDSL runtime | `0.2.4`, `/opt/venv/lib/python3.12/site-packages/flydsl/__init__.py` |
| Source convolution | `/job/FlyDSL/kernels/conv/conv3d_implicit.py` |
| Source autotuner | `/job/FlyDSL/kernels/conv/conv3d_autotune.py` |
| Native MLIR libraries | `/opt/venv/lib/python3.12/site-packages/flydsl/_mlir/_mlir_libs/` |

Job-private caches were kept outside the repository under `/tmp/flydsl-cache-j-7a07215034cb/`. The final cold run used the `runtime-cold-7`, `autotune-cold-7`, `triton-cold-7`, and `inductor-cold-7` subdirectories.

## Shapes and equivalent GEMM work

All shapes are existing test-derived shapes, not new model configurations:

1. `3d_autotune_test`: `(1, 128, 6, 40, 40)` input, `(128, 128, 3, 3, 3)` weight, stride 1, padding 1. Source: `test_conv3d_autotune`.
2. `3d_tile_test`: `(2, 64, 6, 18, 18)` input, `(192, 64, 3, 3, 3)` weight, stride 1, padding 1. Source: `test_conv3d_tile_configs`.
3. `2d_degenerate_test`: `(2, 64, 1, 24, 28)` input, `(128, 64, 1, 3, 3)` weight, stride 1, padding `(0, 1, 1)`. Source: `test_conv2d_vs_torch`.

The equivalent implicit-GEMM dimensions are:

| Shape | M | N | K | FLOPs |
|---|---:|---:|---:|---:|
| `3d_autotune_test` | 9600 | 128 | 3456 | 8,493,465,600 |
| `3d_tile_test` | 3888 | 192 | 1728 | 2,579,890,176 |
| `2d_degenerate_test` | 1344 | 128 | 576 | 198,180,864 |

The GEMM estimate is Torch `mm` on BF16 `(M, K) @ (K, N)` with a preallocated BF16 output. This is a work estimate, not a claim that the GEMM has the same memory-access pattern as implicit convolution.

## Accuracy

The unchanged existing convolution gate is:

```python
torch.allclose(actual, reference, rtol=2e-2, atol=2e-2)
```

Independent Torch references use `torch.nn.functional.conv3d` with the same stride, padding, and dilation. All full NCDHW and NDHWC public-call outputs pass this gate. The measured maximum absolute differences are:

| Shape | Max abs difference |
|---|---:|
| `3d_autotune_test` | 0.0 |
| `3d_tile_test` | 0.5 |
| `2d_degenerate_test` | 0.25 |

The NCDHW-to-NDHWC conversion output is exactly equal to the expected permuted contiguous tensor for all three shapes.

## Baseline results

All timing values below are median CUDA-event times over 100 repetitions after 10 warmups. Standard deviation is shown in parentheses.

| Shape | Current tile | Kernel only | Full NDHWC | Full NCDHW | Layout transpose | Full conversion | Torch GEMM | Torch conv |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `3d_autotune_test` | `(32,32,1,2)` | `0.03502 ms` (`0.00080`) | `0.05032 ms` (`0.00171`) | `0.06158 ms` (`0.00192`) | `0.00788 ms` (`0.00453`) | `0.00864 ms` (`0.00134`) | `0.03732 ms` (`0.00182`) | `0.10016 ms` (`0.00210`) |
| `3d_tile_test` | `(32,32,1,2)` | `0.01652 ms` (`0.00119`) | `0.03220 ms` (`0.00203`) | `0.04510 ms` (`0.00276`) | `0.00754 ms` (`0.00185`) | `0.00832 ms` (`0.00145`) | `0.02646 ms` (`0.00121`) | `0.10444 ms` (`0.00282`) |
| `2d_degenerate_test` | `(32,32,1,2)` | `0.00888 ms` (`0.00279`) | `0.02480 ms` (`0.00472`) | `0.03602 ms` (`0.00262`) | `0.00746 ms` (`0.00199`) | `0.00824 ms` (`0.00164`) | `0.01712 ms` (`0.00213`) | `0.04962 ms` (`0.00368`) |

Cold compilation was measured separately as wall time for FlyDSL executable compilation, not as warm CUDA-event dispatch:

| Shape | Explicit `(128,128,2,4)` | Current `(32,32,1,2)` | Transpose |
|---|---:|---:|---:|
| `3d_autotune_test` | `7.382 s` | `5.088 s` | `0.152 s` |
| `3d_tile_test` | `3.919 s` | `2.584 s` | `0.153 s` |
| `2d_degenerate_test` | `1.533 s` | `0.965 s` | `0.152 s` |

## Bottleneck and six-candidate sweep

The measured bottleneck is `3d_autotune_test`, selected by maximum kernel-only median time among the three baseline shapes. Exactly six supported tile/pipeline candidates were tested:

| Candidate | Tile | WGM | Cold compile | Kernel median | Stddev | TFLOPS | Accuracy |
|---:|---|---:|---:|---:|---:|---:|---|
| 0 | `(128,128,2,4)` | 1 | cached from baseline | `0.04912 ms` | `0.00066` | 172.9 | pass |
| 1 | `(128,128,2,4)` | 4 | `6.437 s` | `0.04960 ms` | `0.00090` | 171.8 | pass |
| 2 | `(128,128,2,4)` | 8 | `6.435 s` | `0.04968 ms` | `0.00103` | 171.7 | pass |
| 3 | `(64,128,1,4)` | 1 | `8.142 s` | `0.04050 ms` | `0.00062` | 207.8 | pass |
| 4 | `(64,64,2,2)` | 1 | `5.693 s` | `0.03202 ms` | `0.00257` | 267.4 | pass |
| 5 | `(256,128,2,4)` | 1 | `12.691 s` | `0.07904 ms` | `0.00111` | 107.5 | pass |

Candidate 0 reuses the baseline executable, so its compile is explicitly marked as cached rather than misreported as cold. No seventh candidate was tested.

The winner, candidate 4, has these full-call medians:

| Path | Current `(32,32,1,2)` | Winner `(64,64,2,2)` | Speedup |
|---|---:|---:|---:|
| Kernel only | `0.03502 ms` | `0.03202 ms` | `1.09x` |
| Full NDHWC | `0.05032 ms` | `0.04496 ms` | `1.12x` |
| Full NCDHW | `0.06158 ms` | `0.05830 ms` | `1.06x` |

## Findings

1. **Kernel-only convolution is not the main gap on these small shapes.** The current `(32,32,1,2)` kernel is faster than the equivalent Torch `mm` estimate for all three shapes. On the bottleneck, `0.03502 ms` convolution versus `0.03732 ms` GEMM is a `1.07x` kernel-only throughput advantage.
2. **Layout conversion is measurable but not dominant.** The transpose kernel is `0.00788 ms`, and the full conversion operation is `0.00864 ms`. The full NCDHW call is `0.01126 ms` slower than full NDHWC, so layout conversion accounts for roughly 18% of the full NCDHW call on the bottleneck.
3. **Public-call overhead is larger than layout conversion.** Full NDHWC (`0.05032 ms`) minus kernel-only (`0.03502 ms`) is `0.01530 ms`, reflecting output allocation and dispatch overhead. This is larger than the measured layout conversion.
4. **A smaller tile improves the measured bottleneck.** `(64,64,2,2)` improves kernel-only time by `8.6%` and full NDHWC time by `10.6%` relative to the current `(32,32,1,2)` path. The improvement is smaller than the explicit-default comparison because `_pick_tile` already selects a small tile for these shapes.
5. **Pipeline WGM changes do not help this shape.** WGM values 4 and 8 on `(128,128,2,4)` are slightly slower than WGM 1.
6. **Cold compilation dominates one-shot latency.** The current tile takes `5.09 s` to compile, while the winning candidate takes `5.69 s`. The worst tested candidate takes `12.69 s`. These costs are much larger than the sub-millisecond steady-state kernels.
7. **Shared-hardware variance is small but recorded.** Candidate standard deviations range from `0.00062 ms` to `0.00257 ms`. The GPU reported a low-power state during the run; before/after `rocm-smi` snapshots show 0% GPU use and 0% VRAM use outside the active measurement intervals. Full p10/p90/min/max values are retained in `results.json`.

## Runtime compatibility and limitations

The repository source is FlyDSL `0.3.3`, while the qualified image provides FlyDSL `0.2.4`. The benchmark uses two in-process compatibility shims, without replacing or rebuilding the qualified stack:

1. `s_waitcnt` named-counter encoding for gfx950.
2. `make_buffer_ptr` buffer-resource construction.

The source's automatic split-K path also requires `get_buffer_rsrc`, which is absent from the installed 0.2.4 native bindings. Therefore all measured convolution paths force `splitk=1`. The automatic `splitk=3` path was not measured and no performance claim is made for it.

The source gfx950 GEMM path is also incompatible with the installed 0.2.4 bindings because `cdna4.BufferLoadAsyncLDS128b` is absent. No FlyDSL GEMM kernel result is claimed; Torch `mm` is used only as the equivalent GEMM work estimate.

No LLVM rebuild, framework replacement, full-model run, model-weight download, or node-wide state change was performed.

## Reproduction

From the repository root:

```bash
export FLYDSL_RUNTIME_CACHE_DIR=/tmp/flydsl-cache-j-7a07215034cb/runtime-cold-7
export FLYDSL_AUTOTUNE_CACHE_DIR=/tmp/flydsl-cache-j-7a07215034cb/autotune-cold-7
export TRITON_CACHE_DIR=/tmp/flydsl-cache-j-7a07215034cb/triton-cold-7
export TORCHINDUCTOR_CACHE_DIR=/tmp/flydsl-cache-j-7a07215034cb/inductor-cold-7
mkdir -p "$FLYDSL_RUNTIME_CACHE_DIR" "$FLYDSL_AUTOTUNE_CACHE_DIR" "$TRITON_CACHE_DIR" "$TORCHINDUCTOR_CACHE_DIR"

/opt/venv/bin/python3 reports/j-7a07215034cb/bench_conv_gap.py \
  --output reports/j-7a07215034cb/results.json \
  --warmup 10 \
  --repetitions 100
```

The complete raw JSON, including environment paths, GPU snapshots, all timing statistics, cold compilation times, candidate results, and accuracy booleans, is retained in `reports/j-7a07215034cb/results.json`.
