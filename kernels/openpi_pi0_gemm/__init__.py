# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

"""OpenPI PI0 LIBERO bf16 GEMM kernel (FlyDSL).

Target shape: M=11, N=1024, K=2048, bf16.
Layout: A row-major (M,K), B stored row-major (N,K) used as logical transposed (K,N).
Computes C = A @ B.T.
"""

from .pi0_gemm import build_pi0_gemm_module, pi0_gemm_dispatch

__all__ = ["build_pi0_gemm_module", "pi0_gemm_dispatch"]
