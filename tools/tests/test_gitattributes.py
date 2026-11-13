"""The generated trees are marked linguist-generated in the root .gitattributes, so GitHub folds them in a diff."""

import subprocess

import pytest

from tests.conftest import REPO_ROOT

GENERATED = [
    ".claude-plugin/marketplace.json",
    ".claude/agents/python-pro/python-pro.md",
    ".agents/agents/python-pro.md",
    ".codex/agents/python-pro.toml",
    ".github/agents/python-pro.agent.md",
]


@pytest.mark.parametrize("path", GENERATED)
def test_a_generated_file_is_marked_generated(path):
    result = subprocess.run(["git", "-C", str(REPO_ROOT), "check-attr", "linguist-generated", "--", path], capture_output=True, text=True, check=True)

    assert result.stdout.strip() == f"{path}: linguist-generated: true"


@pytest.mark.parametrize("path", ["subagents/python-pro.md", "tools/plugins.yaml", ".agents/skills/python-patterns/SKILL.md"])
def test_a_canonical_file_is_not(path):
    result = subprocess.run(["git", "-C", str(REPO_ROOT), "check-attr", "linguist-generated", "--", path], capture_output=True, text=True, check=True)

    assert result.stdout.strip().endswith("unspecified")
