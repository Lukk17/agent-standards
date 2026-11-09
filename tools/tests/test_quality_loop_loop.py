"""Tests for .metrics/tools/quality_loop/loop.py: which tool runs when, with which arguments.

The tool environments are replaced by fixed paths and every command goes to a RecordingRunner, so these cases pin
the order and the arguments of the runs without starting a tool.
"""

from pathlib import Path

import pytest
from tests.quality_loop_support import RecordingRunner, write

from quality_loop import environments, loop
from quality_loop.host import Host

POSIX = Host(windows=False)
WINDOWS = Host(windows=True)


@pytest.fixture(autouse=True)
def ready_tool_environments(monkeypatch):
    monkeypatch.setattr(
        environments, "tool_python", lambda _tools, tool, _host, _run, _say: Path(f"/envs/{tool}/python")
    )
    monkeypatch.setattr(loop.prepare, "git_ignores_target", lambda _root: True)


def session(root, runner, host=POSIX, said=None):
    return loop.Session(root=root, tools_dir=root / ".metrics" / "tools", host=host, run=runner, say=(said if said is not None else []).append)


def python_project(root):
    write(root, "pyproject.toml", "[tool.pytest.ini_options]\n")
    write(root, ".venv/bin/python")
    write(root, ".venv/Scripts/python.exe")
    write(root, "src/app.py")


def gradle_project(root):
    write(root, "build.gradle", "plugins { id 'java' }\n")
    write(root, "src/main/java/App.java")


def writes_jacoco(argv, cwd):
    """Answer like Gradle: the report command leaves a JaCoCo XML where the tools read it."""
    if "--coverage-command" in argv and "jacocoTestReport" in argv[argv.index("--coverage-command") + 1]:
        write(cwd, "target/site/jacoco/jacoco.xml", "<report/>")
    return 0


def test_measure_on_python_runs_each_tool_once_in_full_and_never_with_changed(tmp_path):
    python_project(tmp_path)
    runner = RecordingRunner()

    code = loop.measure(session(tmp_path, runner))

    assert code == loop.SUCCESS
    assert runner.tool_runs("crapper") == [[]]
    assert runner.tool_runs("dryer") == [[]]
    assert runner.tool_runs("mutator") == [["--reuse-coverage"]]
    assert not any("--changed" in command for command in runner.commands)


def test_surviving_mutants_are_data_for_measure_and_a_status_for_mutate(tmp_path):
    python_project(tmp_path)

    def survivors(argv, _cwd):
        return loop.MUTATOR_SURVIVED if "mutator" in argv else 0

    assert loop.measure(session(tmp_path, RecordingRunner(survivors))) == loop.SUCCESS
    assert loop.mutate(session(tmp_path, RecordingRunner(survivors)), changed=True) == loop.SURVIVED


def test_a_failed_mutator_baseline_fails_the_run(tmp_path):
    python_project(tmp_path)

    def baseline_fails(argv, _cwd):
        return 2 if "mutator" in argv else 0

    assert loop.mutate(session(tmp_path, RecordingRunner(baseline_fails)), changed=False) == loop.FAILED


def test_gradle_gets_the_report_block_and_the_wrapper_commands(tmp_path):
    gradle_project(tmp_path)
    said = []
    runner = RecordingRunner(writes_jacoco)

    code = loop.measure(session(tmp_path, runner, said=said))

    assert code == loop.SUCCESS
    assert "Added the JaCoCo report block to build.gradle. Commit it on its own." in said
    assert runner.tool_runs("crapper") == [["--coverage-command", "gradle test jacocoTestReport"]]
    assert runner.tool_runs("mutator") == [
        ["--reuse-coverage", "--test-command", "gradle -q --offline --rerun-tasks test", "--timeout-factor", "30"]
    ]


def test_a_stale_gradle_report_is_removed_and_a_missing_new_one_fails_the_measure(tmp_path):
    gradle_project(tmp_path)
    stale = write(tmp_path, "target/site/jacoco/jacoco.xml", "<old/>")
    said = []

    code = loop.measure(session(tmp_path, RecordingRunner(), said=said))

    assert code == loop.FAILED
    assert not stale.exists()
    assert any(message.startswith("No java coverage report was written") for message in said)


def test_two_languages_where_one_needs_the_wrappers_commands_run_once_per_language(tmp_path):
    python_project(tmp_path)
    gradle_project(tmp_path)
    runner = RecordingRunner(writes_jacoco)

    code = loop.measure(session(tmp_path, runner))

    assert code == loop.SUCCESS
    assert runner.tool_runs("crapper") == [
        ["--coverage-command", "gradle test jacocoTestReport", ".java"],
        [".py"],
        ["--use-existing-coverage"],
    ]
    assert runner.tool_runs("dryer") == [[]]
    assert runner.tool_runs("mutator") == [
        ["--reuse-coverage", "--test-command", "gradle -q --offline --rerun-tasks test", "--timeout-factor", "30", ".java"],
        ["--reuse-coverage", ".py"],
    ]


def test_mutate_changed_produces_its_own_coverage_with_the_wrappers_command(tmp_path):
    gradle_project(tmp_path)
    runner = RecordingRunner()

    loop.mutate(session(tmp_path, runner), changed=True)

    assert runner.tool_runs("crapper") == []
    assert runner.tool_runs("mutator") == [
        [
            "--changed",
            "--coverage-command",
            "gradle test jacocoTestReport",
            "--test-command",
            "gradle -q --offline --rerun-tasks test",
            "--timeout-factor",
            "30",
        ]
    ]


def test_on_windows_mutator_starts_through_the_process_group_shim(tmp_path):
    python_project(tmp_path)
    runner = RecordingRunner(lambda argv, cwd: write(cwd, "target/coverage/python/lcov.info") and 0)

    loop.measure(session(tmp_path, runner, host=WINDOWS))

    (mutator,) = [command for command in runner.commands if command[0] == "/envs/mutator/python"]
    assert mutator[1] == str(tmp_path / ".metrics" / "tools" / "quality_loop" / "mutator_windows.py")
    assert "--test-command" in mutator


def test_without_symlinks_mutator_is_skipped_with_the_developer_mode_fix(tmp_path, monkeypatch):
    python_project(tmp_path)

    def refuse(_target, _link):
        raise OSError("[WinError 1314] A required privilege is not held by the client")

    monkeypatch.setattr(loop.os, "symlink", refuse)
    said = []
    runner = RecordingRunner()

    code = loop.measure(session(tmp_path, runner, said=said))

    assert code == loop.FAILED
    assert runner.tool_runs("mutator") == []
    assert any("Developer Mode" in message and "WinError 1314" in message for message in said)


def test_a_project_with_no_supported_language_runs_nothing(tmp_path):
    write(tmp_path, "src/Main.kt")
    said = []
    runner = RecordingRunner()

    assert loop.measure(session(tmp_path, runner, said=said)) == loop.SUCCESS
    assert runner.commands == []
    assert said[0].startswith("No Clojure, Go, Java, JavaScript, Python, Rust or TypeScript source")


def test_a_failed_crapper_fails_the_measure(tmp_path):
    python_project(tmp_path)

    def crapper_fails(argv, _cwd):
        return 1 if "crapper" in argv else 0

    assert loop.measure(session(tmp_path, RecordingRunner(crapper_fails))) == loop.FAILED


def test_a_missing_report_in_a_per_language_run_fails_the_measure(tmp_path):
    python_project(tmp_path)
    gradle_project(tmp_path)
    runner = RecordingRunner()

    assert loop.measure(session(tmp_path, runner)) == loop.FAILED
    assert runner.tool_runs("crapper")[-1] == ["--use-existing-coverage"]


def test_a_maven_project_never_gets_a_gradle_build_file(tmp_path):
    write(tmp_path, "pom.xml", "<project/>")
    write(tmp_path, "src/main/java/App.java")
    write(tmp_path, "tools/helper.py")
    write(tmp_path, ".venv/bin/python")

    loop.measure(session(tmp_path, RecordingRunner()))

    assert not (tmp_path / "build.gradle").exists()
