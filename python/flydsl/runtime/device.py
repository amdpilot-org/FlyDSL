# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

import functools
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

_ROCM_AGENT_TIMEOUT_S = int(os.environ.get("FLYDSL_ROCM_AGENT_TIMEOUT", "300"))


class RocmToolchainError(RuntimeError):
    """Raised when an explicitly selected ROCm toolkit is unusable."""


def _validate_rocm_toolkit(root: Path, source: str) -> str:
    """Validate the files used by MLIR's ROCDL serializer."""
    root = root.expanduser().absolute()
    linker = root / "llvm" / "bin" / "ld.lld"
    bitcode = root / "amdgcn" / "bitcode"

    if not linker.exists():
        raise RocmToolchainError(f"ROCm toolkit from {source} is missing linker: {linker}")
    if not linker.is_file():
        raise RocmToolchainError(f"ROCm toolkit linker from {source} is not a file: {linker}")
    if not os.access(linker, os.X_OK):
        raise RocmToolchainError(f"ROCm toolkit linker from {source} is not executable: {linker}")
    if not bitcode.is_dir():
        raise RocmToolchainError(f"ROCm toolkit from {source} is missing device libraries: {bitcode}")
    return str(root)


def _toolkit_from_path_linker(linker: str) -> Optional[str]:
    """Infer a toolkit root from either a PATH link or its resolved target."""
    linker_path = Path(linker).absolute()
    candidates = []
    if linker_path.parent.name == "bin" and linker_path.parent.parent.name == "llvm":
        candidates.append(linker_path.parents[2])

    # Distribution packages commonly expose ld.lld through an arbitrary PATH
    # symlink while the target lives below <toolkit>/lib/llvm/bin. Walk the
    # resolved target's ancestors and accept only a root that fully validates.
    resolved = linker_path.resolve()
    candidates.extend(resolved.parents)
    for root in dict.fromkeys(candidates):
        try:
            return _validate_rocm_toolkit(root, "PATH")
        except RocmToolchainError:
            continue
    return None


def get_rocm_toolkit_path() -> str:
    """Return a validated ROCm root for ``gpu-module-to-binary``.

    Discovery is deterministic: ``FLYDSL_ROCM_TOOLKIT_PATH``, the standard
    ROCm root variables, ``ld.lld`` on ``PATH``, then ``/opt/rocm``. Explicit
    roots are diagnosed instead of silently falling through to another
    installation.
    """
    for env_var in ("FLYDSL_ROCM_TOOLKIT_PATH", "ROCM_PATH", "ROCM_ROOT", "ROCM_HOME"):
        value = os.environ.get(env_var)
        if value:
            return _validate_rocm_toolkit(Path(value), env_var)

    linker = shutil.which("ld.lld")
    if linker:
        toolkit = _toolkit_from_path_linker(linker)
        if toolkit:
            return toolkit

    opt_rocm = Path("/opt/rocm")
    if opt_rocm.exists():
        return _validate_rocm_toolkit(opt_rocm, "default /opt/rocm")

    searched = (
        "FLYDSL_ROCM_TOOLKIT_PATH, ROCM_PATH, ROCM_ROOT, ROCM_HOME, "
        "a linker associated with a usable ROCm toolkit on PATH, and /opt/rocm"
    )
    raise RocmToolchainError(f"Unable to find a usable ROCm toolkit; searched {searched}")


def _arch_from_rocm_agent_enumerator() -> Optional[str]:
    """Query rocm_agent_enumerator (standard ROCm tool) for the first GPU arch."""
    try:
        out = subprocess.check_output(
            ["rocm_agent_enumerator", "-name"],
            text=True,
            timeout=_ROCM_AGENT_TIMEOUT_S,
            stderr=subprocess.DEVNULL,
        )
        for line in out.splitlines():
            name = line.strip()
            if name.startswith("gfx") and name != "gfx000":
                return name
    except Exception:
        pass
    return None


@functools.lru_cache(maxsize=None)
def _arch_from_hardware() -> str:
    """Cached hardware detection (rocm_agent_enumerator is slow)."""
    arch = _arch_from_rocm_agent_enumerator()
    if arch:
        return arch.split(":", 1)[0]
    return "gfx942"


def get_rocm_arch() -> str:
    """Best-effort ROCm GPU arch string, always lower-cased (e.g. 'gfx942').

    Lower-casing happens here so every caller can compare against lower-case
    literals without normalising first; ROCm itself only ever emits lower-case
    names, so this only affects hand-set environment overrides.
    """
    env = os.environ.get("FLYDSL_GPU_ARCH") or os.environ.get("HSA_OVERRIDE_GFX_VERSION")
    if env:
        env = env.lower()
        if env.startswith("gfx"):
            return env
        if env.count(".") == 2:
            parts = env.split(".")
            return f"gfx{parts[0]}{parts[1]}{parts[2]}"

    return _arch_from_hardware().lower()


@functools.lru_cache(maxsize=None)
def get_rocm_device_count() -> int:
    """Best-effort ROCm visible GPU count via ``rocm_agent_enumerator`` (standard ROCm tool).

    Uses the same invocation as :func:`_arch_from_rocm_agent_enumerator`. Returns 0
    when the tool is unavailable or no discrete GPU agents are reported.
    """
    try:
        out = subprocess.check_output(
            ["rocm_agent_enumerator", "-name"],
            text=True,
            timeout=5,
            stderr=subprocess.DEVNULL,
        )
        n = 0
        for line in out.splitlines():
            name = line.strip()
            if name.startswith("gfx") and name != "gfx000":
                n += 1
        return n
    except Exception:
        return 0


def is_rdna_arch(arch: Optional[str] = None) -> bool:
    """Check if architecture is RDNA-based (gfx10/11/12, wave32).

    This is the single source of truth for CDNA vs RDNA classification.
    RDNA architectures use wave32 and have different buffer descriptor flags.

    If arch is None, the current GPU arch is auto-detected.
    """
    if arch is None:
        arch = get_rocm_arch()
    if not arch:
        return False
    arch = arch.lower()
    if arch.startswith("gfx10") or arch.startswith("gfx11"):
        return True
    if arch.startswith("gfx120"):
        return True
    return False


def get_warp_size(arch: Optional[str] = None) -> int:
    """Lanes per warp for an architecture.

    If arch is None, the current GPU arch is auto-detected.
    """
    if arch is None:
        arch = get_rocm_arch()
    if not arch:
        return 64
    arch = arch.lower()
    if arch.startswith("gfx10") or arch.startswith("gfx11") or arch.startswith("gfx12"):
        return 32
    return 64
