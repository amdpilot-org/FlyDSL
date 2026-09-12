# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

"""Host stdio helpers for device-side diagnostics."""

import ctypes


_libc = ctypes.CDLL(None, use_errno=True)
_libc.fflush.argtypes = [ctypes.c_void_p]
_libc.fflush.restype = ctypes.c_int


def flush_device_printf() -> None:
    """Make completed device ``printf`` output visible on host stdout.

    ROCm delivers device ``printf`` records to the host when the relevant GPU
    work completes.  If stdout is redirected or piped, libc normally block
    buffers those records.  Call this function *after* synchronizing the
    relevant stream or device to flush the host C stdio buffers.

    This function does not synchronize GPU work.  It uses ``fflush(NULL)``, so
    it also flushes any other host C output streams open in the process.

    Raises:
        OSError: If libc reports that a stream could not be flushed.
    """
    if _libc.fflush(None) != 0:
        errno = ctypes.get_errno()
        raise OSError(errno, "failed to flush host C stdio")
