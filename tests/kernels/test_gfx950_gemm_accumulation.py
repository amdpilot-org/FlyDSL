#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors.

"""gfx950 split-K GEMM accumulation semantics."""

import os
import sys

import pytest

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    import torch
except ImportError:
    torch = None

pytestmark = [pytest.mark.l2_device, pytest.mark.rocm_lower]

if torch is None or not torch.cuda.is_available():
    pytest.skip("CUDA/ROCm not available", allow_module_level=True)

from flydsl.runtime.device import get_rocm_arch  # noqa: E402
from kernels.gemm.gemm_a16w16_gfx950 import gemm_a16w16  # noqa: E402

_ARCH = str(get_rocm_arch() or "")
if _ARCH != "gfx950":
    pytest.skip(
        f"GFX950 split-K accumulation tests require gfx950, got {_ARCH}",
        allow_module_level=True,
    )


def test_gemm_a16w16_two_part_k_fp32_accumulation():
    torch.manual_seed(821)
    m, n, k = 64, 128, 2048
    input_sentinel = -13.0
    output_sentinel = 123.0
    pad = 8

    a_storage = torch.full(
        (m + 2, k + 2 * pad), input_sentinel, dtype=torch.bfloat16, device="cuda"
    )
    b_storage = torch.full(
        (n + 2, k + 2 * pad), input_sentinel, dtype=torch.bfloat16, device="cuda"
    )
    a_storage[1 : m + 1, pad : k + pad].uniform_(-1, 1)
    b_storage[1 : n + 1, pad : k + pad].uniform_(-1, 1)
    a = a_storage[1 : m + 1, pad : k + pad]
    b = b_storage[1 : n + 1, pad : k + pad].t()

    out_storage = torch.full(
        (16 + m * n + 16,), output_sentinel, dtype=torch.float32, device="cuda"
    )
    out = out_storage[16 : 16 + m * n].view(m, n)
    out.zero_()

    assert torch.isfinite(a.float()).all()
    assert torch.isfinite(b.float()).all()
    assert a.data_ptr() % 16 == 0
    assert b.data_ptr() % 16 == 0

    kwargs = {
        "block_m": 32,
        "block_n": 64,
        "block_k": 128,
        "stages": 4,
        "m_waves": 1,
        "n_waves": 2,
        "k_waves": 2,
        "group_m": 0,
        "use_half_tile_interleaved": False,
        "split_k": 2,
    }
    gemm_a16w16(
        a,
        b,
        out=out,
        bias=None,
        user_kwargs=kwargs,
        layout="nt",
        out_dtype=torch.float32,
    )
    torch.cuda.synchronize()

    reference = a.float().cpu() @ b.float().cpu()
    max_abs_delta = (out.cpu() - reference).abs().max().item()
    assert torch.isfinite(out).all()
    torch.testing.assert_close(
        out.cpu(),
        reference,
        atol=1e-1,
        rtol=2e-1,
        check_dtype=True,
    )
    torch.testing.assert_close(
        a_storage[0].float(),
        torch.full_like(a_storage[0].float(), input_sentinel),
    )
    torch.testing.assert_close(
        a_storage[-1].float(),
        torch.full_like(a_storage[-1].float(), input_sentinel),
    )
    torch.testing.assert_close(
        a_storage[1 : m + 1, :pad].float(),
        torch.full_like(a_storage[1 : m + 1, :pad].float(), input_sentinel),
    )
    torch.testing.assert_close(
        a_storage[1 : m + 1, k + pad :].float(),
        torch.full_like(a_storage[1 : m + 1, k + pad :].float(), input_sentinel),
    )
    torch.testing.assert_close(
        b_storage[0].float(),
        torch.full_like(b_storage[0].float(), input_sentinel),
    )
    torch.testing.assert_close(
        b_storage[-1].float(),
        torch.full_like(b_storage[-1].float(), input_sentinel),
    )
    torch.testing.assert_close(
        b_storage[1 : n + 1, :pad].float(),
        torch.full_like(b_storage[1 : n + 1, :pad].float(), input_sentinel),
    )
    torch.testing.assert_close(
        b_storage[1 : n + 1, k + pad :].float(),
        torch.full_like(b_storage[1 : n + 1, k + pad :].float(), input_sentinel),
    )
    torch.testing.assert_close(
        out_storage[:16],
        torch.full_like(out_storage[:16], output_sentinel),
    )
    torch.testing.assert_close(
        out_storage[16 + m * n :],
        torch.full_like(out_storage[16 + m * n :], output_sentinel),
    )
    print(f"max_abs_delta={max_abs_delta:.9g}", flush=True)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
