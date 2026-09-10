import pytest
import torch

import flydsl.compiler as flyc
import flydsl.expr as fx
from flydsl.expr import arith
from flydsl.expr.arith import CmpIPredicate

pytestmark = [pytest.mark.l2_device, pytest.mark.rocm_lower]


PREDICATES = (
    "eq",
    "ne",
    "lt",
    "le",
    "gt",
    "ge",
)

EXPLICIT_SIGNED_PREDICATES = {
    "eq": CmpIPredicate.eq,
    "ne": CmpIPredicate.ne,
    "lt": CmpIPredicate.slt,
    "le": CmpIPredicate.sle,
    "gt": CmpIPredicate.sgt,
    "ge": CmpIPredicate.sge,
}


EXPLICIT_UNSIGNED_PREDICATES = {
    "eq": CmpIPredicate.eq,
    "ne": CmpIPredicate.ne,
    "lt": CmpIPredicate.ult,
    "le": CmpIPredicate.ule,
    "gt": CmpIPredicate.ugt,
    "ge": CmpIPredicate.uge,
}


def _operator_condition(name, left, right):
    if name == "eq":
        return left == right
    if name == "ne":
        return left != right
    if name == "lt":
        return left < right
    if name == "le":
        return left <= right
    if name == "gt":
        return left > right
    return left >= right


def _record_case(left, right, values_out, predicates_out, base, signed):
    one = fx.Uint8(1)
    zero = fx.Uint8(0)
    for column, name in enumerate(PREDICATES):
        operator_condition = _operator_condition(name, left, right)
        explicit_predicates = (
            EXPLICIT_SIGNED_PREDICATES
            if signed
            else EXPLICIT_UNSIGNED_PREDICATES
        )
        explicit_condition = arith.cmpi(explicit_predicates[name], left, right)
        predicates_out[base + column] = operator_condition.select(one, zero)
        predicates_out[base + len(PREDICATES) + column] = explicit_condition.select(
            one, zero
        )
        values_out[base + column] = operator_condition.select(left, right)
        values_out[base + len(PREDICATES) + column] = arith.select(
            explicit_condition, left, right
        )


@flyc.kernel
def integer_predicate_select_kernel(
    signed32_x: fx.Pointer,
    signed32_y: fx.Pointer,
    unsigned32_x: fx.Pointer,
    unsigned32_y: fx.Pointer,
    signed64_x: fx.Pointer,
    signed64_y: fx.Pointer,
    unsigned64_x: fx.Pointer,
    unsigned64_y: fx.Pointer,
    signed32_out: fx.Pointer,
    unsigned32_out: fx.Pointer,
    signed64_out: fx.Pointer,
    unsigned64_out: fx.Pointer,
    signed32_predicates: fx.Pointer,
    unsigned32_predicates: fx.Pointer,
    signed64_predicates: fx.Pointer,
    unsigned64_predicates: fx.Pointer,
    n: fx.Int32,
):
    idx = fx.block_idx.x * fx.block_dim.x + fx.thread_idx.x
    if idx < n:
        base = idx * (len(PREDICATES) * 2)
        _record_case(
            signed32_x[idx],
            signed32_y[idx],
            signed32_out,
            signed32_predicates,
            base,
            True,
        )
        _record_case(
            unsigned32_x[idx],
            unsigned32_y[idx],
            unsigned32_out,
            unsigned32_predicates,
            base,
            False,
        )
        _record_case(
            signed64_x[idx],
            signed64_y[idx],
            signed64_out,
            signed64_predicates,
            base,
            True,
        )
        _record_case(
            unsigned64_x[idx],
            unsigned64_y[idx],
            unsigned64_out,
            unsigned64_predicates,
            base,
            False,
        )


@flyc.jit
def integer_predicate_select(
    signed32_x: fx.Pointer,
    signed32_y: fx.Pointer,
    unsigned32_x: fx.Pointer,
    unsigned32_y: fx.Pointer,
    signed64_x: fx.Pointer,
    signed64_y: fx.Pointer,
    unsigned64_x: fx.Pointer,
    unsigned64_y: fx.Pointer,
    signed32_out: fx.Pointer,
    unsigned32_out: fx.Pointer,
    signed64_out: fx.Pointer,
    unsigned64_out: fx.Pointer,
    signed32_predicates: fx.Pointer,
    unsigned32_predicates: fx.Pointer,
    signed64_predicates: fx.Pointer,
    unsigned64_predicates: fx.Pointer,
    n: fx.Int32,
    stream: fx.Stream = fx.Stream(None),
):
    block_dim = 64
    grid_x = (n + block_dim - 1) // block_dim
    integer_predicate_select_kernel(
        signed32_x,
        signed32_y,
        unsigned32_x,
        unsigned32_y,
        signed64_x,
        signed64_y,
        unsigned64_x,
        unsigned64_y,
        signed32_out,
        unsigned32_out,
        signed64_out,
        unsigned64_out,
        signed32_predicates,
        unsigned32_predicates,
        signed64_predicates,
        unsigned64_predicates,
        n,
    ).launch(grid=(grid_x, 1, 1), block=(block_dim, 1, 1), stream=stream)


def _matrix(bits):
    high = 1 << (bits - 1)
    maximum = high - 1
    return [
        (0, 0),
        (0, 1),
        (1, 0),
        (0, high),
        (high, 0),
        (high, high),
        (high, maximum),
        (maximum, high),
        (high, 1),
        (1, high),
        (high - 1, high),
        (high, high - 1),
        (maximum, maximum),
        (maximum, maximum - 1),
        (maximum - 1, maximum),
    ]


def _signed(value, bits):
    value &= (1 << bits) - 1
    return value - (1 << bits) if value >= (1 << (bits - 1)) else value


def _reference(values, bits, signed):
    results = []
    for left, right in values:
        if signed:
            compare_left = _signed(left, bits)
            compare_right = _signed(right, bits)
        else:
            compare_left = left & ((1 << bits) - 1)
            compare_right = right & ((1 << bits) - 1)
        predicates = [
            compare_left == compare_right,
            compare_left != compare_right,
            compare_left < compare_right,
            compare_left <= compare_right,
            compare_left > compare_right,
            compare_left >= compare_right,
        ]
        selected = [left if predicate else right for predicate in predicates]
        results.append((predicates, selected))
    return results


def _pointer(dtype, tensor):
    return flyc.from_c_void_p(dtype, tensor.data_ptr())


@pytest.mark.xfail(
    strict=True,
    reason="main reconstructs unsigned pointer loads as signed; upstream PR 920 fixes this",
)
def test_loaded_integer_predicates_and_select():
    values32 = _matrix(32)
    values64 = _matrix(64)
    count = len(values32)
    columns = len(PREDICATES) * 2

    signed32_x = torch.tensor(
        [_signed(left, 32) for left, _ in values32], dtype=torch.int32, device="cuda"
    )
    signed32_y = torch.tensor(
        [_signed(right, 32) for _, right in values32], dtype=torch.int32, device="cuda"
    )
    unsigned32_x = signed32_x.clone()
    unsigned32_y = signed32_y.clone()
    signed64_x = torch.tensor(
        [_signed(left, 64) for left, _ in values64], dtype=torch.int64, device="cuda"
    )
    signed64_y = torch.tensor(
        [_signed(right, 64) for _, right in values64], dtype=torch.int64, device="cuda"
    )
    unsigned64_x = signed64_x.clone()
    unsigned64_y = signed64_y.clone()

    outputs = {
        "signed32": torch.empty((count, columns), dtype=torch.int32, device="cuda"),
        "unsigned32": torch.empty(
            (count, columns), dtype=torch.int32, device="cuda"
        ),
        "signed64": torch.empty((count, columns), dtype=torch.int64, device="cuda"),
        "unsigned64": torch.empty(
            (count, columns), dtype=torch.int64, device="cuda"
        ),
    }
    predicates = {
        "signed32": torch.empty((count, columns), dtype=torch.int8, device="cuda"),
        "unsigned32": torch.empty(
            (count, columns), dtype=torch.int8, device="cuda"
        ),
        "signed64": torch.empty((count, columns), dtype=torch.int8, device="cuda"),
        "unsigned64": torch.empty(
            (count, columns), dtype=torch.int8, device="cuda"
        ),
    }
    stream = torch.cuda.current_stream()

    integer_predicate_select(
        _pointer(fx.Int32, signed32_x),
        _pointer(fx.Int32, signed32_y),
        _pointer(fx.Uint32, unsigned32_x),
        _pointer(fx.Uint32, unsigned32_y),
        _pointer(fx.Int64, signed64_x),
        _pointer(fx.Int64, signed64_y),
        _pointer(fx.Uint64, unsigned64_x),
        _pointer(fx.Uint64, unsigned64_y),
        _pointer(fx.Int32, outputs["signed32"]),
        _pointer(fx.Uint32, outputs["unsigned32"]),
        _pointer(fx.Int64, outputs["signed64"]),
        _pointer(fx.Uint64, outputs["unsigned64"]),
        _pointer(fx.Uint8, predicates["signed32"]),
        _pointer(fx.Uint8, predicates["unsigned32"]),
        _pointer(fx.Uint8, predicates["signed64"]),
        _pointer(fx.Uint8, predicates["unsigned64"]),
        count,
        stream=stream,
    )
    torch.cuda.synchronize()

    cases = (
        ("signed32", values32, 32, True, torch.int32),
        ("unsigned32", values32, 32, False, torch.int32),
        ("signed64", values64, 64, True, torch.int64),
        ("unsigned64", values64, 64, False, torch.int64),
    )
    mismatches = []
    for name, values, bits, signed, storage_dtype in cases:
        expected = _reference(values, bits, signed)
        actual_values = outputs[name].cpu().tolist()
        actual_predicates = predicates[name].cpu().tolist()
        for row, ((expected_predicates, expected_selected), value_row) in enumerate(
            zip(expected, actual_values)
        ):
            expected_predicate_row = expected_predicates + expected_predicates
            expected_selected_row = expected_selected + expected_selected
            expected_predicate_ints = [
                int(value) for value in expected_predicate_row
            ]
            if actual_predicates[row] != expected_predicate_ints:
                mismatches.append(
                    {
                        "kind": "predicates",
                        "case": name,
                        "row": row,
                        "x": values[row][0],
                        "y": values[row][1],
                        "actual": actual_predicates[row],
                        "expected": expected_predicate_ints,
                    }
                )
            if signed:
                expected_value_row = [
                    _signed(value, bits) for value in expected_selected_row
                ]
            else:
                unsigned_actual = (
                    torch.tensor(value_row, dtype=storage_dtype)
                    .view(getattr(torch, f"uint{bits}"))
                    .tolist()
                )
                expected_value_row = expected_selected_row
                value_row = unsigned_actual
            if value_row != expected_value_row:
                mismatches.append(
                    {
                        "kind": "selected_values",
                        "case": name,
                        "row": row,
                        "x": values[row][0],
                        "y": values[row][1],
                        "actual": value_row,
                        "expected": expected_value_row,
                    }
                )
    assert not mismatches, mismatches
