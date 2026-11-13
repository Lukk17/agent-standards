#!/usr/bin/env python3
"""Lints a markdown file the model just wrote and reports the violations back.

The repository markdown rules (no em-dash or en-dash, no level-2 heading, no
skill linking outside its own folder) live in .agents/hooks/markdown-lint-check/_check_markdown.py
beside this hook, and CI runs them over the whole target set through
tools/check-markdown.py. That is the second opinion rather than the first: by
the time it fails, the edit is already committed and pushed. This hook closes
the loop at the moment of the edit instead, so a violation comes back while
the file is still open.

It applies to one surface only. `--format claude` after Edit, Write or
MultiEdit is the whole of it, and every other invocation returns 0 before
reading anything: `--format plain` is the runner contract, whose only event is
`tool.execute.before`, where the file has not been edited yet and whose runner
throws away anything written to stderr unless the hook exits 2. The rules
module is looked up beside this hook first, where every import of
.agents/hooks and the hook-markdown-lint-check plugin both put it, then under
the project root, and a copy that finds neither is silent rather than
spawning a process on every edit to learn that.

It reads the edited path out of
`tool_input.file_path` (documented at https://code.claude.com/docs/en/hooks-guide
as `jq -r '.tool_input.file_path'` on a PostToolUse hook matching `Edit|Write`),
falls back to the first `file_path` inside `tool_input.edits` for a batched
shape, and stays silent unless that path is inside the lint scope:

    README.md, AGENTS.md.example, .metrics/tools/README.md, docs/, .agents/skills/, subagents/

The vendored tools beside .metrics/tools/README.md keep their author's style
and stay out of scope.

Paths are resolved against the project root before the comparison, and matched
case-insensitively on Windows only, where the filesystem is.

The one output shape prints the violations as `additionalContext` under
`hookSpecificOutput`. It never blocks: this hook reports, and the model
decides.

Another tool, a file out of scope, a clean file, a missing rules module, or any
error at all: exit 0 with nothing printed. A broken hook must never break a
session.
"""

import json
import os
import re
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

LINT_RULES_NAME = "_check_markdown.py"

LINT_SCRIPT = (".agents", "hooks", "markdown-lint-check", LINT_RULES_NAME)

LINT_TIMEOUT_SECONDS = 10

SCOPED_FILES = ("README.md", "AGENTS.md.example", ".metrics/tools/README.md")

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


def _project_root(payload: Dict[str, Any]) -> Path:
    """The session's project, never the folder this copy is installed in.

    Claude Code names the project in CLAUDE_PROJECT_DIR, and the payload names
    the session's directory in `cwd`. Without either, the working directory is
    trusted once it holds the hooks directory that proves it is a project root,
    and then the project this copy sits in, three folders up from
    .agents/hooks/markdown-lint-check/. A plugin copy in the Claude Code plugin
    cache has no such project, so it falls back to the working directory.
    """
    named = os.environ.get(PROJECT_DIR_VARIABLE) or payload.get("cwd")

    if isinstance(named, str) and named and Path(named).is_dir():
        return Path(named).resolve()

    cwd = Path.cwd().resolve()
    script = Path(__file__).resolve()

    if (cwd / ".agents" / "hooks").is_dir() or script.parents[2].name != ".agents":
        return cwd

    return script.parents[3]


def _lint_script(root: Path) -> Path:
    """The rules module: the one beside this hook, which a plugin copy carries, else the project's own."""
    beside = Path(__file__).resolve().parent / LINT_RULES_NAME

    return beside if beside.is_file() else root.joinpath(*LINT_SCRIPT)


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


# A plugin copy of this hook stands down when the project's own Claude Code
# wiring already runs this same script for the same call, so one call never
# runs it twice. Claude Code exports CLAUDE_PLUGIN_ROOT and CLAUDE_PROJECT_DIR
# to a hook's process (https://code.claude.com/docs/en/hooks, "Reference
# scripts by path"). It stands down only on the claude format, only as a copy
# installed in the Claude Code plugin cache under CLAUDE_CONFIG_DIR or
# ~/.claude, only on a payload that names its event, for a wiring group of
# that event whose matcher takes the call's tool, and for a synchronous
# command hook that runs a script of the same name under the project's own
# .agents/hooks/ that exists and is not this very file. Anything else, or any
# doubt, runs the hook. The preflight gate never stands down: running it twice
# only repeats a deny. tools/tests/test_plugin_copy.py holds this block equal
# in every hook that carries it.
PLUGIN_ROOT_VARIABLE = "CLAUDE_PLUGIN_ROOT"
PROJECT_DIR_VARIABLE = "CLAUDE_PROJECT_DIR"
CONFIG_DIR_VARIABLE = "CLAUDE_CONFIG_DIR"
CLAUDE_HOME = ".claude"
PLUGIN_CACHE = ("plugins", "cache")
PROJECT_CLAUDE_WIRING = (".claude", "settings.json")
PROJECT_HOOK_PATH = r"\.agents/hooks/(?:[a-z0-9-]+/)*"
TOOL_EVENTS = frozenset({"PreToolUse", "PostToolUse", "PostToolUseFailure", "PermissionRequest"})
MATCH_ALL = (None, "", "*")
GUARDED_FORMAT = "claude"


def _plugin_caches() -> list:
    """The Claude Code plugin cache under CLAUDE_CONFIG_DIR, when set, and under ~/.claude."""
    caches = []

    for base in (os.environ.get(CONFIG_DIR_VARIABLE, ""), "~/" + CLAUDE_HOME):
        try:
            if base:
                caches.append(Path(base).expanduser().resolve().joinpath(*PLUGIN_CACHE))
        except (OSError, RuntimeError, ValueError, KeyError):
            continue

    return caches


def _project_runs_this_script(project: Path, command: str, script: Path) -> bool:
    """True when the command runs a copy of this script from the project's .agents/hooks/ other than this file."""
    for match in re.finditer(PROJECT_HOOK_PATH + re.escape(script.name) + r"(?![A-Za-z0-9_.])", command):
        own = project.joinpath(*match.group(0).split("/"))

        if own.is_file() and own.resolve() != script:
            return True

    return False


def _matcher_takes(group: object, event: str, tool: object) -> bool:
    """True when a wiring group of a tool event matches the call's tool, as Claude Code matches it."""
    if event not in TOOL_EVENTS:
        return True

    matcher = group.get("matcher") if isinstance(group, dict) else None

    if matcher in MATCH_ALL:
        return True

    try:
        return isinstance(tool, str) and re.fullmatch(str(matcher), tool) is not None
    except re.error:
        return False


def _plugin_copy_is_shadowed(payload: object, fmt: str) -> bool:
    """True when this copy runs from the Claude Code plugin cache and the project's own wiring runs it for this call."""
    try:
        plugin_root = os.environ.get(PLUGIN_ROOT_VARIABLE, "")
        script = Path(__file__).resolve()

        if fmt != GUARDED_FORMAT or not plugin_root:
            return False

        installed = Path(plugin_root).resolve()

        if not script.is_relative_to(installed) or not any(installed.is_relative_to(cache) for cache in _plugin_caches()):
            return False

        fields = payload if isinstance(payload, dict) else {}
        event = fields.get("hook_event_name")
        project = os.environ.get(PROJECT_DIR_VARIABLE) or fields.get("cwd")

        if not isinstance(event, str) or not event or not isinstance(project, str) or not project:
            return False

        root = Path(project)
        settings = json.loads(root.joinpath(*PROJECT_CLAUDE_WIRING).read_text(encoding="utf-8"))

        for group in settings["hooks"].get(event, []):
            if not _matcher_takes(group, event, fields.get("tool_name")):
                continue

            for entry in group["hooks"]:
                if entry.get("type") != "command" or entry.get("async"):
                    continue

                if _project_runs_this_script(root, str(entry.get("command", "")), script):
                    return True
    except Exception:
        return False

    return False


def main(argv: List[str]) -> int:
    try:
        if _flag(argv, "--format").lower() != CLAUDE_FORMAT:
            return 0

        payload = json.loads(_stdin_text() or "{}")

        if not isinstance(payload, dict) or _plugin_copy_is_shadowed(payload, CLAUDE_FORMAT):
            return 0

        if _tool_name(payload) not in EDIT_TOOLS:
            return 0

        root = _project_root(payload)
        script = _lint_script(root)

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
