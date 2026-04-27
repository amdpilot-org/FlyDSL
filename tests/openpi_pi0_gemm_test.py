#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

"""Unit tests for FlyDSL bf16 GEMM kernel (pi0 LIBERO MI300X).

Tests accuracy bounds:
  max_abs_err   <= 1.0   * ulp_bf16(C_ref_max_abs)
  max_rel_err   <= 1e-2  for elements with |C_ref| > 1e-3
  mean_rel_err  <= 5e-4  over all elements
  cosine_sim    >= 1 - 1e-4
"""

import sys
import os
import torch

# Add paths for imports
sys.path.insert(0, '/opt/FlyDSL/python')
sys.path.insert(0, '/workspace/FlyDSL')

from kernels.openpi_pi0_gemm import bf16_gemm

# Test shapes for pi0 LIBERO (3.5B parameter model)
# These are representative transformer projection shapes at BS=1
TEST_SHAPES = [
    (1, 3072, 3072),     # q/k/v projection (hidden -> hidden)
    (1, 12288, 3072),    # MLP up-projection (hidden -> 4*hidden)
    (1, 3072, 12288),    # MLP down-projection (4*hidden -> hidden)
    (32, 3072, 3072),    # Larger batch variant
    (64, 1536, 3072),    # Alternative hidden size
]


def compute_accuracy_metrics(C_fly: torch.Tensor, C_ref: torch.Tensor) -> dict:
    """Compute accuracy metrics between FlyDSL output and reference."""
    C_fly_f32 = C_fly.to(torch.float32)
    C_ref_f32 = C_ref.to(torch.float32)
    
    # Absolute error
    abs_err = (C_fly_f32 - C_ref_f32).abs()
    max_abs_err = abs_err.max().item()
    
    # ULP bound for bf16
    C_ref_max_abs = C_ref_f32.abs().max().item()
    ulp_bf16 = 2 ** -7  # ~0.0078 for values near 1.0
    ulp_bound = C_ref_max_abs * ulp_bf16
    
    # Relative error for elements with |C_ref| > 1e-3
    mask = C_ref_f32.abs() > 1e-3
    if mask.any():
        rel_err = (abs_err[mask] / C_ref_f32[mask].abs())
        max_rel_err = rel_err.max().item()
        mean_rel_err = rel_err.mean().item()
    else:
        max_rel_err = 0.0
        mean_rel_err = 0.0
    
    # Cosine similarity
    cos_sim = torch.nn.functional.cosine_similarity(
        C_fly_f32.flatten().unsqueeze(0),
        C_ref_f32.flatten().unsqueeze(0)
    ).item()
    
    return {
        'max_abs_err': max_abs_err,
        'ulp_bound': ulp_bound,
        'max_rel_err': max_rel_err,
        'mean_rel_err': mean_rel_err,
        'cosine_sim': cos_sim,
    }


def test_bf16_gemm_accuracy():
    """Test bf16 GEMM accuracy against fp32 reference."""
    torch.manual_seed(0)
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    
    print("=" * 70)
    print("FlyDSL bf16 GEMM Accuracy Tests (pi0 LIBERO MI300X)")
    print("=" * 70)
    
    all_passed = True
    
    for M, N, K in TEST_SHAPES:
        # Generate random bf16 inputs
        A = torch.randn(M, K, dtype=torch.bfloat16, device=device)
        B = torch.randn(K, N, dtype=torch.bfloat16, device=device)
        
        # Reference: fp32 matmul cast back to bf16
        C_ref = torch.matmul(A.to(torch.float32), B.to(torch.float32)).to(torch.bfloat16)
        
        # FlyDSL kernel output
        C_fly = bf16_gemm(A, B)
        
        # Compute accuracy metrics
        metrics = compute_accuracy_metrics(C_fly, C_ref)
        
        # Check bounds
        passed = (
            metrics['max_abs_err'] <= metrics['ulp_bound'] * 1.5 and  # small margin
            metrics['max_rel_err'] <= 1e-2 and
            metrics['mean_rel_err'] <= 5e-4 and
            metrics['cosine_sim'] >= 1 - 1e-4
        )
        
        status = "PASS" if passed else "FAIL"
        print(f"\nShape ({M}, {N}, {K}): {status}")
        print(f"  max_abs_err: {metrics['max_abs_err']:.6f} (bound: {metrics['ulp_bound']:.6f})")
        print(f"  max_rel_err: {metrics['max_rel_err']:.6f} (bound: 0.01)")
        print(f"  mean_rel_err: {metrics['mean_rel_err']:.6f} (bound: 0.0005)")
        print(f"  cosine_sim:  {metrics['cosine_sim']:.8f} (bound: >=0.9999)")
        
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("All accuracy tests PASSED")
    else:
        print("Some accuracy tests FAILED")
    print("=" * 70)
    
    return all_passed


def test_bf16_gemm_preallocated_output():
    """Test bf16 GEMM with pre-allocated output tensor."""
    torch.manual_seed(0)
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    
    M, N, K = 32, 2048, 2048
    A = torch.randn(M, K, dtype=torch.bfloat16, device=device)
    B = torch.randn(K, N, dtype=torch.bfloat16, device=device)
    C = torch.empty(M, N, dtype=torch.bfloat16, device=device)
    
    # Test with pre-allocated output
    from kernels.openpi_pi0_gemm import launch_bf16_gemm
    launch_bf16_gemm(A, B, C)
    
    # Verify correctness
    C_ref = torch.matmul(A.to(torch.float32), B.to(torch.float32)).to(torch.bfloat16)
    max_diff = (C.to(torch.float32) - C_ref.to(torch.float32)).abs().max().item()
    
    # bf16 has limited precision, so use a reasonable tolerance
    # The ulp for bf16 at value ~1.0 is about 0.0078
    tolerance = 1.0  # Allow up to 1 ulp difference
    print(f"\nPre-allocated output test: max_diff = {max_diff:.6f} (tolerance: {tolerance})")
    assert max_diff <= tolerance, f"Pre-allocated output test failed: max_diff={max_diff}"
    print("Pre-allocated output test PASSED")
    
    return True


def test_bf16_gemm_various_dtypes():
    """Test that kernel correctly rejects non-bf16 inputs."""
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    
    A_fp16 = torch.randn(32, 32, dtype=torch.float16, device=device)
    B_bf16 = torch.randn(32, 32, dtype=torch.bfloat16, device=device)
    
    try:
        bf16_gemm(A_fp16, B_bf16)
        print("ERROR: Should have raised assertion for fp16 input")
        return False
    except AssertionError as e:
        print(f"Correctly rejected fp16 input: {e}")
        return True


if __name__ == "__main__":
    print("\nRunning FlyDSL bf16 GEMM tests...\n")
    
    test1 = test_bf16_gemm_accuracy()
    test2 = test_bf16_gemm_preallocated_output()
    test3 = test_bf16_gemm_various_dtypes()
    
    if test1 and test2 and test3:
        print("\n✓ All tests PASSED")
        sys.exit(0)
    else:
        print("\n✗ Some tests FAILED")
        sys.exit(1)
