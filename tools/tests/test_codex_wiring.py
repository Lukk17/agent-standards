"""Tests for the Windows command variants of the Codex hooks in .codex/config.toml.

Codex 0.156.1 runs a hook through the session shell, which on Windows is pwsh,
then Windows PowerShell, then cmd, invoked as `<shell> -NoProfile -Command
<commandWindows>`. Each value is therefore parsed and run the same way here,
under every PowerShell that is installed.
"""

import json
import os
import shutil
import subprocess
import tomllib

import pytest

from tests.conftest import REPO_ROOT
from tests.process_tree import run_bounded
from tests.test_prompt_reminder import canonical_reminder, canonical_subagent_reminder

CODEX_CONFIG = REPO_ROOT / ".codex" / "config.toml"
REMINDER_EVENTS = ("UserPromptSubmit", "SubagentStart")
SCRIPT_EVENTS = ("SessionStart", "Stop", "PreToolUse")

PARSE_ONLY = (
    "$errors = $null; "
    "$ast = [System.Management.Automation.Language.Parser]::ParseInput("
    "$env:CODEX_HOOK_COMMAND, [ref]$null, [ref]$errors); "
    "$literals = $ast.FindAll({ param($node) "
    "$node -is [System.Management.Automation.Language.StringConstantExpressionAst] "
    "-and $node.StringConstantType -eq 'SingleQuoted' }, $true) | ForEach-Object Value; "
    "ConvertTo-Json -Compress -InputObject @{ errors = @($errors | ForEach-Object Message); literals = @($literals) }"
)

SHELLS = [
    pytest.param(
        name,
        marks=pytest.mark.skipif(shutil.which(name) is None, reason=f"{name} is not installed"),
    )
    for name in ("pwsh", "powershell")
]


def windows_commands() -> dict[str, list[str]]:
    config = tomllib.loads(CODEX_CONFIG.read_text(encoding="utf-8"))

    return {
        event: [hook["commandWindows"] for group in groups for hook in group["hooks"]]
        for event, groups in config["hooks"].items()
    }


def canonical_text(event: str) -> str:
    """The text an injecting event delivers: the reminder on the main thread, the subagent text in a subagent."""
    return canonical_subagent_reminder() if event == "SubagentStart" else canonical_reminder()


def windows_command(event: str) -> str:
    [command] = windows_commands()[event]

    return command


def parse(shell: str, command: str) -> dict[str, list[str]]:
    result = run_bounded(
        [shell, "-NoProfile", "-Command", PARSE_ONLY],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "CODEX_HOOK_COMMAND": command},
        timeout=60,
    )

    return json.loads(result.stdout)


def run(shell: str, command: str, cwd, stdin: str = "{}") -> subprocess.CompletedProcess:
    return run_bounded(
        [shell, "-NoProfile", "-Command", command],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd,
        timeout=60,
    )


def test_every_hook_carries_a_windows_command():
    commands = windows_commands()

    assert sorted(commands) == sorted(REMINDER_EVENTS + SCRIPT_EVENTS)
    assert all(len(values) == 1 for values in commands.values())


@pytest.mark.parametrize("event", REMINDER_EVENTS + SCRIPT_EVENTS)
def test_every_windows_command_forces_a_zero_exit(event):
    assert windows_command(event).endswith("; exit 0")


@pytest.mark.parametrize("shell", SHELLS)
@pytest.mark.parametrize("event", REMINDER_EVENTS + SCRIPT_EVENTS)
def test_every_windows_command_parses_in_powershell(shell, event):
    assert parse(shell, windows_command(event))["errors"] == []


@pytest.mark.parametrize("shell", SHELLS)
@pytest.mark.parametrize("event", REMINDER_EVENTS)
def test_reminder_literal_carries_the_canonical_text(shell, event):
    # Given
    [literal] = parse(shell, windows_command(event))["literals"]

    # When
    output = json.loads(literal)["hookSpecificOutput"]

    # Then
    assert output == {"hookEventName": event, "additionalContext": canonical_text(event)}


@pytest.mark.parametrize("shell", SHELLS)
@pytest.mark.parametrize("event", REMINDER_EVENTS)
def test_reminder_command_prints_the_canonical_text(shell, event, tmp_path):
    result = run(shell, windows_command(event), tmp_path)

    assert result.returncode == 0
    assert json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"] == canonical_text(event)


def user_prompt(agent_id: str | None = None) -> str:
    """A Codex 0.150.1 UserPromptSubmit payload, which carries agent_id only inside a subagent."""
    payload = {"session_id": "s-1", "hook_event_name": "UserPromptSubmit", "prompt": 'mention "agent_id" here', "turn_id": "t-1"}

    if agent_id:
        payload["agent_id"] = agent_id

    return json.dumps(payload)


@pytest.mark.parametrize("shell", SHELLS)
def test_windows_reminder_stays_silent_inside_a_subagent(shell, tmp_path):
    result = run(shell, windows_command("UserPromptSubmit"), tmp_path, user_prompt("a-1"))

    assert (result.returncode, result.stdout) == (0, "")


@pytest.mark.parametrize("shell", SHELLS)
def test_windows_reminder_reaches_the_main_thread_even_when_the_prompt_names_agent_id(shell, tmp_path):
    result = run(shell, windows_command("UserPromptSubmit"), tmp_path, user_prompt())

    assert result.returncode == 0
    assert json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"] == canonical_reminder()


POSIX_SHELL = shutil.which("sh")


def posix_command(event: str) -> str:
    config = tomllib.loads(CODEX_CONFIG.read_text(encoding="utf-8"))
    [command] = [hook["command"] for group in config["hooks"][event] for hook in group["hooks"]]

    return command


@pytest.mark.skipif(POSIX_SHELL is None, reason="sh is not installed")
def test_posix_reminder_stays_silent_inside_a_subagent(tmp_path):
    result = run_bounded([POSIX_SHELL, "-c", posix_command("UserPromptSubmit")], input=user_prompt("a-1"), capture_output=True, text=True, cwd=tmp_path, timeout=60)

    assert (result.returncode, result.stdout) == (0, "")


@pytest.mark.skipif(POSIX_SHELL is None, reason="sh is not installed")
def test_posix_reminder_reaches_the_main_thread_even_when_the_prompt_names_agent_id(tmp_path):
    result = run_bounded([POSIX_SHELL, "-c", posix_command("UserPromptSubmit")], input=user_prompt(), capture_output=True, text=True, cwd=tmp_path, timeout=60)

    assert result.returncode == 0
    assert json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"] == canonical_reminder()


@pytest.mark.parametrize("shell", SHELLS)
def test_gate_command_reaches_the_gate_from_a_subdirectory(shell):
    # Given a main-thread write inside the repository, from a session started below the root
    payload = {
        "session_id": "s-1",
        "hook_event_name": "PreToolUse",
        "cwd": str(REPO_ROOT),
        "tool_name": "Bash",
        "tool_input": {"command": f"echo hi > {(REPO_ROOT / 'codex-wiring-probe.txt').as_posix()}"},
    }

    # When
    result = run(shell, windows_command("PreToolUse"), REPO_ROOT / "tools", json.dumps(payload))

    # Then
    assert result.returncode == 0
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.mark.parametrize("shell", SHELLS)
@pytest.mark.parametrize("event", SCRIPT_EVENTS)
def test_script_command_allows_when_the_hook_script_is_missing(shell, event, tmp_path):
    result = run(shell, windows_command(event), tmp_path)

    assert result.returncode == 0
    assert result.stdout == ""
