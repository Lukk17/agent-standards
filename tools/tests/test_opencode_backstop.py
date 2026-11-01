"""Tests for the native edit backstop in .opencode/opencode.json and its OpenCode 1.x variant.

The backstop denies the main session a native edit of any project file but tasks.md, for a runtime where the
plugin gate never fires. One shape cannot serve every runtime, measured on OpenCode 1.18.25 and 1.19.5,
OpenCode 2.0.28 and 2.2.5, and Kilo Code 7.5.5 and 7.8.18:

- OpenCode 1.x refuses to start on a `permissions` key, at the top level or under `agent.<name>`, in any
  configuration file it reads ("V2 permissions are not supported by OpenCode V1").
- OpenCode 2.x matches an in-project path relative to the session directory and an outside path as an absolute
  one, so `/*` lets an outside write through. 1.x matches every path relative to the worktree, so an outside
  path starts with `../`, and allowing `../*` on 2.x would let a session started in a subfolder edit the rest
  of the project.
- Kilo Code reads only the root opencode.json, and re-applies its project rules after a subagent's own, so an
  edit deny there takes write and edit away from every writing subagent.

So the default ships the 2.x form, `.opencode/opencode.json.v1` ships the 1.x form a 1.x user copies over it,
and the root file carries no edit rule at all. docs/agent-compatibility.md records the measurements.
"""

import json
import shlex

import pytest

from tests.conftest import REPO_ROOT

ROOT_CONFIG = REPO_ROOT / "opencode.json"
DEFAULT_BACKSTOP = REPO_ROOT / ".opencode" / "opencode.json"
V1_BACKSTOP = REPO_ROOT / ".opencode" / "opencode.json.v1"
IMPORT_DOCUMENTS = ("README.md", "docs/AGENT_TOOLING.md", "docs/AGENTS-UPDATE.md")

# Every project file OpenCode 1.x reads as configuration, the default backstop aside, which a 1.x user replaces.
V1_READ_CONFIGS = (
    ROOT_CONFIG,
    REPO_ROOT / "opencode.jsonc",
    REPO_ROOT / ".opencode" / "opencode.jsonc",
    V1_BACKSTOP,
)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def v2_permission_keys(config):
    """Where a configuration carries the 2.x `permissions` key that OpenCode 1.x refuses to start on."""
    top = ["permissions"] if "permissions" in config else []
    per_agent = [f"agent.{name}.permissions" for name, agent in config.get("agent", {}).items() if "permissions" in agent]

    return top + per_agent


@pytest.mark.parametrize("path", [path for path in V1_READ_CONFIGS if path.exists()], ids=lambda path: path.name)
def test_no_file_a_1x_user_keeps_carries_the_v2_permissions_key(path):
    # Given a configuration file OpenCode 1.x reads once the 1.x variant is in place
    config = load(path)

    # When/Then it carries no key that makes 1.x refuse the whole project
    assert v2_permission_keys(config) == []


def test_the_default_backstop_denies_project_edits_but_tasks_md_and_outside_paths_in_the_2x_form():
    # Given the default every import delivers
    config = load(DEFAULT_BACKSTOP)

    # When
    rules = [(rule["action"], rule["resource"], rule["effect"]) for rule in config["permissions"]]

    # Then the last match wins: deny first, then the absolute outside paths and the task list
    assert rules == [("edit", "*", "deny"), ("edit", "/*", "allow"), ("edit", "tasks.md", "allow")]
    assert set(config) == {"$schema", "permissions"}


def test_the_v1_variant_holds_the_same_backstop_in_the_1x_form():
    # Given the variant a 1.x user copies over the default
    config = load(V1_BACKSTOP)

    # When
    rules = list(config["permission"]["edit"].items())

    # Then outside paths, which 1.x sees relative to the worktree, stay open
    assert rules == [("*", "deny"), ("../*", "allow"), ("tasks.md", "allow")]
    assert set(config) == {"$schema", "permission"}
    assert set(config["permission"]) == {"edit"}


def test_the_root_config_carries_no_edit_rule_that_kilo_code_would_apply_to_writing_subagents():
    # Given the one OpenCode file Kilo Code reads
    edit = load(ROOT_CONFIG).get("permission", {}).get("edit", "allow")

    # When/Then edits stay allowed there, so no subagent loses its write and edit tools
    assert edit == "allow"


def import_commands():
    """Every git checkout of upstream in the documents that describe an import or an update, as word lists."""
    return [
        shlex.split(line.strip().split(" -- ", 1)[1])
        for document in IMPORT_DOCUMENTS
        for line in (REPO_ROOT / document).read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("git checkout agent-standards/master -- ")
    ]


def test_every_import_that_delivers_the_default_backstop_delivers_the_1x_variant_too():
    # Given every import and update command a consumer copies
    commands = import_commands()

    # When
    delivering = [words for words in commands if {".opencode", ".opencode/opencode.json"} & set(words)]

    # Then at least one delivers the backstop, and each one that does carries the variant beside it
    assert delivering
    for words in delivering:
        assert {".opencode", ".opencode/opencode.json.v1"} & set(words), words
