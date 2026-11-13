"""Tests for tools/check_tags.py against a throwaway repository with a master history and tags."""

import json
import subprocess

import pytest

import check_tags

IDENTITY = ("-c", "user.name=test", "-c", "user.email=test@example.invalid")


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *IDENTITY, *args], capture_output=True, text=True, check=True).stdout.strip()


def release(root, versions, message):
    """Commit a marketplace listing these plugin versions on the current branch and return the commit."""
    path = root / ".claude-plugin" / "marketplace.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"name": "lab", "plugins": [{"name": n, "version": v} for n, v in versions.items()]}), encoding="utf-8")
    git(root, "add", "--all")
    git(root, "commit", "--quiet", "-m", message)
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path):
    """master: core 0.9.0 untagged, then core 1.0.0 and skill 1.0.0 tagged, then core 1.1.0 tagged."""
    root = tmp_path / "repo"
    git(tmp_path, "init", "--quiet", "--initial-branch=master", str(root))
    release(root, {"core": "0.9.0"}, "before tagging")
    first = release(root, {"core": "1.0.0", "skill": "1.0.0"}, "first tagged")
    git(root, "tag", "core--v1.0.0", first)
    git(root, "tag", "skill--v1.0.0", first)
    second = release(root, {"core": "1.1.0", "skill": "1.0.0"}, "core raised")
    git(root, "tag", "core--v1.1.0", second)
    return root


def problems(root):
    return check_tags.check(root, "master")


def test_a_consistent_history_passes(repo):
    assert problems(repo) == []


def test_a_version_older_than_the_first_tag_is_not_asked_for(repo):
    assert not any("0.9.0" in p for p in problems(repo))


def test_a_deleted_tag_is_named(repo):
    git(repo, "tag", "-d", "core--v1.0.0")

    assert problems(repo) == ["tag core--v1.0.0: missing, though master shipped core 1.0.0 after the first tag and lists it at 1.1.0"]


def test_a_moved_tag_is_named(repo):
    git(repo, "tag", "-f", "core--v1.0.0", "HEAD")

    assert problems(repo) == ["tag core--v1.0.0: the marketplace at " + git(repo, "rev-parse", "--short=12", "HEAD") + " lists core at 1.1.0"]


def test_a_tag_off_master_is_named(repo):
    git(repo, "switch", "--quiet", "-c", "side")
    side = release(repo, {"core": "1.2.0", "skill": "1.0.0"}, "side")
    git(repo, "tag", "core--v1.2.0", side)
    git(repo, "switch", "--quiet", "master")

    assert problems(repo) == [f"tag core--v1.2.0: points at {side[:12]}, which is not on master"]


@pytest.mark.parametrize("name", ["core--v1.0", "Core--v1.0.0", "core--v1.0.1١", "core--vnext"])
def test_a_tag_that_is_not_name_dash_dash_v_version_is_named(repo, name):
    git(repo, "tag", name)

    assert f"tag {name}: not <name>--v<version>" in problems(repo)


def test_a_tag_for_a_plugin_the_commit_does_not_list_is_named(repo):
    git(repo, "tag", "ghost--v1.0.0", "HEAD")

    assert problems(repo) == ["tag ghost--v1.0.0: the marketplace at " + git(repo, "rev-parse", "--short=12", "HEAD") + " does not list ghost"]


def test_a_removed_plugin_keeps_valid_tags_and_needs_no_new_one(repo):
    release(repo, {"core": "1.1.0"}, "skill removed")

    assert problems(repo) == []


def test_a_repository_with_no_plugin_tag_passes(tmp_path):
    root = tmp_path / "repo"
    git(tmp_path, "init", "--quiet", "--initial-branch=master", str(root))
    release(root, {"core": "1.0.0"}, "only")

    assert problems(root) == []


def test_the_command_line_names_the_tag_and_exits_1(repo, monkeypatch, capsys):
    git(repo, "tag", "-d", "core--v1.1.0")
    monkeypatch.setattr(check_tags, "ROOT", repo)

    assert check_tags.main(["--master", "master"]) == 1
    assert "::error::tag core--v1.1.0: missing" in capsys.readouterr().out


def test_an_unknown_master_ref_exits_2(repo, monkeypatch, capsys):
    monkeypatch.setattr(check_tags, "ROOT", repo)

    assert check_tags.main(["--master", "no-such-ref"]) == 2
    assert "ERROR" in capsys.readouterr().err


def test_a_tag_whose_name_starts_with_a_dash_resolves_to_its_commit_and_is_named(repo):
    # git tag refuses such a name, while update-ref writes it, and rev-parse reads a bare one as an option
    git(repo, "update-ref", "refs/tags/-core--v1.1.0", "HEAD")

    tags = {tag.name: tag.commit for tag in check_tags.plugin_tags(repo)}

    assert tags["-core--v1.1.0"] == git(repo, "rev-parse", "HEAD")
    assert "tag -core--v1.1.0: not <name>--v<version>" in problems(repo)
