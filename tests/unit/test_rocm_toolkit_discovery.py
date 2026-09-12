# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

import pytest

from flydsl._mlir import ir
from flydsl._mlir.passmanager import PassManager
from flydsl.compiler.backends.rocm import RocmBackend
from flydsl.compiler.mlir_utils import quote_pass_option_value
from flydsl.runtime.device import RocmToolchainError, get_rocm_toolkit_path


_ROOT_ENV_VARS = ("FLYDSL_ROCM_TOOLKIT_PATH", "ROCM_PATH", "ROCM_ROOT", "ROCM_HOME")


def _toolkit(root: Path, *, executable: bool = True) -> Path:
    linker = root / "llvm" / "bin" / "ld.lld"
    linker.parent.mkdir(parents=True)
    linker.write_text("#!/bin/sh\nexit 0\n")
    linker.chmod(0o755 if executable else 0o644)
    (root / "amdgcn" / "bitcode").mkdir(parents=True)
    return root


def _clear_roots(monkeypatch):
    for name in _ROOT_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_explicit_toolkit_has_precedence(tmp_path, monkeypatch):
    explicit = _toolkit(tmp_path / "explicit")
    standard = _toolkit(tmp_path / "standard")
    monkeypatch.setenv("FLYDSL_ROCM_TOOLKIT_PATH", str(explicit))
    monkeypatch.setenv("ROCM_PATH", str(standard))

    assert get_rocm_toolkit_path() == str(explicit)


@pytest.mark.parametrize(
    ("setup", "message"),
    [
        (lambda root: root.mkdir(), "is missing linker"),
        (lambda root: _toolkit(root, executable=False), "is not executable"),
    ],
)
def test_invalid_explicit_toolkit_is_diagnosed(tmp_path, monkeypatch, setup, message):
    root = tmp_path / "invalid"
    setup(root)
    monkeypatch.setenv("FLYDSL_ROCM_TOOLKIT_PATH", str(root))

    with pytest.raises(RocmToolchainError, match=message):
        get_rocm_toolkit_path()


def test_path_toolkit_precedes_default(tmp_path, monkeypatch):
    _clear_roots(monkeypatch)
    root = _toolkit(tmp_path / "path-toolkit")
    monkeypatch.setenv("PATH", os.pathsep.join((str(root / "llvm" / "bin"), os.environ.get("PATH", ""))))

    assert get_rocm_toolkit_path() == str(root)


def test_toolkit_with_space_is_quoted_in_binary_pipeline(tmp_path, monkeypatch):
    root = _toolkit(tmp_path / "toolkit with space")
    monkeypatch.setenv("FLYDSL_ROCM_TOOLKIT_PATH", str(root))

    backend = RocmBackend(RocmBackend.make_target("gfx950"))
    binary = backend.pipeline_fragments(compile_hints={})[-1]

    assert f'toolkit="{root}"' in binary
    with ir.Context() as ctx:
        PassManager.parse(f"builtin.module({binary})", context=ctx)


@pytest.mark.parametrize("value", [r'/tmp/toolkit with space', '/tmp/toolkit"quoted', r"/tmp/toolkit\\root"])
def test_pass_option_value_escapes_mlir_string_syntax(value):
    option = quote_pass_option_value(value)

    with ir.Context() as ctx:
        PassManager.parse(
            f'builtin.module(gpu-module-to-binary{{format=fatbin opts="" toolkit={option}}})', context=ctx
        )
