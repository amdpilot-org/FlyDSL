#!/usr/bin/env python3

"""Exact GPU oracles for integer Vector.reduce semantics.

Unsigned cases use same-width signed Torch storage because the Torch bridge
does not expose unsigned memrefs. The kernel casts elements to the unsigned DSL
type before reduction and casts results back to storage for comparison.
"""

import pytest
import torch

import flydsl.compiler as flyc
import flydsl.expr as fx

pytestmark = [pytest.mark.l2_device, pytest.mark.rocm_lower]

if not torch.cuda.is_available():
    pytest.skip("CUDA/ROCm not available", allow_module_level=True)


@flyc.kernel
def _reduce_kernel(
    values: fx.Tensor,
    results: fx.Tensor,
    active_vectors: fx.Int32,
    vec_width: fx.Constexpr[int],
    op: fx.Constexpr[str],
    signed: fx.Constexpr[bool],
    bits: fx.Constexpr[int],
):
    tid = fx.thread_idx.x
    if tid < active_vectors:
        base = tid * vec_width
        element_dtype = (
            values.dtype
            if signed
            else fx.Uint8
            if bits == 8
            else fx.Uint16
            if bits == 16
            else fx.Uint32
            if bits == 32
            else fx.Uint64
        )
        elements = [values[base + i].to(element_dtype) for i in fx.range_constexpr(vec_width)]
        result = fx.Vector.from_elements(elements).reduce(op)
        results[tid] = result.to(values.dtype)


@flyc.jit
def _launch_reduce(
    values: fx.Tensor,
    results: fx.Tensor,
    active_vectors: fx.Int32,
    vec_width: fx.Constexpr[int],
    op: fx.Constexpr[str],
    signed: fx.Constexpr[bool],
    bits: fx.Constexpr[int],
    block_dim: fx.Constexpr[int],
    stream: fx.Stream = fx.Stream(None),
):
    _reduce_kernel(values, results, active_vectors, vec_width, op, signed, bits).launch(
        grid=(1, 1, 1), block=(block_dim, 1, 1), stream=stream
    )


_DTYPE_CASES = [
    pytest.param(torch.int8, True, 8, id="int8"),
    pytest.param(torch.int8, False, 8, id="uint8"),
    pytest.param(torch.int16, True, 16, id="int16"),
    pytest.param(torch.int16, False, 16, id="uint16"),
    pytest.param(torch.int32, True, 32, id="int32"),
    pytest.param(torch.int32, False, 32, id="uint32"),
    pytest.param(torch.int64, True, 64, id="int64"),
    pytest.param(torch.int64, False, 64, id="uint64"),
]


def _wrap(value, signed, bits):
    value %= 1 << bits
    if signed and value >= 1 << (bits - 1):
        value -= 1 << bits
    return value


def _vector_values(op, vector_index, vec_width, signed, bits):
    maximum = (1 << (bits - 1)) - 1 if signed else (1 << bits) - 1
    minimum = -(1 << (bits - 1)) if signed else 0
    if op == "add":
        return [maximum - (vector_index % 2)] + [1] * (vec_width - 1)
    if signed:
        pattern = [maximum, 0, minimum, -1]
    else:
        pattern = [maximum, 0, 1, 0x55]
    return [pattern[(index + vector_index) % 4] for index in range(vec_width)]


def _expected(op, values, signed, bits):
    if op == "add":
        result = sum(values)
    elif op == "and":
        result = values[0]
        for value in values[1:]:
            result &= value
    elif op == "or":
        result = values[0]
        for value in values[1:]:
            result |= value
    else:
        result = values[0]
        for value in values[1:]:
            result ^= value
    return _wrap(result, signed, bits)


def _run_case(op, torch_dtype, signed, bits, vec_width, block_dim, active_vectors):
    vectors = [
        _vector_values(op, index, vec_width, signed, bits)
        for index in range(block_dim)
    ]
    flat_values = [value for vector in vectors for value in vector]
    expected = [_expected(op, vector, signed, bits) for vector in vectors[:active_vectors]]
    storage_values = [
        value if signed or value < (1 << (bits - 1)) else value - (1 << bits)
        for value in flat_values
    ]
    values = torch.tensor(storage_values, dtype=torch_dtype, device="cuda")
    results = torch.zeros(block_dim, dtype=torch_dtype, device="cuda")
    stream = torch.cuda.current_stream()
    _launch_reduce(
        values,
        results,
        active_vectors,
        vec_width,
        op,
        signed,
        bits,
        block_dim,
        stream=stream,
    )
    torch.cuda.synchronize()
    actual = [
        value if signed or value >= 0 else value + (1 << bits)
        for value in results[:active_vectors].tolist()
    ]
    assert actual == expected
    if active_vectors < block_dim:
        assert results[active_vectors:].tolist() == [0] * (block_dim - active_vectors)


@pytest.mark.parametrize("op", ["add", "and", "or", "xor"])
@pytest.mark.parametrize(("torch_dtype", "signed", "bits"), _DTYPE_CASES)
def test_integer_reduce_semantics(op, torch_dtype, signed, bits):
    _run_case(
        op,
        torch_dtype,
        signed,
        bits,
        vec_width=4,
        block_dim=64,
        active_vectors=3,
    )


@pytest.mark.parametrize("op", ["add", "xor"])
@pytest.mark.parametrize("vec_width", [1, 2, 4, 8, 16])
@pytest.mark.parametrize(
    ("torch_dtype", "signed", "bits"),
    [case.values for case in _DTYPE_CASES if case.id in ("int32", "uint32")],
)
def test_integer_reduce_supported_widths(op, torch_dtype, signed, bits, vec_width):
    _run_case(
        op,
        torch_dtype,
        signed,
        bits,
        vec_width=vec_width,
        block_dim=64,
        active_vectors=64,
    )


@pytest.mark.parametrize("op", ["add", "xor"])
@pytest.mark.parametrize("active_vectors", [1, 3, 63, 127])
@pytest.mark.parametrize(
    ("torch_dtype", "signed", "bits"),
    [case.values for case in _DTYPE_CASES if case.id in ("int32", "uint32")],
)
def test_integer_reduce_partial_active_vectors(
    op, torch_dtype, signed, bits, active_vectors
):
    _run_case(
        op,
        torch_dtype,
        signed,
        bits,
        vec_width=4,
        block_dim=128,
        active_vectors=active_vectors,
    )
