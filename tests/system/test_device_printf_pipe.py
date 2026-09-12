# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

"""Regression for device printf visibility through a pipe."""

import os
import selectors
import subprocess
import sys

import pytest

_CHILD_FLAG = "--device-printf-pipe-child"

pytestmark = [pytest.mark.l2_device, pytest.mark.rocm_lower]


def _run_child() -> None:
    import torch

    import flydsl.compiler as flyc
    import flydsl.expr as fx
    from flydsl.runtime import flush_device_printf

    launches = int(sys.argv[sys.argv.index(_CHILD_FLAG) + 1])
    explicit_flush = sys.argv[sys.argv.index(_CHILD_FLAG) + 2] == "flush"

    @flyc.kernel
    def hello_kernel():
        tid = fx.thread_idx.x
        fx.printf("hello from thread {}", tid)

    @flyc.jit
    def hello(stream: fx.Stream = fx.Stream(None)):
        hello_kernel().launch(grid=(1, 1, 1), block=(4, 1, 1), stream=stream)

    for _ in range(launches):
        hello()
    torch.cuda.synchronize()
    if explicit_flush:
        flush_device_printf()
    os.write(2, b"READY\n")
    if sys.stdin.buffer.readline() != b"release\n":
        raise RuntimeError("parent closed the control pipe before observing output")


if _CHILD_FLAG in sys.argv:
    _run_child()
    raise SystemExit(0)


@pytest.mark.parametrize(
    ("launches", "explicit_flush"),
    [(1, False), (3, False), (1, True), (3, True)],
)
def test_device_printf_visible_in_pipe_after_synchronize(launches, explicit_flush):
    """The unchanged synchronize-only sequence exposes output while the child lives."""
    process = subprocess.Popen(
        [sys.executable, __file__, _CHILD_FLAG, str(launches), "flush" if explicit_flush else "automatic"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    stdout = bytearray()
    stderr = bytearray()
    ready = False

    try:
        expected_lines = 4 * launches
        while not ready or stdout.count(b"hello from thread ") < expected_lines:
            events = selector.select(timeout=30)
            assert events, (
                "timed out waiting for synchronized device printf output; "
                f"observed={stdout.decode()!r}, stderr={stderr.decode()!r}"
            )
            for key, _ in events:
                data = os.read(key.fileobj.fileno(), 4096)
                assert data, f"child exited before output was observed; stderr={stderr.decode()}"
                if key.data == "stdout":
                    stdout.extend(data)
                else:
                    stderr.extend(data)
                    ready = b"READY\n" in stderr

        assert process.poll() is None, "output was visible only after process teardown"
        lines = stdout.decode().splitlines()
        assert len(lines) == expected_lines
        observed_threads = [int(line.removeprefix("hello from thread ")) for line in lines]
        assert sorted(observed_threads) == sorted([0, 1, 2, 3] * launches)

        process.stdin.write(b"release\n")
        process.stdin.flush()
        assert process.wait(timeout=10) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
