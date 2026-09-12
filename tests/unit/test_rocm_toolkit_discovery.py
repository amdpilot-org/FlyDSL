# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

import pytest

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
