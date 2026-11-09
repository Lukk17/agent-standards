"""Tests for the quality loop entry points: the launchers, run.py and the command line in quality_loop/cli.py."""

import os
import shutil
import subprocess
import sys

import pytest
from tests.conftest import REPO_ROOT, SUBPROCESS_TIMEOUT_SECONDS
from tests.quality_loop_support import QUALITY_TOOLS

from quality_loop import cli, loop


def test_summary_reads_the_project_named_by_root(tmp_path, capsys):
    (tmp_path / ".metrics").mkdir()
    (tmp_path / ".metrics" / "crap.edn").write_text("{:entries []}\n", encoding="utf-8")

    code = cli.main(["summary", "--root", str(tmp_path)])

    assert code == loop.SUCCESS
    assert capsys.readouterr().out.startswith("CRAP (.metrics/crap.edn): 0 functions")


def test_the_default_project_is_the_folder_holding_metrics():
    assert cli.TOOLS_DIR.parent.parent == REPO_ROOT


@pytest.mark.parametrize("argv", [["summary", "--limit", "0"], ["mutate", "--everything"], []])
def test_a_usage_error_exits_2(argv):
    with pytest.raises(SystemExit) as raised:
        cli.main(argv)

    assert raised.value.code == 2


@pytest.mark.skipif(os.name == "nt", reason="the POSIX launcher")
def test_the_posix_launcher_starts_the_wrapper(tmp_path):
    launcher = QUALITY_TOOLS / "run"

    result = subprocess.run(
        [str(launcher), "summary", "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
        check=False,
    )

    assert (result.returncode, result.stderr) == (0, "")
    assert "Run .metrics/tools/run measure." in result.stdout
    assert os.access(launcher, os.X_OK)


@pytest.mark.skipif(shutil.which("sh") is None, reason="needs a POSIX shell")
def test_the_posix_launcher_is_plain_sh():
    result = subprocess.run(["sh", "-n", str(QUALITY_TOOLS / "run")], capture_output=True, text=True, check=False)

    assert (result.returncode, result.stderr) == (0, "")


@pytest.mark.parametrize(("launcher", "eol"), [("run.cmd", "crlf"), ("run", "lf")])
def test_the_tools_folder_alone_sets_each_launchers_line_endings(tmp_path, launcher, eol):
    """A consumer project has no .gitattributes of ours, so .metrics/tools must carry its own."""
    shutil.copytree(QUALITY_TOOLS, tmp_path / ".metrics" / "tools", ignore=shutil.ignore_patterns(".venv", "__pycache__"))
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)

    result = subprocess.run(
        ["git", "-C", str(tmp_path), "check-attr", "eol", "--", f".metrics/tools/{launcher}"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == f".metrics/tools/{launcher}: eol: {eol}"


def test_the_windows_launcher_prefers_python_and_falls_back_to_the_py_launcher():
    text = (QUALITY_TOOLS / "run.cmd").read_text(encoding="utf-8")

    assert text.index('python "%QUALITY_LOOP_RUN%" %*') < text.index('py -3 "%QUALITY_LOOP_RUN%" %*')
    assert "exit /b %ERRORLEVEL%" in text


def test_run_py_is_runnable_by_path_from_any_folder(tmp_path):
    result = subprocess.run(
        [sys.executable, str(QUALITY_TOOLS / "run.py"), "summary", "--root", str(tmp_path), "--limit", "1"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
        check=False,
    )

    assert result.returncode == 0, result.stderr
