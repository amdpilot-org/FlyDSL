import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import time

import torch
import torch.nn.functional as F

from kernels.conv.conv3d_implicit import conv3d_implicit


DEVICE = torch.device("cuda:0")
ROOT = Path(__file__).resolve().parents[2]
SOURCE = str(ROOT / "kernels/conv/conv3d_implicit.py")
FINITE_VALUES = (-1.0, -0.5, 0.0, 0.5, 1.0)
RTOL = 2.0e-2
ATOL = 2.0e-2
SENTINEL_BOUND = 32.0


def finite_tensor(shape, seed):
    generator = torch.Generator(device="cpu").manual_seed(seed)
    values = torch.tensor(FINITE_VALUES, dtype=torch.float32)
    flat = values[
        torch.randint(0, len(values), (torch.Size(shape).numel(),), generator=generator)
    ]
    return flat.reshape(shape).to(device=DEVICE, dtype=torch.bfloat16)


def reference_ndhwc(x_cl, weight, bias, stride, padding, groups=1):
    x_ncdhw = x_cl.permute(0, 4, 1, 2, 3).float().cpu()
    weight_cpu = weight.float().cpu()
    bias_cpu = None if bias is None else bias.float().cpu()
    y_ncdhw = F.conv3d(
        x_ncdhw,
        weight_cpu,
        bias=bias_cpu,
        stride=stride,
        padding=padding,
        groups=groups,
    )
    return y_ncdhw.permute(0, 2, 3, 4, 1).contiguous()


def call_conv(x_cl, weight, bias, splitk, layout="NDHWC", out_layout="NDHWC"):
    torch.cuda.synchronize(DEVICE)
    started = time.perf_counter()
    kwargs = {
        "groups": weight.shape[0] if weight.shape[1] == 1 else 1,
        "splitk": splitk,
    }
    if os.environ.get("CONV3D_USE_ALIAS", "1") == "1":
        kwargs["layout"] = layout
        kwargs["out_layout"] = out_layout
    else:
        kwargs["input_layout"] = layout
        kwargs["output_layout"] = out_layout
    actual = conv3d_implicit(
        x_cl,
        weight,
        bias=bias,
        stride=1,
        padding=1 if weight.shape[-1] == 3 else 0,
        **kwargs,
    )
    torch.cuda.synchronize(DEVICE)
    return actual, time.perf_counter() - started


def compare(name, actual, expected, elapsed, splitk):
    actual_float = actual.float().cpu()
    difference = (actual_float - expected).abs()
    return {
        "case": name,
        "splitk": splitk,
        "max_abs_error": float(difference.max().item()),
        "mean_abs_error": float(difference.mean().item()),
        "finite": bool(torch.isfinite(actual_float).all().item()),
        "within_sentinel_bound": bool(actual_float.abs().max().item() <= SENTINEL_BOUND),
        "elapsed_s": elapsed,
        "passed": bool(
            torch.allclose(actual_float, expected, rtol=RTOL, atol=ATOL)
            and torch.isfinite(actual_float).all().item()
            and actual_float.abs().max().item() <= SENTINEL_BOUND
        ),
    }


def main():
    torch.cuda.set_device(DEVICE)
    results = []
    first_elapsed = None

    def record(name, x_cl, weight, bias, splitk):
        nonlocal first_elapsed
        actual, elapsed = call_conv(x_cl, weight, bias, splitk)
        if first_elapsed is None:
            first_elapsed = elapsed
        expected = reference_ndhwc(
            x_cl,
            weight,
            bias,
            stride=1,
            padding=1 if weight.shape[-1] == 3 else 0,
            groups=weight.shape[0] // weight.shape[1] if weight.shape[1] == 1 else 1,
        )
        result = compare(name, actual, expected, elapsed, splitk)
        results.append(result)
        return actual

    n, c, d, h, w, k = 2, 3, 2, 3, 4, 4
    weight = finite_tensor((k, c, 3, 3, 3), seed=101)
    bias = torch.tensor(
        [0.25, -0.25, 0.5, -0.5], device=DEVICE, dtype=torch.float32
    )

    for splitk in (1, 2):
        x_a = finite_tensor((n, d, h, w, c), seed=201 + splitk)
        x_b = finite_tensor((n, d, h, w, c), seed=301 + splitk)
        output_a = record(f"superposition-a-splitk-{splitk}", x_a, weight, bias, splitk)
        output_b = record(f"superposition-b-splitk-{splitk}", x_b, weight, bias, splitk)
        x_sum = x_a + x_b
        output_sum = record(
            f"superposition-sum-splitk-{splitk}", x_sum, weight, bias, splitk
        )
        bias_ndhwc = bias.to(torch.bfloat16).float().cpu().reshape(1, 1, 1, 1, k)
        residual = (output_sum.float().cpu() - bias_ndhwc) - (
            (output_a.float().cpu() - bias_ndhwc)
            + (output_b.float().cpu() - bias_ndhwc)
        )
        results.append(
            {
                "case": f"superposition-bias-subtracted-splitk-{splitk}",
                "splitk": splitk,
                "max_abs_error": float(residual.abs().max().item()),
                "mean_abs_error": float(residual.abs().mean().item()),
                "finite": bool(torch.isfinite(residual).all().item()),
                "within_sentinel_bound": bool(
                    residual.abs().max().item() <= ATOL
                ),
                "elapsed_s": None,
                "passed": bool(
                    torch.isfinite(residual).all().item()
                    and residual.abs().max().item() <= ATOL
                ),
            }
        )

    impulse_c = 4
    impulse_weight = torch.zeros(
        (impulse_c, 1, 3, 3, 3), device=DEVICE, dtype=torch.bfloat16
    )
    for channel in range(impulse_c):
        impulse_weight[channel, 0, channel % 3, (channel + 1) % 3, (channel + 2) % 3] = (
            0.5 if channel % 2 == 0 else -0.25
        )
    impulse_bias = torch.tensor(
        [0.25, -0.25, 0.5, -0.5], device=DEVICE, dtype=torch.float32
    )
    for splitk in (1, 2):
        for channel in range(impulse_c):
            x_impulse = torch.zeros(
                (1, 3, 3, 3, impulse_c), device=DEVICE, dtype=torch.bfloat16
            )
            x_impulse[0, 1, 1, 1, channel] = 1.0
            actual = record(
                f"impulse-channel-{channel}-splitk-{splitk}",
                x_impulse,
                impulse_weight,
                impulse_bias,
                splitk,
            )
            expected = reference_ndhwc(
                x_impulse,
                impulse_weight,
                impulse_bias,
                stride=1,
                padding=1,
                groups=impulse_c,
            )
            actual_float = actual.float().cpu()
            target_error = (
                actual_float[0, 1, 1, 1, channel] - expected[0, 1, 1, 1, channel]
            ).abs()
            other = [index for index in range(impulse_c) if index != channel]
            other_bias = impulse_bias.to(torch.bfloat16).float().cpu()[other]
            other_error = (
                actual_float[..., other] - other_bias
            ).abs()
            results[-1]["target_channel_error"] = float(target_error.item())
            results[-1]["other_channel_bias_error"] = float(other_error.max().item())

    sentinel_weight = torch.full(
        (2, 2, 1, 1, 1), 0.5, device=DEVICE, dtype=torch.bfloat16
    )
    sentinel_bias = torch.tensor(
        [0.25, -0.25], device=DEVICE, dtype=torch.float32
    )
    x_sentinel = torch.full(
        (1, 2, 2, 2, 2), -7.0, device=DEVICE, dtype=torch.bfloat16
    )
    record("sentinel-finite-bound", x_sentinel, sentinel_weight, sentinel_bias, 1)

    source_commit = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()
    report = {
        "label": "GPU controls for channels-last conv3d; alias mode tests PR 315, legacy mode tests current main",
        "api_mode": "layout/out_layout" if os.environ.get("CONV3D_USE_ALIAS", "1") == "1" else "input_layout/output_layout",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "campaign": "repo-e2e-20260909",
        "candidate_commit": source_commit,
        "gpu": {
            "name": torch.cuda.get_device_name(DEVICE),
            "capability": list(torch.cuda.get_device_capability(DEVICE)),
            "count": torch.cuda.device_count(),
        },
        "image": {
            "qualified_name": "amdpilotv2/open-job:gbt350-20260909",
            "local_image_id": "sha256:bd1e01173a8f79133863f0f9a482eebfbf6abc1cfca34909fcaf487ee63c74e7",
            "container_id": open("/proc/1/cgroup").read().strip().split("/")[-1],
        },
        "interpreter": "/opt/venv/bin/python",
        "versions": {
            "torch": importlib.metadata.version("torch"),
            "triton": importlib.metadata.version("triton"),
            "flydsl": importlib.metadata.version("flydsl"),
        },
        "paths": {
            "source": SOURCE,
            "flydsl_python": "/tmp/flydsl-cache-j-cefb12089b1a/wheel-0.3.2/flydsl/__init__.py",
            "flydsl_native": "/tmp/flydsl-cache-j-cefb12089b1a/wheel-0.3.2/flydsl/_mlir/_mlir_libs/libfly_jit_runtime.so",
            "flydsl_rocdl_native": "/tmp/flydsl-cache-j-cefb12089b1a/wheel-0.3.2/flydsl/_mlir/_mlir_libs/_mlirDialectsFlyROCDL.cpython-312-x86_64-linux-gnu.so",
            "torch_native": "/opt/venv/lib/python3.12/site-packages/torch/lib/libtorch_cuda.so",
        },
        "commands": [
            "PYTHONPATH=/tmp/flydsl-cache-j-cefb12089b1a/wheel-0.3.2:/job/FlyDSL /opt/venv/bin/python /tmp/conv3d_controls.py",
            "PYTHONPATH=/tmp/flydsl-cache-j-cefb12089b1a/wheel-0.3.2:/job/FlyDSL /opt/venv/bin/python -m pytest -q tests/kernels/test_conv3d_implicit.py --disable-warnings",
        ],
        "reference": "independent CPU float32 torch.nn.functional.conv3d cross-correlation; bias subtracted once on each superposition side",
        "timing_method": "time.perf_counter around one FlyDSL call with torch.cuda.synchronize before and after; first call includes JIT compilation",
        "first_gpu_execution_elapsed_s": first_elapsed,
        "finite_matrix": {
            "values": list(FINITE_VALUES),
            "superposition_shape": [n, d, h, w, c],
            "output_channels": k,
            "impulse_channels": impulse_c,
            "splitk": [1, 2],
            "rtol": RTOL,
            "atol": ATOL,
            "sentinel_bound": SENTINEL_BOUND,
        },
        "results": results,
        "passed": all(result["passed"] for result in results),
    }
    output_path = (
        str(Path(__file__).with_name("conv3d-controls-results-alias.json"))
        if os.environ.get("CONV3D_USE_ALIAS", "1") == "1"
        else str(Path(__file__).with_name("conv3d-controls-results-legacy.json"))
    )
    with open(output_path, "w", encoding="utf-8") as output:
        json.dump(report, output, indent=2, sort_keys=True)
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "cases": len(results),
                "first_gpu_execution_elapsed_s": first_elapsed,
            }
        )
    )


if __name__ == "__main__":
    main()
