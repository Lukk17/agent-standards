#!/usr/bin/env python3
"""Shared preflight gate for every agent surface.

Reads one hook payload as JSON on stdin and decides whether a tool call may
proceed. Two rules:

A. The main thread may not edit source files. It delegates the change to a
   subagent that owns the area.
B. A subagent whose own definition declares no skills may not act. The caller
   spawns a specialist that declares its skills instead.

The output shape is picked with --format:

  claude, codex   PreToolUse JSON on stdout, exit 0
  copilot         flat permission JSON on stdout, exit 0
  plain           reason on stderr, exit 2, for the OpenCode / Kilo plugin shim

Allowing prints nothing and exits 0 in every format. Any parse error, missing
key, or unexpected payload also allows: a broken gate must never break a
session.
"""

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Tuple

EDIT_TOOLS = {
    "edit",
    "write",
    "multiedit",
    "notebookedit",
    "create",
    "update",
    "str_replace_editor",
    "apply_patch",
    "applypatch",
}

SHELL_TOOLS = {"bash", "shell", "powershell", "pwsh", "terminal", "run_command"}

PATH_KEYS = ("file_path", "filePath", "path", "notebook_path", "notebookPath")

COMMAND_KEYS = ("command", "cmd", "script")

NON_SOURCE_SUFFIXES = {
    ".md",
    ".markdown",
    ".txt",
    ".json",
    ".jsonc",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
}

NON_SOURCE_NAMES = {
    ".env.example",
    ".gitignore",
    ".gitattributes",
    "license",
}

CODE_SUFFIXES = {
    ".py",
    ".pyi",
    ".ipynb",
    ".js",
    ".mjs",
    ".cjs",
    ".jsx",
    ".ts",
    ".tsx",
    ".mts",
    ".cts",
    ".vue",
    ".svelte",
    ".java",
    ".kt",
    ".kts",
    ".scala",
    ".groovy",
    ".gradle",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".cs",
    ".fs",
    ".c",
    ".h",
    ".cc",
    ".hh",
    ".cpp",
    ".hpp",
    ".m",
    ".mm",
    ".swift",
    ".dart",
    ".lua",
    ".pl",
    ".r",
    ".sql",
    ".sh",
    ".bash",
    ".zsh",
    ".ps1",
    ".psm1",
    ".psd1",
    ".tf",
    ".proto",
    ".graphql",
    ".gql",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    ".less",
}

AGENT_DIRS = (".claude/agents", ".agents/agents", ".opencode/agents")

REDIRECT_RE = re.compile(r">>?\s*([^\s;|&<>()\"']+)")
TEE_RE = re.compile(r"\btee\b\s+(?:-[a-zA-Z]+\s+)*([^\s;|&<>()\"']+)")
SED_INPLACE_RE = re.compile(r"\bsed\b[^|;&]*?\s-i[^\s]*\s[^|;&]*?([^\s;|&<>()\"']+)\s*$")
HEREDOC_RE = re.compile(r"<<-?\s*['\"]?\w+")
FRONT_MATTER_SKILLS_RE = re.compile(r"^skills:[ \t]*(.*)$")
SKILLS_HEADING_RE = re.compile(r"^#{1,6}[ \t]+.*\bskills\b", re.IGNORECASE)
LIST_ITEM_RE = re.compile(r"^[ \t]*[-*][ \t]+\S")

RULE_A_REASON = (
    "PREFLIGHT: the main thread may not edit source files directly. Delegate this "
    "change to a subagent that owns the area, name the skills it must load, and let "
    "it make the edit. Blocked target: {target}"
)

RULE_B_REASON = (
    "PREFLIGHT: subagent '{agent}' declares no skills in its definition, so it is not "
    "a specialist. Spawn a subagent that declares the skills the task needs and "
    "delegate the work to it."
)


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _tool_name(payload: Dict[str, Any]) -> str:
    for key in ("tool_name", "toolName"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value.strip().lower()
    return ""


def _tool_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    for key in ("tool_input", "toolArgs", "toolInput", "tool_args"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _is_subagent(payload: Dict[str, Any], fmt: str, flag: bool) -> bool:
    if fmt in ("claude", "codex"):
        agent_id = payload.get("agent_id")
        return isinstance(agent_id, str) and bool(agent_id.strip())
    return flag


def _agent_type(payload: Dict[str, Any]) -> str:
    for key in ("agent_type", "agentType", "subagent_type", "agent"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _direct_target(tool_input: Dict[str, Any]) -> str:
    for key in PATH_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _shell_targets(command: str) -> List[str]:
    targets: List[str] = []

    for pattern in (REDIRECT_RE, TEE_RE, SED_INPLACE_RE):
        for match in pattern.finditer(command):
            candidate = match.group(1).strip()
            if candidate:
                targets.append(candidate)

    return targets


def _shell_writes(command: str) -> bool:
    if HEREDOC_RE.search(command):
        return True

    return bool(_shell_targets(command))


def _is_source(target: str) -> bool:
    if not target:
        return False

    path = PurePosixPath(target.replace("\\", "/"))
    name = path.name
    lowered = name.lower()

    if not name:
        return False

    if any(part == "docs" for part in path.parts[:-1]):
        return False

    if lowered in NON_SOURCE_NAMES or lowered.startswith("license."):
        return False

    if lowered.endswith(".env.example"):
        return False

    suffix = path.suffix.lower()

    if suffix in NON_SOURCE_SUFFIXES:
        return False

    return suffix in CODE_SUFFIXES


def _roots() -> List[Path]:
    roots: List[Path] = []

    for candidate in (Path.cwd(), Path(__file__).resolve().parents[2]):
        resolved = candidate.resolve()
        if resolved not in roots:
            roots.append(resolved)

    return roots


def _read_agent_definition(agent_type: str) -> Optional[str]:
    if not agent_type or "/" in agent_type or "\\" in agent_type or ".." in agent_type:
        return None

    for root in _roots():
        for agent_dir in AGENT_DIRS:
            path = root / agent_dir / (agent_type + ".md")
            if path.is_file():
                return path.read_text(encoding="utf-8", errors="replace")

    return None


def _front_matter_end(lines: List[str]) -> int:
    """Index of the closing front-matter marker, or 0 when there is none."""
    if not lines or lines[0].strip() != "---":
        return 0

    for index in range(1, len(lines)):
        if lines[index].strip() in ("---", "..."):
            return index

    return 0


def _front_matter_declares_skills(lines: List[str], end: int) -> bool:
    for index in range(1, end):
        match = FRONT_MATTER_SKILLS_RE.match(lines[index])
        if not match:
            continue

        inline = match.group(1).strip()
        if inline and inline not in ("[]", "~", "null", "''", '""'):
            return True

        for follower in lines[index + 1 : end]:
            stripped = follower.strip()
            if not stripped:
                continue
            if follower[:1] not in (" ", "\t", "-"):
                break
            if stripped.startswith("- ") and stripped[2:].strip():
                return True
            break

        return False

    return False


def _body_declares_skills(lines: List[str], start: int) -> bool:
    """True when a body section headed 'skills' lists at least one entry.

    The generated OpenCode-format definitions carry no front matter key. They
    name their skills under a `## Preloaded skills` heading instead.
    """
    in_section = False

    for line in lines[start:]:
        if line.startswith("#"):
            in_section = bool(SKILLS_HEADING_RE.match(line))
            continue

        if in_section and LIST_ITEM_RE.match(line):
            return True

    return False


def _declares_skills(text: str) -> bool:
    lines = text.splitlines()
    end = _front_matter_end(lines)

    if _front_matter_declares_skills(lines, end):
        return True

    return _body_declares_skills(lines, end + 1 if end else 0)


def _decide(payload: Dict[str, Any], fmt: str, subagent_flag: bool) -> Optional[str]:
    """Return a deny reason, or None to allow."""
    subagent = _is_subagent(payload, fmt, subagent_flag)

    if subagent:
        agent_type = _agent_type(payload)
        definition = _read_agent_definition(agent_type)

        if definition is None:
            return None

        if _declares_skills(definition):
            return None

        return RULE_B_REASON.format(agent=agent_type)

    tool = _tool_name(payload)
    tool_input = _tool_input(payload)

    if tool in EDIT_TOOLS:
        target = _direct_target(tool_input)
        if _is_source(target):
            return RULE_A_REASON.format(target=target)
        return None

    if tool in SHELL_TOOLS:
        command = ""
        for key in COMMAND_KEYS:
            value = tool_input.get(key)
            if isinstance(value, str) and value.strip():
                command = value
                break

        if not command or not _shell_writes(command):
            return None

        for target in _shell_targets(command):
            if _is_source(target):
                return RULE_A_REASON.format(target=target)

    return None


def _emit(reason: str, fmt: str) -> int:
    if fmt in ("claude", "codex"):
        payload = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
        sys.stdout.write(json.dumps(payload))
        return 0

    if fmt == "copilot":
        payload = {"permissionDecision": "deny", "permissionDecisionReason": reason}
        sys.stdout.write(json.dumps(payload))
        return 0

    sys.stderr.write(reason)
    return 2


def _parse_args(argv: Optional[List[str]]) -> Tuple[str, bool]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format",
        required=True,
        choices=("claude", "codex", "copilot", "plain"),
    )
    parser.add_argument("--subagent", action="store_true")
    args, _unknown = parser.parse_known_args(argv)

    return args.format, args.subagent


def main(argv: Optional[List[str]] = None) -> int:
    fmt, subagent_flag = _parse_args(argv)

    try:
        payload = _as_dict(json.loads(sys.stdin.read() or "{}"))
        reason = _decide(payload, fmt, subagent_flag)
    except Exception:
        return 0

    if not reason:
        return 0

    try:
        return _emit(reason, fmt)
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main())
