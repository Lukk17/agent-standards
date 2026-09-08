#!/usr/bin/env python3
"""Lints a markdown file the model just wrote and reports the violations back.

The repository markdown rules (no em-dash or en-dash, no prose line over 120
characters, no level-2 heading) are enforced by tools/check-markdown.py, which
CI runs over the whole target set. That is the second opinion rather than the
first: by the time it fails, the edit is already committed and pushed. This
hook closes the loop at the moment of the edit instead, so a violation comes
back while the file is still open.

It applies to one surface only. `--format claude` after Edit, Write or
MultiEdit is the whole of it, and every other invocation returns 0 before
reading anything: `--format plain` is the runner contract, whose only event is
`tool.execute.before`, where the file has not been edited yet and whose runner
throws away anything written to stderr unless the hook exits 2. The lint
script is checked for before the report is prepared as well, because a
consumer repository pulls the hooks without tools/check-markdown.py and the
hook would otherwise spawn a process on every edit to learn that.

It reads the edited path out of
`tool_input.file_path` (documented at https://code.claude.com/docs/en/hooks-guide
as `jq -r '.tool_input.file_path'` on a PostToolUse hook matching `Edit|Write`),
falls back to the first `file_path` inside `tool_input.edits` for a batched
shape, and stays silent unless that path is inside the lint scope:

    README.md, AGENTS.md.example, docs/, .agents/skills/, subagents/

Paths are resolved against the project root before the comparison, and matched
case-insensitively on Windows only, where the filesystem is.

The one output shape prints the violations as `additionalContext` under
`hookSpecificOutput`. It never blocks: this hook reports, and the model
decides.

Another tool, a file out of scope, a clean file, a missing lint script, or any
error at all: exit 0 with nothing printed. A broken hook must never break a
session.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

# Runner order. After the gate, the formatting check, and the task list, none
# of which this one has anything to say about.
HOOK_ORDER = 40

CLAUDE_FORMAT = "claude"

EVENT_NAME = "PostToolUse"

EDIT_TOOLS = ("edit", "write", "multiedit")

LINT_SCRIPT = ("tools", "check-markdown.py")

LINT_TIMEOUT_SECONDS = 10

SCOPED_FILES = ("README.md", "AGENTS.md.example")

SCOPED_DIRECTORIES = ("docs/", ".agents/skills/", "subagents/")


def _stdin_text() -> str:
    """Decode stdin as UTF-8 explicitly, never through the system code page."""
    return sys.stdin.buffer.read().decode("utf-8", errors="replace")


def _flag(argv: List[str], name: str) -> str:
    """Read one --flag value by hand.

    argparse exits 2 on a usage error and 2 is the deny code in the runner
    contract, so no hook in this directory may use it.
    """
    for index, token in enumerate(argv):
        if token == name and index + 1 < len(argv):
            return argv[index + 1]

        if token.startswith(name + "="):
            return token.split("=", 1)[1]

    return ""


def _project_root() -> Path:
    """The repository root.

    Every wiring moves there before invoking a hook, so the working directory
    is the contract. It is trusted only once it holds the hooks directory that
    proves it is a project root, because that guarantee has broken silently
    before (see AGENTS.md "Required opening move"). The hook's own location two
    parents up is the fallback.
    """
    cwd = Path.cwd().resolve()
    anchored = Path(__file__).resolve().parents[2]

    return cwd if (cwd / ".agents" / "hooks").is_dir() else anchored


def _tool_name(payload: Dict[str, Any]) -> str:
    name = payload.get("tool_name")

    return name.strip().lower() if isinstance(name, str) else ""


def _file_path(payload: Dict[str, Any]) -> str:
    """The edited path, from `tool_input.file_path` or a batched edit entry."""
    tool_input = payload.get("tool_input")

    if not isinstance(tool_input, dict):
        return ""

    direct = tool_input.get("file_path")

    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    edits = tool_input.get("edits")

    if not isinstance(edits, list):
        return ""

    for edit in edits:
        if not isinstance(edit, dict):
            continue

        nested = edit.get("file_path")

        if isinstance(nested, str) and nested.strip():
            return nested.strip()

    return ""


def _comparable(value: str) -> str:
    return value.lower() if os.name == "nt" else value


def _relative(path: str, root: Path) -> str:
    """The path relative to the root in posix form, empty when it escapes it."""
    if not path:
        return ""

    try:
        relative = Path(os.path.relpath(Path(path).resolve(), root)).as_posix()
    except (OSError, ValueError):
        return ""

    return "" if relative == ".." or relative.startswith("../") else relative


def _in_scope(relative: str) -> str:
    if not relative:
        return ""

    candidate = _comparable(relative)

    if candidate in tuple(_comparable(name) for name in SCOPED_FILES):
        return relative

    for directory in SCOPED_DIRECTORIES:
        if candidate.startswith(_comparable(directory)):
            return relative

    return ""


def _violations(script: Path, relative: str, root: Path) -> str:
    """Run the repository lint over one file and return what it reported."""
    result = subprocess.run(
        [sys.executable, "-S", "-E", str(script), relative],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(root),
        timeout=LINT_TIMEOUT_SECONDS,
    )

    if result.returncode == 0:
        return ""

    return (result.stdout or "").strip()


def _report(violations: str) -> int:
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": EVENT_NAME,
                    "additionalContext": violations,
                }
            }
        )
    )

    return 0


def main(argv: List[str]) -> int:
    try:
        if _flag(argv, "--format").lower() != CLAUDE_FORMAT:
            return 0

        payload = json.loads(_stdin_text() or "{}")

        if not isinstance(payload, dict):
            return 0

        if _tool_name(payload) not in EDIT_TOOLS:
            return 0

        root = _project_root()
        script = root.joinpath(*LINT_SCRIPT)

        if not script.is_file():
            return 0

        relative = _in_scope(_relative(_file_path(payload), root))

        if not relative:
            return 0

        violations = _violations(script, relative, root)

        if not violations:
            return 0

        return _report(violations)
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
