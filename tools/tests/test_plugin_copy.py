"""The plugin-copy guard is one block of text, carried by every hook a Claude Code hook plugin ships.

A hook plugin installs only its own folder, so the guard cannot live in a
shared module. Each hook carries the same block instead, and this test holds
every copy equal to the one in the preflight gate.
"""

import pytest

from tests.conftest import MARKDOWN_LINT_HOOK, PREFLIGHT_GATE, STANDARDS_ADVISORY_HOOK, TASK_LIST_SYNC_HOOK

START = "# A plugin copy of this hook stands down"

END = "\n    return False\n"


def guard_block(path):
    text = path.read_text(encoding="utf-8")
    start = text.index(START)
    end = text.index(END, text.index("def _plugin_copy_is_shadowed", start)) + len(END)

    return text[start:end]


@pytest.mark.parametrize("hook", [TASK_LIST_SYNC_HOOK, MARKDOWN_LINT_HOOK, STANDARDS_ADVISORY_HOOK], ids=lambda p: p.stem)
def test_every_plugin_hook_carries_the_gate_s_guard_word_for_word(hook):
    assert guard_block(hook) == guard_block(PREFLIGHT_GATE)


def test_the_guard_is_called_by_every_hook_that_carries_it():
    for hook in (PREFLIGHT_GATE, TASK_LIST_SYNC_HOOK, MARKDOWN_LINT_HOOK, STANDARDS_ADVISORY_HOOK):
        assert hook.read_text(encoding="utf-8").count("_plugin_copy_is_shadowed(") == 2, hook.name
