"""The Python environment of each tool, built by the wrapper rather than by the tools' POSIX `sh` launchers.

Each tool gets `<tool>/.venv`, created with the Python running the wrapper and installed editable with the pinned
`constraints.txt`. A stamp file records what the environment was built from, so a newer Python, a changed
constraint or a newer copy of the tool rebuilds it, and an unchanged one is reused.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

from quality_loop.host import Host
from quality_loop.process import Runner

TOOLS = ("crapper", "dryer", "mutator")
STAMP_NAME = "quality-loop.json"
CONSTRAINTS_NAME = "constraints.txt"

PIP = ("-m", "pip", "install", "--disable-pip-version-check", "--quiet")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_stamp(tool_dir: Path, constraints: Path) -> dict[str, str]:
    """What a ready environment was built from."""
    return {
        "python": sys.version,
        "constraints": _digest(constraints),
        "pyproject": _digest(tool_dir / "pyproject.toml"),
    }


def read_stamp(venv: Path) -> dict[str, str] | None:
    try:
        data = json.loads((venv / STAMP_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def build_steps(tool_dir: Path, python: Path, constraints: Path) -> list[list[str]]:
    """The commands that create one tool environment, in order.

    setuptools is installed first and the tool without build isolation, so the build backend is pinned too.
    """
    venv = tool_dir / ".venv"
    return [
        [sys.executable, "-m", "venv", str(venv)],
        [str(python), *PIP, "-c", str(constraints), "setuptools"],
        [str(python), *PIP, "--no-build-isolation", "-c", str(constraints), "-e", str(tool_dir)],
    ]


def tool_python(
    tools_dir: Path,
    tool: str,
    host: Host,
    run: Runner,
    say: Callable[[str], None],
) -> Path | None:
    """The interpreter of one tool's environment, building or rebuilding the environment when it is not ready.

    Returns:
        The interpreter path, or None when a build step failed, which `say` has already explained.
    """
    tool_dir = tools_dir / tool
    venv = tool_dir / ".venv"
    python = host.venv_python(venv)
    constraints = tools_dir / CONSTRAINTS_NAME
    expected = expected_stamp(tool_dir, constraints)
    if python.is_file() and read_stamp(venv) == expected:
        return python
    say(f"Building the {tool} environment in {venv}.")
    if venv.exists():
        shutil.rmtree(venv)
    for argv in build_steps(tool_dir, python, constraints):
        if run(argv, tool_dir) != 0:
            say(f"Could not build the {tool} environment. The command above failed. It needs network access to PyPI.")
            return None
    (venv / STAMP_NAME).write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    return python
