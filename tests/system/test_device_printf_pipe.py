# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 FlyDSL Project Contributors

"""Regression for device printf visibility through a pipe."""

import os
import selectors
import subprocess
import sys

_CHILD_FLAG = "--device-printf-pipe-child"


def _run_child() -> None:
    import torch

    import flydsl.compiler as flyc
    import flydsl.expr as fx
    from flydsl.runtime import flush_device_printf

    @flyc.kernel
    def hello_kernel():
        tid = fx.thread_idx.x
        fx.printf("hello from thread {}", tid)

    @flyc.jit
    def hello(stream: fx.Stream = fx.Stream(None)):
        hello_kernel().launch(grid=(1, 1, 1), block=(4, 1, 1), stream=stream)

    hello()
    torch.cuda.synchronize()
    flush_device_printf()
    os.write(2, b"READY\n")
    if sys.stdin.buffer.readline() != b"release\n":
        raise RuntimeError("parent closed the control pipe before observing output")


if _CHILD_FLAG in sys.argv:
    _run_child()
    raise SystemExit(0)


def test_device_printf_visible_in_pipe_before_process_exit():
    """A synchronized and flushed four-thread printf is readable while the child lives."""
    process = subprocess.Popen(
        [sys.executable, __file__, _CHILD_FLAG],
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
        while not ready or stdout.count(b"hello from thread ") < 4:
            events = selector.select(timeout=30)
            assert events, "timed out waiting for synchronized device printf output"
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
        assert len(lines) == 4
        observed_threads = {int(line.removeprefix("hello from thread ")) for line in lines}
        assert observed_threads == {0, 1, 2, 3}

        process.stdin.write(b"release\n")
        process.stdin.flush()
        assert process.wait(timeout=10) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
