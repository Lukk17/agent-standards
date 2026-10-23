"""Tests for tools/check-skill-mentions.py.

Every case builds a throwaway .agents/skills tree and runs the script as a
child process against it, the way CI runs it. The last test runs the guard over
the real repository, so a skill that names a skill with no folder can never
reach a green suite.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import REPO_ROOT, SUBPROCESS_TIMEOUT_SECONDS

CHECK_SKILL_MENTIONS = REPO_ROOT / "tools" / "check-skill-mentions.py"


class _SkillTree:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.skills = root / ".agents" / "skills"
        self.skills.mkdir(parents=True)

    def skill(self, name: str, body: str = "", description: str = "A skill.") -> Path:
        return self.write(f"{name}/SKILL.md", f"---\nname: {name}\ndescription: {description}\n---\n\n{body}")

    def write(self, relative: str, content: str) -> Path:
        path = self.skills / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")

        return path


@pytest.fixture
def tree(tmp_path):
    skill_tree = _SkillTree(tmp_path)
    skill_tree.skill("bash")
    skill_tree.skill("powershell")

    return skill_tree


def _run_guard(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECK_SKILL_MENTIONS), "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )


def _assert_passes(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""


def _assert_fails_naming(result: subprocess.CompletedProcess[str], *fragments: str) -> None:
    assert result.returncode == 1, result.stdout + result.stderr
    for fragment in fragments:
        assert fragment in result.stderr


def test_related_skills_naming_existing_skills_passes(tree):
    tree.skill("research", "### Related skills\n\n- `bash` and `powershell` own the scripts\n")

    _assert_passes(_run_guard(tree.root))


def test_related_skills_naming_a_missing_skill_fails(tree):
    tree.skill("research", "### Related skills\n\n- `bash`\n- `user-communication` owns the reply\n")

    _assert_fails_naming(_run_guard(tree.root), ".agents/skills/research/SKILL.md:9", "`user-communication`")


def test_every_name_in_a_leading_related_skills_list_is_checked(tree):
    tree.skill("research", "### Related skills\n\n- `bash`, `zsh` and `powershell` own the scripts\n")

    _assert_fails_naming(_run_guard(tree.root), "`zsh`")


def test_related_skills_heading_is_matched_in_any_case(tree):
    tree.skill("research", "### Related Skills\n\n- `user-communication` owns the reply\n")

    _assert_fails_naming(_run_guard(tree.root), "`user-communication`")


def test_a_subagent_in_related_skills_is_not_a_skill(tree):
    tree.skill("research", "### Related skills\n\n- `security-auditor` agent takes over for threat models\n")

    _assert_passes(_run_guard(tree.root))


def test_a_command_later_in_a_related_skills_bullet_is_not_a_skill(tree):
    tree.skill("research", "### Related skills\n\n- `bash` for the scripts a `command` task ends up invoking\n")

    _assert_passes(_run_guard(tree.root))


def test_when_not_to_activate_naming_a_missing_skill_fails(tree):
    tree.skill("research", "### When not to activate\n\n- Wording the reply itself, use `user-communication`\n")

    _assert_fails_naming(_run_guard(tree.root), "research/SKILL.md:8", "`user-communication`")


def test_when_not_to_activate_list_broken_across_lines_is_read_whole(tree):
    tree.skill("research", "### When not to activate\n\n- Writing a script, use `bash` or\n  `fish-shell`\n")

    _assert_fails_naming(_run_guard(tree.root), "research/SKILL.md:8", "`fish-shell`")


def test_use_of_a_command_outside_the_skill_sections_is_not_a_skill(tree):
    tree.skill("bash-extra", "### Argument parsing\n\nUse `getopts` for single-character flags.\n")

    _assert_passes(_run_guard(tree.root))


def test_description_naming_a_missing_skill_fails(tree):
    tree.skill("research", description="Research. Not for the reply wording, use `user-communication`.")

    _assert_fails_naming(_run_guard(tree.root), "research/SKILL.md:3", "`user-communication`")


def test_name_followed_by_the_word_skill_anywhere_fails(tree):
    tree.skill("research", "### Rules\n\nThe reply follows the `user-communication` skill.\n")

    _assert_fails_naming(_run_guard(tree.root), "`user-communication`")


def test_a_reference_file_is_checked(tree):
    tree.skill("research")
    tree.write("research/references/output.md", "### Shape\n\nThe `user-communication` skill words the reply.\n")

    _assert_fails_naming(_run_guard(tree.root), "research/references/output.md:3")


def test_a_folder_without_skill_md_does_not_count_as_a_skill(tree):
    tree.write("user-communication/notes.md", "left behind\n")
    tree.skill("research", "### Related skills\n\n- `user-communication` owns the reply\n")

    _assert_fails_naming(_run_guard(tree.root), "`user-communication`")


def test_every_missing_mention_is_reported_in_one_run(tree):
    tree.skill(
        "research",
        "### When not to activate\n\n- Recall, use `ascend-memory`\n\n### Related skills\n\n- `audio-scribe` for text\n",
    )

    _assert_fails_naming(_run_guard(tree.root), "`ascend-memory`", "`audio-scribe`")


def test_a_root_without_a_skills_folder_exits_2(tmp_path):
    result = _run_guard(tmp_path)

    assert result.returncode == 2, result.stdout + result.stderr


def test_the_real_repository_passes():
    _assert_passes(_run_guard(REPO_ROOT))
