#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

"""Guard large ``scf.if`` accumulator phis against VGPR-range divergence.

Problem
-------
When a large accumulator (N x f32x4 = 4N VGPRs) flows through an ``scf.IfOp``
phi, LLVM's register allocator makes independent allocation choices per branch.
With 32 x f32x4 = 128 VGPRs crossing phi, the two branches may assign disjoint
VGPR ranges, effectively doubling register consumption at the merge point.  The
allocator must insert copies to coalesce them, and under pressure this causes
scratch spills.

This was the historically catastrophic issue in the MLA decode kernel:
  - oaccu (32 x f32x4 = 128 VGPRs) flowed through phi across 6 branch instances
  - LLVM produced 71 unique MFMA destination register groups
  - 170 scratch spills (vgpr_spill_count = 170)
  - Fix: restructure so oaccu never enters phi nodes -- keep it branch-local

This test yields NUM_ACCU_VECS x f32x4 through ``scf.IfOp`` phi.  Each branch
performs structurally different computation (different chain lengths and
intermediate ops) so LLVM cannot merge them via v_cndmask pointer selection.
The predicate depends on the runtime block id; using ``warp_id == 0`` with a
single wave made the else branch unreachable and invalidated the experiment.

How to inspect
--------------
::

    FLYDSL_DUMP_IR=1 python tests/kernels/test_ssa_phi_divergence.py
    grep 'v_mfma' ~/.flydsl/debug/ssa_phi_accu_kernel_0/17_final_isa.s
    grep 'vgpr_spill_count' ~/.flydsl/debug/ssa_phi_accu_kernel_0/17_final_isa.s
"""

import os
from pathlib import Path

import pytest

pytestmark = [pytest.mark.l2_device, pytest.mark.rocm_lower]

try:
    import torch
except ImportError:
    torch = None
if torch is None or not torch.cuda.is_available():
    pytest.skip("CUDA/ROCm not available.", allow_module_level=True)

import flydsl.compiler as flyc
import flydsl.expr as fx
from flydsl.expr import arith, range_constexpr
from flydsl.expr.arith import ArithValue
from flydsl.expr.typing import T
from flydsl.expr.typing import Float16, Float32, full
from kernels.common import buffer_ops

from flydsl._mlir import ir
from flydsl._mlir.dialects import scf
from flydsl._mlir.dialects import arith as _std_arith
from flydsl._mlir.dialects import vector as _vd

from flydsl.runtime.device import get_rocm_arch

BLOCK_THREADS = 64

# Number of f32x4 vectors yielded through phi.
NUM_ACCU_VECS = 32


def _raw(v):
    """Unwrap to ir.Value."""
    if hasattr(v, "ir_value"):
        return v.ir_value()
    if hasattr(v, "result"):
        return v.result
    return v


def _i32_const(val):
    """Create an i32 constant in the current insertion point."""
    return _std_arith.ConstantOp(T.i32, val).result


def build_ssa_phi_accu(N: int):
    """Build a kernel where a large accumulator crosses scf.IfOp phi.

    Each branch does structurally different computation:
      - Branch A: load from A, chain 3 MFMAs per accumulator
      - Branch B: load from B, chain 2 MFMAs + MulFOp per accumulator
    This prevents LLVM from merging branches via v_cndmask pointer selection.
    """

    @flyc.kernel
    def ssa_phi_accu_kernel(
        A: fx.Tensor,
        B: fx.Tensor,
        C: fx.Tensor,
    ):
        bid = fx.block_idx.x
        tid = fx.thread_idx.x

        f32x4_type = T.f32x4

        rsrc_a = buffer_ops.create_buffer_resource(A)
        rsrc_b = buffer_ops.create_buffer_resource(B)
        rsrc_c = buffer_ops.create_buffer_resource(C)

        tid_i32 = _raw(ArithValue(tid))
        bid_i32 = _raw(ArithValue(bid))
        row_elem_offset = _std_arith.MulIOp(bid_i32, _i32_const(N)).result
        tid_elem_offset = _std_arith.MulIOp(tid_i32, _i32_const(4)).result
        base_elem_offset = _std_arith.AddIOp(row_elem_offset, tid_elem_offset).result

        b_frag = _raw(full(4, Float16(1.0), Float16))
        c_zero = _raw(full(4, Float32(0.0), Float32))

        # Scale factor for branch B's MulFOp (different from 1.0 to prevent DCE)
        scale_vec = _raw(full(4, Float32(0.5), Float32))

        block_parity = _std_arith.RemUIOp(bid_i32, _i32_const(2)).result
        is_even_block = _std_arith.CmpIOp(
            _std_arith.CmpIPredicate.eq,
            block_parity,
            _i32_const(0),
        ).result

        result_types = [f32x4_type] * NUM_ACCU_VECS
        if_op = scf.IfOp(is_even_block, result_types, has_else=True)

        # Branch A (even blocks): load from A, 3-MFMA chain per accumulator
        with ir.InsertionPoint(if_op.regions[0].blocks[0]):
            yields_a = []
            for vec_idx in range_constexpr(NUM_ACCU_VECS):
                elem_off = _std_arith.AddIOp(
                    base_elem_offset,
                    _i32_const(vec_idx * BLOCK_THREADS * 4),
                ).result
                a_frag = buffer_ops.buffer_load(
                    rsrc_a, elem_off, vec_width=4, dtype=T.f16
                )
                # 3-MFMA chain (structurally different from branch B)
                accu = _raw(fx.rocdl.mfma_f32_16x16x16f16(
                    f32x4_type, [a_frag, b_frag, c_zero, 0, 0, 0]
                ))
                accu = _raw(fx.rocdl.mfma_f32_16x16x16f16(
                    f32x4_type, [a_frag, b_frag, accu, 0, 0, 0]
                ))
                accu = _raw(fx.rocdl.mfma_f32_16x16x16f16(
                    f32x4_type, [a_frag, b_frag, accu, 0, 0, 0]
                ))
                yields_a.append(accu)
            scf.YieldOp(yields_a)

        # Branch B (odd blocks): load from B, 2-MFMA + MulF per accumulator
        with ir.InsertionPoint(if_op.regions[1].blocks[0]):
            yields_b = []
            for vec_idx in range_constexpr(NUM_ACCU_VECS):
                elem_off = _std_arith.AddIOp(
                    base_elem_offset,
                    _i32_const(vec_idx * BLOCK_THREADS * 4),
                ).result
                a_frag = buffer_ops.buffer_load(
                    rsrc_b, elem_off, vec_width=4, dtype=T.f16
                )
                # 2-MFMA + MulF chain (structurally different from branch A)
                accu = _raw(fx.rocdl.mfma_f32_16x16x16f16(
                    f32x4_type, [a_frag, b_frag, c_zero, 0, 0, 0]
                ))
                accu = _raw(fx.rocdl.mfma_f32_16x16x16f16(
                    f32x4_type, [a_frag, b_frag, accu, 0, 0, 0]
                ))
                # Multiply by scale (this extra op makes the DAG different)
                accu = _std_arith.MulFOp(accu, scale_vec).result
                yields_b.append(accu)
            scf.YieldOp(yields_b)

        # After merge: all NUM_ACCU_VECS f32x4 values came through phi.
        merged = [if_op.results[i] for i in range(NUM_ACCU_VECS)]

        # Sum all f32x4 to one (prevents DCE)
        total = merged[0]
        for i in range_constexpr(1, NUM_ACCU_VECS):
            total = _std_arith.AddFOp(total, merged[i]).result

        # Store to C
        for elem in range_constexpr(4):
            val = _vd.extract(total, [], [elem])
            store_idx = _std_arith.AddIOp(
                _std_arith.AddIOp(row_elem_offset, tid_elem_offset).result,
                _i32_const(elem),
            ).result
            buffer_ops.buffer_store(val, rsrc_c, store_idx)

    @flyc.jit
    def launch_ssa_phi_accu(
        A: fx.Tensor,
        B: fx.Tensor,
        C: fx.Tensor,
        m_in: fx.Int32,
        stream: fx.Stream = fx.Stream(None),
    ):
        idx_m = ArithValue(m_in).index_cast(T.index)
        launcher = ssa_phi_accu_kernel(A, B, C)
        launcher.launch(
            grid=(idx_m, 1, 1),
            block=(BLOCK_THREADS, 1, 1),
            stream=stream,
        )

    return launch_ssa_phi_accu


def _parse_isa_stats(isa_path):
    """Parse the ISA file for MFMA destinations and spill count."""
    stats = {
        "vgpr_spill_count": 0,
        "vgpr_count": 0,
        "total_mfma_count": 0,
        "unique_mfma_dsts": set(),
    }

    try:
        with open(isa_path, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return None

    for line in lines:
        stripped = line.strip()

        if "v_mfma" in stripped:
            stats["total_mfma_count"] += 1
            parts = stripped.split()
            if len(parts) > 1 and parts[1].startswith("v["):
                stats["unique_mfma_dsts"].add(parts[1].rstrip(","))

        if "vgpr_spill_count" in stripped:
            try:
                val = stripped.split(":")[-1].strip()
                stats["vgpr_spill_count"] = int(val)
            except ValueError:
                pass
        if ".vgpr_count" in stripped:
            try:
                val = stripped.split(":")[-1].strip()
                stats["vgpr_count"] = int(val)
            except ValueError:
                pass

    return stats


def test_ssa_phi_accu_explosion():
    """Compile and run the SSA phi accumulator explosion demo."""
    M = 4
    N = NUM_ACCU_VECS * BLOCK_THREADS * 4

    print(f"\n{'='*70}")
    print(f"SSA Phi Accumulator Explosion Demo")
    print(f"  M={M}, N={N}, BLOCK_THREADS={BLOCK_THREADS}")
    print(f"  NUM_ACCU_VECS={NUM_ACCU_VECS} ({NUM_ACCU_VECS * 4} VGPRs through phi)")
    compile_only = os.environ.get("COMPILE_ONLY", "").lower() in ("1", "true")
    target_arch = os.environ.get("ARCH") or str(get_rocm_arch())
    print(f"  execution_arch={get_rocm_arch()}")
    print(f"  target_arch={target_arch}")
    print(f"{'='*70}")

    launch_fn = build_ssa_phi_accu(N)

    a_dev = torch.ones((M, N), device="cuda", dtype=torch.float16)
    b_dev = torch.ones((M, N), device="cuda", dtype=torch.float16)
    c_dev = torch.zeros((M, N), device="cuda", dtype=torch.float32)
    stream = torch.cuda.current_stream()

    launch_fn(a_dev, b_dev, c_dev, M, stream=stream)
    if not compile_only:
        torch.cuda.synchronize()

        # Independent analytical reference for all-one MFMA operands.  Each
        # 16x16x16 MFMA contributes 16; even blocks execute three MFMAs per
        # accumulator, while odd blocks execute two and multiply by 0.5.
        expected = torch.zeros_like(c_dev)
        expected[0::2, : BLOCK_THREADS * 4] = NUM_ACCU_VECS * 3 * 16
        expected[1::2, : BLOCK_THREADS * 4] = NUM_ACCU_VECS * 2 * 16 * 0.5
        torch.testing.assert_close(c_dev, expected, rtol=0, atol=0)
        print("  Numerical reference: exact match")

    dump_root = Path(os.environ.get("FLYDSL_DUMP_DIR", "~/.flydsl/debug")).expanduser()
    isa_files = sorted((dump_root / "ssa_phi_accu_kernel_0").glob("*_final_isa.s"))
    isa_path = str(isa_files[-1]) if isa_files else ""
    stats = _parse_isa_stats(isa_path)

    if stats:
        print(f"\n  ISA analysis ({isa_path}):")
        print(f"    Total MFMA instructions: {stats['total_mfma_count']}")
        print(f"    Unique MFMA dst groups: {len(stats['unique_mfma_dsts'])}")
        print(f"    VGPR count: {stats['vgpr_count']}")
        print(f"    VGPR spill count: {stats['vgpr_spill_count']}")

        assert stats["total_mfma_count"] == 160, "both structural branches must survive codegen"
        assert len(stats["unique_mfma_dsts"]) <= 40
        assert stats["vgpr_spill_count"] == 0
    else:
        print(f"\n  ISA file not found at {isa_path}")
        print(f"  Run with FLYDSL_DUMP_IR=1 to generate ISA output")

    # Count phi nodes in LLVM IR
    llvm_files = sorted((dump_root / "ssa_phi_accu_kernel_0").glob("*_llvm_ir.ll"))
    llvm_ir_path = str(llvm_files[-1]) if llvm_files else ""
    try:
        with open(llvm_ir_path) as f:
            ir_text = f.read()
        phi_f32x4 = ir_text.count("phi <4 x float>")
        phi_total = ir_text.count(" phi ")
        print(f"\n  LLVM IR phi nodes: {phi_total} total, {phi_f32x4} x <4 x float>")
        assert phi_f32x4 == NUM_ACCU_VECS
    except FileNotFoundError:
        pass

    print("\n  PASSED (large cross-branch phi remained bounded and spill-free)")
if __name__ == "__main__":
    if "FLYDSL_DUMP_IR" not in os.environ:
        os.environ["FLYDSL_DUMP_IR"] = "1"

    test_ssa_phi_accu_explosion()
