import torch

import flydsl.compiler as flyc
import flydsl.expr as fx


@flyc.kernel
def sum_kernel(A: fx.Tensor, B: fx.Tensor, tileM: fx.Constexpr[int], tileN: fx.Constexpr[int]):
    bx = fx.block_idx.x
    by = fx.block_idx.y
    tid = fx.thread_idx.x

    A = A[None, bx, by]
    tv_tilemn = (32, 64)
    tv_layout = fx.make_layout(((8, 32), 8), ((256, 1), 32))

    load_atom = fx.make_copy_atom(fx.UniversalCopy128b(), fx.Float32)
    store_atom = fx.make_copy_atom(fx.UniversalAtomicAdd(fx.Float32), fx.Float32)
    tiled_load = fx.make_tiled_copy(load_atom, tv_layout, tv_tilemn)
    tiled_store = fx.make_tiled_copy(store_atom, tv_layout, tv_tilemn)

    broadcasted_B = fx.composition(B, fx.make_layout((tileM, tileN), (0, 0)))
    part_A = tiled_load.get_slice(tid).partition_S(A)
    part_B = tiled_store.get_slice(tid).partition_D(broadcasted_B)

    load_fragment = fx.make_fragment_like(part_A)
    fx.copy(load_atom, part_A, load_fragment)
    store_fragment = tiled_store.get_slice(tid).retile(load_fragment)

    for bm in fx.range_constexpr(tileM // tv_tilemn[0]):
        for bn in fx.range_constexpr(tileN // tv_tilemn[1]):
            fx.copy(store_atom, store_fragment[None, bm, bn], part_B[None, bm, bn])


@flyc.jit
def universal_copy_atomic_sum(
    A: fx.Tensor,
    B: fx.Tensor,
    tileM: fx.Constexpr[int],
    tileN: fx.Constexpr[int],
    stream: fx.Stream = fx.Stream(None),
):
    A = fx.tiled_divide(A, (tileM, tileN))
    grid_x = fx.get_scalar(A.shape[1])
    grid_y = fx.get_scalar(A.shape[2])
    sum_kernel(A, B, tileM, tileN).launch(
        grid=(grid_x, grid_y, 1),
        block=(256, 1, 1),
        stream=stream,
    )


torch.manual_seed(0)
A = torch.randn((64, 64), device="cuda", dtype=torch.float32)
B = torch.zeros(1, device="cuda", dtype=torch.float32)
universal_copy_atomic_sum(A, B, 64, 64, stream=torch.cuda.Stream())
torch.cuda.synchronize()

expected = A.sum()
actual = B.item()
absolute_error = (B - expected).abs().item()
relative_error = absolute_error / expected.abs().item()
print(f"expected={expected.item():.9g}")
print(f"actual={actual:.9g}")
print(f"absolute_error={absolute_error:.9g}")
print(f"relative_error={relative_error:.9g}")
assert relative_error < 1e-5
