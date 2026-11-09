"""Start mutator on Windows with the process-group kill its timeout needs.

mutator stops a mutant that runs past its timeout with `os.killpg(pid, signal.SIGKILL)`. Windows has neither, so
the first infinite loop a mutant causes would end the whole run with an AttributeError. This file runs under
mutator's own environment, adds both names when they are missing, killing the whole process tree with
`taskkill /T /F`, and then starts mutator exactly as `python -m mutator` would. mutator's code is unchanged.
"""

from __future__ import annotations

import os
import runpy
import signal
import subprocess
import sys


def kill_process_tree(pid: int, _signal: int) -> None:
    """End a process and every process it started, the closest Windows has to killing a process group."""
    subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True, check=False)


def add_process_group_kill() -> None:
    """Give os and signal the two names mutator's timeout uses, only where the platform lacks them."""
    if not hasattr(signal, "SIGKILL"):
        signal.SIGKILL = signal.SIGTERM  # type: ignore[attr-defined]
    if not hasattr(os, "killpg"):
        os.killpg = kill_process_tree  # type: ignore[attr-defined]


def main() -> None:
    add_process_group_kill()
    sys.argv[0] = "mutator"
    runpy.run_module("mutator", run_name="__main__", alter_sys=True)


if __name__ == "__main__":
    main()
