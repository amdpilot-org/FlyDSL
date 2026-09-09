#!/usr/bin/env python3
"""Validate logical Uint32/Uint8 signedness across FlyDSL JIT/kernel boundaries."""

from __future__ import annotations

import argparse
import json
import sys

import torch

import flydsl
import flydsl.compiler as flyc
import flydsl.expr as fx


UINT32_BITS = [0, 1, 0x7FFFFFFF, 0x80000000, 0xC0000000, 0xFFFFFFFE, 0xFFFFFFFF, 0x80000007]
UINT8_BITS = [0x00, 0x01, 0x7F, 0x80, 0xC0, 0xFE, 0xFF, 0x87]
BOUNDARY_LABELS: list[str] = []


@flyc.kernel
def pointer_shift_kernel(src: fx.Pointer, dst: fx.Pointer, n: fx.Int32):
    BOUNDARY_LABELS.append(str(src.element_type))
    tid = fx.thread_idx.x
    if tid < n:
        dst[tid] = (src[tid] >> 4).to(fx.Int32)


@flyc.jit
def pointer_shift_launch(
    src: fx.Pointer,
    dst: fx.Pointer,
    n: fx.Int32,
    stream: fx.Stream = fx.Stream(None),
):
    pointer_shift_kernel(src, dst, n).launch(
        grid=(1, 1, 1), block=(len(UINT32_BITS), 1, 1), stream=stream
    )


@flyc.kernel
def tensor_shift_kernel_32(src: fx.Tensor, dst: fx.Tensor, n: fx.Int32):
    BOUNDARY_LABELS.append(str(src.element_type))
    tid = fx.thread_idx.x
    if tid < n:
        layout = fx.make_layout(1, 1)
        view_in = fx.Tensor(
            fx.make_view(fx.add_offset(fx.get_iter(src), fx.make_int_tuple(tid)), layout)
        )
        view_out = fx.Tensor(
            fx.make_view(fx.add_offset(fx.get_iter(dst), fx.make_int_tuple(tid)), layout)
        )
        frag_in = fx.make_fragment_like(view_in, view_in.element_type)
        frag_out = fx.make_fragment_like(view_out, fx.Int32)
        fx.copy(
            fx.make_copy_atom(fx.UniversalCopy32b(), view_in.element_type),
            view_in,
            frag_in,
        )
        frag_out.store((frag_in.load() >> 4).to(fx.Int32))
        fx.copy(
            fx.make_copy_atom(fx.UniversalCopy128b(), fx.Int32),
            frag_out,
            view_out,
        )


@flyc.kernel
def tensor_shift_kernel_8(src: fx.Tensor, dst: fx.Tensor, n: fx.Int32):
    BOUNDARY_LABELS.append(str(src.element_type))
    tid = fx.thread_idx.x
    if tid < n:
        layout = fx.make_layout(1, 1)
        view_in = fx.Tensor(
            fx.make_view(fx.add_offset(fx.get_iter(src), fx.make_int_tuple(tid)), layout)
        )
        view_out = fx.Tensor(
            fx.make_view(fx.add_offset(fx.get_iter(dst), fx.make_int_tuple(tid)), layout)
        )
        frag_in = fx.make_fragment_like(view_in, view_in.element_type)
        frag_out = fx.make_fragment_like(view_out, fx.Int32)
        fx.copy(
            fx.make_copy_atom(fx.UniversalCopy8b(), view_in.element_type),
            view_in,
            frag_in,
        )
        frag_out.store((frag_in.load() >> 4).to(fx.Int32))
        fx.copy(
            fx.make_copy_atom(fx.UniversalCopy32b(), fx.Int32),
            frag_out,
            view_out,
        )


@flyc.jit
def tensor_uint32_launch(
    src: fx.Tensor,
    dst: fx.Tensor,
    n: fx.Int32,
    stream: fx.Stream = fx.Stream(None),
):
    unsigned_iter = fx.recast_iter(fx.Uint32, fx.get_iter(src))
    unsigned_src = fx.Tensor(fx.make_view(unsigned_iter, fx.make_layout(1, 1)))
    tensor_shift_kernel_32(unsigned_src, dst, n).launch(
        grid=(1, 1, 1), block=(len(UINT32_BITS), 1, 1), stream=stream
    )


@flyc.jit
def tensor_int32_launch(
    src: fx.Tensor,
    dst: fx.Tensor,
    n: fx.Int32,
    stream: fx.Stream = fx.Stream(None),
):
    tensor_shift_kernel_32(src, dst, n).launch(
        grid=(1, 1, 1), block=(len(UINT32_BITS), 1, 1), stream=stream
    )


@flyc.jit
def tensor_uint8_launch(
    src: fx.Tensor,
    dst: fx.Tensor,
    n: fx.Int32,
    stream: fx.Stream = fx.Stream(None),
):
    unsigned_iter = fx.recast_iter(fx.Uint8, fx.get_iter(src))
    unsigned_src = fx.Tensor(fx.make_view(unsigned_iter, fx.make_layout(1, 1)))
    tensor_shift_kernel_8(unsigned_src, dst, n).launch(
        grid=(1, 1, 1), block=(len(UINT8_BITS), 1, 1), stream=stream
    )


@flyc.jit
def tensor_int8_launch(
    src: fx.Tensor,
    dst: fx.Tensor,
    n: fx.Int32,
    stream: fx.Stream = fx.Stream(None),
):
    tensor_shift_kernel_8(src, dst, n).launch(
        grid=(1, 1, 1), block=(len(UINT8_BITS), 1, 1), stream=stream
    )


def _pointer_case(
    name: str, dtype, source: torch.Tensor, expected: list[int], expected_label: str
) -> dict:
    BOUNDARY_LABELS.clear()
    output = torch.zeros(source.numel(), dtype=torch.int32, device="cuda")
    pointer_shift_launch(
        flyc.from_c_void_p(dtype, source.data_ptr()),
        flyc.from_c_void_p(fx.Int32, output.data_ptr()),
        source.numel(),
        stream=torch.cuda.current_stream(),
    )
    torch.cuda.synchronize()
    observed = output.tolist()
    boundary_label = BOUNDARY_LABELS.pop()
    return {
        "case": name,
        "boundary_label": boundary_label,
        "expected_label": expected_label,
        "expected": expected,
        "observed": observed,
        "pass": observed == expected and boundary_label == expected_label,
    }


def _tensor_case(
    name: str, launch, source: torch.Tensor, expected: list[int], expected_label: str
) -> dict:
    BOUNDARY_LABELS.clear()
    output = torch.zeros(source.numel(), dtype=torch.int32, device="cuda")
    launch(
        source,
        output,
        source.numel(),
        stream=torch.cuda.current_stream(),
    )
    torch.cuda.synchronize()
    observed = output.tolist()
    boundary_label = BOUNDARY_LABELS.pop()
    return {
        "case": name,
        "boundary_label": boundary_label,
        "expected_label": expected_label,
        "expected": expected,
        "observed": observed,
        "pass": observed == expected and boundary_label == expected_label,
    }


def run_validation() -> list[dict]:
    if not torch.cuda.is_available():
        raise RuntimeError("One assigned gfx942 GPU is required")
    if torch.cuda.get_device_capability(0) != (9, 4):
        raise RuntimeError(
            f"expected gfx942, got {torch.cuda.get_device_name(0)} "
            f"{torch.cuda.get_device_capability(0)}"
        )

    uint32_source = torch.tensor(
        [value - (1 << 32) if value >= (1 << 31) else value for value in UINT32_BITS],
        dtype=torch.int32,
        device="cuda",
    )
    uint32_signed_expected = [value >> 4 for value in uint32_source.tolist()]
    uint32_unsigned_expected = [value >> 4 for value in UINT32_BITS]

    uint8_source = torch.tensor(UINT8_BITS, dtype=torch.uint8, device="cuda")
    int8_source = uint8_source.view(torch.int8)
    uint8_signed_expected = [value >> 4 for value in int8_source.tolist()]
    uint8_unsigned_expected = [value >> 4 for value in UINT8_BITS]

    return [
        _pointer_case(
            "pointer_uint32", fx.Uint32, uint32_source, uint32_unsigned_expected, "Uint32"
        ),
        _pointer_case(
            "pointer_int32_control", fx.Int32, uint32_source, uint32_signed_expected, "Int32"
        ),
        _tensor_case(
            "tensor_uint32", tensor_uint32_launch, uint32_source, uint32_unsigned_expected, "Uint32"
        ),
        _tensor_case(
            "tensor_int32_control", tensor_int32_launch, uint32_source, uint32_signed_expected, "Int32"
        ),
        _pointer_case(
            "pointer_uint8", fx.Uint8, uint8_source, uint8_unsigned_expected, "Uint8"
        ),
        _pointer_case(
            "pointer_int8_control", fx.Int8, int8_source, uint8_signed_expected, "Int8"
        ),
        _tensor_case(
            "tensor_uint8", tensor_uint8_launch, uint8_source, uint8_unsigned_expected, "Uint8"
        ),
        _tensor_case(
            "tensor_int8_control", tensor_int8_launch, int8_source, uint8_signed_expected, "Int8"
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="emit raw results as JSON")
    args = parser.parse_args()

    results = run_validation()
    payload = {
        "gpu": torch.cuda.get_device_name(0),
        "capability": list(torch.cuda.get_device_capability(0)),
        "flydsl_version": flydsl.__version__,
        "results": results,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for result in results:
            print(
                f"{result['case']}: {'PASS' if result['pass'] else 'FAIL'}\n"
                f"  expected={result['expected']}\n"
                f"  observed={result['observed']}"
            )
    return 0 if all(result["pass"] for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
