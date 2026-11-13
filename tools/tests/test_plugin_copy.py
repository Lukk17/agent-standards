"""The plugin-copy guard is one block of text, carried by every hook a Claude Code hook plugin ships.

A hook plugin installs only its own folder, so the guard cannot live in a
shared module. Each hook carries the same block instead, and this test holds
every copy equal to the one in the preflight gate.
"""

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
    end = text.index(END, text.index("def _plugin_copy_is_shadowed", start)) + len(END)

    return text[start:end]


@pytest.mark.parametrize("hook", GUARDED, ids=lambda p: p.stem)
def test_every_plugin_hook_carries_the_gate_s_guard_word_for_word(hook):
    assert guard_block(hook) == guard_block(PREFLIGHT_GATE)


def test_the_guard_is_called_by_every_hook_that_carries_it():
    for hook in (PREFLIGHT_GATE, *GUARDED):
        assert hook.read_text(encoding="utf-8").count("_plugin_copy_is_shadowed(") == 2, hook.name


# The stand-down itself, driven through a plugin copy of the gate on PreToolUse.

import json  # noqa: E402
import os  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402

GATE_COMMAND = 'cd "${CLAUDE_PROJECT_DIR}" && python3 -S -E .agents/hooks/preflight-gate/preflight_gate.py --format claude ; exit 0'


def run_plugin_gate(tmp_path, matcher="^(Edit|Write)$", command=GATE_COMMAND, own_script=True, event="PreToolUse", tool="Edit"):
    """Run a plugin-cache copy of the gate for a main-thread edit; True when it stood down."""
    folder = tmp_path / "cache" / "agent-standards" / "hook-preflight-gate" / "1.0.0"
    folder.mkdir(parents=True)
    gate = folder / PREFLIGHT_GATE.name
    shutil.copy2(PREFLIGHT_GATE, gate)
    project = tmp_path / "project"
    group = {"hooks": [{"type": "command", "command": command}]}
    if matcher is not None:
        group["matcher"] = matcher
    (project / ".claude").mkdir(parents=True)
    (project / ".claude" / "settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [group]}}), encoding="utf-8")
    if own_script:
        (project / ".agents" / "hooks" / "preflight-gate").mkdir(parents=True)
        (project / ".agents" / "hooks" / "preflight-gate" / "preflight_gate.py").write_text("# own\n", encoding="utf-8")
    payload = {"tool_name": tool, "tool_input": {"file_path": str(project / "app.py")}, "cwd": str(project)}
    if event is not None:
        payload["hook_event_name"] = event
    environment = {key: value for key, value in os.environ.items() if key not in ("CLAUDE_PLUGIN_ROOT", "CLAUDE_PROJECT_DIR")}
    environment.update(CLAUDE_PLUGIN_ROOT=str(folder), CLAUDE_PROJECT_DIR=str(project))
    result = subprocess.run(
        [sys.executable, str(gate), "--format", "claude"], input=json.dumps(payload), capture_output=True, text=True,
        cwd=project, env=environment, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout == ""


def test_the_copy_stands_down_for_the_call_the_project_wiring_runs(tmp_path):
    assert run_plugin_gate(tmp_path)


def test_a_group_with_no_matcher_takes_every_tool(tmp_path):
    assert run_plugin_gate(tmp_path, matcher=None)


@pytest.mark.parametrize(
    "case",
    [
        pytest.param({"matcher": "^(Bash)$"}, id="narrower-matcher"),
        pytest.param({"matcher": "Edi"}, id="matcher-must-match-the-whole-name"),
        pytest.param({"own_script": False}, id="named-script-missing-in-the-project"),
        pytest.param({"command": "true # preflight_gate.py"}, id="non-script-mention"),
        pytest.param({"command": "python3 /elsewhere/hooks/preflight_gate.py"}, id="script-outside-the-project-hooks"),
        pytest.param({"event": None}, id="no-event-name"),
        pytest.param({"event": "PostToolUse"}, id="other-event"),
        pytest.param({"matcher": "("}, id="unreadable-matcher"),
    ],
)
def test_the_copy_runs_whenever_the_project_wiring_does_not_run_it_for_this_call(tmp_path, case):
    assert not run_plugin_gate(tmp_path, **case)
