"""Tests for the Claude Code PreToolUse matcher that decides which tools reach the gate.

Claude Code tests a matcher with JavaScript's RegExp.prototype.test, which
re.search reproduces for this anchored pattern. The project wiring, the global
install in docs/GLOBAL_SETUP.md and the sandbox's global install must all carry
the same matcher.
"""

import json
import re

import pytest

from tests.conftest import REPO_ROOT

CLAUDE_SETTINGS = REPO_ROOT / ".claude" / "settings.json"
GLOBAL_COPIES = ("docs/GLOBAL_SETUP.md", "sandbox-agent/setup-global.sh")


def gate_matchers():
    settings = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))

    return [
        group["matcher"]
        for group in settings["hooks"]["PreToolUse"]
        if any("preflight_gate.py" in entry["command"] for entry in group["hooks"])
    ]


@pytest.mark.parametrize(
    "tool",
    ["Edit", "Write", "MultiEdit", "NotebookEdit", "Bash", "PowerShell", "WebFetch", "WebSearch"],
)
def test_the_gate_sees_every_tool_that_writes_or_researches(tool):
    assert [re.search(matcher, tool) is not None for matcher in gate_matchers()] == [True]


@pytest.mark.parametrize("tool", ["Read", "Grep", "NotebookEditor", "bash", "powershell", "edit"])
def test_the_gate_matcher_is_anchored_and_case_sensitive(tool):
    assert all(re.search(matcher, tool) is None for matcher in gate_matchers())


@pytest.mark.parametrize("relative", GLOBAL_COPIES)
def test_every_global_install_carries_the_project_matcher(relative):
    text = (REPO_ROOT / relative).read_text(encoding="utf-8")

    assert '"matcher": ' + json.dumps(gate_matchers()[0]) in text
