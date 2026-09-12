#!/usr/bin/env python3
"""Run a hinted vector-add kernel and report numerical/compiler evidence."""

import re

import torch

import flydsl.compiler as flyc
import flydsl.expr as fx


@flyc.kernel
def _vector_add_kernel(a: fx.Pointer, b: fx.Pointer, out: fx.Pointer, n: fx.Int32):
    index = fx.block_idx.x * fx.block_dim.x + fx.thread_idx.x
    if index < n:
        out[index] = a[index] + b[index]


@flyc.jit
def _vector_add(a: fx.Pointer, b: fx.Pointer, out: fx.Pointer, n: fx.Int32, stream: fx.Stream = fx.Stream(None)):
    block = 256
    _vector_add_kernel(a, b, out, n).launch(
        grid=((n + block - 1) // block, 1, 1),
        block=(block, 1, 1),
        stream=stream,
    )


def main():
    torch.manual_seed(1054)
    size = 4099
    a = torch.randn(size, device="cuda", dtype=torch.float32)
    b = torch.randn(size, device="cuda", dtype=torch.float32)
    out = torch.empty_like(a)
    reference = a.cpu() + b.cpu()
    stream = torch.cuda.Stream()

    hinted = flyc.compile[{"fast_fp_math": True, "unsafe_fp_math": True}](_vector_add)
    hinted(
        flyc.from_c_void_p(fx.Float32, a.data_ptr()),
        flyc.from_c_void_p(fx.Float32, b.data_ptr()),
        flyc.from_c_void_p(fx.Float32, out.data_ptr()),
        size,
        stream,
    )
    torch.cuda.synchronize()

    ir_text = _vector_add._last_compiled[1]._ir_text
    targets = re.findall(r"#gpu\.object<(#rocdl\.target<[^>]*>)", ir_text)
    max_abs_error = (out.cpu() - reference).abs().max().item()
    print(f"device={torch.cuda.get_device_name(0)}")
    print(f"gpu_arch={torch.cuda.get_device_properties(0).gcnArchName}")
    print(f"gpu_objects={len(targets)}")
    print(f"selected_target={targets[0] if len(targets) == 1 else '<ambiguous>'}")
    print(f"max_abs_error={max_abs_error:.9g}")
    assert len(targets) == 1
    assert "fast" in targets[0]
    assert "unsafe_math" in targets[0]
    torch.testing.assert_close(out.cpu(), reference, rtol=0, atol=0)


if __name__ == "__main__":
    main()
