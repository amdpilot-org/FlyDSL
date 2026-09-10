#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""Backend-agnostic tests for the public GPU shuffle wrappers."""

import pytest

import flydsl.expr as fx
from flydsl._mlir import ir
from flydsl._mlir.dialects import func
from flydsl.expr import gpu


def _build_module(build_fn, arg_types=()):
    with ir.Context() as context:
        context.allow_unregistered_dialects = True
        with ir.Location.unknown(context):
            types = [type_factory() if callable(type_factory) else type_factory for type_factory in arg_types]
            module = ir.Module.create()
            with ir.InsertionPoint(module.body):
                function = func.FuncOp("test", ir.FunctionType.get(types, []))
                with ir.InsertionPoint(function.add_entry_block()):
                    build_fn(*function.entry_block.arguments)
                    func.ReturnOp([])
            module.operation.verify()
            return str(module)


@pytest.mark.l0_backend_agnostic
def test_shuffle_wrappers_are_exported():
    assert fx.shuffle_xor is gpu.shuffle_xor
    assert fx.shuffle_up is gpu.shuffle_up
    assert fx.shuffle_down is gpu.shuffle_down
    assert fx.shuffle_idx is gpu.shuffle_idx


@pytest.mark.l0_backend_agnostic
@pytest.mark.parametrize(
    ("function", "mode"),
    [
        (fx.shuffle_xor, "xor"),
        (fx.shuffle_up, "up"),
        (fx.shuffle_down, "down"),
        (fx.shuffle_idx, "idx"),
    ],
)
def test_shuffle_emits_mode(function, mode):
    def build(value):
        function(value, 1, 64)

    ir_text = _build_module(build, [ir.F32Type.get])
    assert f"gpu.shuffle {mode}" in ir_text


@pytest.mark.l0_backend_agnostic
def test_shuffle_converts_offset_and_width_to_int32():
    def build(value):
        fx.shuffle_xor(value, 1, 64)

    ir_text = _build_module(build, [ir.F32Type.get])
    assert "arith.constant 1 : i32" in ir_text
    assert "arith.constant 64 : i32" in ir_text


@pytest.mark.l0_backend_agnostic
@pytest.mark.parametrize(
    ("dtype", "mlir_type"),
    [
        (fx.Int16, "i16"),
        (fx.Int32, "i32"),
        (fx.Int64, "i64"),
        (fx.Float16, "f16"),
        (fx.BFloat16, "bf16"),
        (fx.Float64, "f64"),
    ],
)
def test_shuffle_preserves_supported_operand_width(dtype, mlir_type):
    def build(value):
        result = fx.shuffle_xor(dtype(value), 1, 64)
        assert isinstance(result, dtype)

    ir_text = _build_module(build, [lambda: dtype.ir_type])
    assert "gpu.shuffle xor" in ir_text
    assert f": {mlir_type}" in ir_text


@pytest.mark.l0_backend_agnostic
def test_shuffle_preserves_vector_shape_and_dtype():
    def build():
        value = fx.Vector.filled(4, 1.0, fx.Float32)
        result = fx.shuffle_idx(value, 0, 64)
        assert isinstance(result, fx.Vector)
        assert result.shape == (4,)
        assert result.dtype is fx.Float32

    ir_text = _build_module(build)
    assert "gpu.shuffle idx" in ir_text
    assert "vector<4xf32>" in ir_text


@pytest.mark.l0_backend_agnostic
def test_shuffle_rejects_unknown_mode():
    with ir.Context():
        with pytest.raises(ValueError, match="invalid shuffle mode 'bogus'"):
            gpu.shuffle(fx.Float32(1.0), 1, 64, mode="bogus")
