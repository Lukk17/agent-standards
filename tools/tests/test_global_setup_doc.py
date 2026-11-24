"""Tests for the Unix shell commands docs/GLOBAL_SETUP.md gives Claude Code.

The commands that move an older user-wide install to the plugins, and the two
that write the reply rules output style, are read out of the guide and run
with HOME pointing at a throwaway home, so the guide and what its commands do
cannot drift apart. No command here starts Claude Code, and no test reads or
writes the real home directory.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import REPO_ROOT, SUBPROCESS_TIMEOUT_SECONDS

GUIDE = REPO_ROOT / "docs" / "GLOBAL_SETUP.md"
REPLY_RULES = REPO_ROOT / ".agents" / "instructions" / "reply-rules.md"
BASH = shutil.which("bash")
MOVE_HEADING = "### Moving Claude Code to the plugins\n"
CLAUDE_HEADING = "#### Claude Code\n"
CODEX_HEADING = "#### Codex\n"
OLD_GATE = "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E HOME/.config/agents/hooks/preflight-gate/preflight_gate.py --format claude ; exit 0"
OLD_REMINDER = "echo 'PREFLIGHT: before code work, name the skills and subagents that own this task and invoke them, or say none apply and why.'"
OLD_NOTE = "echo 'When you launch a background subagent, note how long its task should take.'"
OWN_HOOK = {"hooks": [{"type": "command", "command": "sh ~/bin/my-own-hook.sh"}]}

pytestmark = [
    pytest.mark.skipif(BASH is None, reason="bash is not installed"),
    pytest.mark.skipif(sys.platform == "win32", reason="the Unix shell commands of the guide"),
]


def section(start: str, end: str) -> str:
    text = GUIDE.read_text(encoding="utf-8")
    begin = text.index(start)

    return text[begin : text.index(end, begin + len(start))]


def bash_blocks(text: str) -> list[str]:
    return [block.strip() for block in re.findall(r"^ *```bash\n(.*?)\n *```$", text, re.MULTILINE | re.DOTALL)]


def one_block(text: str, phrase: str) -> str:
    found = [block for block in bash_blocks(text) if phrase in block]
    assert len(found) == 1, f"expected one bash block holding {phrase!r}, found {len(found)}"

    return found[0]


def move_section() -> str:
    return section(MOVE_HEADING, "\n---\n")


def claude_section() -> str:
    return section(CLAUDE_HEADING, CODEX_HEADING)


def run(home: Path, command: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [BASH, "-c", command],
        capture_output=True,
        text=True,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
        env={"HOME": str(home), "PATH": os.environ["PATH"]},
        cwd=home,
    )


def write(path: Path, text: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def old_settings(home: Path, own_hook: bool) -> dict:
    stop = [{"hooks": [{"type": "command", "command": OLD_GATE.replace("HOME", home.as_posix()).replace("preflight-gate/preflight_gate.py --format claude", "no-ai-markers-check/no_ai_markers_check.py --format claude")}]}]
    if own_hook:
        stop.append(OWN_HOOK)

    return {
        "permissions": {"allow": ["Bash(ls:*)"]},
        "hooks": {
            "SessionStart": [{"hooks": [{"type": "command", "command": OLD_REMINDER}, {"type": "command", "command": OLD_NOTE}]}],
            "PreToolUse": [{"matcher": "^(Edit|Write)$", "hooks": [{"type": "command", "timeout": 10, "command": OLD_GATE.replace("HOME", home.as_posix())}]}],
            "Stop": stop,
        },
        "model": "sonnet",
    }


@pytest.fixture
def old_home(tmp_path) -> Path:
    """A home that holds the user-wide Claude Code install made before the plugins, beside files of the user's own."""
    home = tmp_path / "home"
    shared = home / ".config" / "agents"
    for skill in ("alpha", "beta"):
        write(shared / "skills" / skill / "SKILL.md")
    for agent in ("a", "b"):
        write(shared / "agents" / f"{agent}.md")
    skills = home / ".claude" / "skills"
    skills.mkdir(parents=True)
    for skill in ("alpha", "beta"):
        (skills / skill).symlink_to(os.path.relpath(shared / "skills" / skill, skills), target_is_directory=True)
    (skills / "foreign").symlink_to(tmp_path / "elsewhere", target_is_directory=True)
    write(skills / "mine" / "SKILL.md", "mine\n")
    write(skills / "synced" / "abc" / "SKILL.md", "synced\n")
    agents = home / ".claude" / "agents"
    write(agents / "a" / "a.md", "copy\n")
    write(agents / "a" / "notes.txt", "my note\n")
    write(agents / "b.md", "flat copy\n")
    write(agents / "mine" / "mine.md", "my own\n")
    write(home / ".claude" / "settings.json", json.dumps(old_settings(home, own_hook=True), indent=2) + "\n")
    write(home / ".claude" / "CLAUDE.md", "@~/.config/agents/AGENTS.md\n")

    return home


def move_commands() -> dict[str, str]:
    text = move_section()

    return {
        "links": one_block(text, "-delete"),
        "copies": one_block(text, "rm -f ~/.claude/agents/"),
        "hooks": one_block(text, "python3 -c"),
    }


def check_commands() -> list[str]:
    text = move_section()
    link_checks = [block for block in bash_blocks(text) if "-lname" in block and "-delete" not in block]
    assert len(link_checks) == 1

    return [link_checks[0], one_block(text, "ls ~/.claude/agents/"), one_block(text, "grep -n 'config/agents/hooks/'")]


def test_the_skill_link_command_removes_only_the_links_into_the_shared_skills(old_home):
    result = run(old_home, move_commands()["links"])

    assert result.returncode == 0, result.stderr
    skills = old_home / ".claude" / "skills"
    assert sorted(path.name for path in skills.iterdir()) == ["foreign", "mine", "synced"]
    assert (skills / "foreign").is_symlink()
    assert (skills / "mine" / "SKILL.md").read_text(encoding="utf-8") == "mine\n"
    assert (old_home / ".config" / "agents" / "skills" / "alpha" / "SKILL.md").is_file()


def test_the_subagent_command_removes_only_the_copies_of_shared_subagents(old_home):
    result = run(old_home, move_commands()["copies"])

    assert result.returncode == 0, result.stderr
    agents = old_home / ".claude" / "agents"
    left = sorted(path.relative_to(agents).as_posix() for path in agents.rglob("*") if path.is_file())
    assert left == ["a/notes.txt", "mine/mine.md"]
    assert (old_home / ".config" / "agents" / "agents" / "a.md").is_file()


def test_the_hooks_command_removes_only_the_groups_the_install_wrote(old_home):
    result = run(old_home, move_commands()["hooks"])

    assert result.returncode == 0, result.stderr
    settings = json.loads((old_home / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert settings == {"permissions": {"allow": ["Bash(ls:*)"]}, "hooks": {"Stop": [OWN_HOOK]}, "model": "sonnet"}
    assert list(settings) == ["permissions", "hooks", "model"]


def test_the_hooks_command_drops_the_hooks_key_when_nothing_of_the_user_is_left(old_home):
    settings_file = old_home / ".claude" / "settings.json"
    settings_file.write_text(json.dumps(old_settings(old_home, own_hook=False)) + "\n", encoding="utf-8")

    result = run(old_home, move_commands()["hooks"])

    assert result.returncode == 0, result.stderr
    assert json.loads(settings_file.read_text(encoding="utf-8")) == {"permissions": {"allow": ["Bash(ls:*)"]}, "model": "sonnet"}


def test_every_check_prints_something_before_the_move_and_nothing_after_it(old_home):
    before = [run(old_home, command).stdout for command in check_commands()]
    for command in move_commands().values():
        assert run(old_home, command).returncode == 0
    after = [run(old_home, command).stdout for command in check_commands()]

    assert all(before)
    assert after == ["", "", ""]


def test_the_move_changes_nothing_in_the_shared_folder_or_the_import(old_home):
    shared = old_home / ".config" / "agents"
    before = sorted(path.relative_to(shared).as_posix() for path in shared.rglob("*"))

    for command in move_commands().values():
        assert run(old_home, command).returncode == 0

    assert sorted(path.relative_to(shared).as_posix() for path in shared.rglob("*")) == before
    assert (old_home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8") == "@~/.config/agents/AGENTS.md\n"


def test_the_move_ends_with_the_install_commands_of_the_claude_code_section():
    install = [block for block in bash_blocks(move_section()) if block.startswith("claude plugin ")]

    assert install[0] == "claude plugin marketplace add Lukk17/agent-standards --scope user"
    assert "claude plugin install core@agent-standards --scope user" in install
    assert set(install) <= set(bash_blocks(claude_section()))
    assert [command for command in install if "--scope user" not in command and command != "claude plugin list"] == []


def test_the_output_style_command_writes_the_front_matter_above_the_reply_rules(tmp_path):
    home = tmp_path / "home"
    write(home / ".config" / "agents" / "instructions" / "reply-rules.md", REPLY_RULES.read_text(encoding="utf-8"))

    result = run(home, one_block(claude_section(), "~/.claude/output-styles/reply-rules.md"))

    assert result.returncode == 0, result.stderr
    style = (home / ".claude" / "output-styles" / "reply-rules.md").read_text(encoding="utf-8")
    front_matter = "---\nname: Reply rules\ndescription: The agent-standards reply rules\nkeep-coding-instructions: true\n---\n\n"
    assert style == front_matter + REPLY_RULES.read_text(encoding="utf-8")


def test_the_output_style_setting_command_keeps_every_other_key(tmp_path):
    home = tmp_path / "home"
    write(home / ".claude" / "settings.json", '{"enabledPlugins": {"core@agent-standards": true}, "model": "sonnet"}\n')

    result = run(home, one_block(claude_section(), 's["outputStyle"]'))

    assert result.returncode == 0, result.stderr
    settings = json.loads((home / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert settings == {"enabledPlugins": {"core@agent-standards": True}, "model": "sonnet", "outputStyle": "Reply rules"}
