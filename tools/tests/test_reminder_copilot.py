"""test_reminder_copilot"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
import pytest
import tests.reminder_support as S
from tests.reminder_support import *
from tests.reminder_support import _load_module
from tests.conftest import HOOKS_DIR, PROMPT_REMINDER_HOOK, REPO_ROOT
from tests.process_tree import run_bounded



def test_reminder_is_appended_on_a_new_line():
    result = run(payload("fix the build"))

    assert result.returncode == 0
    assert json.loads(result.stdout) == {"modifiedTransformedPrompt": f"fix the build\n{REMINDER}"}


def test_non_ascii_prompt_survives_the_round_trip():
    result = run(payload("popraw błąd"))

    assert json.loads(result.stdout)["modifiedTransformedPrompt"] == f"popraw błąd\n{REMINDER}"


def test_prompt_already_carrying_the_reminder_is_left_unchanged():
    result = run(payload(f"fix the build\n{REMINDER}\n"))

    assert result.returncode == 0
    assert result.stdout == b""


def test_a_prompt_that_opens_a_subagent_session_gets_no_reminder():
    # Given the recorded opening prompt of a Copilot subagent session
    stdin = recorded_subagent_prompt()

    # When
    result = run(stdin)

    # Then the subagent is not told to delegate its own task
    assert result.returncode == 0
    assert result.stdout == b""


def test_the_recorded_subagent_text_is_the_canonical_one():
    hook = _load_module("prompt_reminder_opening", PROMPT_REMINDER_HOOK)

    assert RECORDED_SUBAGENT_TEXT == canonical_subagent_reminder()
    assert canonical_subagent_reminder().startswith(hook.SUBAGENT_OPENING)


def test_a_main_thread_prompt_that_mentions_the_subagent_text_still_gets_the_reminder():
    result = run(payload(f"Delegate this and pass on: {RECORDED_SUBAGENT_TEXT}"))

    assert json.loads(result.stdout)["modifiedTransformedPrompt"].endswith(REMINDER)


@pytest.mark.parametrize(
    "stdin",
    [
        b"",
        b"not json",
        b"[]",
        json.dumps({"prompt": "no transformed field"}).encode("utf-8"),
        payload(None),
        payload(42),
        b"\xff\xfe",
    ],
)
def test_unusable_payload_prints_nothing_and_exits_zero(stdin):
    result = run(stdin)

    assert result.returncode == 0
    assert result.stdout == b""
    assert result.stderr == b""


def test_hook_sits_below_the_directory_the_tool_call_runner_discovers():
    assert PROMPT_REMINDER_HOOK.is_file()
    assert PROMPT_REMINDER_HOOK.parent.parent == HOOKS_DIR


@pytest.mark.parametrize("shell", ["bash", "powershell"])
def test_copilot_wiring_calls_the_hook_where_it_lives(shell):
    wiring = json.loads(COPILOT_WIRING.read_text(encoding="utf-8"))
    commands = [entry[shell] for entry in wiring["hooks"]["userPromptTransformed"]]
    relative = PROMPT_REMINDER_HOOK.relative_to(REPO_ROOT).as_posix()

    assert commands
    assert all(f"-S -E {relative} " in command for command in commands)
