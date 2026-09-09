#!/usr/bin/env python3

import pytest

import flydsl.compiler as flyc
import flydsl.expr as fx
from flydsl.expr import const_expr

pytestmark = [pytest.mark.l0_backend_agnostic]


def test_kernel_accepts_top_level_bare_return():
    @flyc.kernel
    def kernel(Out: fx.Tensor):
        Out[0] = fx.Int32(1)
        return

    assert kernel._func.__name__ == "kernel"


def test_kernel_accepts_constexpr_control_flow_return():
    @flyc.kernel
    def kernel(Out: fx.Tensor, flag: fx.Constexpr[int]):
        if const_expr(flag > 0):
            Out[0] = fx.Int32(1)
            return
        Out[0] = fx.Int32(2)

    assert kernel._func.__name__ == "kernel"


def test_kernel_rejects_valued_return():
    with pytest.raises(SyntaxError, match="kernel return must not carry a value"):

        @flyc.kernel
        def kernel(Out: fx.Tensor):
            return fx.Int32(1)


@pytest.mark.parametrize(
    "body",
    [
        "if flag > fx.Int32(0):\n        return",
        "for i in range(fx.Int32(2)):\n        return",
        "while flag > fx.Int32(0):\n        return",
        "if const_expr(True):\n        if flag > fx.Int32(0):\n            return",
    ],
)
def test_kernel_rejects_dynamic_control_flow_return(body, tmp_path):
    source = f"def kernel(Out: fx.Tensor, flag: fx.Int32):\n    {body}\n"
    source_file = tmp_path / "early_return_probe.py"
    source_file.write_text(source)
    namespace = {"fx": fx, "const_expr": const_expr, "flyc": flyc}
    exec(compile(source, str(source_file), "exec"), namespace)

    with pytest.raises(SyntaxError, match="does not support early return inside dynamic control flow"):
        flyc.kernel(namespace["kernel"])
