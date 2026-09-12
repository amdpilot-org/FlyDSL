# Cooperative prefix scans

`flydsl.extension.coop` provides reusable warp- and block-scope prefix scans.
This is one cooperative building block; it does not attempt to provide a
complete library of GPU collectives.

For a block-wide scan, specialize `fx.coop.BlockScan` with the element type and
the kernel's block size, allocate its shared storage, and choose an explicit
inclusive or exclusive form:

```python
block_scan = fx.coop.BlockScan[fx.Int32, fx.known_block_size()]
storage = fx.SharedAllocator().allocate(block_scan.SharedStorage).peek()

inclusive = block_scan.inclusive(value, fx.ReductionOp.ADD, storage=storage)
fx.barrier()
exclusive = block_scan.exclusive(value, fx.ReductionOp.ADD, storage=storage)
```

The inclusive result for thread `t` folds values from thread 0 through `t`.
The exclusive result folds values strictly before `t`; thread 0 receives the
operation's identity. Passing `init=` places that value before the block's
sequence. Each block scans independently, and threads are ordered by their
linear `(x, y, z)` thread id.

A `Vector` value represents consecutive items owned by one thread. For a
vector of length `n`, thread `t` owns sequence positions `t * n` through
`t * n + n - 1`.

The operation must be an associative `fx.ReductionOp`. The current public
operations are `ADD`, `MUL`, `MIN`, and `MAX`. Every thread in the block must
participate together, and the specialized block size must match the launch.
The current block implementation requires a power-of-two thread count and uses
the `WARP_SCANS` policy; the enum's raking policies are not implemented.

Use `inclusive_with_aggregate` or `exclusive_with_aggregate` when every thread
also needs the fold of all input values. The aggregate excludes `init`. Insert
an `fx.barrier()` before reusing the same shared storage for another collective.

See `examples/extension/coop/02-block_scan.py` for a GPU stream-compaction
example whose output positions come from an exclusive scan.
