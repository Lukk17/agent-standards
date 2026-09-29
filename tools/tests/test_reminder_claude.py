"""Claude Code reminder and subagent wiring tests. Expects CLAUDE_REMINDER."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.reminder_support import (
    CLAUDE_REMINDER,
    SUBAGENT_MARKER,
    MARKER,
    canonical_subagent_reminder,
    delivered_text,
    printed_literal,
    reminder_commands,
    run_in,
    shells_for,
    subagent_start_commands,
    wiring_commands,
)
from tests.conftest import REPO_ROOT

RELATIVE = ".claude/settings.json"


def test_the_claude_wiring_delivers_the_long_text_it_ships():
    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    for _key, command in reminder_commands(settings):
        assert delivered_text(printed_literal(command)) == CLAUDE_REMINDER


def test_the_claude_reminder_copies_match_the_canonical_block(tmp_path):
    copies = [delivered_text(printed_literal(c)) for _k, c in wiring_commands(RELATIVE)]
    assert len(copies) == 2
    assert all(text == CLAUDE_REMINDER for text in copies)


def test_the_claude_subagent_copies_match_the_canonical_block(tmp_path):
    canonical = canonical_subagent_reminder()
    copies = [delivered_text(printed_literal(c)) for _k, c in wiring_commands(RELATIVE, SUBAGENT_MARKER)]
    assert len(copies) == 1
    assert all(text == canonical for text in copies)


def test_the_claude_subagent_start_carries_the_subagent_text_and_never_the_reminder():
    import tomllib  # noqa: F401
    text = (REPO_ROOT / RELATIVE).read_text(encoding="utf-8")
    documents = [json.loads(text)]
    commands = [command for document in documents for _key, command in subagent_start_commands(document)]
    assert commands
    assert all(SUBAGENT_MARKER in command and MARKER not in command for command in commands)


PRINTED_COMMANDS = [
    pytest.param(key, command, shell, id=f"claude-{index}-{key}-{Path(shell).stem if shell else 'none'}")
    for index, (key, command) in enumerate(wiring_commands(RELATIVE))
    for shell in shells_for(RELATIVE, key) or [None]
]


@pytest.mark.parametrize(("key", "command", "shell"), PRINTED_COMMANDS)
def test_every_wired_command_prints_the_canonical_newlines(key, command, shell, tmp_path):
    if shell is None:
        pytest.skip(f"no shell that runs {key} is installed")
    result = run_in(shell, command, tmp_path)
    assert result.returncode == 0, result.stderr
    assert delivered_text(result.stdout) == CLAUDE_REMINDER


PRINTED_SUBAGENT_COMMANDS = [
    pytest.param(key, command, shell, id=f"claude-sub-{index}-{key}-{Path(shell).stem if shell else 'none'}")
    for index, (key, command) in enumerate(wiring_commands(RELATIVE, SUBAGENT_MARKER))
    for shell in shells_for(RELATIVE, key) or [None]
]


@pytest.mark.parametrize(("key", "command", "shell"), PRINTED_SUBAGENT_COMMANDS)
def test_every_wired_subagent_command_prints_the_canonical_text(key, command, shell, tmp_path):
    if shell is None:
        pytest.skip(f"no shell that runs {key} is installed")
    result = run_in(shell, command, tmp_path)
    assert result.returncode == 0, result.stderr
    assert delivered_text(result.stdout) == canonical_subagent_reminder()
