"""Claude Code reminder wiring tests.

Each reminder is one script in its own folder under .agents/hooks/claude/,
shipped as a hook plugin of the marketplace, and the project's
.claude/settings.json switches those plugins on instead of wiring the scripts
itself. Each script holds its text as a constant, which is the canonical copy,
and prints exactly what the bare echo it replaced printed: the text and one
newline.
"""
import json
import os
from pathlib import Path

import pytest

from tests import claude_wiring_support as wiring
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

SUBAGENT_JSON = json.dumps({"hookSpecificOutput": {"hookEventName": "SubagentStart", "additionalContext": canonical_subagent_reminder()}})

WIRED = [
    ("SessionStart", PREFLIGHT_REMINDER_HOOK, CLAUDE_REMINDER),
    ("SessionStart", BACKGROUND_SUBAGENT_REMINDER_HOOK, canonical_background_subagent_reminder()),
    ("UserPromptSubmit", PREFLIGHT_REMINDER_HOOK, CLAUDE_REMINDER),
    ("SubagentStart", SUBAGENT_REMINDER_HOOK, SUBAGENT_JSON),
]


def wired_handler(event: str, script: Path) -> wiring.Handler:
    found = wiring.wired(event, script.name)
    assert len(found) == 1 and found[0].folder == script.parent, (event, script, wiring.commands(event))
    return found[0]


def test_the_claude_wiring_prints_no_reminder_literal_any_more():
    every = [handler.command for handler in wiring.handlers()]

    assert every
    assert not [command for command in every if MARKER in command or "PREFLIGHT" in command or command.startswith("echo")]


def test_session_start_runs_the_preflight_reminder_the_background_reminder_and_the_task_list_once_each():
    scripts = ["preflight_reminder.py", "background_subagent_reminder.py", "task_list_sync.py"]
    started = wiring.commands("SessionStart")

    assert len(started) == len(scripts)
    assert sorted(name for name in scripts for command in started if f"/{name} " in command) == sorted(scripts)


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
    handler = wired_handler(event, script)
    environment = wiring.hook_environment(handler, REPO_ROOT, dict(os.environ))

    result = run_bounded(
        [shell, "-c", handler.command],
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
