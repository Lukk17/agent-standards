"""Tests for .metrics/tools/quality_loop/plan.py: the commands each language gets on each system."""

import json
from pathlib import Path

import pytest
from tests.quality_loop_support import write

from quality_loop import languages, plan
from quality_loop.host import Host

POSIX = Host(windows=False)
WINDOWS = Host(windows=True)


def only(root, language, host, interpreters=None):
    (item,) = plan.plan_languages(root, [language], host, interpreters)
    return item


@pytest.mark.parametrize("language", [languages.PYTHON, languages.TYPESCRIPT, languages.GO, languages.RUST, languages.CLOJURE])
def test_on_posix_every_language_but_gradle_java_keeps_the_tools_own_commands(tmp_path, language):
    write(tmp_path, "package.json", json.dumps({"scripts": {"test": "vitest run"}}))
    write(tmp_path, "pyproject.toml", "[tool.pytest.ini_options]\n")

    item = only(tmp_path, language, POSIX, {tmp_path: tmp_path / ".venv/bin/python"})

    assert not item.overridden


def test_maven_on_posix_keeps_its_commands_and_gets_the_jvm_timeout(tmp_path):
    write(tmp_path, "pom.xml")

    item = only(tmp_path, languages.JAVA, POSIX)

    assert not item.overridden
    assert item.timeout_factor == plan.JVM_TIMEOUT_FACTOR


@pytest.mark.parametrize(("host", "gradle"), [(POSIX, "./gradlew"), (WINDOWS, "gradlew.bat")])
def test_gradle_gets_its_report_task_and_an_honest_baseline_on_every_system(tmp_path, host, gradle):
    write(tmp_path, "build.gradle")
    write(tmp_path, "gradlew")
    write(tmp_path, "gradlew.bat")

    item = only(tmp_path, languages.JAVA, host)

    assert item.coverage_command == f"{gradle} --no-daemon test jacocoTestReport"
    assert item.test_command == f"{gradle} --no-daemon -q --offline --rerun-tasks test"
    assert "target/site/jacoco/jacoco.xml" in item.reports
    assert item.timeout_factor == plan.JVM_TIMEOUT_FACTOR


@pytest.mark.parametrize("host", [POSIX, WINDOWS])
@pytest.mark.parametrize("wrapper", [None, "gradlew", "gradlew.bat"])
def test_every_gradle_command_runs_without_a_daemon(tmp_path, host, wrapper):
    """A daemon a mutant's build leaves behind keeps writing into its worker folder while mutator deletes it."""
    write(tmp_path, "build.gradle")
    if wrapper:
        write(tmp_path, wrapper)

    item = only(tmp_path, languages.JAVA, host)

    commands = [item.coverage_command, item.test_command]
    assert all(command is not None and command.split()[1] == "--no-daemon" for command in commands), commands


def test_maven_on_windows_runs_through_the_shell_that_finds_mvn_cmd(tmp_path):
    write(tmp_path, "pom.xml")

    item = only(tmp_path, languages.JAVA, WINDOWS)

    assert item.coverage_command == (
        "mvn -q org.jacoco:jacoco-maven-plugin:0.8.12:prepare-agent test org.jacoco:jacoco-maven-plugin:0.8.12:report"
    )
    assert item.test_command == "mvn -q test -DexcludeTags=no-mutate"


def test_python_on_windows_uses_the_project_interpreter_and_writes_lcov(tmp_path):
    write(tmp_path, "pytest.ini")
    python = tmp_path / "my env" / "Scripts" / "python.exe"

    item = only(tmp_path, languages.PYTHON, WINDOWS, {tmp_path: python})

    data = tmp_path / "target/coverage/python/.coverage"
    assert item.coverage_command == (
        f'"{python}" -m coverage run --data-file={data} -m pytest'
        f' & "{python}" -m coverage lcov --data-file={data} -o {tmp_path / "target/coverage/python/lcov.info"}'
    )
    assert item.test_command == f'"{python}" -m pytest'
    assert item.report_dir == "target/coverage/python"


def test_python_without_pytest_on_windows_runs_unittest(tmp_path):
    python = tmp_path / ".venv" / "Scripts" / "python.exe"

    item = only(tmp_path, languages.PYTHON, WINDOWS, {tmp_path: python})

    assert item.test_command == f"{python} -m unittest discover -s ."


def test_python_in_a_subfolder_on_windows_changes_into_it_first(tmp_path):
    python = tmp_path / "backend" / ".venv" / "Scripts" / "python.exe"
    write(tmp_path, "backend/apps/pyproject.toml", "[tool.pytest.ini_options]\n")

    item = only(tmp_path, languages.PYTHON, WINDOWS, {tmp_path / "backend" / "apps": python})

    assert item.test_command == f"cd backend\\apps && {python} -m pytest"
    assert item.coverage_command.startswith("cd backend\\apps && ")


def test_python_in_two_folders_on_windows_warns_rather_than_guess(tmp_path):
    item = only(tmp_path, languages.PYTHON, WINDOWS, {tmp_path / "a": Path("a"), tmp_path / "b": Path("b")})

    assert not item.overridden
    assert "a, b" in item.warning


@pytest.mark.parametrize(
    ("scripts", "coverage"),
    [
        ({"coverage": "jest --coverage", "test": "jest"}, "npm run coverage"),
        (
            {"test": "vitest run"},
            "npx vitest run --coverage --coverage.reporter=lcov "
            "--coverage.reportsDirectory=target/coverage/typescript --coverage.reportOnFailure=true",
        ),
        ({"test": "node --test"}, "npx --yes c8@12.0.0 --reporter=lcov --reports-dir target/coverage/typescript npm test"),
        ({}, None),
    ],
)
def test_typescript_on_windows_makes_crappers_own_choice_through_the_shell(tmp_path, scripts, coverage):
    write(tmp_path, "package.json", json.dumps({"scripts": scripts}))

    item = only(tmp_path, languages.TYPESCRIPT, WINDOWS)

    assert item.coverage_command == coverage
    assert item.test_command == ("npm test" if "test" in scripts else None)


def test_typescript_without_a_root_package_json_is_left_to_the_tools(tmp_path):
    assert not only(tmp_path, languages.TYPESCRIPT, WINDOWS).overridden


def test_python_roots_are_the_nearest_folders_with_a_marker(tmp_path):
    write(tmp_path, "service/pyproject.toml")
    files = [write(tmp_path, "service/src/app/main.py"), write(tmp_path, "scripts/tool.py")]

    assert plan.python_roots(tmp_path, files) == sorted([tmp_path / "service", tmp_path])


def test_a_test_command_alone_makes_a_plan_overridden():
    assert plan.LanguagePlan(languages.JAVA, (".java",), test_command="mvn test").overridden
