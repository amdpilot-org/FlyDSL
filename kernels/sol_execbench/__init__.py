# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

"""SOL-ExecBench problem ports.

Each module ports one SOL-ExecBench (``amdpilot-org/SOL-ExecBench``) problem to
an AMD-native GPU kernel.  Where the FlyDSL MLIR toolchain is unavailable in the
execution container, the port delivers the equivalent optimization as a Triton
fused kernel + ROCm ``aten`` GEMM, captured in a CUDA graph to collapse launch
overhead (the same launch-overhead-reduction lever a FlyDSL kernel would get
from a single fused launch).
"""
