"""Tests for the global updater in global/bin, in its POSIX sh and its PowerShell form.

Every test builds a throwaway upstream repository and a fake home directory
under tmp_path, installs the fake home the way docs/GLOBAL_SETUP.md does, and
runs the updater with --home-dir pointing at it. No test reads or writes the
real home directory: HOME and USERPROFILE point at the fake one as well.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.conftest import REPO_ROOT
from tests.process_tree import run_bounded

UPDATER_DIR = REPO_ROOT / "global" / "bin"
SH = shutil.which("sh")
PWSH = shutil.which("pwsh")

IMPLEMENTATIONS = [
    pytest.param("sh", marks=pytest.mark.skipif(SH is None, reason="sh is not installed")),
    pytest.param("pwsh", marks=pytest.mark.skipif(PWSH is None, reason="pwsh is not installed")),
]

ACTION_VERBS = ("update ", "add ", "remove ", "keep ", "skip ")

FIRST_RELEASE = {
    ".agents/hooks/preflight_gate.py": "gate v1\n",
    ".agents/hooks/old_hook.py": "old hook\n",
    ".agents/hooks/copilot/prompt_reminder.py": "reminder\n",
    ".agents/plugin/hooks.js": "plugin v1\n",
    "global/bin/update-global.sh": "updater v1\n",
    ".agents/skills/alpha/SKILL.md": "alpha v1\n",
    ".agents/skills/alpha/references/old.md": "old reference\n",
    ".agents/skills/beta/SKILL.md": "beta v1\n",
    ".agents/skills/delta/SKILL.md": "delta v1\n",
    ".agents/agents/a.md": "a v1\n",
    ".agents/agents/b.md": "b v1\n",
    ".agents/agents/c.md": "c v1\n",
    ".claude/agents/a.md": "claude a v1\n",
    ".claude/agents/b.md": "claude b v1\n",
    ".claude/agents/c.md": "claude c v1\n",
    ".codex/agents/a.toml": "codex a v1\n",
    ".codex/agents/c.toml": "codex c v1\n",
    ".github/agents/a.agent.md": "copilot a v1\n",
    ".github/agents/c.agent.md": "copilot c v1\n",
    ".claude/settings.json": "{}\n",
    ".codex/config.toml": "\n",
    ".github/hooks/preflight.json": "{}\n",
    "docs/GLOBAL_SETUP.md": "guide v1\n",
}

SECOND_RELEASE_CHANGES = {
    ".agents/hooks/preflight_gate.py": "gate v2\n",
    ".agents/hooks/new_hook.py": "new hook\n",
    "global/bin/update-global.sh": "updater v2\n",
    ".agents/skills/alpha/SKILL.md": "alpha v2\n",
    ".agents/skills/alpha/references/new.md": "new reference\n",
    ".agents/skills/beta/SKILL.md": "beta v2\n",
    ".agents/skills/gamma/SKILL.md": "gamma v2\n",
    ".agents/agents/a.md": "a v2\n",
    ".agents/agents/d.md": "d v2\n",
    ".claude/agents/a.md": "claude a v2\n",
    ".claude/agents/b.md": "claude b v2\n",
    ".codex/agents/a.toml": "codex a v2\n",
    ".github/agents/a.agent.md": "copilot a v2\n",
    ".claude/settings.json": '{"hooks": {}}\n',
}

SECOND_RELEASE_REMOVALS = (
    ".agents/hooks/old_hook.py",
    ".agents/hooks/copilot/prompt_reminder.py",
    ".agents/skills/alpha/references/old.md",
    ".agents/skills/delta/SKILL.md",
    ".agents/agents/c.md",
    ".claude/agents/c.md",
    ".codex/agents/c.toml",
    ".github/agents/c.agent.md",
)

INSTALLED_TREES = {
    ".agents/skills": ".agents/skills",
    ".agents/agents": ".agents/agents",
    ".agents/hooks": ".agents/hooks",
    ".agents/plugin": ".agents/plugin",
    "global/bin": ".agents/bin",
    ".claude/agents": ".claude/agents",
    ".codex/agents": ".codex/agents",
    ".github/agents": ".copilot/agents",
}

INSTALL_ROOTS = (".agents", ".claude", ".codex", ".copilot")

USER_SETTINGS ='{"permissions": {"allow": ["mine"]}}\n'
USER_SKILL = "---\nname: mine\ndescription: The user's own skill.\n---\n"


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=test", "-c", "user.email=test@example.invalid", *args],
        capture_output=True,
        text=True,
        check=True,
    )

    return result.stdout.strip()


def write_files(root: Path, files: dict[str, str]) -> None:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))


def commit_all(repo: Path, message: str) -> str:
    git(repo, "add", "--all")
    git(repo, "commit", "--quiet", "-m", message)

    return git(repo, "rev-parse", "HEAD")


def make_upstream(root: Path) -> tuple[Path, str]:
    repo = root / "upstream"
    repo.mkdir()
    git(repo, "init", "--quiet")
    git(repo, "config", "core.autocrlf", "false")
    write_files(repo, FIRST_RELEASE)

    return repo, commit_all(repo, "first release")


def release_second(repo: Path) -> str:
    write_files(repo, SECOND_RELEASE_CHANGES)
    for relative in SECOND_RELEASE_REMOVALS:
        (repo / relative).unlink()

    return commit_all(repo, "second release")


def install_home(root: Path, repo: Path, commit: str) -> Path:
    """Install the fake home from the upstream checkout the way docs/GLOBAL_SETUP.md does, then personalise it."""
    home = root / "home"
    for upstream, installed in INSTALLED_TREES.items():
        shutil.copytree(repo / upstream, home / installed)
    (home / ".agents" / ".upstream-commit").write_bytes(f"{commit}\n".encode("ascii"))

    shutil.rmtree(home / ".agents" / "skills" / "beta")
    (home / ".claude" / "agents" / "b.md").unlink()
    write_files(home, {
        ".agents/skills/mine/SKILL.md": USER_SKILL,
        ".claude/agents/mine.md": "my own subagent\n",
        ".claude/settings.json": USER_SETTINGS,
    })

    return home


def snapshot(home: Path) -> dict[str, bytes]:
    """Every file under the directories the install lives in, keyed by its path, leaving out what pwsh caches."""
    return {
        path.relative_to(home).as_posix(): path.read_bytes()
        for top in INSTALL_ROOTS
        for path in sorted((home / top).rglob("*"))
        if path.is_file()
    }


def run_updater(implementation: str, home: Path, source: str, *, dry_run: bool = False) -> subprocess.CompletedProcess:
    if implementation == "sh":
        command = [SH, (UPDATER_DIR / "update-global.sh").as_posix(), "--source", source, "--home-dir", home.as_posix()]
        if dry_run:
            command.append("--dry-run")
    else:
        command = [PWSH, "-NoProfile", "-NonInteractive", "-File", str(UPDATER_DIR / "update-global.ps1"), "-Source", source, "-HomeDir", str(home)]
        if dry_run:
            command.append("-DryRun")

    environment = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}

    return run_bounded(command, capture_output=True, text=True, env=environment)


def action_lines(output: str) -> list[str]:
    return [line for line in output.splitlines() if line.startswith(ACTION_VERBS)]


def report_lines(output: str) -> list[str]:
    """Every line both implementations print identically, which is all but the Source and Home header."""
    return [line for line in output.splitlines() if not line.startswith(("Source:", "Home:"))]


@pytest.fixture
def released(tmp_path):
    repo, first = make_upstream(tmp_path)
    home = install_home(tmp_path, repo, first)

    return repo, home, first


@pytest.mark.parametrize("implementation", IMPLEMENTATIONS)
def test_a_fresh_install_is_already_current(released, implementation):
    # Given a home installed from the commit the upstream is still at
    repo, home, first = released
    before = snapshot(home)

    # When
    result = run_updater(implementation, home, str(repo))

    # Then only the user's own items are reported, and nothing changed
    assert result.returncode == 0, result.stderr
    assert action_lines(result.stdout) == [
        "skip    ~/.agents/skills/mine (not an upstream skill)",
        "skip    ~/.claude/agents/mine.md (not an upstream subagent)",
    ]
    assert "Updated 0, added 0, removed 0." in result.stdout
    assert snapshot(home) == before


@pytest.mark.parametrize("implementation", IMPLEMENTATIONS)
def test_an_update_refreshes_only_what_is_installed(released, implementation):
    # Given a second upstream release with changed, added and removed files
    repo, home, first = released
    second = release_second(repo)

    # When
    result = run_updater(implementation, home, str(repo))

    # Then
    assert result.returncode == 0, result.stderr
    assert action_lines(result.stdout) == [
        "add     ~/.agents/hooks/new_hook.py",
        "update  ~/.agents/hooks/preflight_gate.py",
        "remove  ~/.agents/hooks/copilot/prompt_reminder.py",
        "remove  ~/.agents/hooks/old_hook.py",
        "update  ~/.agents/bin/update-global.sh",
        "update  ~/.agents/skills/alpha/SKILL.md",
        "add     ~/.agents/skills/alpha/references/new.md",
        "remove  ~/.agents/skills/alpha/references/old.md",
        "keep    ~/.agents/skills/delta (removed upstream, left in place)",
        "skip    ~/.agents/skills/mine (not an upstream skill)",
        "update  ~/.agents/agents/a.md",
        "keep    ~/.agents/agents/c.md (removed upstream, left in place)",
        "update  ~/.claude/agents/a.md",
        "keep    ~/.claude/agents/c.md (removed upstream, left in place)",
        "skip    ~/.claude/agents/mine.md (not an upstream subagent)",
        "update  ~/.codex/agents/a.toml",
        "keep    ~/.codex/agents/c.toml (removed upstream, left in place)",
        "update  ~/.copilot/agents/a.agent.md",
        "keep    ~/.copilot/agents/c.agent.md (removed upstream, left in place)",
    ]
    assert "Updated 7, added 2, removed 3. Unchanged 2. Left alone: 5 removed upstream, 2 not from upstream." in result.stdout
    assert f"Hook wiring changed upstream since {first}." in result.stdout
    assert "  .claude/settings.json" in result.stdout

    files = snapshot(home)
    assert files[".agents/hooks/preflight_gate.py"] == b"gate v2\n"
    assert files[".agents/hooks/new_hook.py"] == b"new hook\n"
    assert ".agents/hooks/old_hook.py" not in files
    assert not (home / ".agents" / "hooks" / "copilot").exists()
    assert files[".agents/bin/update-global.sh"] == b"updater v2\n"
    assert files[".agents/skills/alpha/references/new.md"] == b"new reference\n"
    assert ".agents/skills/alpha/references/old.md" not in files
    assert not (home / ".agents" / "skills" / "beta").exists()
    assert not (home / ".agents" / "skills" / "gamma").exists()
    assert files[".agents/skills/delta/SKILL.md"] == b"delta v1\n"
    assert files[".agents/skills/mine/SKILL.md"] == USER_SKILL.encode("utf-8")
    assert ".agents/agents/d.md" not in files
    assert ".claude/agents/b.md" not in files
    assert files[".claude/agents/mine.md"] == b"my own subagent\n"
    assert files[".claude/settings.json"] == USER_SETTINGS.encode("utf-8")
    assert files[".copilot/agents/a.agent.md"] == b"copilot a v2\n"
    assert files[".agents/.upstream-commit"] == f"{second}\n".encode("ascii")


@pytest.mark.parametrize("implementation", IMPLEMENTATIONS)
def test_a_dry_run_writes_nothing_and_lists_what_the_update_does(released, implementation):
    # Given a second upstream release
    repo, home, first = released
    release_second(repo)
    before = snapshot(home)

    # When
    planned = run_updater(implementation, home, str(repo), dry_run=True)

    # Then nothing changed, and the real run does exactly what the dry run listed
    assert planned.returncode == 0, planned.stderr
    assert snapshot(home) == before
    assert "Dry run, nothing was written. Would update 7, add 2, remove 3." in planned.stdout

    applied = run_updater(implementation, home, str(repo))

    assert applied.returncode == 0, applied.stderr
    assert action_lines(planned.stdout) == action_lines(applied.stdout)


@pytest.mark.parametrize("implementation", IMPLEMENTATIONS)
def test_uncommitted_work_in_the_source_never_reaches_the_home(released, implementation):
    # Given a source checkout with an edited and an untracked hook, neither committed
    repo, home, first = released
    write_files(repo, {".agents/hooks/preflight_gate.py": "uncommitted\n", ".agents/hooks/dirty.py": "untracked\n"})

    # When
    result = run_updater(implementation, home, str(repo))

    # Then
    assert result.returncode == 0, result.stderr
    assert (home / ".agents" / "hooks" / "preflight_gate.py").read_bytes() == b"gate v1\n"
    assert not (home / ".agents" / "hooks" / "dirty.py").exists()


@pytest.mark.parametrize("implementation", IMPLEMENTATIONS)
def test_an_unknown_previous_commit_removes_nothing(released, implementation):
    # Given an install whose recorded commit the source does not know
    repo, home, first = released
    release_second(repo)
    (home / ".agents" / ".upstream-commit").write_bytes(b"0" * 40 + b"\n")

    # When
    result = run_updater(implementation, home, str(repo))

    # Then files upstream removed stay, because nothing proves they came from upstream
    assert result.returncode == 0, result.stderr
    assert (home / ".agents" / "hooks" / "old_hook.py").exists()
    assert "remove " not in result.stdout
    assert "the previously installed commit is unknown here" in result.stdout
    assert "skip    ~/.agents/skills/delta (not an upstream skill)" in result.stdout


@pytest.mark.parametrize("implementation", IMPLEMENTATIONS)
def test_a_home_without_an_install_exits_1(tmp_path, implementation):
    # Given
    repo, first = make_upstream(tmp_path)
    home = tmp_path / "empty-home"
    home.mkdir()

    # When
    result = run_updater(implementation, home, str(repo))

    # Then
    assert result.returncode == 1
    assert "no global install" in result.stderr
    assert snapshot(home) == {}


@pytest.mark.skipif(SH is None or PWSH is None, reason="needs both sh and pwsh")
@pytest.mark.parametrize("dry_run", [True, False])
def test_both_implementations_print_the_same_report(tmp_path, dry_run):
    # Given two identical homes behind the same second release
    repo, first = make_upstream(tmp_path)
    homes = {}
    for implementation in ("sh", "pwsh"):
        homes[implementation] = install_home(tmp_path / implementation, repo, first)
    release_second(repo)

    # When
    outputs = {name: run_updater(name, home, str(repo), dry_run=dry_run) for name, home in homes.items()}

    # Then
    assert outputs["sh"].returncode == outputs["pwsh"].returncode == 0
    assert report_lines(outputs["sh"].stdout) == report_lines(outputs["pwsh"].stdout)
    assert snapshot(homes["sh"]) == snapshot(homes["pwsh"])


def drop_object(repo: Path, revision: str) -> str:
    """Delete the loose object a revision names, so git fails on the one read that needs it."""
    oid = git(repo, "rev-parse", revision)
    loose = repo / ".git" / "objects" / oid[:2] / oid[2:]
    loose.chmod(0o644)
    loose.unlink()

    return oid


@pytest.mark.parametrize("implementation", IMPLEMENTATIONS)
def test_a_user_skill_named_only_deep_inside_an_upstream_path_is_not_upstream(tmp_path, implementation):
    # Given an upstream that once shipped .agents/skills/mine/ nested inside another skill, never at the top
    repo, first = make_upstream(tmp_path)
    write_files(repo, {".agents/skills/alpha/references/.agents/skills/mine/SKILL.md": "nested\n"})
    first = commit_all(repo, "nested path")
    home = install_home(tmp_path, repo, first)
    release_second(repo)

    # When
    result = run_updater(implementation, home, str(repo))

    # Then the user's own skill is skipped as theirs, not kept as a removed upstream one
    assert result.returncode == 0, result.stderr
    assert "skip    ~/.agents/skills/mine (not an upstream skill)" in result.stdout
    assert "keep    ~/.agents/skills/mine" not in result.stdout


@pytest.mark.parametrize("implementation", IMPLEMENTATIONS)
def test_a_failed_listing_of_the_previous_commit_names_the_commit(released, implementation):
    # Given a previous commit whose root tree git can no longer read
    repo, home, first = released
    release_second(repo)
    drop_object(repo, f"{first}^{{tree}}")

    # When
    result = run_updater(implementation, home, str(repo))

    # Then
    assert result.returncode == 1
    assert f"update-global: git ls-tree failed at {first}" in result.stderr


@pytest.mark.parametrize("implementation", IMPLEMENTATIONS)
def test_a_failed_wiring_diff_names_both_commits(released, implementation):
    # Given a previous commit whose docs tree, read only by the wiring diff, git can no longer read
    repo, home, first = released
    write_files(repo, {"docs/GLOBAL_SETUP.md": "guide v2\n"})
    second = release_second(repo)
    drop_object(repo, f"{first}:docs")

    # When
    result = run_updater(implementation, home, str(repo))

    # Then
    assert result.returncode == 1
    assert f"update-global: git diff failed between {first} and {second}" in result.stderr
