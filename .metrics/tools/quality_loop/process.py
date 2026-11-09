"""Starting other programs: the one place the wrapper touches subprocess for a command it shows the user."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol

# Exit status of a program that could not be started at all, the shell's own convention.
NOT_STARTED = 127


class Runner(Protocol):
    """Runs one argument vector in a directory and returns its exit status."""

    def __call__(self, argv: Sequence[str], cwd: Path, env: Mapping[str, str] | None = None) -> int: ...


def shown(argv: Sequence[str]) -> str:
    """argv as the user's own shell would spell it."""
    return subprocess.list2cmdline(list(argv)) if os.name == "nt" else shlex.join(argv)


def run_process(argv: Sequence[str], cwd: Path, env: Mapping[str, str] | None = None) -> int:
    """Run argv with the wrapper's own output streams, so the user sees each tool's report as it prints."""
    print(f"+ {shown(argv)}", file=sys.stderr, flush=True)
    try:
        return subprocess.run(list(argv), cwd=cwd, env=None if env is None else dict(env), check=False).returncode
    except OSError as exc:
        print(f"Could not start {argv[0]}: {exc}", file=sys.stderr, flush=True)
        return NOT_STARTED


def tool_environment() -> dict[str, str]:
    """The environment every tool runs in: the user's own, with Python's UTF-8 mode on.

    UTF-8 mode keeps a report that prints a non-ASCII name from failing on a Windows console code page.
    """
    environment = dict(os.environ)
    environment["PYTHONUTF8"] = "1"
    return environment
