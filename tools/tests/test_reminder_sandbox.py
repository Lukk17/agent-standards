"""Sandbox install, global guide, and setup-global text tests."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.reminder_support import (
    CLAUDE_MARKER,
    SHORT_REMINDER,
    canonical_subagent_reminder,
    delivered_text,
    json_blocks,
    printed_literal,
    reminder_commands,
    subagent_start_commands,
)
from tests.conftest import REPO_ROOT
from tests.process_tree import run_bounded


def test_the_setup_global_preflight_text_matches_the_canonical_block():
    script = (REPO_ROOT / "sandbox-agent" / "setup-global.sh").read_text(encoding="utf-8")
    copies = re.findall(r"^readonly PREFLIGHT_TEXT='([^']*)'$", script, re.MULTILINE)
    assert len(copies) == 1
    assert copies[0] == SHORT_REMINDER


def test_the_setup_global_subagent_text_matches_the_canonical_block():
    script = (REPO_ROOT / "sandbox-agent" / "setup-global.sh").read_text(encoding="utf-8")
    copies = re.findall(r"^readonly SUBAGENT_TEXT='([^']*)'$", script, re.MULTILINE)
    assert len(copies) == 1
    assert copies[0] == canonical_subagent_reminder()


def test_the_global_guide_shows_the_shipped_copilot_wiring_with_every_script_path_absolute():
    shipped = (REPO_ROOT / ".github" / "hooks" / "preflight.json").read_text(encoding="utf-8")
    expected = json.loads(shipped.replace(" .agents/hooks/", " /home/you/.config/agents/hooks/"))
    guide = (REPO_ROOT / "docs" / "GLOBAL_SETUP.md").read_text(encoding="utf-8")
    copilot_blocks = [block for block in json_blocks(guide) if "subagentStart" in block.get("hooks", {})]
    assert copilot_blocks == [expected]


def test_the_global_guide_json_blocks_match_the_shipped_wirings():
    guide = (REPO_ROOT / "docs" / "GLOBAL_SETUP.md").read_text(encoding="utf-8")
    blocks = json_blocks(guide)
    assert len(blocks) == 2
    texts = [delivered_text(printed_literal(c)) for b in blocks for _k, c in reminder_commands(b)]
    assert SHORT_REMINDER in texts


def test_the_global_guide_copilot_wiring_uses_short_reminder():
    guide = (REPO_ROOT / "docs" / "GLOBAL_SETUP.md").read_text(encoding="utf-8")
    copilot_blocks = [block for block in json_blocks(guide) if "subagentStart" in block.get("hooks", {})]
    assert copilot_blocks
    for block in copilot_blocks:
        for _key, command in reminder_commands(block):
            assert delivered_text(printed_literal(command)) == SHORT_REMINDER


from tests.reminder_support import posix_shell


@pytest.mark.skipif(posix_shell() is None, reason="bash is not installed")
def test_the_sandbox_install_renders_the_canonical_newlines():
    script = (REPO_ROOT / "sandbox-agent" / "setup-global.sh").read_text(encoding="utf-8")
    definitions = script.split('\nmain "$@"\n', 1)[0]
    rendered = [
        run_bounded(
            [posix_shell(), "-s"],
            input=f"{definitions}\n{function}\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
            timeout=60,
        ).stdout
        for function in ("codex_hooks",)
    ]
    commands = [command for _key, command in reminder_commands(json.loads(rendered[0]))]
    assert len(commands) == 2
    assert delivered_text(printed_literal(commands[0])) == SHORT_REMINDER
    assert delivered_text(printed_literal(commands[1])) == SHORT_REMINDER
    subagent = [command for text in rendered for _key, command in subagent_start_commands(json.loads(text))]
    assert len(subagent) == 2
    assert all(delivered_text(printed_literal(command)) == canonical_subagent_reminder() for command in subagent)


def test_the_sandbox_install_carries_no_copy_of_the_claude_code_reminder():
    script = (REPO_ROOT / "sandbox-agent" / "setup-global.sh").read_text(encoding="utf-8")

    assert CLAUDE_MARKER not in script
    assert "claude_settings" not in script


def test_the_background_subagent_note_lives_in_its_hook_and_nowhere_in_a_global_install():
    from tests.reminder_support import canonical_background_subagent_reminder

    canonical = canonical_background_subagent_reminder()
    opening = canonical.split(",", 1)[0]
    script = (REPO_ROOT / "sandbox-agent" / "setup-global.sh").read_text(encoding="utf-8")
    guide = (REPO_ROOT / "docs" / "GLOBAL_SETUP.md").read_text(encoding="utf-8")

    assert opening == "When you launch a background subagent"
    assert opening not in script
    assert opening not in guide
