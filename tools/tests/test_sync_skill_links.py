"""Tests for .agents/hooks/claude/sync_skill_links.py.

Driven as a subprocess with HOME and USERPROFILE pointing at a throwaway home,
because that is how Claude Code and the updaters run it. No test reads or
writes the real home directory.
"""

import os
import sys

import pytest

from tests.conftest import HOOKS_DIR, SYNC_SKILL_LINKS_HOOK
from tests.process_tree import run_bounded

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="the hook does nothing on Windows by design")


@pytest.fixture
def home(tmp_path):
    root = tmp_path / "home"
    (root / ".config" / "agents" / "skills").mkdir(parents=True)
    (root / ".claude").mkdir()

    return root


def source(home):
    return home / ".config" / "agents" / "skills"


def target(home):
    return home / ".claude" / "skills"


def add_skill(home, name):
    folder = source(home) / name
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text(f"---\nname: {name}\ndescription: test.\n---\n", encoding="utf-8")

    return folder


def run(home, stdin='{"hook_event_name": "SessionStart", "source": "startup"}', codex_home=None):
    environment = {key: value for key, value in os.environ.items() if key != "CODEX_HOME"}
    environment.update({"HOME": str(home), "USERPROFILE": str(home)})
    if codex_home is not None:
        environment["CODEX_HOME"] = str(codex_home)

    result = run_bounded(
        [sys.executable, "-S", "-E", str(SYNC_SKILL_LINKS_HOOK)],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
    )

    return result.returncode, result.stdout, result.stderr


def entries(home):
    return sorted(path.name for path in target(home).iterdir())


def test_every_skill_with_a_manifest_is_linked_into_a_real_directory(home):
    # Given two shared skills and no ~/.claude/skills yet
    add_skill(home, "alpha")
    add_skill(home, "beta")

    # When
    code, out, err = run(home)

    # Then
    assert (code, out) == (0, "")
    assert not target(home).is_symlink()
    assert entries(home) == ["alpha", "beta"]
    assert (target(home) / "alpha" / "SKILL.md").is_file()
    assert (target(home) / "alpha").resolve() == (source(home) / "alpha").resolve()
    assert "linked alpha" in err


def test_synced_trash_dot_entries_and_folders_without_a_manifest_are_not_linked(home):
    # Given folders Claude Code owns, a dot folder, and a folder that is not a skill
    for name in ("synced", "Synced", ".trash", ".hidden", "notes"):
        (source(home) / name).mkdir()
    (source(home) / "synced" / "SKILL.md").write_text("x", encoding="utf-8")
    add_skill(home, "alpha")

    # When
    code, _out, _err = run(home)

    # Then
    assert code == 0
    assert entries(home) == ["alpha"]


def test_a_link_into_the_source_whose_skill_is_gone_is_removed(home):
    # Given a skill that was linked and then removed upstream
    gone = add_skill(home, "gone")
    add_skill(home, "kept")
    run(home)
    (gone / "SKILL.md").unlink()
    gone.rmdir()

    # When
    code, _out, err = run(home)

    # Then
    assert code == 0
    assert entries(home) == ["kept"]
    assert "unlinked gone" in err


def test_real_directories_foreign_links_and_claude_owned_entries_are_never_touched(home, tmp_path):
    # Given a real skill directory, a link to somewhere else that no longer exists,
    # and Claude Code's own synced and .trash entries
    add_skill(home, "alpha")
    target(home).mkdir()
    own = target(home) / "my-own"
    own.mkdir()
    (own / "SKILL.md").write_text("mine", encoding="utf-8")
    foreign = target(home) / "foreign"
    foreign.symlink_to(tmp_path / "elsewhere" / "foreign", target_is_directory=True)
    (target(home) / "synced").mkdir()
    (target(home) / ".trash").symlink_to(source(home) / "missing", target_is_directory=True)

    # When
    code, _out, _err = run(home)

    # Then
    assert code == 0
    assert entries(home) == [".trash", "alpha", "foreign", "my-own", "synced"]
    assert (own / "SKILL.md").read_text(encoding="utf-8") == "mine"
    assert foreign.is_symlink()


def test_an_existing_entry_of_the_same_name_wins(home):
    # Given a user's own folder named like a shared skill
    add_skill(home, "alpha")
    (target(home) / "alpha").mkdir(parents=True)

    # When
    code, _out, _err = run(home)

    # Then it stays a real directory
    assert code == 0
    assert not (target(home) / "alpha").is_symlink()


def test_nothing_happens_while_the_skills_directory_is_itself_a_link(home, tmp_path):
    # Given the layout before the migration, a whole-directory link
    add_skill(home, "alpha")
    elsewhere = tmp_path / "legacy-skills"
    elsewhere.mkdir()
    target(home).symlink_to(elsewhere, target_is_directory=True)

    # When
    code, out, err = run(home)

    # Then
    assert (code, out, err) == (0, "", "")
    assert list(elsewhere.iterdir()) == []


def test_a_second_run_changes_nothing(home):
    add_skill(home, "alpha")
    run(home)

    code, out, err = run(home)

    assert (code, out, err) == (0, "", "")
    assert entries(home) == ["alpha"]


def test_a_missing_source_is_a_silent_no_op(tmp_path):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)

    code, out, err = run(home)

    assert (code, out, err) == (0, "", "")
    assert not target(home).exists()


def test_an_agent_that_is_not_installed_gets_no_skills_folder(tmp_path):
    # Given shared skills but neither a ~/.claude nor a Codex home
    home = tmp_path / "home"
    add_skill(home, "alpha")

    code, out, err = run(home)

    assert (code, out, err) == (0, "", "")
    assert not (home / ".claude").exists()
    assert not (home / ".config" / "codex").exists()


def test_the_codex_home_gets_its_own_links_and_keeps_its_system_skills(home):
    # Given CODEX_HOME at the guide's location, holding the bundled skills Codex writes itself
    codex_skills = home / ".config" / "codex" / "skills"
    (codex_skills / ".system" / "skill-creator").mkdir(parents=True)
    add_skill(home, "alpha")

    # When
    code, _out, _err = run(home, codex_home=home / ".config" / "codex")

    # Then the shared skill is linked beside .system, which stays a real directory
    assert code == 0
    assert sorted(path.name for path in codex_skills.iterdir()) == [".system", "alpha"]
    assert (codex_skills / "alpha").is_symlink()
    assert not (codex_skills / ".system").is_symlink()
    assert not (source(home) / ".system").exists()


def test_without_codex_home_the_default_codex_location_is_used(home):
    (home / ".config" / "codex").mkdir()
    add_skill(home, "alpha")

    code, _out, _err = run(home)

    assert code == 0
    assert (home / ".config" / "codex" / "skills" / "alpha").is_symlink()


@pytest.mark.parametrize("stdin", ["", "not json", "{}"], ids=["empty", "garbage", "empty-object"])
def test_any_payload_exits_0(home, stdin):
    add_skill(home, "alpha")

    code, out, _err = run(home, stdin)

    assert (code, out) == (0, "")


def test_an_unwritable_target_is_reported_and_still_exits_0(home):
    # Given a ~/.claude/skills that is a file, so the skills directory cannot be made
    add_skill(home, "alpha")
    target(home).write_text("not a directory", encoding="utf-8")

    # When
    code, out, err = run(home)

    # Then the session is never broken
    assert (code, out) == (0, "")
    assert "skipped" in err and "File exists" in err


def test_the_hook_sits_where_the_opencode_runner_never_discovers_it():
    # The runner picks up only files directly in .agents/hooks, see docs/hooks-contract.md
    assert SYNC_SKILL_LINKS_HOOK.parent != HOOKS_DIR
    assert SYNC_SKILL_LINKS_HOOK.parent.parent == HOOKS_DIR
