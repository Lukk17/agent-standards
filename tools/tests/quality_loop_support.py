"""Shared helpers for the quality loop wrapper tests.

The wrapper ships as the `quality_loop` package under `.metrics/tools`, so the tests put that folder on the import
path once here. RecordingRunner stands in for `process.run_process`: it records every command instead of starting
it, and lets a test decide each exit status and any file the command would have written.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from tests.conftest import REPO_ROOT

QUALITY_TOOLS = REPO_ROOT / ".metrics" / "tools"

if str(QUALITY_TOOLS) not in sys.path:
    sys.path.insert(0, str(QUALITY_TOOLS))

Respond = Callable[[list[str], Path], int]


class RecordingRunner:
    """Records each command and answers with what `respond` returns, 0 by default."""

    def __init__(self, respond: Respond | None = None) -> None:
        self.calls: list[tuple[list[str], Path]] = []
        self.respond = respond

    def __call__(self, argv: Sequence[str], cwd: Path, env: Mapping[str, str] | None = None) -> int:
        command = [str(part) for part in argv]
        self.calls.append((command, Path(cwd)))
        return self.respond(command, Path(cwd)) if self.respond else 0

    @property
    def commands(self) -> list[list[str]]:
        return [command for command, _cwd in self.calls]

    def tool_runs(self, tool: str) -> list[list[str]]:
        """The argument lists one tool was started with, everything after `--root <path>`."""
        runs = []
        for command in self.commands:
            if "--root" in command and (tool in command or any(part.endswith(f"{tool}_windows.py") for part in command)):
                runs.append(command[command.index("--root") + 2 :])
        return runs


def write(root: Path, relative: str, text: str = "") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
