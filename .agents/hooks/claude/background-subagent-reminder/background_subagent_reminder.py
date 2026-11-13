#!/usr/bin/env python3
"""Prints the background-subagent supervision note on Claude Code's SessionStart.

Claude Code adds a SessionStart, UserPromptSubmit or SubagentStart hook's
stdout to the context, so printing the text is the whole hook. It used to be a
bare echo in .claude/settings.json, and a script of its own lets the
marketplace ship it as its own hook plugin. The output is byte for byte what
that echo printed: the text and one newline.

Every outcome exits 0, and a payload that cannot be read still prints the
text, so a broken hook never costs a session its reminder.
"""

import json
import os
import re
import sys
from pathlib import Path

SUPERVISION_TEXT = (
    "When you launch a background subagent, note how long its task should take and schedule a recurring "
    "check every 10 minutes while any subagent runs. At each check compare its running time and "
    "latest output with that expectation. Leave it alone unless it is far over (for example 30 minutes "
    "on a task that should take 1) or clearly looping, then ask it for status or stop it and tell "
    "the user why."
)


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


def main() -> int:
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace") or "{}")
    except Exception:
        payload = {}

    if _plugin_copy_is_shadowed(payload, GUARDED_FORMAT):
        return 0

    sys.stdout.buffer.write((SUPERVISION_TEXT + "\n").encode("utf-8"))
    sys.stdout.flush()

    return 0


if __name__ == "__main__":
    sys.exit(main())
