"""Copilot wiring reminder and subagent tests. Expects SHORT_REMINDER."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.reminder_support import (
    SHORT_REMINDER,
    SUBAGENT_MARKER,
    MARKER,
    canonical_subagent_reminder,
    delivered_text,
    printed_literal,
    run_in,
    shells_for,
    subagent_start_commands,
    wiring_commands,
)
from tests.conftest import REPO_ROOT

RELATIVE = ".github/hooks/preflight.json"


def test_the_copilot_wiring_reminder_copies_match_the_canonical_block(tmp_path):
    copies = [delivered_text(printed_literal(c)) for _k, c in wiring_commands(RELATIVE)]
    assert len(copies) == 2
    assert all(text == SHORT_REMINDER for text in copies)


def test_the_copilot_wiring_subagent_copies_match_the_canonical_block(tmp_path):
    canonical = canonical_subagent_reminder()
    copies = [delivered_text(printed_literal(c)) for _k, c in wiring_commands(RELATIVE, SUBAGENT_MARKER)]
    assert len(copies) == 2
    assert all(text == canonical for text in copies)


def test_the_copilot_wiring_subagent_start_carries_the_subagent_text_and_never_the_reminder():
    documents = [json.loads((REPO_ROOT / RELATIVE).read_text(encoding="utf-8"))]
    commands = [command for document in documents for _key, command in subagent_start_commands(document)]
    assert commands
    assert all(SUBAGENT_MARKER in command and MARKER not in command for command in commands)


PRINTED_COMMANDS = [
    pytest.param(key, command, shell, id=f"copilot-{index}-{key}-{Path(shell).stem if shell else 'none'}")
    for index, (key, command) in enumerate(wiring_commands(RELATIVE))
    for shell in shells_for(RELATIVE, key) or [None]
]


@pytest.mark.parametrize(("key", "command", "shell"), PRINTED_COMMANDS)
def test_every_wired_command_prints_the_canonical_newlines(key, command, shell, tmp_path):
    if shell is None:
        pytest.skip(f"no shell that runs {key} is installed")
    result = run_in(shell, command, tmp_path)
    assert result.returncode == 0, result.stderr
    assert delivered_text(result.stdout) == SHORT_REMINDER


PRINTED_SUBAGENT_COMMANDS = [
    pytest.param(key, command, shell, id=f"copilot-sub-{index}-{key}-{Path(shell).stem if shell else 'none'}")
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
