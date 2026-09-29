"""test_status_template"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
import pytest
import tests.reminder_support as S
from tests.reminder_support import *
from tests.conftest import HOOKS_DIR, PROMPT_REMINDER_HOOK, REPO_ROOT
from tests.process_tree import run_bounded



def test_the_canonical_reminder_ends_with_the_status_block_template_line_for_line():
    assert canonical_reminder().endswith(
        "Follow the user-communication skill when writing "
        "to the user. End every reply with the status block the skill describes, plain text only."
    )


def test_the_canonical_reminder_survives_single_quoting():
    assert "'" not in canonical_reminder()


def test_the_canonical_subagent_text_survives_quoting_as_one_line():
    text = canonical_subagent_reminder()

    assert text.startswith(SUBAGENT_MARKER)
    assert not set("'\"\\\n") & set(text)
    assert "Delegate investigation" not in text


def test_the_user_communication_skill_carries_the_same_template():
    reference = REPO_ROOT / ".agents" / "skills" / "user-communication" / "references" / "status-block.md"
    text = reference.read_text(encoding="utf-8")
    after_intro = text.split("Copy this template exactly as shown", 1)[1]
    after_intro = after_intro.split("Every item sits in its own code block", 1)[0]
    after_intro = after_intro.split("in place.", 1)[1]
    blocks = re.findall("```text\n(.*?)\n```", after_intro, re.DOTALL)
    separators = re.findall("^---------------------$", after_intro, re.MULTILINE)
    assert separators == ["---------------------"]
    assert [block.split("\n") for block in blocks] == [
        ["Running: name of each running task, with progress like 3 of 10 todos done"],
        ["Done: older finished task", "Done: most recent finished task"],
        ["NOW: what is being done right now, one line"],
        ["Next: the next task", "Then: the task after that"],
        ["Waiting on: what the agent waits for"],
        ["State: WAITING FOR YOU"],
    ]
    template = after_intro.strip()
    assert template == STATUS_BLOCK_TEMPLATE
    assert template.index("---------------------") < template.index("Status")
    assert template.rindex("```text\nState:") > template.rindex("```text\nWaiting on:")
