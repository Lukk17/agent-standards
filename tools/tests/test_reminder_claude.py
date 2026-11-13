"""Claude Code reminder wiring tests.

The project's .claude/settings.json runs one script per reminder, each in its
own folder under .agents/hooks/claude/, so the marketplace can ship each as a
hook plugin. Each script holds its text as a constant, which is the canonical
copy, and prints exactly what the bare echo it replaced printed: the text and
one newline.
"""
import json
import os
from pathlib import Path

import pytest

from tests.conftest import BACKGROUND_SUBAGENT_REMINDER_HOOK, PREFLIGHT_REMINDER_HOOK, REPO_ROOT, SUBAGENT_REMINDER_HOOK
from tests.process_tree import run_bounded
from tests.reminder_support import (
    CLAUDE_REMINDER,
    MARKER,
    SUBAGENT_MARKER,
    _load_module,
    canonical_background_subagent_reminder,
    canonical_subagent_reminder,
    delivered_text,
    posix_shell,
)

SETTINGS = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))

SUBAGENT_JSON = json.dumps({"hookSpecificOutput": {"hookEventName": "SubagentStart", "additionalContext": canonical_subagent_reminder()}})

WIRED = [
    ("SessionStart", PREFLIGHT_REMINDER_HOOK, CLAUDE_REMINDER),
    ("SessionStart", BACKGROUND_SUBAGENT_REMINDER_HOOK, canonical_background_subagent_reminder()),
    ("UserPromptSubmit", PREFLIGHT_REMINDER_HOOK, CLAUDE_REMINDER),
    ("SubagentStart", SUBAGENT_REMINDER_HOOK, SUBAGENT_JSON),
]


def commands(event: str) -> list[str]:
    return [hook["command"] for group in SETTINGS["hooks"][event] for hook in group["hooks"]]


def wired_command(event: str, script: Path) -> str:
    relative = script.relative_to(REPO_ROOT).as_posix()
    found = [command for command in commands(event) if relative in command]
    assert len(found) == 1, (event, relative, commands(event))
    return found[0]


def test_the_claude_wiring_prints_no_reminder_literal_any_more():
    every = [command for event in SETTINGS["hooks"] for command in commands(event)]

    assert not [command for command in every if MARKER in command or "PREFLIGHT" in command or command.startswith("echo")]


def test_session_start_runs_the_preflight_and_the_background_reminders_before_the_task_list():
    order = ["preflight_reminder.py", "background_subagent_reminder.py", "task_list_sync.py"]

    assert [next(name for name in order if name in command) for command in commands("SessionStart")] == order


def test_the_preflight_script_holds_the_canonical_claude_text():
    assert _load_module("preflight_reminder_check", PREFLIGHT_REMINDER_HOOK).REMINDER == CLAUDE_REMINDER


def test_the_subagent_text_never_carries_the_delegating_reminder():
    text = canonical_subagent_reminder()

    assert text.startswith(SUBAGENT_MARKER) and MARKER not in text and "Delegate" not in text


@pytest.mark.parametrize(("event", "script", "expected"), WIRED, ids=[f"{e}-{s.stem}" for e, s, _x in WIRED])
def test_every_wired_reminder_prints_byte_for_byte_what_its_echo_printed(tmp_path, event, script, expected):
    shell = posix_shell()
    if shell is None:
        pytest.skip("no POSIX shell is installed")
    environment = {key: value for key, value in os.environ.items() if key != "CLAUDE_PLUGIN_ROOT"}
    environment["CLAUDE_PROJECT_DIR"] = str(REPO_ROOT)

    result = run_bounded(
        [shell, "-c", wired_command(event, script)],
        input=json.dumps({"hook_event_name": event, "cwd": str(REPO_ROOT)}).encode("utf-8"),
        capture_output=True,
        env=environment,
        cwd=tmp_path,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == (expected + "\n").encode("utf-8")


def test_the_subagent_reminder_hands_claude_code_the_canonical_context():
    assert delivered_text(SUBAGENT_JSON) == canonical_subagent_reminder()
