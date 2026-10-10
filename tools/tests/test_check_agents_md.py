"""Tests for tools/check-agents-md.py.

The script's filename carries a hyphen, so it is loaded in-process via
importlib rather than a normal `import` statement, the same technique
tests/test_check_badges.py uses for its own hyphenated sibling. Every case
runs the script as a child process against a throwaway git repository, because
the guard reads what git tracks rather than what sits on disk. The last test
runs the guard over the real repository, so an instruction file that outgrows
its limit can never reach a green suite.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import REPO_ROOT, SUBPROCESS_TIMEOUT_SECONDS

CHECK_AGENTS_MD = REPO_ROOT / "tools" / "check-agents-md.py"


def _load_check_agents_md_module():
    spec = importlib.util.spec_from_file_location("check_agents_md", CHECK_AGENTS_MD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


GUARD = _load_check_agents_md_module()


def _lines(count: int) -> str:
    return "".join(f"line {number}\n" for number in range(count))


class _GuardRepository:
    def __init__(self, root: Path) -> None:
        self.root = root
        subprocess.run(["git", "init", "-q", str(root)], check=True)

    def track(self, relative: str, content: str | bytes) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8", newline="\n")
        subprocess.run(["git", "-C", str(self.root), "add", "--", relative], check=True)

        return path

    def untracked(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")


def _run_guard(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECK_AGENTS_MD), "--root", str(root)],
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


@pytest.fixture
def repo(tmp_path: Path) -> _GuardRepository:
    return _GuardRepository(tmp_path / "repo")


def test_small_agents_files_and_no_claude_md_pass(repo):
    repo.track("AGENTS.md", _lines(10))
    repo.track("module/AGENTS.md", _lines(10))

    result = _run_guard(repo.root)

    _assert_passes(result)


def test_tracked_claude_md_at_the_root_fails(repo):
    repo.track("AGENTS.md", _lines(10))
    repo.track("CLAUDE.md", "@AGENTS.md\n")

    result = _run_guard(repo.root)

    _assert_fails_naming(result, "CLAUDE.md", "switches off Claude Code's native AGENTS.md loading")


def test_tracked_claude_md_under_dot_claude_fails(repo):
    repo.track("AGENTS.md", _lines(10))
    repo.track(".claude/CLAUDE.md", "@../AGENTS.md\n")

    result = _run_guard(repo.root)

    _assert_fails_naming(result, ".claude/CLAUDE.md")


def test_untracked_claude_md_does_not_count(repo):
    repo.track("AGENTS.md", _lines(10))
    repo.untracked("CLAUDE.md", "@AGENTS.md\n")

    result = _run_guard(repo.root)

    _assert_passes(result)


def test_tracked_claude_md_deleted_from_the_working_tree_does_not_count(repo):
    repo.track("AGENTS.md", _lines(10))
    repo.track(".claude/CLAUDE.md", "@../AGENTS.md\n").unlink()

    result = _run_guard(repo.root)

    _assert_passes(result)


def test_root_agents_md_one_line_under_the_limit_passes(repo):
    repo.track("AGENTS.md", _lines(GUARD.ROOT_MAX_LINES - 1))

    result = _run_guard(repo.root)

    _assert_passes(result)


def test_root_agents_md_exactly_at_the_line_limit_fails(repo):
    repo.track("AGENTS.md", _lines(GUARD.ROOT_MAX_LINES))

    result = _run_guard(repo.root)

    _assert_fails_naming(result, "AGENTS.md has 200 lines", "fewer than 200")


def test_root_agents_md_one_byte_under_the_size_limit_passes(repo):
    repo.track("AGENTS.md", b"x" * (GUARD.ROOT_MAX_BYTES - 1))

    result = _run_guard(repo.root)

    _assert_passes(result)


def test_root_agents_md_exactly_at_the_size_limit_fails(repo):
    repo.track("AGENTS.md", b"x" * GUARD.ROOT_MAX_BYTES)

    result = _run_guard(repo.root)

    _assert_fails_naming(result, "AGENTS.md is 32768 bytes", "under 32768 bytes")


def test_template_at_the_root_is_held_to_the_root_limit(repo):
    repo.track("AGENTS.md", _lines(10))
    repo.track("AGENTS.md.example", _lines(GUARD.ROOT_MAX_LINES))

    result = _run_guard(repo.root)

    _assert_fails_naming(result, "AGENTS.md.example has 200 lines", "fewer than 200")


def test_template_one_line_under_the_root_limit_passes(repo):
    repo.track("AGENTS.md", _lines(10))
    repo.track("AGENTS.md.example", _lines(GUARD.ROOT_MAX_LINES - 1))

    result = _run_guard(repo.root)

    _assert_passes(result)


def test_nested_agents_md_one_line_under_the_limit_passes(repo):
    repo.track("AGENTS.md", _lines(10))
    repo.track("module/sub/AGENTS.md", _lines(GUARD.NESTED_MAX_LINES - 1))

    result = _run_guard(repo.root)

    _assert_passes(result)


def test_nested_agents_md_exactly_at_the_line_limit_fails(repo):
    repo.track("AGENTS.md", _lines(10))
    repo.track("module/sub/AGENTS.md", _lines(GUARD.NESTED_MAX_LINES))

    result = _run_guard(repo.root)

    _assert_fails_naming(result, "module/sub/AGENTS.md has 60 lines", "fewer than 60")


def test_nested_agents_md_is_not_held_to_the_root_limit(repo):
    repo.track("AGENTS.md", _lines(10))
    repo.track("module/AGENTS.md", _lines(GUARD.NESTED_MAX_LINES + 50))

    result = _run_guard(repo.root)

    _assert_fails_naming(result, "module/AGENTS.md has 110 lines")


def test_last_line_without_a_newline_still_counts(repo):
    repo.track("AGENTS.md", _lines(GUARD.ROOT_MAX_LINES - 1) + "last")

    result = _run_guard(repo.root)

    _assert_fails_naming(result, "AGENTS.md has 200 lines")


def test_every_failure_is_reported_in_one_run(repo):
    repo.track("AGENTS.md", _lines(GUARD.ROOT_MAX_LINES))
    repo.track("module/AGENTS.md", _lines(GUARD.NESTED_MAX_LINES))
    repo.track("CLAUDE.md", "@AGENTS.md\n")

    result = _run_guard(repo.root)

    _assert_fails_naming(result, "CLAUDE.md", "AGENTS.md has 200 lines", "module/AGENTS.md has 60 lines")


def test_a_directory_that_is_not_a_git_repository_exits_2(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()

    result = _run_guard(outside)

    assert result.returncode == 2, result.stdout + result.stderr


def test_the_real_repository_passes():
    result = _run_guard(REPO_ROOT)

    _assert_passes(result)
