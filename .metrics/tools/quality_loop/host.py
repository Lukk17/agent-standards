"""What differs between Windows and the POSIX systems for the wrapper: paths, shells and executables."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Host:
    """The operating system the wrapper runs on, passed around so tests can pick either one."""

    windows: bool

    @classmethod
    def current(cls) -> Host:
        return cls(windows=os.name == "nt")

    def venv_python(self, venv: Path) -> Path:
        """The interpreter inside a virtual environment, `Scripts\\python.exe` on Windows."""
        if self.windows:
            return venv / "Scripts" / "python.exe"
        return venv / "bin" / "python"

    def join(self, argv: Sequence[str]) -> str:
        """One command line for a tool's `--coverage-command` or `--test-command`.

        The tools run that string in a shell: cmd.exe on Windows, /bin/sh elsewhere,
        so each one gets the quoting its own shell reads.
        """
        if self.windows:
            return subprocess.list2cmdline(list(argv))
        return shlex.join(argv)

    def then(self, *commands: str) -> str:
        """Commands that run one after another whatever each one returns, ending with the last one's status."""
        return (" & " if self.windows else " ; ").join(commands)

    def which(self, name: str) -> str | None:
        """The full path of an executable on PATH, which finds `npm.cmd` for `npm` on Windows."""
        return shutil.which(name)
