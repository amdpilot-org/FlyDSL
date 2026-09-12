# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

from contextlib import nullcontext

from flydsl.compiler import jit_function


class _FakeOperation:
    def verify(self):
        return None

    def get_asm(self, **kwargs):
        return "module {}"


class _FakeModule:
    def __init__(self):
        self.operation = _FakeOperation()


class _FakeBackend:
    def lower_compile_hints(self, module, *, compile_hints):
        assert module is _PARSED_MODULE


_MODULE = _FakeModule()
_PARSED_MODULE = _FakeModule()


def test_mlir_compiler_reuses_retained_source_ir(monkeypatch):
    """The JIT source snapshot should also feed the required parse copy."""

    monkeypatch.setattr(jit_function, "get_backend", lambda arch="": _FakeBackend())
    monkeypatch.setattr(
        jit_function,
        "_pipeline_fragments_for_mode",
        lambda backend, *, compile_hints: type(
            "Config",
            (),
            {
                "fragments": ["test-pass"],
                "pre_binary": [],
                "binary_fragment": "",
                "llvm_opts": [],
                "external": False,
            },
        )(),
    )
    monkeypatch.setattr(jit_function, "_run_pipeline", lambda module, fragments, **kwargs: None)
    monkeypatch.setattr(jit_function, "_llvm_options", lambda options: nullcontext(), raising=False)

    def parse(source):
        assert source == "retained source"
        return _PARSED_MODULE

    monkeypatch.setattr(jit_function.ir.Module, "parse", parse)

    def reject_second_serialization(**kwargs):
        raise AssertionError("JIT module was unnecessarily serialized twice")

    _MODULE.operation.get_asm = reject_second_serialization

    assert jit_function.MlirCompiler.compile(_MODULE, source_ir="retained source") is _PARSED_MODULE
