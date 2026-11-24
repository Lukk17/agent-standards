"""Tests that every Claude Code hook script runs once per event.

Claude Code runs a handler defined in several settings files once, but "A
plugin's or skill's copy of the same handler stays separate"
(https://code.claude.com/docs/en/hooks, "Hook handler fields"). So for a
script wired in .claude/settings.json and carried by a hook plugin as well,
both handlers start on one event, every plugin copy but the gate stands down,
and only the gate runs twice. A script that two enabled plugins both wire to
the same event runs twice, because neither copy stands down for the other.
These tests fail on either. A script is known by its file name, because a plugin names it from
"${CLAUDE_PLUGIN_ROOT}" and a settings file by its project path. The sandbox
suite in sandbox-agent/e2e-mock/subagent-write.sh counts the real runs in the
debug log of a session.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

import pytest

from tests import claude_wiring_support as wiring

SETTINGS_SOURCE = ".claude/settings.json"
SCRIPT = re.compile(r"[A-Za-z0-9_.-]+\.(?:py|sh|mjs|js|ps1)\b")
GATE_HANDLER = {"type": "command", "command": 'python3 .agents/hooks/preflight-gate/preflight_gate.py --format claude'}


@dataclass(frozen=True, slots=True)
class DoubleRun:
    """One script that more than one source wires to one event."""

    event: str
    script: str
    sources: tuple[str, ...]


def scripts(command: str) -> set[str]:
    """The file name of every script a command runs."""
    return set(SCRIPT.findall(command))


def runs(source: str, hooks: dict) -> list[tuple[str, str, str]]:
    """Every (event, script, source) a hooks block in the settings shape runs."""
    return [
        (event, script, source)
        for event, groups in hooks.items()
        for group in groups
        for handler in group.get("hooks", [])
        if handler.get("type", "command") == "command"
        for script in scripts(str(handler.get("command", "")))
    ]


def double_runs(wired: Iterable[tuple[str, str, str]]) -> list[DoubleRun]:
    """Every script that two or more sources wire to the same event."""
    sources: dict[tuple[str, str], set[str]] = {}
    for event, script, source in wired:
        sources.setdefault((event, script), set()).add(source)

    return [DoubleRun(event, script, tuple(sorted(found))) for (event, script), found in sorted(sources.items()) if len(found) > 1]


def plugin_runs(plugins: Iterable[str]) -> list[tuple[str, str, str]]:
    entries = wiring.hook_plugins()

    return [run for plugin in sorted(plugins) for run in runs(entries[plugin]["name"], entries[plugin]["hooks"])]


def settings_runs(settings: dict) -> list[tuple[str, str, str]]:
    return runs(SETTINGS_SOURCE, settings.get("hooks", {}))


def from_settings(found: list[DoubleRun]) -> list[DoubleRun]:
    return [double for double in found if SETTINGS_SOURCE in double.sources]


PLUGIN_SETS = {
    "enabled in .claude/settings.json": wiring.enabled_plugins() & set(wiring.hook_plugins()),
    "every hook plugin of the marketplace": set(wiring.hook_plugins()),
}


def test_no_hook_script_is_wired_in_the_settings_and_in_an_enabled_plugin():
    found = double_runs(settings_runs(wiring.settings()) + plugin_runs(wiring.enabled_plugins() & set(wiring.hook_plugins())))

    assert from_settings(found) == []


@pytest.mark.parametrize("plugins", PLUGIN_SETS.values(), ids=PLUGIN_SETS.keys())
def test_no_two_hook_plugins_wire_one_script_to_one_event(plugins):
    assert plugins
    assert double_runs(plugin_runs(plugins)) == []


def test_a_settings_hook_that_a_plugin_also_wires_is_found():
    settings = {**wiring.settings(), "hooks": {"PreToolUse": [{"matcher": "^Write$", "hooks": [GATE_HANDLER]}]}}

    found = double_runs(settings_runs(settings) + plugin_runs(wiring.enabled_plugins() & set(wiring.hook_plugins())))

    assert from_settings(found) == [DoubleRun("PreToolUse", "preflight_gate.py", (SETTINGS_SOURCE, "hook-preflight-gate"))]


def test_two_plugins_that_wire_one_script_to_one_event_are_found():
    gate = wiring.hook_plugins()["hook-preflight-gate@agent-standards"]
    copy = runs("hook-gate-copy", {"PreToolUse": [{"matcher": "^Bash$", "hooks": gate["hooks"]["PreToolUse"][0]["hooks"]}]})

    found = double_runs(plugin_runs(PLUGIN_SETS["every hook plugin of the marketplace"]) + copy)

    assert found == [DoubleRun("PreToolUse", "preflight_gate.py", ("hook-gate-copy", "hook-preflight-gate"))]


def test_one_script_on_several_events_of_one_plugin_is_not_a_double_run():
    sync = wiring.hook_plugins()["hook-task-list-sync@agent-standards"]

    assert len(sync["hooks"]) > 1
    assert double_runs(runs(sync["name"], sync["hooks"])) == []
