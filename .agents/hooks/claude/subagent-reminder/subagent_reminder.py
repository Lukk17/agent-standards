#!/usr/bin/env python3
"""Prints the subagent reminder on Claude Code's SubagentStart, as hookSpecificOutput.

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

SUBAGENT_TEXT = (
    "PREFLIGHT for a subagent: you are a subagent, and the main thread delegated this task to you. "
    "Do the work yourself with your own tools and load the skills your definition names. "
    "The rules that the main thread must delegate and may not write files apply to the main thread "
    "only, so do not hand this task on and do not refuse it for that reason. "
    "The preflight gate still checks every tool call you make. Report back what you changed and "
    "how you verified it."
)


# A plugin copy of this hook stands down when the project's own Claude Code
# wiring already runs this same script for the same call, so one call never
# runs it twice. Claude Code exports CLAUDE_PLUGIN_ROOT and CLAUDE_PROJECT_DIR
# to a hook's process (https://code.claude.com/docs/en/hooks, "Reference
# scripts by path"). It stands down only on a payload that names its event,
# for a wiring group of that event whose matcher takes the call's tool, and
# for a command that runs a script of the same name under the project's own
# .agents/hooks/ that exists. Anything else, or any doubt, runs the hook.
# tools/tests/test_plugin_copy.py holds this block equal in every hook that
# carries it.
PLUGIN_ROOT_VARIABLE = "CLAUDE_PLUGIN_ROOT"
PROJECT_DIR_VARIABLE = "CLAUDE_PROJECT_DIR"
PROJECT_CLAUDE_WIRING = (".claude", "settings.json")
PROJECT_HOOK_PATH = r"\.agents/hooks/(?:[a-z0-9-]+/)*"
TOOL_EVENTS = frozenset({"PreToolUse", "PostToolUse", "PostToolUseFailure", "PermissionRequest"})
MATCH_ALL = (None, "", "*")


def _project_runs_this_script(project: Path, command: str, script: str) -> bool:
    """True when the command runs this script from the project's .agents/hooks/ and that file exists."""
    for match in re.finditer(PROJECT_HOOK_PATH + re.escape(script) + r"(?![A-Za-z0-9_.])", command):
        if project.joinpath(*match.group(0).split("/")).is_file():
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


def _plugin_copy_is_shadowed(payload: object) -> bool:
    """True when this copy runs as a Claude Code plugin and the project's own wiring runs it for this call."""
    try:
        plugin_root = os.environ.get(PLUGIN_ROOT_VARIABLE, "")
        script = Path(__file__).resolve()

        if not plugin_root or not script.is_relative_to(Path(plugin_root).resolve()):
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
                if _project_runs_this_script(root, str(entry.get("command", "")), script.name):
                    return True
    except Exception:
        return False

    return False


def main() -> int:
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace") or "{}")
    except Exception:
        payload = {}

    if _plugin_copy_is_shadowed(payload):
        return 0

    sys.stdout.buffer.write((json.dumps({"hookSpecificOutput": {"hookEventName": "SubagentStart", "additionalContext": SUBAGENT_TEXT}}) + "\n").encode("utf-8"))
    sys.stdout.flush()

    return 0


if __name__ == "__main__":
    sys.exit(main())
