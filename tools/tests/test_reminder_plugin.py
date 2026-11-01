"""OpenCode and Kilo Code plugin per-prompt text tests.

The plugin carries the subagent text as the SUBAGENT_TEXT constant in
.agents/plugin/hooks.js. It must equal the SubagentStart text the other wirings
ship, reach a child session on both loaders, and never reach a root session.

The main-thread reminder is not copied into the plugin. It is read at run time
from the REMINDER constant of .agents/hooks/copilot/prompt_reminder.py beside
the hooks the project runs, so what the plugin reads must equal what Python
loads. A root session gets it on every prompt on 1.x and Kilo Code and on
every model request on 2.x, a child session never does, and a session that
cannot be placed gets neither text.
"""
import re
import shutil
from pathlib import Path

import pytest

from tests.conftest import PROMPT_REMINDER_HOOK, REPO_ROOT
from tests.reminder_support import (
    CLAUDE_MARKER,
    MARKER,
    SUBAGENT_MARKER,
    canonical_reminder,
    canonical_subagent_reminder,
)
from tests.test_hook_runner import CHILD_SESSION, NODE, ROOT_SESSION, drive, drive_v2, isolated_home, user_message

PLUGIN = REPO_ROOT / ".agents" / "plugin" / "hooks.js"

# The constant is written as concatenated double-quoted literals, one per sentence.
SUBAGENT_CONSTANT = re.compile(r"^const SUBAGENT_TEXT =\n((?:  \"[^\"\n]*\"(?: \+)?\n)+)", re.MULTILINE)

needs_node = pytest.mark.skipif(NODE is None, reason="node is not installed")


def plugin_constant() -> str:
    match = SUBAGENT_CONSTANT.search(PLUGIN.read_text(encoding="utf-8"))
    assert match, "no SUBAGENT_TEXT constant in the plugin"

    return "".join(re.findall(r'"([^"]*)"', match.group(1)))


def with_reminder_hook(hooks_dir: Path, source: str | None = None) -> Path:
    """Puts copilot/prompt_reminder.py under hooks_dir, the shipped file unless source is given."""
    target = hooks_dir / "copilot" / "prompt_reminder.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    if source is None:
        shutil.copy(PROMPT_REMINDER_HOOK, target)
    else:
        target.write_bytes(source.encode("utf-8"))

    return target


def texts(parts: list[dict]) -> list[str]:
    return [part["text"] for part in parts]


def test_the_plugin_constant_is_the_canonical_subagent_text():
    assert plugin_constant() == canonical_subagent_reminder()


def test_the_plugin_source_copies_no_main_thread_reminder_wording():
    source = PLUGIN.read_text(encoding="utf-8")

    assert MARKER not in source and CLAUDE_MARKER not in source
    assert plugin_constant().startswith(SUBAGENT_MARKER)


@needs_node
def test_a_root_session_prompt_gets_the_canonical_reminder_on_opencode_1_and_kilo_code(tmp_path):
    # Given the project ships the shipped reminder hook
    with_reminder_hook(tmp_path / ".agents" / "hooks")
    typed = {"id": "prt_0", "sessionID": ROOT_SESSION, "messageID": "msg_1", "type": "text", "text": "Hi"}

    # When
    parts = drive(tmp_path, [user_message([typed])])[0]["parts"]

    # Then the prompt is followed by one synthetic part on the same message, the canonical reminder alone
    added = parts[-1]

    assert parts[0] == typed
    assert len(parts) == 2
    assert (added["type"], added["synthetic"]) == ("text", True)
    assert (added["sessionID"], added["messageID"]) == (ROOT_SESSION, "msg_1")
    assert added["id"].startswith("prt_") and added["id"] != typed["id"]
    assert added["text"] == canonical_reminder()


@needs_node
def test_a_child_session_prompt_gets_the_subagent_text_and_never_the_reminder_on_opencode_1_and_kilo_code(tmp_path):
    with_reminder_hook(tmp_path / ".agents" / "hooks")

    parts = drive(tmp_path, [user_message(session=CHILD_SESSION)])[0]["parts"]

    assert texts(parts) == [canonical_subagent_reminder()]


@needs_node
def test_an_unplaced_prompt_gets_no_text_on_opencode_1_and_kilo_code(tmp_path):
    with_reminder_hook(tmp_path / ".agents" / "hooks")

    assert drive(tmp_path, [user_message(session="unknown")])[0]["parts"] == []


@needs_node
def test_a_root_session_and_a_child_session_each_get_only_their_own_text(tmp_path):
    with_reminder_hook(tmp_path / ".agents" / "hooks")
    steps = [user_message(session=ROOT_SESSION), user_message(message_id="msg_2", session=CHILD_SESSION)]

    root_parts, child_parts = (result["parts"] for result in drive(tmp_path, steps))

    assert texts(root_parts) == [canonical_reminder()]
    assert texts(child_parts) == [canonical_subagent_reminder()]


@needs_node
def test_a_root_prompt_that_already_carries_the_reminder_is_left_alone(tmp_path):
    with_reminder_hook(tmp_path / ".agents" / "hooks")
    held = {"id": "prt_0", "sessionID": ROOT_SESSION, "messageID": "msg_1", "type": "text", "text": canonical_reminder()}

    assert drive(tmp_path, [user_message([held])])[0]["parts"] == [held]


@needs_node
def test_the_reminder_comes_from_the_global_hooks_when_the_project_ships_none(tmp_path):
    # Given no .agents/hooks in the project and the global install under the home directory
    home = isolated_home(tmp_path)
    with_reminder_hook(home / ".config" / "agents" / "hooks")

    parts = drive(tmp_path, [user_message()], home=home)[0]["parts"]

    assert texts(parts) == [canonical_reminder()]


@needs_node
def test_a_root_prompt_gets_nothing_when_no_reminder_hook_is_installed(tmp_path):
    (tmp_path / ".agents" / "hooks").mkdir(parents=True)

    assert drive(tmp_path, [user_message()])[0]["parts"] == []


@needs_node
@pytest.mark.parametrize(
    "source",
    [
        'REMINDER = "one literal on one line"\n',
        'REMINDER = (\n    "an escaped \\" quote"\n)\n',
        "nothing here\n",
    ],
    ids=["single-line", "escape", "no-constant"],
)
def test_a_reminder_constant_in_another_shape_yields_no_text(tmp_path, source):
    with_reminder_hook(tmp_path / ".agents" / "hooks", source)

    assert drive(tmp_path, [user_message()])[0]["parts"] == []


@needs_node
def test_a_reminder_file_with_windows_line_endings_still_reads(tmp_path):
    shipped = PROMPT_REMINDER_HOOK.read_text(encoding="utf-8").replace("\n", "\r\n")
    with_reminder_hook(tmp_path / ".agents" / "hooks", shipped)

    assert texts(drive(tmp_path, [user_message()])[0]["parts"]) == [canonical_reminder()]


@needs_node
def test_a_child_session_request_gets_the_subagent_text_on_opencode_2(tmp_path):
    with_reminder_hook(tmp_path / ".agents" / "hooks")

    system = drive_v2(tmp_path, [{"kind": "context", "sessionID": CHILD_SESSION}])[0]["system"]

    assert system == [{"type": "text", "text": canonical_subagent_reminder()}]


@needs_node
def test_a_root_session_request_gets_the_reply_rules_then_the_canonical_reminder_on_opencode_2(tmp_path):
    # Given a project that ships its reply rules and the reminder hook
    with_reminder_hook(tmp_path / ".agents" / "hooks")
    rules = tmp_path / ".agents" / "instructions" / "reply-rules.md"
    rules.parent.mkdir(parents=True)
    rules.write_text("Project rules.\n", encoding="utf-8")

    # When
    system = drive_v2(tmp_path, [{"kind": "context", "sessionID": ROOT_SESSION}])[0]["system"]

    # Then
    assert system == [
        {"type": "text", "text": f"Instructions from: {rules}\nProject rules.\n"},
        {"type": "text", "text": canonical_reminder()},
    ]


@needs_node
def test_an_unplaced_request_gets_no_reminder_on_opencode_2(tmp_path):
    with_reminder_hook(tmp_path / ".agents" / "hooks")

    results = drive_v2(tmp_path, [{"kind": "context", "sessionID": "unknown"}, {"kind": "context"}])

    assert [result["system"] for result in results] == [[], []]
