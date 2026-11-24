"""The status block has one canonical source and every reminder carries it word for word.

Section 3 of .agents/instructions/reply-rules.md defines the block with its two
instruction sentences. The Claude Code reminder and the reminder every other
agent prints both end with that same text.
"""
import pytest

from tests.conftest import HOOKS_DIR, PREFLIGHT_REMINDER_HOOK
from tests.reminder_support import (
    CLAUDE_REMINDER,
    STATUS_BLOCK,
    STATUS_BLOCK_LINES,
    SUBAGENT_MARKER,
    _load_module,
    canonical_reminder,
    canonical_status_block,
    canonical_subagent_reminder,
)

SHARED_OPENING = (
    "Before code work, name the skills and subagents that own this task and invoke them, "
    "or say none apply and why, in one line. "
)


def test_the_reply_rules_define_the_status_block_exactly():
    assert canonical_status_block() == STATUS_BLOCK


def test_the_reply_rules_define_the_status_block_once():
    rules = (HOOKS_DIR.parent / "instructions" / "reply-rules.md").read_text(encoding="utf-8")

    assert rules.count(STATUS_BLOCK_LINES[0]) == 1
    assert rules.count(STATUS_BLOCK_LINES[-1]) == 1


def test_the_shared_reminder_is_its_opening_and_the_canonical_status_block():
    assert canonical_reminder() == SHARED_OPENING + canonical_status_block()


def test_the_claude_reminder_ends_with_the_canonical_status_block():
    reminder = _load_module("preflight_reminder_block", PREFLIGHT_REMINDER_HOOK).REMINDER

    assert reminder == CLAUDE_REMINDER
    assert reminder.endswith(" " + canonical_status_block())


@pytest.mark.parametrize("character", ["'", '"', "\\"])
def test_the_canonical_reminder_survives_quoting_inside_a_shell_and_json(character):
    assert character not in canonical_reminder()


def test_the_canonical_subagent_text_survives_quoting_as_one_line():
    text = canonical_subagent_reminder()

    assert text.startswith(SUBAGENT_MARKER)
    assert not set("'\"\\\n") & set(text)
    assert "Delegate investigation" not in text
