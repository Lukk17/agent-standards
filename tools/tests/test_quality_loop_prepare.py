"""Tests for .metrics/tools/quality_loop/prepare.py: the ignore line, the project Python and the npm packages."""

import json
import subprocess
import sys

import pytest
from tests.quality_loop_support import RecordingRunner, write

from quality_loop import prepare
from quality_loop.host import Host

POSIX = Host(windows=False)
WINDOWS = Host(windows=True)


def not_ignored(_root, _folder):
    return False


def test_target_is_added_to_a_new_gitignore(tmp_path):
    assert prepare.ensure_ignored(tmp_path, "target", git_check=not_ignored) is True

    assert (tmp_path / ".gitignore").read_text(encoding="utf-8") == "target/\n"


def test_a_folder_below_the_root_is_ignored_by_its_path_from_the_root(tmp_path):
    write(tmp_path, ".gitignore", "build/\n")

    assert prepare.ensure_ignored(tmp_path, "svc/.venv", git_check=not_ignored) is True

    assert (tmp_path / ".gitignore").read_text(encoding="utf-8") == "build/\nsvc/.venv/\n"


@pytest.mark.parametrize("line", [".venv", ".venv/", "**/.venv/", "svc/.venv", "/svc/.venv/"])
def test_a_gitignore_line_that_already_covers_a_nested_folder_is_enough(tmp_path, line):
    write(tmp_path, ".gitignore", f"{line}\n")

    assert prepare.ensure_ignored(tmp_path, "svc/.venv", git_check=not_ignored) is False
    assert (tmp_path / ".gitignore").read_text(encoding="utf-8") == f"{line}\n"


def test_target_is_appended_on_its_own_line_keeping_crlf(tmp_path):
    (tmp_path / ".gitignore").write_bytes(b"node_modules/\r\n.env")

    prepare.ensure_ignored(tmp_path, "target", git_check=not_ignored)

    assert (tmp_path / ".gitignore").read_bytes() == b"node_modules/\r\n.env\r\ntarget/\r\n"


@pytest.mark.parametrize("line", ["target", "/target/", "**/target", "  target/  "])
def test_a_gitignore_that_already_names_target_is_left_alone(tmp_path, line):
    write(tmp_path, ".gitignore", f"build/\n{line}\n")

    assert prepare.ensure_ignored(tmp_path, "target", git_check=not_ignored) is False
    assert (tmp_path / ".gitignore").read_text(encoding="utf-8") == f"build/\n{line}\n"


def test_git_ignoring_the_folder_elsewhere_is_enough(tmp_path):
    assert prepare.ensure_ignored(tmp_path, "target", git_check=lambda _root, _folder: True) is False
    assert not (tmp_path / ".gitignore").exists()


def test_git_answers_whether_it_ignores_a_folder(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    assert prepare.git_ignores(tmp_path, "svc/.venv") is False

    write(tmp_path, ".gitignore", ".venv/\n")

    assert prepare.git_ignores(tmp_path, "svc/.venv") is True


def test_outside_a_repository_git_has_no_answer(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))

    assert prepare.git_ignores(tmp_path, "target") is None


def test_a_fresh_environment_installs_requirements_and_the_project_with_its_test_extras(tmp_path):
    write(tmp_path, "requirements.txt")
    write(tmp_path, "requirements-dev.txt")
    write(tmp_path, "pyproject.toml", '[project]\nname = "x"\n[project.optional-dependencies]\ntest = ["pytest"]\n')
    python = tmp_path / ".venv/bin/python"

    steps = prepare.install_steps(tmp_path, python)

    assert [step[-2:] for step in steps] == [["-r", "requirements.txt"], ["-r", "requirements-dev.txt"], ["-e", ".[test]"]]


def test_a_folder_with_only_tests_needs_nothing_installed(tmp_path):
    write(tmp_path, "pyproject.toml", "[tool.pytest.ini_options]\n")

    assert prepare.install_steps(tmp_path, tmp_path / "python") == []


def test_a_project_without_an_environment_gets_a_venv_and_the_pinned_test_modules(tmp_path):
    write(tmp_path, "pytest.ini")
    source = write(tmp_path, "app.py")
    runner = RecordingRunner(respond=lambda argv, _cwd: 1 if argv[1:2] == ["-c"] else 0)

    found = prepare.project_interpreters(tmp_path, [source], POSIX, tmp_path / "c.txt", runner, lambda _m: None)

    python = tmp_path / ".venv/bin/python"
    assert found == {tmp_path: python}
    assert runner.commands[0] == [sys.executable, "-m", "venv", str(tmp_path / ".venv")]
    installed = [command[-1] for command in runner.commands if "install" in command]
    assert installed == ["coverage", "pytest"]
    assert all("-c" in command and str(tmp_path / "c.txt") in command for command in runner.commands if "install" in command)


@pytest.mark.parametrize(("folder", "line"), [("", ".venv/"), ("svc", "svc/.venv/")])
def test_a_venv_the_wrapper_creates_is_ignored_from_the_root_it_was_made_in(tmp_path, monkeypatch, folder, line):
    monkeypatch.setattr(prepare, "git_ignores", not_ignored)
    write(tmp_path, f"{folder}/pyproject.toml" if folder else "pyproject.toml", "[project]\nname = 'x'\n")
    source = write(tmp_path, f"{folder}/app.py" if folder else "app.py")
    said = []

    prepare.project_interpreters(tmp_path, [source], POSIX, tmp_path / "c.txt", RecordingRunner(), said.append)

    assert (tmp_path / ".gitignore").read_text(encoding="utf-8") == f"{line}\n"
    assert f"Added {line} to .gitignore." in said


def test_an_existing_venv_is_not_added_to_gitignore(tmp_path, monkeypatch):
    monkeypatch.setattr(prepare, "git_ignores", not_ignored)
    write(tmp_path, ".venv/bin/python")
    source = write(tmp_path, "app.py")

    prepare.project_interpreters(tmp_path, [source], POSIX, tmp_path / "c.txt", RecordingRunner(), lambda _m: None)

    assert not (tmp_path / ".gitignore").exists()


def test_an_existing_venv_is_reused_and_nothing_is_installed_when_ready(tmp_path):
    write(tmp_path, "venv/Scripts/python.exe")
    source = write(tmp_path, "app.py")
    runner = RecordingRunner()

    found = prepare.project_interpreters(tmp_path, [source], WINDOWS, tmp_path / "c.txt", runner, lambda _m: None)

    assert found == {tmp_path: tmp_path / "venv/Scripts/python.exe"}
    assert runner.commands == [[str(tmp_path / "venv/Scripts/python.exe"), "-c", "import coverage"]]


@pytest.mark.parametrize(("lockfile", "command"), [(True, "ci"), (False, "install")])
def test_missing_node_modules_are_installed_from_the_lockfile_when_there_is_one(tmp_path, monkeypatch, lockfile, command):
    write(tmp_path, "package.json", "{}")
    if lockfile:
        write(tmp_path, "package-lock.json", "{}")
    monkeypatch.setattr(prepare.Host, "which", lambda _self, name: f"/bin/{name}")
    runner = RecordingRunner()

    prepare.ensure_node_modules(tmp_path, POSIX, runner, lambda _m: None)

    assert runner.commands == [["/bin/npm", command]]


def test_present_node_modules_are_left_alone(tmp_path):
    write(tmp_path, "package.json", "{}")
    (tmp_path / "node_modules").mkdir()
    runner = RecordingRunner()

    prepare.ensure_node_modules(tmp_path, POSIX, runner, lambda _m: None)

    assert runner.commands == []


def test_without_npm_the_user_is_told_and_nothing_runs(tmp_path, monkeypatch):
    write(tmp_path, "package.json", "{}")
    monkeypatch.setattr(prepare.Host, "which", lambda _self, _name: None)
    said = []

    prepare.ensure_node_modules(tmp_path, POSIX, RecordingRunner(), said.append)

    assert said == ["npm is not on PATH, so the TypeScript and JavaScript tests cannot run."]


def test_on_windows_the_vitest_provider_is_installed_and_the_manifests_restored(tmp_path, monkeypatch):
    manifest = json.dumps({"scripts": {"test": "vitest run"}})
    write(tmp_path, "package.json", manifest)
    write(tmp_path, "node_modules/vitest/package.json", json.dumps({"version": "5.1.0"}))
    monkeypatch.setattr(prepare.Host, "which", lambda _self, name: f"C:/node/{name}.cmd")

    def npm_rewrites_the_manifest(argv, cwd):
        (cwd / "package.json").write_text("{}", encoding="utf-8")
        (cwd / "package-lock.json").write_text("{}", encoding="utf-8")
        return 0

    runner = RecordingRunner(respond=npm_rewrites_the_manifest)

    prepare.ensure_vitest_provider(tmp_path, WINDOWS, runner, lambda _m: None)

    assert runner.commands == [["C:/node/npm.cmd", "install", "--no-save", "--no-package-lock", "@vitest/coverage-v8@5.1.0"]]
    assert (tmp_path / "package.json").read_text(encoding="utf-8") == manifest
    assert not (tmp_path / "package-lock.json").exists()


@pytest.mark.parametrize("scripts", [{"coverage": "vitest run --coverage", "test": "vitest run"}, {"test": "jest"}])
def test_on_windows_no_provider_is_installed_when_vitest_does_not_write_the_coverage(tmp_path, monkeypatch, scripts):
    write(tmp_path, "package.json", json.dumps({"scripts": scripts}))
    monkeypatch.setattr(prepare.Host, "which", lambda _self, name: f"C:/node/{name}.cmd")
    runner = RecordingRunner()

    prepare.ensure_vitest_provider(tmp_path, WINDOWS, runner, lambda _m: None)

    assert runner.commands == []


def test_a_manifest_npm_deletes_is_written_back(tmp_path, monkeypatch):
    manifest = json.dumps({"scripts": {"test": "vitest run"}})
    write(tmp_path, "package.json", manifest)
    monkeypatch.setattr(prepare.Host, "which", lambda _self, name: f"C:/node/{name}.cmd")

    def npm_deletes_the_manifest(_argv, cwd):
        (cwd / "package.json").unlink()
        return 0

    prepare.ensure_vitest_provider(tmp_path, WINDOWS, RecordingRunner(npm_deletes_the_manifest), lambda _m: None)

    assert (tmp_path / "package.json").read_text(encoding="utf-8") == manifest


def test_on_posix_crapper_installs_the_vitest_provider_itself(tmp_path):
    write(tmp_path, "package.json", json.dumps({"scripts": {"test": "vitest run"}}))
    runner = RecordingRunner()

    prepare.ensure_vitest_provider(tmp_path, POSIX, runner, lambda _m: None)

    assert runner.commands == []
