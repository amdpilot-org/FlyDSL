# Intra-kernel profiling

FlyDSL exposes the AMDGPU global real-time counter as
`fx.rocdl.global_timer()` and the convenience store
`fx.rocdl.record_timestamp(buffer, index)`. Profiling is opt-in: kernels that do
not call either function generate no timer reads, stores, barriers, or extra
arguments.

The timestamp buffer is deliberately caller-owned. This lets a kernel choose
one sample per thread, wave, workgroup, or logical stage without imposing a
fixed record layout. The buffer element type must be `fx.Uint64`.

```python
if fx.thread_idx.x == 0:
    fx.rocdl.record_timestamp(timestamps, fx.block_idx.x * 2)

# stage being measured

fx.barrier()  # if this stage boundary requires workgroup synchronization
if fx.thread_idx.x == 0:
    fx.rocdl.record_timestamp(timestamps, fx.block_idx.x * 2 + 1)
```

Subtract the two unsigned 64-bit values to obtain elapsed timer ticks. A timer
read is not a barrier and does not wait for outstanding memory operations, so
the kernel must use the barrier or wait operation appropriate to the stage.

## Comparison scope

`global_timer()` lowers to `llvm.amdgcn.s.memrealtime`, which selects the
`s_memrealtime` hardware counter rather than the shader-engine-local
`s_memtime` counter. On one GPU, its common time domain permits comparisons
between workgroups, including workgroups scheduled on different XCDs. This is
useful for relative start/end ordering, imbalance, and tail measurements.

Readings from ordered launches on the same GPU remain in that device's common
time domain. The timer does not itself establish stream or launch ordering, and
different GPUs have no synchronized shared-epoch guarantee. Timer ticks are not
converted to nanoseconds because the applicable frequency is device-specific;
report ticks unless the frequency is obtained independently for the running
device.

Instrumentation has a cost: each sample adds one scalar timer instruction and
one global 64-bit store (plus any synchronization explicitly added by the
kernel). Measure an instrumented and uninstrumented specialization on the
target workload when overhead matters.
