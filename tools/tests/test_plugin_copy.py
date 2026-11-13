"""The plugin-copy guard: one block of text, carried by every hook plugin that may stand down.

A hook plugin installs only its own folder, so the guard cannot live in a
shared module. Each hook that may stand down beside the project's own wiring
carries the same block instead, and this test holds every copy equal. The
preflight gate carries none: running it twice only repeats a deny, so a
plugin copy of the gate always decides.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys

import pytest

from tests.conftest import (
    BACKGROUND_SUBAGENT_REMINDER_HOOK,
    MARKDOWN_LINT_HOOK,
    PREFLIGHT_GATE,
    PREFLIGHT_REMINDER_HOOK,
    STANDARDS_ADVISORY_HOOK,
    SUBAGENT_REMINDER_HOOK,
    TASK_LIST_SYNC_HOOK,
)

GUARDED = [
    TASK_LIST_SYNC_HOOK,
    MARKDOWN_LINT_HOOK,
    STANDARDS_ADVISORY_HOOK,
    PREFLIGHT_REMINDER_HOOK,
    BACKGROUND_SUBAGENT_REMINDER_HOOK,
    SUBAGENT_REMINDER_HOOK,
]

START = "# A plugin copy of this hook stands down"

END = "\n    return False\n"


def guard_block(path):
    text = path.read_text(encoding="utf-8")
    start = text.index(START)
    end = text.index(END, text.index("    except Exception:\n        return False\n", text.index("def _plugin_copy_is_shadowed", start)) + 10) + len(END)

    return text[start:end]


@pytest.mark.parametrize("hook", GUARDED[1:], ids=lambda p: p.stem)
def test_every_guarded_hook_carries_the_same_guard_word_for_word(hook):
    assert guard_block(hook) == guard_block(GUARDED[0])


def test_the_guard_is_called_by_every_hook_that_carries_it_and_never_by_the_gate():
    for hook in GUARDED:
        assert hook.read_text(encoding="utf-8").count("_plugin_copy_is_shadowed(") == 2, hook.name
    assert "_plugin_copy_is_shadowed" not in PREFLIGHT_GATE.read_text(encoding="utf-8")


# The stand-down, driven through a plugin copy of the standards advisory on PostToolUse.

ADVISORY = ".agents/hooks/claude/standards-advisory-check/standards_advisory_check.py"
ADVISORY_COMMAND = 'cd "${CLAUDE_PROJECT_DIR}" && python3 -S -E ' + ADVISORY + " --format claude ; exit 0"


def plugin_copy(root, hook=STANDARDS_ADVISORY_HOOK, plugin="hook-standards-advisory-check"):
    folder = root / "config" / "plugins" / "cache" / "agent-standards" / plugin / "1.0.0"
    folder.mkdir(parents=True)
    copy = folder / hook.name
    shutil.copy2(hook, copy)
    return copy


def project_wiring(root, matcher="^(Edit|Write|MultiEdit)$", command=ADVISORY_COMMAND, own_script=True, entry=None):
    project = root / "project"
    group = {"hooks": [entry or {"type": "command", "command": command}]}
    if matcher is not None:
        group["matcher"] = matcher
    (project / ".claude").mkdir(parents=True)
    (project / ".claude" / "settings.json").write_text(json.dumps({"hooks": {"PostToolUse": [group]}}), encoding="utf-8")
    if own_script:
        (project / ADVISORY).parent.mkdir(parents=True)
        (project / ADVISORY).write_text("# own\n", encoding="utf-8")
    return project


def stood_down(tmp_path, copy, project, event="PostToolUse", tool="Write", plugin_root=None, config=None):
    """Run the plugin copy on a write the advisory warns about; True when it printed nothing."""
    payload = {"tool_name": tool, "tool_input": {"file_path": "ci.yml", "content": "uses: actions/checkout@v5\n"}, "cwd": str(project)}
    if event is not None:
        payload["hook_event_name"] = event
    environment = {key: value for key, value in os.environ.items() if not key.startswith("CLAUDE_")}
    environment.update(
        CLAUDE_PLUGIN_ROOT=str(plugin_root or copy.parent),
        CLAUDE_PROJECT_DIR=str(project),
        CLAUDE_CONFIG_DIR=str(config or tmp_path / "config"),
    )
    result = subprocess.run(
        [sys.executable, str(copy), "--format", "claude"], input=json.dumps(payload), capture_output=True, text=True,
        cwd=project, env=environment, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout == ""


def test_the_copy_stands_down_for_the_call_the_project_wiring_runs(tmp_path):
    assert stood_down(tmp_path, plugin_copy(tmp_path), project_wiring(tmp_path))


def test_a_group_with_no_matcher_takes_every_tool(tmp_path):
    assert stood_down(tmp_path, plugin_copy(tmp_path), project_wiring(tmp_path, matcher=None))


@pytest.mark.parametrize(
    "wiring",
    [
        pytest.param({"matcher": "^(Bash)$"}, id="narrower-matcher"),
        pytest.param({"matcher": "Writ"}, id="matcher-must-match-the-whole-name"),
        pytest.param({"own_script": False}, id="named-script-missing-in-the-project"),
        pytest.param({"command": "true # standards_advisory_check.py"}, id="non-script-mention"),
        pytest.param({"command": "python3 /elsewhere/hooks/standards_advisory_check.py"}, id="script-outside-the-project-hooks"),
        pytest.param({"matcher": "("}, id="unreadable-matcher"),
        pytest.param({"entry": {"type": "prompt", "command": ADVISORY_COMMAND}}, id="not-a-command-hook"),
        pytest.param({"entry": {"type": "command", "async": True, "command": ADVISORY_COMMAND}}, id="async-command"),
    ],
)
def test_the_copy_runs_whenever_the_project_wiring_does_not_run_it_for_this_call(tmp_path, wiring):
    assert not stood_down(tmp_path, plugin_copy(tmp_path), project_wiring(tmp_path, **wiring))


@pytest.mark.parametrize("event", [None, "PreToolUse"], ids=["no-event-name", "other-event"])
def test_the_copy_runs_on_a_payload_that_does_not_name_the_wired_event(tmp_path, event):
    assert not stood_down(tmp_path, plugin_copy(tmp_path), project_wiring(tmp_path), event=event)


def test_a_copy_outside_the_plugin_cache_never_stands_down(tmp_path):
    # Given the same script at a plugin root that is no Claude Code plugin cache
    folder = tmp_path / "elsewhere" / "1.0.0"
    folder.mkdir(parents=True)
    copy = folder / STANDARDS_ADVISORY_HOOK.name
    shutil.copy2(STANDARDS_ADVISORY_HOOK, copy)

    assert not stood_down(tmp_path, copy, project_wiring(tmp_path))


def test_a_plugin_root_the_script_is_not_under_never_stands_down(tmp_path):
    copy = plugin_copy(tmp_path)
    other = tmp_path / "config" / "plugins" / "cache" / "agent-standards" / "other" / "1.0.0"
    other.mkdir(parents=True)

    assert not stood_down(tmp_path, copy, project_wiring(tmp_path), plugin_root=other)


def test_the_project_script_being_this_very_file_never_stands_down(tmp_path):
    # Given a project whose own advisory is a link to the running plugin copy
    copy = plugin_copy(tmp_path)
    project = project_wiring(tmp_path, own_script=False)
    (project / ADVISORY).parent.mkdir(parents=True)
    os.symlink(copy, project / ADVISORY)

    assert not stood_down(tmp_path, copy, project)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("fmt", ["codex", "copilot", "plain", ""])
def test_the_guard_never_stands_down_outside_the_claude_format(tmp_path, monkeypatch, fmt):
    copy = plugin_copy(tmp_path, TASK_LIST_SYNC_HOOK, "hook-task-list-sync")
    module = load(copy, "task_list_sync_plugin_copy")
    project = tmp_path / "project"
    (project / ".claude").mkdir(parents=True)
    own = project / ".agents" / "hooks" / "task-list-sync" / "task_list_sync.py"
    own.parent.mkdir(parents=True)
    own.write_text("# own\n", encoding="utf-8")
    command = 'cd "${CLAUDE_PROJECT_DIR}" && python3 .agents/hooks/task-list-sync/task_list_sync.py --event taskcreated --format claude'
    (project / ".claude" / "settings.json").write_text(json.dumps({"hooks": {"TaskCreated": [{"hooks": [{"type": "command", "command": command}]}]}}), encoding="utf-8")
    for name, value in {"CLAUDE_PLUGIN_ROOT": copy.parent, "CLAUDE_PROJECT_DIR": project, "CLAUDE_CONFIG_DIR": tmp_path / "config"}.items():
        monkeypatch.setenv(name, str(value))
    payload = {"hook_event_name": "TaskCreated"}

    assert module._plugin_copy_is_shadowed(payload, "claude") is True
    assert module._plugin_copy_is_shadowed(payload, fmt) is False
