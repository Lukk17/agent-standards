"""Tests for tools/update_quality_tools.py, which copies newer pinned commits of Robert C. Martin's tools.

Every case runs against local git repositories standing in for his three, named in a VERSIONS file of a throwaway
tools folder, so no case touches the network or the real `.metrics/tools`.
"""

import importlib.util
import subprocess
import sys

import pytest
from tests.conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "tools" / "update_quality_tools.py"
LICENSE_0BSD = "BSD Zero Clause License\n\nCopyright (C) 2026 by Robert C. Martin\n"


def _load():
    spec = importlib.util.spec_from_file_location("update_quality_tools", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve the module of a class through sys.modules
    spec.loader.exec_module(module)
    return module


UPDATE = _load()


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def upstream(root, tool, files):
    """A local repository standing in for one of the tools, with one commit holding `files`."""
    repo = root / "upstream" / tool
    repo.mkdir(parents=True)
    git("init", "-q", cwd=repo)
    for relative, text in files.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (repo / tool).chmod(0o755)
    git("add", "-A", cwd=repo)
    git("-c", "user.name=u", "-c", "user.email=u@example.invalid", "commit", "-q", "-m", "v", cwd=repo)
    return repo, git("rev-parse", "HEAD", cwd=repo)


@pytest.fixture
def tools(tmp_path):
    """A tools folder pinned to old commits of three local upstreams, each upstream one commit ahead."""
    folder = tmp_path / "tools"
    folder.mkdir()
    lines = []
    commits = {}
    for tool in UPDATE.TOOLS:
        repo, commit = upstream(tmp_path, tool, {"LICENSE": LICENSE_0BSD, tool: "#!/bin/sh\n", "src/a.py": "x = 1\n"})
        (folder / tool).mkdir()
        (folder / tool / "old.py").write_text("old\n", encoding="utf-8")
        lines.append(f"{tool} {repo.as_uri()} {'0' * 40}")
        commits[tool] = commit
    (folder / "VERSIONS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (folder / "constraints.txt").write_text("tree-sitter==0.26.0\ntree-sitter-language-pack==1.25.0\ncoverage==7.17.2\n", encoding="utf-8")
    return folder, commits


def test_versions_round_trip():
    text = "crapper https://github.com/unclebob/crapper " + "a" * 40 + "\n"

    pins = UPDATE.parse_versions(text)

    assert pins == {"crapper": UPDATE.Pin("crapper", "https://github.com/unclebob/crapper", "a" * 40)}
    assert UPDATE.render_versions(pins.values()) == text


@pytest.mark.parametrize("text", ["crapper https://x\n", "crapper https://x not-a-commit\n", "other https://x " + "a" * 40 + "\n"])
def test_a_malformed_versions_file_is_refused(text):
    with pytest.raises(UPDATE.UpdateError):
        UPDATE.parse_versions(text)


def test_constraints_keep_their_order_and_take_only_the_resolved_versions():
    old = "tree-sitter==0.26.0\ntree-sitter-language-pack==1.25.0\ncoverage==7.17.2\n"

    new = UPDATE.updated_constraints(old, {"tree-sitter": "0.27.1", "tree-sitter-language-pack": "1.26.0", "pip": "26.0"})

    assert new == "tree-sitter==0.27.1\ntree-sitter-language-pack==1.26.0\ncoverage==7.17.2\n"


def test_the_named_commits_replace_each_tool_and_versions_records_them(tools):
    folder, commits = tools

    code = UPDATE.main(["--tools-dir", str(folder), "--no-verify", *[f"--{tool}={commit}" for tool, commit in commits.items()]])

    assert code == 0
    pins = UPDATE.parse_versions((folder / "VERSIONS").read_text(encoding="utf-8"))
    assert {tool: pin.commit for tool, pin in pins.items()} == commits
    for tool in UPDATE.TOOLS:
        assert sorted(p.name for p in (folder / tool).iterdir()) == sorted(["LICENSE", "src", tool])
        assert (folder / tool / tool).stat().st_mode & 0o111


def test_without_commits_each_tool_follows_its_upstream_head(tools):
    folder, commits = tools

    UPDATE.main(["--tools-dir", str(folder), "--no-verify"])

    pins = UPDATE.parse_versions((folder / "VERSIONS").read_text(encoding="utf-8"))
    assert {tool: pin.commit for tool, pin in pins.items()} == commits


def test_a_tool_whose_licence_is_no_longer_0bsd_stops_the_update_before_anything_changes(tools, tmp_path):
    folder, _commits = tools
    repo = tmp_path / "upstream" / "dryer"
    (repo / "LICENSE").write_text("All rights reserved\n", encoding="utf-8")
    git("-c", "user.name=u", "-c", "user.email=u@example.invalid", "commit", "-q", "-am", "relicense", cwd=repo)
    before = (folder / "VERSIONS").read_text(encoding="utf-8")

    code = UPDATE.main(["--tools-dir", str(folder), "--no-verify"])

    assert code == 2
    assert (folder / "VERSIONS").read_text(encoding="utf-8") == before
    assert (folder / "crapper" / "old.py").exists()


def test_a_tool_that_brings_a_claude_md_is_refused(tools, tmp_path):
    folder, _commits = tools
    repo = tmp_path / "upstream" / "mutator"
    (repo / "CLAUDE.md").write_text("notes\n", encoding="utf-8")
    git("add", "CLAUDE.md", cwd=repo)
    git("-c", "user.name=u", "-c", "user.email=u@example.invalid", "commit", "-q", "-m", "notes", cwd=repo)

    assert UPDATE.main(["--tools-dir", str(folder), "--no-verify"]) == 2
    assert (folder / "mutator" / "old.py").exists()


def test_an_unknown_commit_is_a_usage_error(tools):
    folder, _commits = tools

    assert UPDATE.main(["--tools-dir", str(folder), "--no-verify", "--crapper=" + "f" * 40]) == 2


def test_every_tool_suite_runs_even_after_one_fails(tmp_path):
    ran = []

    def run(argv, cwd):
        ran.append(cwd.name)
        return 1 if cwd.name == "crapper" else 0

    results = UPDATE.run_suites(tmp_path / "python", tmp_path, run)

    assert ran == list(UPDATE.TOOLS)
    assert results == {"crapper": False, "dryer": True, "mutator": True}
