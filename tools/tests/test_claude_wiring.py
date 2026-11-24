"""Tests for the Claude Code wiring of this repository.

.claude/settings.json wires no hook itself: it names the repository's own
marketplace by a path relative to the main checkout and switches on every hook
plugin of it, because a handler wired in a settings file and carried by a
plugin as well runs twice (https://code.claude.com/docs/en/hooks, "A plugin's
or skill's copy of the same handler stays separate"). Each plugin entry carries
the wiring its entry in tools/plugins.yaml defines, and every command starts in
the session's project and runs a script of the plugin's own folder.

Claude Code tests a matcher with JavaScript's RegExp.prototype.test, which
re.search reproduces for this anchored pattern. The hook plugin is the one
place that carries the matcher: the global install in docs/GLOBAL_SETUP.md and
the sandbox's global install give Claude Code the plugins with the user scope
and wire no hook into ~/.claude/settings.json.
"""

import json
import os
import re
import stat

import pytest
import yaml

from tests import claude_wiring_support as wiring
from tests.conftest import REPO_ROOT, SUBPROCESS_TIMEOUT_SECONDS
from tests.process_tree import run_bounded
from tests.reminder_support import posix_shell

GLOBAL_INSTALLS = ("docs/GLOBAL_SETUP.md", "sandbox-agent/setup-global.sh")
CLAUDE_ONLY_EVENTS = ("MessageDisplay", "PreCompact", "TaskCreated", "TaskCompleted")
PLUGIN_MAP = REPO_ROOT / "tools" / "plugins.yaml"
GATE_SCRIPT = "preflight_gate.py"
OWN_MARKETPLACE = {"source": {"source": "directory", "path": "."}}
HANDLERS = wiring.handlers()
PROBE = '#!/bin/sh\nprintf \'%s\\n\' "$PWD" "$@" > "$PROBE_OUT"\n'


def gate_matchers():
    return [handler.matcher for handler in wiring.wired("PreToolUse", GATE_SCRIPT)]


def test_the_settings_wire_no_hook_themselves():
    assert "hooks" not in wiring.settings()


def test_the_settings_name_the_repository_s_own_marketplace_by_a_relative_path():
    name = wiring.marketplace()["name"]

    assert wiring.settings()["extraKnownMarketplaces"] == {name: OWN_MARKETPLACE}
    assert (wiring.CLAUDE_SETTINGS.parents[1] / OWN_MARKETPLACE["source"]["path"]).resolve() == wiring.MARKETPLACE_FILE.parents[1]


def test_the_settings_switch_on_every_hook_plugin_and_nothing_else():
    plugins = wiring.hook_plugins()

    assert len(plugins) == len(yaml.safe_load(PLUGIN_MAP.read_text(encoding="utf-8"))["hooks"])
    assert wiring.settings()["enabledPlugins"] == {plugin: True for plugin in plugins}


def test_every_hook_plugin_carries_the_wiring_the_plugin_map_defines():
    canonical = {f"hook-{hook['name']}": hook["wiring"] for hook in yaml.safe_load(PLUGIN_MAP.read_text(encoding="utf-8"))["hooks"]}
    carried = {entry["name"]: entry["hooks"] for entry in wiring.hook_plugins().values()}

    assert carried == canonical
    assert all(carried.values())


def test_no_handler_is_carried_by_two_plugins():
    seen = [(handler.event, handler.matcher, handler.command) for handler in HANDLERS]

    assert HANDLERS
    assert len(seen) == len(set(seen))


@pytest.mark.parametrize("handler", HANDLERS, ids=[handler.label for handler in HANDLERS])
def test_every_handler_starts_in_the_project_and_runs_a_script_of_its_plugin_loaded_in_place(tmp_path, handler):
    shell = posix_shell()
    if shell is None:
        pytest.skip("no POSIX shell is installed")
    # Given a python3 and a python that only record where they were started and with what
    tools, project, record = tmp_path / "bin", tmp_path / "project", tmp_path / "record"
    tools.mkdir()
    project.mkdir()
    for name in ("python3", "python"):
        probe = tools / name
        probe.write_text(PROBE, encoding="utf-8")
        probe.chmod(probe.stat().st_mode | stat.S_IXUSR)
    environment = wiring.hook_environment(handler, project, {**os.environ, "PATH": f"{tools}{os.pathsep}{os.environ['PATH']}", "PROBE_OUT": str(record)})

    # When the shell runs the handler from another directory, as Claude Code does for a plugin loaded in place
    result = run_bounded([shell, "-c", handler.command], capture_output=True, text=True, env=environment, cwd=tmp_path, timeout=SUBPROCESS_TIMEOUT_SECONDS)

    # Then the interpreter starts in the project, on -S -E, with a script that exists in the plugin's own folder
    assert result.returncode == 0, result.stderr
    directory, *arguments = record.read_text(encoding="utf-8").splitlines()
    assert os.path.realpath(directory) == os.path.realpath(project)
    assert arguments[:2] == ["-S", "-E"]
    script = REPO_ROOT / arguments[2]
    assert script.is_file() and script.parent == handler.folder, arguments


@pytest.mark.parametrize(
    "tool",
    ["Edit", "Write", "MultiEdit", "NotebookEdit", "Bash", "PowerShell", "WebFetch", "WebSearch"],
)
def test_the_gate_sees_every_tool_that_writes_or_researches(tool):
    assert [re.search(matcher, tool) is not None for matcher in gate_matchers()] == [True]


@pytest.mark.parametrize("tool", ["Read", "Grep", "NotebookEditor", "bash", "powershell", "edit"])
def test_the_gate_matcher_is_anchored_and_case_sensitive(tool):
    matchers = gate_matchers()

    assert matchers
    assert all(re.search(matcher, tool) is None for matcher in matchers)


@pytest.mark.parametrize("relative", GLOBAL_INSTALLS)
def test_no_global_install_wires_a_claude_code_hook_beside_the_plugins(relative):
    text = (REPO_ROOT / relative).read_text(encoding="utf-8")

    assert '"matcher": ' + json.dumps(gate_matchers()[0]) not in text
    assert "--format claude" not in text
    assert [event for event in CLAUDE_ONLY_EVENTS if f'"{event}"' in text] == []
