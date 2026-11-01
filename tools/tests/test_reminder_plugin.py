"""OpenCode and Kilo Code plugin subagent wiring tests.

The plugin carries the subagent text as the SUBAGENT_TEXT constant in
.agents/plugin/hooks.js. It must equal the SubagentStart text the other wirings
ship, reach a child session on both loaders, and never reach a root session,
which on these runtimes gets no per-prompt text from the plugin at all.
"""
import re

import pytest

from tests.conftest import REPO_ROOT
from tests.reminder_support import CLAUDE_MARKER, MARKER, SUBAGENT_MARKER, canonical_subagent_reminder
from tests.test_hook_runner import CHILD_SESSION, NODE, ROOT_SESSION, drive, drive_v2, user_message

PLUGIN = REPO_ROOT / ".agents" / "plugin" / "hooks.js"

# The constant is written as concatenated double-quoted literals, one per sentence.
SUBAGENT_CONSTANT = re.compile(r"^const SUBAGENT_TEXT =\n((?:  \"[^\"\n]*\"(?: \+)?\n)+)", re.MULTILINE)

needs_node = pytest.mark.skipif(NODE is None, reason="node is not installed")


def plugin_constant() -> str:
    match = SUBAGENT_CONSTANT.search(PLUGIN.read_text(encoding="utf-8"))
    assert match, "no SUBAGENT_TEXT constant in the plugin"

    return "".join(re.findall(r'"([^"]*)"', match.group(1)))


def test_the_plugin_constant_is_the_canonical_subagent_text():
    assert plugin_constant() == canonical_subagent_reminder()


def test_the_plugin_carries_no_main_thread_reminder():
    source = PLUGIN.read_text(encoding="utf-8")

    assert MARKER not in source and CLAUDE_MARKER not in source
    assert plugin_constant().startswith(SUBAGENT_MARKER)


@needs_node
def test_a_child_session_prompt_gets_the_subagent_text_on_opencode_1_and_kilo_code(tmp_path):
    parts = drive(tmp_path, [user_message(session=CHILD_SESSION)])[0]["parts"]

    assert [part["text"] for part in parts] == [canonical_subagent_reminder()]


@needs_node
@pytest.mark.parametrize("session", [ROOT_SESSION, "unknown"], ids=["root", "unplaced"])
def test_a_main_or_unplaced_prompt_gets_no_text_on_opencode_1_and_kilo_code(tmp_path, session):
    assert drive(tmp_path, [user_message(session=session)])[0]["parts"] == []


@needs_node
def test_a_child_session_request_gets_the_subagent_text_on_opencode_2(tmp_path):
    system = drive_v2(tmp_path, [{"kind": "context", "sessionID": CHILD_SESSION}])[0]["system"]

    assert system == [{"type": "text", "text": canonical_subagent_reminder()}]
