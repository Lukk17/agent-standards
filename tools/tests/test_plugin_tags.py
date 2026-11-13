"""Tests for tools/plugin_tags.py, which lists the plugin release tags the Plugins workflow creates."""

import json
import subprocess

import plugin_tags
from tests.conftest import REPO_ROOT

DOCUMENT = {"plugins": [{"name": "python-patterns", "version": "1.2.0"}, {"name": "agent-python-pro", "version": "1.0.0"}]}


def test_every_plugin_version_gets_a_name_dash_dash_v_tag():
    assert plugin_tags.tag_names(DOCUMENT) == ["python-patterns--v1.2.0", "agent-python-pro--v1.0.0"]


def test_only_a_version_with_no_tag_is_listed():
    assert plugin_tags.missing(DOCUMENT, {"python-patterns--v1.1.0", "agent-python-pro--v1.0.0"}) == ["python-patterns--v1.2.0"]


def test_the_existing_tags_are_read_from_git(tmp_path):
    identity = ("-c", "user.name=t", "-c", "user.email=t@example.invalid")
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), *identity, "commit", "--quiet", "--allow-empty", "-m", "x"], check=True)
    for tag in ("core--v1.0.0", "v0.2.0"):
        subprocess.run(["git", "-C", str(tmp_path), "tag", tag], check=True)

    assert plugin_tags.existing_tags(tmp_path) == {"core--v1.0.0"}


def test_the_committed_marketplace_yields_one_tag_per_plugin(capsys):
    document = json.loads((REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))

    assert plugin_tags.main(["--all"]) == 0
    assert capsys.readouterr().out.splitlines() == plugin_tags.tag_names(document)
    assert len(set(plugin_tags.tag_names(document))) == len(document["plugins"])
