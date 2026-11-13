"""Tests for tools/check_versions.py, the guard that every changed plugin raises its version.

Each test builds a small repository with a master branch, branches off it,
changes one item, and runs the guard against the merge base, so every item
kind is seen to fail without a raise and pass with one.
"""

import json
import os
import pathlib
import re
import subprocess

import pytest

import check_versions as guard
from tests.test_gen_plugins import agent, build_lab, edit_map, write

IDENTITY = ("-c", "user.name=test", "-c", "user.email=test@example.invalid")


def git(root: pathlib.Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *IDENTITY, *args], capture_output=True, check=True)


def write_marketplace(root: pathlib.Path) -> None:
    """The marketplace the generator renders for root, written where the repository commits it."""
    write(root / guard.gen_plugins.MARKETPLACE_FILE, guard.gen_plugins.render_text(guard.gen_plugins.marketplace(guard.gen_plugins.load_sources(root))))


@pytest.fixture
def repository(tmp_path) -> pathlib.Path:
    """The lab repository with its marketplace committed on master, then checked out on a feature branch."""
    root = build_lab(tmp_path / "repo")
    write_marketplace(root)
    git(root, "init", "--quiet", "--initial-branch=master")
    git(root, "add", "--all")
    git(root, "commit", "--quiet", "-m", "base")
    git(root, "switch", "--quiet", "-c", "feature")
    return root


def run(root: pathlib.Path, commit: bool = True) -> tuple[list[str], dict[str, guard.Shipped]]:
    if commit:
        git(root, "add", "--all")
        git(root, "commit", "--quiet", "--allow-empty", "-m", "change")
    _commit, base, head, _note = guard.compare(root, "master")
    return guard.problems(base, head, guard.existing_tags(root)), head


def bump_skill(root: pathlib.Path, name: str, version: str) -> None:
    path = root / ".agents" / "skills" / name / "SKILL.md"
    path.write_text(re.sub(r'version: "[0-9.]+"', f'version: "{version}"', path.read_text(encoding="utf-8")), encoding="utf-8")


def append(path: pathlib.Path, text: str) -> None:
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")


def test_an_unchanged_branch_passes(repository):
    found, head = run(repository)

    assert found == []
    assert set(head) >= {"shared", "agent-pro", "hook-gate", "mcp-docs", "core"}


def test_a_changed_skill_that_kept_its_version_fails_by_name(repository):
    append(repository / ".agents" / "skills" / "solo" / "SKILL.md", "More.\n")

    found, _ = run(repository)

    assert len(found) == 1 and found[0].startswith("solo: changed since the base but still at 1.0.0")


def test_a_changed_skill_that_raised_its_version_passes(repository):
    append(repository / ".agents" / "skills" / "solo" / "SKILL.md", "More.\n")
    bump_skill(repository, "solo", "1.0.1")

    assert run(repository)[0] == []


def test_a_new_reference_file_in_a_skill_counts_as_a_change(repository):
    write(repository / ".agents" / "skills" / "own" / "references" / "deep.md", "# Deep\n")

    assert [p.split(":")[0] for p in run(repository)[0]] == ["own"]


def test_a_changed_canonical_subagent_must_raise_the_agent_plugin(repository):
    append(repository / "subagents" / "pro.md", "Another rule.\n")

    found, _ = run(repository)

    assert [p.split(":")[0] for p in found] == ["agent-pro"]


def test_a_subagent_that_now_preloads_another_skill_must_raise_the_agent_plugin(repository):
    agent(repository, "front", ["shared", "solo", "own"])
    edit_map(repository, "skills: [shared]}", "skills: [shared, own]}")
    edit_map(repository, "agents: [pro], skills: [own]}", "agents: [pro]}")

    found = run(repository)[0]

    assert any(p.startswith("agent-front:") for p in found)
    assert any(p.startswith("core:") for p in found) and any(p.startswith("py:") for p in found)


def test_a_changed_hook_script_must_raise_the_hook_version_in_the_map(repository):
    append(repository / ".agents" / "hooks" / "gate" / "gate.py", "print('more')\n")

    assert [p.split(":")[0] for p in run(repository)[0]] == ["hook-gate"]

    edit_map(repository, "{name: gate, version: 1.0.0,", "{name: gate, version: 1.1.0,")
    assert run(repository)[0] == []


def test_a_changed_hook_wiring_must_raise_the_hook_version(repository):
    settings = repository / ".claude" / "settings.json"
    settings.write_text(settings.read_text(encoding="utf-8").replace('"timeout": 10', '"timeout": 20'), encoding="utf-8")

    assert [p.split(":")[0] for p in run(repository)[0]] == ["hook-gate"]


def test_a_changed_server_block_must_raise_the_server_version(repository):
    write(repository / ".mcp.json", json.dumps({"mcpServers": {"docs": {"type": "http", "url": "https://docs.example/v2"}}}))

    assert [p.split(":")[0] for p in run(repository)[0]] == ["mcp-docs"]


def test_a_changed_bundle_membership_must_raise_the_bundle_version(repository):
    write(repository / ".agents" / "skills" / "extra" / "SKILL.md", '---\nname: extra\ndescription: Extra.\nmetadata:\n  version: "1.0.0"\n---\nBody.\n')
    edit_map(repository, "agents: [front], skills: [solo]}", "agents: [front], skills: [solo, extra]}")

    found = run(repository)[0]

    assert [p.split(":")[0] for p in found] == ["web"]


def test_a_new_plugin_with_a_version_passes(repository):
    write(repository / ".agents" / "skills" / "extra" / "SKILL.md", '---\nname: extra\ndescription: Extra.\nmetadata:\n  version: "1.0.0"\n---\nBody.\n')
    edit_map(repository, "agents: [front], skills: [solo]}", "agents: [front], skills: [solo, extra]}")
    edit_map(repository, "{name: web, version: 1.0.0,", "{name: web, version: 1.1.0,")

    found, head = run(repository)

    assert found == [] and head["extra"].version == "1.0.0"


def test_a_new_plugin_without_a_version_is_refused(repository):
    write(repository / ".agents" / "skills" / "extra" / "SKILL.md", "---\nname: extra\ndescription: Extra.\n---\nBody.\n")

    with pytest.raises(guard.gen_plugins.PluginMapError, match="metadata.version"):
        run(repository)


def test_a_lowered_version_fails_even_with_no_change(repository):
    git(repository, "switch", "--quiet", "master")
    bump_skill(repository, "own", "2.0.0")
    write_marketplace(repository)
    git(repository, *("commit", "--quiet", "-am", "raise own"))
    git(repository, "switch", "--quiet", "-C", "feature")
    bump_skill(repository, "own", "1.9.9")

    found = run(repository)[0]

    assert found == ["own: version 1.9.9 is lower than 2.0.0 on the base"]


def test_an_uncommitted_change_counts(repository):
    append(repository / ".agents" / "skills" / "solo" / "SKILL.md", "More.\n")

    assert [p.split(":")[0] for p in run(repository, commit=False)[0]] == ["solo"]


def test_a_change_behind_a_link_inside_the_repository_counts(repository):
    # Given the quality-loop layout: a skill whose tools folder is a link to a folder elsewhere in the repository
    write(repository / ".metrics" / "tools" / "run", "#!/bin/sh\n")
    os.symlink("../../../.metrics/tools", repository / ".agents" / "skills" / "solo" / "tools")
    bump_skill(repository, "solo", "1.1.0")
    write_marketplace(repository)
    run(repository)
    git(repository, "switch", "--quiet", "master")
    git(repository, "merge", "--quiet", "--ff-only", "feature")
    git(repository, "switch", "--quiet", "-c", "second")

    # When only the linked file changes
    append(repository / ".metrics" / "tools" / "run", "echo changed\n")

    # Then the skill that ships it has to raise its version
    assert [p.split(":")[0] for p in run(repository)[0]] == ["solo"]


def test_a_base_whose_map_breaks_a_rule_the_head_added_is_still_compared(repository, monkeypatch):
    # Given a base whose committed map the head's rules would refuse, here one with no hooks-all bundle
    git(repository, "switch", "--quiet", "master")
    edit_map(repository, "  - {name: hooks-all, version: 1.0.0, category: bundle, description: Hooks., dependencies: [hook-gate]}\n", "")
    git(repository, "commit", "--quiet", "-am", "a map from before hooks-all")
    git(repository, "switch", "--quiet", "-C", "feature")
    edit_map(repository, "  - {name: mcp-all,", "  - {name: hooks-all, version: 1.0.0, category: bundle, description: Hooks., dependencies: [hook-gate]}\n  - {name: mcp-all,")

    # When a skill changes without a raise
    append(repository / ".agents" / "skills" / "solo" / "SKILL.md", "More.\n")

    # Then the base is read from its committed marketplace, not rendered by the head's rules, and the change is caught
    assert [p.split(":")[0] for p in run(repository)[0]] == ["solo"]


def test_a_base_with_a_broken_marketplace_is_an_error(repository):
    git(repository, "switch", "--quiet", "master")
    (repository / ".claude-plugin" / "marketplace.json").write_text("{not json", encoding="utf-8")
    git(repository, "commit", "--quiet", "-am", "break it")
    git(repository, "switch", "--quiet", "-C", "feature")

    with pytest.raises(guard.VersionCheckError, match="marketplace.json"):
        run(repository)


def test_a_base_with_no_plugin_catalog_counts_every_plugin_as_new(tmp_path):
    # Given a master from before the marketplace, and a branch that adds the whole lab
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "--quiet", "--initial-branch=master")
    write(root / "README.md", "old\n")
    git(root, "add", "--all")
    git(root, "commit", "--quiet", "-m", "old")
    git(root, "switch", "--quiet", "-c", "feature")
    build_lab(root)
    git(root, "add", "--all")

    # When
    _commit, base, head, note = guard.compare(root, "master")

    # Then
    assert base == {} and "no committed .claude-plugin/marketplace.json" in note
    assert guard.problems(base, head) == []


@pytest.mark.parametrize(("lower", "higher"), [("1.9.0", "1.10.0"), ("1.0.9", "1.0.10"), ("0.9.9", "1.0.0"), ("2.0.0", "10.0.0")])
def test_versions_compare_as_numbers(lower, higher):
    assert guard.version_key(lower) < guard.version_key(higher)


def test_the_command_line_names_the_plugin_and_exits_1(repository, monkeypatch, capsys):
    append(repository / ".agents" / "skills" / "solo" / "SKILL.md", "More.\n")
    git(repository, "add", "--all")
    git(repository, "commit", "--quiet", "-m", "change")
    monkeypatch.setattr(guard, "ROOT", repository)

    code = guard.main(["--base", "master"])

    out = capsys.readouterr().out
    assert code == 1
    assert "::error::solo: changed since the base" in out
    assert "Violations: 1." in out


def test_an_unknown_base_exits_2(repository, monkeypatch, capsys):
    monkeypatch.setattr(guard, "ROOT", repository)

    assert guard.main(["--base", "no-such-branch"]) == 2
    assert "merge-base" in capsys.readouterr().err


def test_a_base_with_a_map_but_no_committed_marketplace_counts_every_plugin_as_new(repository):
    # Given the first pull request: the base holds an older plugin map and no marketplace yet
    git(repository, "switch", "--quiet", "master")
    git(repository, "rm", "--quiet", "-r", ".claude-plugin")
    git(repository, "commit", "--quiet", "-m", "no marketplace yet")
    git(repository, "switch", "--quiet", "-C", "feature")
    append(repository / ".agents" / "skills" / "solo" / "SKILL.md", "More.\n")

    found, _head = run(repository)
    _commit, base, _head, note = guard.compare(repository, "master")

    assert found == [] and base == {} and "no committed" in note


def test_a_submodule_is_left_out_of_the_working_tree_copy(tmp_path):
    # Given a tracked gitlink whose folder holds a repository of its own
    root = tmp_path / "repo"
    write(root / "file.txt", "x\n")
    git(tmp_path, "init", "--quiet", str(root))
    sub = root / "sub"
    git(tmp_path, "init", "--quiet", str(sub))
    write(sub / "inner.txt", "y\n")
    git(sub, "add", "--all")
    git(sub, "commit", "--quiet", "-m", "inner")
    git(root, "add", "file.txt")
    git(root, "update-index", "--add", "--cacheinfo", f"160000,{subprocess.run(['git', '-C', str(sub), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()},sub")

    # When
    target = tmp_path / "copy"
    guard.copy_tracked(root, target)

    # Then
    assert sorted(p.relative_to(target).as_posix() for p in target.rglob("*")) == ["file.txt"]


def test_a_link_loop_inside_a_plugin_folder_is_read_once(tmp_path):
    folder = tmp_path / ".agents" / "skills" / "solo"
    write(folder / "SKILL.md", "x\n")
    os.symlink(".", folder / "loop")

    files = [relative for relative, _file in guard.shipped_files(tmp_path, pathlib.PurePosixPath(".agents/skills/solo"))]

    assert files == [".agents/skills/solo/SKILL.md"]


def test_a_new_plugin_whose_release_tag_already_exists_fails(repository):
    # Given a tag left by an earlier plugin of the same name and version
    git(repository, "tag", "extra--v1.0.0")
    write(repository / ".agents" / "skills" / "extra" / "SKILL.md", '---\nname: extra\ndescription: Extra.\nmetadata:\n  version: "1.0.0"\n---\nBody.\n')
    edit_map(repository, "agents: [front], skills: [solo]}", "agents: [front], skills: [solo, extra]}")
    edit_map(repository, "{name: web, version: 1.0.0,", "{name: web, version: 1.1.0,")

    found = run(repository)[0]

    assert found == ["extra: the tag extra--v1.0.0 already exists, so 1.0.0 was released before, raise it"]


def test_a_raised_version_whose_tag_already_exists_fails(repository):
    git(repository, "tag", "solo--v1.0.1")
    append(repository / ".agents" / "skills" / "solo" / "SKILL.md", "More.\n")
    bump_skill(repository, "solo", "1.0.1")

    assert [p.split(":")[0] for p in run(repository)[0]] == ["solo"]


@pytest.mark.parametrize("version", ["1.0.1\u0661", "\u0661.0.0", "1.0", "1.0.0-rc1"])
def test_a_version_that_is_not_ascii_major_minor_patch_is_an_error(version):
    with pytest.raises(guard.VersionCheckError, match="MAJOR.MINOR.PATCH"):
        guard.version_key(version)
