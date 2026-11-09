"""Tests for .metrics/tools/quality_loop/environments.py: each tool's own pinned environment."""

import sys
from pathlib import Path

import pytest
from tests.quality_loop_support import RecordingRunner, write

from quality_loop import environments
from quality_loop.host import Host

POSIX = Host(windows=False)
WINDOWS = Host(windows=True)


@pytest.fixture
def tools(tmp_path):
    write(tmp_path, "constraints.txt", "tree-sitter==0.26.0\n")
    write(tmp_path, "crapper/pyproject.toml", "[project]\nname = 'crapper'\n")
    return tmp_path


def creating_runner(host):
    """A runner whose venv step leaves an interpreter behind, the way python -m venv does."""

    def respond(argv, _cwd):
        if argv[1:3] == ["-m", "venv"]:
            python = host.venv_python(Path(argv[3]))
            python.parent.mkdir(parents=True, exist_ok=True)
            python.write_text("", encoding="utf-8")
        return 0

    return RecordingRunner(respond)


@pytest.mark.parametrize(("host", "relative"), [(POSIX, "bin/python"), (WINDOWS, "Scripts/python.exe")])
def test_a_missing_environment_is_built_pinned_and_editable(tools, host, relative):
    runner = creating_runner(host)

    python = environments.tool_python(tools, "crapper", host, runner, lambda _m: None)

    venv = tools / "crapper" / ".venv"
    assert python == venv / relative
    constraints = str(tools / "constraints.txt")
    assert runner.commands == [
        [sys.executable, "-m", "venv", str(venv)],
        [str(python), *environments.PIP, "-c", constraints, "setuptools"],
        [str(python), *environments.PIP, "--no-build-isolation", "-c", constraints, "-e", str(tools / "crapper")],
    ]


def test_a_ready_environment_is_reused_without_running_anything(tools):
    environments.tool_python(tools, "crapper", POSIX, creating_runner(POSIX), lambda _m: None)
    runner = RecordingRunner()

    python = environments.tool_python(tools, "crapper", POSIX, runner, lambda _m: None)

    assert python is not None
    assert runner.commands == []


def test_a_changed_constraint_rebuilds_the_environment_from_scratch(tools):
    environments.tool_python(tools, "crapper", POSIX, creating_runner(POSIX), lambda _m: None)
    leftover = write(tools, "crapper/.venv/lib/stale.txt")
    write(tools, "constraints.txt", "tree-sitter==0.27.0\n")
    runner = creating_runner(POSIX)

    environments.tool_python(tools, "crapper", POSIX, runner, lambda _m: None)

    assert len(runner.commands) == 3
    assert not leftover.exists()


def test_a_failed_install_reports_and_leaves_no_ready_stamp(tools):
    said = []
    runner = RecordingRunner(respond=lambda argv, _cwd: 1 if "-e" in argv else 0)

    python = environments.tool_python(tools, "crapper", POSIX, runner, said.append)

    assert python is None
    assert "network access to PyPI" in said[-1]
    assert environments.read_stamp(tools / "crapper" / ".venv") is None
