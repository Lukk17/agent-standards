"""Tests for run_bounded, the one way every test in this suite starts a child process.

A plain subprocess.run with a timeout kills only the direct child and then
waits, with no bound at all, for the pipes to close. A grandchild still holding
them keeps that wait open forever, so these tests drive exactly that tree.
"""

import ctypes
import os
import subprocess
import sys
import time

import pytest

from tests.process_tree import run_bounded

TIMEOUT_SECONDS = 1
RETURN_BOUND_SECONDS = 15
GRANDCHILD_SLEEP_SECONDS = 120
REAP_WAIT_SECONDS = 5

LEAVES_A_GRANDCHILD_ON_THE_PIPE = f"""
import subprocess, sys
grandchild = subprocess.Popen([sys.executable, "-c", "import time; time.sleep({GRANDCHILD_SLEEP_SECONDS})"])
print(grandchild.pid, flush=True)
"""


def is_running(pid: int) -> bool:
    if sys.platform == "win32":
        synchronize, wait_object_0 = 0x00100000, 0
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.restype = ctypes.c_void_p
        handle = kernel32.OpenProcess(synchronize, False, pid)

        if not handle:
            return False

        try:
            return kernel32.WaitForSingleObject(ctypes.c_void_p(handle), 0) != wait_object_0
        finally:
            kernel32.CloseHandle(ctypes.c_void_p(handle))

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False

    return True


def eventually_gone(pid: int) -> bool:
    deadline = time.monotonic() + REAP_WAIT_SECONDS

    while is_running(pid):
        if time.monotonic() > deadline:
            return False

        time.sleep(0.1)

    return True


def test_a_finished_child_returns_its_code_and_output():
    # When
    result = run_bounded(
        [sys.executable, "-c", "import sys; print(sys.stdin.read().upper()); sys.exit(3)"],
        input="hello",
        capture_output=True,
        text=True,
    )

    # Then
    assert (result.returncode, result.stdout.strip()) == (3, "HELLO")


def test_check_raises_on_a_non_zero_exit():
    with pytest.raises(subprocess.CalledProcessError):
        run_bounded([sys.executable, "-c", "raise SystemExit(1)"], capture_output=True, check=True)


def test_a_grandchild_holding_the_pipe_is_killed_and_the_call_returns_within_the_bound():
    # Given a child that exits at once and leaves a grandchild holding its stdout
    started = time.monotonic()

    # When
    with pytest.raises(subprocess.TimeoutExpired) as timed_out:
        run_bounded(
            [sys.executable, "-c", LEAVES_A_GRANDCHILD_ON_THE_PIPE],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )

    elapsed = time.monotonic() - started

    # Then the call came back long before the grandchild would have let go
    assert elapsed < RETURN_BOUND_SECONDS

    # And the grandchild the child reported is gone, not orphaned
    grandchild = int(timed_out.value.output.split()[0])
    assert eventually_gone(grandchild)
