# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

"""Host stdio handling for device-side diagnostics."""

import ctypes


_libc = ctypes.CDLL(None, use_errno=True)
_libc.fflush.argtypes = [ctypes.c_void_p]
_libc.fflush.restype = ctypes.c_int
_libc.setvbuf.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t]
_libc.setvbuf.restype = ctypes.c_int

# POSIX follows the C values used by glibc: unbuffered, line buffered, fully buffered.
_IONBF = 2
_configured = False


def _stdout_stream() -> ctypes.c_void_p:
    return ctypes.c_void_p.in_dll(_libc, "stdout")


def configure_device_printf_stdout() -> None:
    """Make newline-terminated device diagnostics promptly visible on stdout.

    HIP writes device ``printf`` output through the process' C ``stdout``
    stream.  libc normally block-buffers that stream when it is redirected or
    piped, including the pipe used by Jupyter kernels. FlyDSL configures it as
    unbuffered so records delivered by a completed GPU synchronization are
    visible without a separate host-side flush, including when another C stdio
    writer used stdout before FlyDSL was imported.

    The process-wide setting is applied once and also affects other C/C++
    writers to stdout.  Python's own text stream keeps its existing buffering.

    Raises:
        OSError: If libc rejects the buffering change.
    """
    global _configured
    if _configured:
        return
    stdout = _stdout_stream()
    if _libc.fflush(stdout) != 0:
        errno = ctypes.get_errno()
        raise OSError(errno, "failed to flush host stdout before disabling buffering")
    if _libc.setvbuf(stdout, None, _IONBF, 0) != 0:
        errno = ctypes.get_errno()
        raise OSError(errno, "failed to disable host stdout buffering")
    _configured = True


def flush_device_printf() -> None:
    """Flush completed device ``printf`` output and all other C stdio streams.

    This explicit helper remains available for callers that also need to flush
    other C stdio streams. It does not synchronize GPU work, so callers must
    first synchronize the relevant stream or device.

    Raises:
        OSError: If libc reports that a stream could not be flushed.
    """
    if _libc.fflush(None) != 0:
        errno = ctypes.get_errno()
        raise OSError(errno, "failed to flush host C stdio")
