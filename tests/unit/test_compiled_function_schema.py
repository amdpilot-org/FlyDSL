import inspect

import pytest

torch = pytest.importorskip("torch")

import flydsl.expr as fx
from flydsl.compiler import jit_argument as ja
from flydsl.compiler.jit_function import CompiledFunction, _compiled_argument_schema, _validate_compiled_args
from flydsl.expr.numeric import Int32


def _schema():
    signature = inspect.Signature(
        [
            inspect.Parameter("a", inspect.Parameter.POSITIONAL_ONLY, annotation=fx.Tensor),
            inspect.Parameter("n", inspect.Parameter.POSITIONAL_ONLY, annotation=fx.Int32),
            inspect.Parameter("block", inspect.Parameter.POSITIONAL_ONLY, annotation=fx.Constexpr[int]),
        ]
    )
    tensor = ja.TorchTensorJitArg(torch.empty(8, dtype=torch.float32))
    return _compiled_argument_schema(signature, (tensor, Int32(8), 64))


def test_compiled_function_schema_accepts_matching_arguments():
    tensor = torch.empty(8, dtype=torch.float32)
    _validate_compiled_args(_schema(), (tensor, 8, 64))


@pytest.mark.parametrize(
    "args,match",
    [
        ((torch.empty(8, dtype=torch.float64), 8, 64), "dtype mismatch"),
        ((torch.empty(2, 4, dtype=torch.float32), 8, 64), "rank mismatch"),
        ((torch.empty(8, dtype=torch.float32), 8.0, 64), "scalar mismatch"),
        ((torch.empty(8, dtype=torch.float32), 8), "expects 3 positional arguments"),
    ],
)
def test_compiled_function_schema_rejects_mismatch_before_launch(args, match):
    def dispatch(_args):
        raise AssertionError("invalid arguments reached kernel dispatch")

    compiled = CompiledFunction(dispatch, None, _schema())
    with pytest.raises(TypeError, match=match):
        compiled(*args)
