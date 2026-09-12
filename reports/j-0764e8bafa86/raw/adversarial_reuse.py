import sys

sys.path.insert(0, "/job/repo/tests/extension/coop")

import torch

import flydsl.compiler as flyc
import flydsl.expr as fx


BLOCK = 256
GRID = 8


def make_launch(with_barrier):
    @flyc.kernel(known_block_size=[BLOCK, 1, 1])
    def kernel(A: fx.Tensor, Inclusive: fx.Tensor, Exclusive: fx.Tensor):
        scan = fx.coop.BlockScan[fx.Int32, BLOCK]
        storage = fx.SharedAllocator().allocate(scan.SharedStorage).peek()
        index = fx.block_idx.x * BLOCK + fx.thread_idx.x
        Inclusive[index] = scan.inclusive(A[index], fx.ReductionOp.ADD, storage=storage)
        if with_barrier:
            fx.barrier()
        Exclusive[index] = scan.exclusive(A[index], fx.ReductionOp.ADD, storage=storage)

    @flyc.jit
    def launch(A: fx.Tensor, Inclusive: fx.Tensor, Exclusive: fx.Tensor, stream: fx.Stream = fx.Stream(None)):
        kernel(A, Inclusive, Exclusive).launch(grid=(GRID, 1, 1), block=(BLOCK, 1, 1), stream=stream)

    return launch


values = torch.arange(1, GRID * BLOCK + 1, dtype=torch.int32, device="cuda")
host = values.cpu().reshape(GRID, BLOCK)
expected_inclusive = host.cumsum(1).flatten()
expected_exclusive = torch.cat(
    [torch.zeros((GRID, 1), dtype=torch.int32), host.cumsum(1)[:, :-1]], dim=1
).flatten()

for with_barrier in (False, True):
    launch = make_launch(with_barrier)
    failures = 0
    first = None
    for iteration in range(100):
        inc_out = torch.empty_like(values)
        exc_out = torch.empty_like(values)
        launch(values, inc_out, exc_out, stream=torch.cuda.Stream())
        torch.cuda.synchronize()
        ok_inc = torch.equal(inc_out.cpu(), expected_inclusive)
        ok_exc = torch.equal(exc_out.cpu(), expected_exclusive)
        if not (ok_inc and ok_exc):
            failures += 1
            if first is None:
                first = (iteration, ok_inc, ok_exc)
    print({"with_barrier": with_barrier, "failures": failures, "first_failure": first})
