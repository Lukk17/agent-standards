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
    pytest.skip("user-communication skill removed")
