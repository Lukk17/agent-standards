"""Runs the POSIX update commands of docs/AGENTS-UPDATE.md against a throwaway project.

The guide is the only way a project imported with git takes an upstream
change, so the steps that move or rename upstream paths are run here for real:
a fake upstream with the current layout, a project imported from an older
one, and the guide's own fenced bash blocks, picked by a phrase each holds.
The PowerShell blocks mirror them line for line and are not run here, because
pwsh is not on every machine the suite runs on.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.conftest import REPO_ROOT

GUIDE = REPO_ROOT / "docs" / "AGENTS-UPDATE.md"
BASH = shutil.which("bash")
IDENTITY = ("-c", "user.name=test", "-c", "user.email=test@example.invalid")
OLD_FLAT_HOOKS = (
    "preflight_gate.py",
    "task_list_sync.py",
    "no_ai_markers_check.py",
    "markdown_lint_check.py",
    "_check_markdown.py",
    "question_numbering_check.py",
    "status_block_check.py",
    "task_watchdog.py",
    "claude/sync_skill_links.py",
    "claude/standards_advisory_check.py",
    "copilot/prompt_reminder.py",
)

pytestmark = pytest.mark.skipif(BASH is None, reason="bash is not installed")


def bash_block(phrase: str) -> str:
    """The one fenced bash block of the guide that holds phrase."""
    blocks = re.findall(r"```bash\n(.*?)\n```", GUIDE.read_text(encoding="utf-8"), re.S)
    found = [block for block in blocks if phrase in block]
    assert len(found) == 1, f"expected one bash block holding {phrase!r}, found {len(found)}"
    return found[0]


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *IDENTITY, *args], capture_output=True, text=True, check=True).stdout


def write(root: Path, relative: str, text: str = "x\n") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def project(tmp_path) -> Path:
    """A project imported from the flat layout, with an agent-standards remote at the current one."""
    upstream = tmp_path / "upstream"
    for name in ("preflight-gate/preflight_gate.py", "task-list-sync/task_list_sync.py", "claude/sync-skill-links/sync_skill_links.py"):
        write(upstream, f".agents/hooks/{name}", "new\n")
    write(upstream, ".agents/skills/application-security-review/SKILL.md", "renamed\n")
    write(upstream, ".agents/skills/kept/SKILL.md", "kept v2\n")
    git(upstream.parent, "init", "--quiet", "--initial-branch=master", str(upstream))
    git(upstream, "add", "--all")
    git(upstream, "commit", "--quiet", "-m", "current layout")

    root = tmp_path / "project"
    for name in OLD_FLAT_HOOKS:
        write(root, f".agents/hooks/{name}", "old\n")
    write(root, ".agents/skills/security-review/SKILL.md", "old name\n")
    write(root, ".agents/skills/kept/SKILL.md", "kept v1\n")
    git(tmp_path, "init", "--quiet", "--initial-branch=main", str(root))
    git(root, "add", "--all")
    git(root, "commit", "--quiet", "-m", "flat import")
    git(root, "remote", "add", "agent-standards", str(upstream))
    git(root, "fetch", "--quiet", "agent-standards")
    return root


def run(root: Path, block: str) -> None:
    result = subprocess.run([BASH, "-c", block], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_the_update_removes_every_old_flat_hook_before_it_refreshes_the_hook_folders(project):
    run(project, bash_block("git rm -q --ignore-unmatch -- .agents/hooks/preflight_gate.py"))
    run(project, bash_block("for p in .agents/hooks .agents/plugin"))

    left = sorted(p.relative_to(project / ".agents" / "hooks").as_posix() for p in (project / ".agents" / "hooks").rglob("*.py"))
    assert left == ["claude/sync-skill-links/sync_skill_links.py", "preflight-gate/preflight_gate.py", "task-list-sync/task_list_sync.py"]


def test_every_old_flat_hook_is_named_in_the_removal(project):
    block = bash_block("git rm -q --ignore-unmatch -- .agents/hooks/preflight_gate.py")

    assert all(f".agents/hooks/{name}" in block for name in OLD_FLAT_HOOKS)


def test_the_update_moves_the_renamed_security_skill_and_refreshes_the_rest(project):
    run(project, bash_block("security-review"))
    run(project, bash_block("for d in .agents/skills/*/"))

    skills = project / ".agents" / "skills"
    assert sorted(p.name for p in skills.iterdir()) == ["application-security-review", "kept"]
    assert (skills / "application-security-review" / "SKILL.md").read_text(encoding="utf-8") == "renamed\n"
    assert (skills / "kept" / "SKILL.md").read_text(encoding="utf-8") == "kept v2\n"


def test_the_rename_step_leaves_a_project_without_the_old_skill_alone(project):
    shutil.rmtree(project / ".agents" / "skills" / "security-review")

    run(project, bash_block("security-review"))

    assert sorted(p.name for p in (project / ".agents" / "skills").iterdir()) == ["kept"]
