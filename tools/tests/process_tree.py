"""run_bounded: subprocess.run for this suite, with a timeout that covers the whole process tree.

subprocess.run kills only the direct child when its timeout fires, then calls
communicate() again with no timeout. A grandchild still holding the pipes
(a hook the node driver spawned, or pwsh running a hook) keeps that second
wait open forever. run_bounded starts the child in its own process group, and
on Windows inside a job object as well, kills the whole tree on timeout, and
collects the remaining output with a bounded wait.
"""

import os
import signal
import subprocess
import sys

from tests.conftest import SUBPROCESS_TIMEOUT_SECONDS

DRAIN_SECONDS = 10


class _WindowsJob:
    """A job object that owns the child and every process it starts."""

    _EXTENDED_LIMIT_INFORMATION = 9
    _KILL_ON_JOB_CLOSE = 0x2000

    def __init__(self) -> None:
        import ctypes
        from ctypes import wintypes

        class IoCounters(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in ("r", "w", "o", "rb", "wb", "ob")]

        class BasicLimits(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class ExtendedLimits(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", BasicLimits),
                ("IoInfo", IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        self._kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self._kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        self._kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self._kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self._kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

        self._handle = self._kernel32.CreateJobObjectW(None, None)

        if not self._handle:
            raise ctypes.WinError(ctypes.get_last_error())

        limits = ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = self._KILL_ON_JOB_CLOSE
        configured = self._kernel32.SetInformationJobObject(
            self._handle, self._EXTENDED_LIMIT_INFORMATION, ctypes.byref(limits), ctypes.sizeof(limits)
        )

        if not configured:
            error = ctypes.WinError(ctypes.get_last_error())
            self.close()
            raise error

    def assign(self, process: subprocess.Popen) -> bool:
        return bool(self._kernel32.AssignProcessToJobObject(self._handle, int(process._handle)))

    def terminate(self) -> None:
        self._kernel32.TerminateJobObject(self._handle, 1)

    def close(self) -> None:
        if self._handle:
            self._kernel32.CloseHandle(self._handle)
            self._handle = None


def _kill_tree(process: subprocess.Popen, job: _WindowsJob | None) -> None:
    if sys.platform == "win32":
        if job is not None:
            job.terminate()

        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(process.pid)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=DRAIN_SECONDS,
            check=False,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    process.kill()


def run_bounded(
    args,
    *,
    input=None,
    capture_output: bool = False,
    timeout: float = SUBPROCESS_TIMEOUT_SECONDS,
    check: bool = False,
    **popen_kwargs,
) -> subprocess.CompletedProcess:
    """Run a command like subprocess.run, and on timeout kill every process it started.

    stdin defaults to the null device when no input is given, so a child can
    never block reading the terminal.

    Raises:
        subprocess.TimeoutExpired: when the tree is still running after timeout, carrying the output collected.
        subprocess.CalledProcessError: when check is set and the exit code is not zero.
    """
    if capture_output:
        popen_kwargs["stdout"] = subprocess.PIPE
        popen_kwargs["stderr"] = subprocess.PIPE

    if input is not None:
        popen_kwargs["stdin"] = subprocess.PIPE
    else:
        popen_kwargs.setdefault("stdin", subprocess.DEVNULL)

    job = None

    if sys.platform == "win32":
        popen_kwargs["creationflags"] = popen_kwargs.get("creationflags", 0) | subprocess.CREATE_NEW_PROCESS_GROUP
        job = _WindowsJob()
    else:
        popen_kwargs["start_new_session"] = True

    try:
        process = subprocess.Popen(args, **popen_kwargs)

        if job is not None and not job.assign(process):
            job.close()
            job = None

        try:
            stdout, stderr = process.communicate(input, timeout=timeout)
        except subprocess.TimeoutExpired:
            _kill_tree(process, job)

            try:
                stdout, stderr = process.communicate(timeout=DRAIN_SECONDS)
            except subprocess.TimeoutExpired:
                stdout, stderr = None, None

            raise subprocess.TimeoutExpired(process.args, timeout, output=stdout, stderr=stderr) from None
        except BaseException:
            _kill_tree(process, job)
            raise
    finally:
        if job is not None:
            job.close()

    result = subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)

    if check:
        result.check_returncode()

    return result
