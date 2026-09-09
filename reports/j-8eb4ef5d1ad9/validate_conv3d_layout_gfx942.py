#!/usr/bin/env python3
"""Run a small two-layer conv3d layout check on the assigned GPU."""

import argparse

import torch
import torch.nn.functional as F

from flydsl.runtime.device import get_rocm_arch
from kernels.conv.conv3d_implicit import conv3d_implicit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("default", "channels_last"), required=True)
    args = parser.parse_args()

    torch.manual_seed(993)
    device = "cuda"
    dtype = torch.bfloat16
    rtol = atol = 2e-2

    print("torch", torch.__version__, "hip", torch.version.hip)
    print("device", torch.cuda.get_device_name(0), "capability", torch.cuda.get_device_capability(0))
    print("flydsl_runtime_arch", get_rocm_arch())

    n, c, d, h, w, k = 1, 32, 4, 8, 8, 64
    x = torch.randn((n, c, d, h, w), device=device, dtype=dtype) * 0.1
    x_cl = x.permute(0, 2, 3, 4, 1).contiguous()
    weight_1 = torch.randn((k, c, 3, 3, 3), device=device, dtype=dtype) * 0.1
    weight_2 = torch.randn((k, k, 3, 3, 3), device=device, dtype=dtype) * 0.1
    bias = torch.randn((k,), device=device, dtype=torch.float32) * 0.1
    stride = (1, 2, 1)
    padding = (1, 0, 1)

    if args.mode == "default":
        source, layout, out_layout = x, "NCDHW", None
    else:
        source, layout, out_layout = x_cl, "NDHWC", "NDHWC"

    print("mode", args.mode, flush=True)
    y = conv3d_implicit(
        source,
        weight_1,
        bias=bias,
        stride=stride,
        padding=padding,
        layout=layout,
        out_layout=out_layout,
    )
    y = conv3d_implicit(
        y,
        weight_2,
        bias=bias,
        stride=stride,
        padding=padding,
        layout=layout,
        out_layout=out_layout,
    )
    torch.cuda.synchronize()

    reference = F.conv3d(x, weight_1, bias=bias.to(dtype), stride=stride, padding=padding)
    reference = F.conv3d(reference, weight_2, bias=bias.to(dtype), stride=stride, padding=padding)
    if out_layout == "NDHWC":
        reference = reference.permute(0, 2, 3, 4, 1).contiguous()

    max_abs = (y.float() - reference.float()).abs().max().item()
    passed = torch.allclose(y, reference, rtol=rtol, atol=atol)
    print("shape", tuple(y.shape), "reference_shape", tuple(reference.shape))
    print("max_abs", max_abs, "allclose", passed)
    assert y.shape == reference.shape
    assert passed


if __name__ == "__main__":
    main()
