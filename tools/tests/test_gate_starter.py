"""Tests for the starter of the preflight gate, .agents/hooks/preflight-gate/preflight_gate.py.

Every wiring runs the starter, and the starter imports the rules from
_gate_rules.py beside it, so the interpreter loads the compiled copy it keeps
in __pycache__ instead of compiling the rules on every tool call. The cases
start the gate the way the wirings do, with -S -E and a path relative to the
project root, and hold each answer to the one the rules give in-process.
"""

import importlib.util
import io
import json
import os
import shutil
import stat
import sys
import tomllib

import pytest

from tests import claude_wiring_support as wiring
from tests.conftest import GATE_RULES, HOOKS_DIR, PREFLIGHT_GATE, REPO_ROOT, SUBPROCESS_TIMEOUT_SECONDS, copy_gate
from tests.process_tree import run_bounded

WIRING_FLAGS = ("-S", "-E")
STARTER = PREFLIGHT_GATE.relative_to(REPO_ROOT).as_posix()
GIT = shutil.which("git")
SHELL = None if sys.platform == "win32" else shutil.which("sh")
ALLOWED = (0, "", "")

WRITE = {"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": {"file_path": "src/app.py", "content": "x"}}
STATUS = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "git status"}}
RUNNER_WRITE = {
    "contract": 3,
    "event": "tool.execute.before",
    "tool_name": "Edit",
    "tool_input": {"file_path": "src/app.py"},
    "agent_type": "",
    "is_subagent": False,
}
RUNNER_STATUS = {**RUNNER_WRITE, "tool_name": "Bash", "tool_input": {"command": "git status"}}
WRITES = {"claude": WRITE, "codex": WRITE, "copilot": WRITE, "plain": RUNNER_WRITE}

BROKEN_RULES = {
    "missing": None,
    "not-python": "def main(:\n",
    "raises-on-import": 'raise RuntimeError("the rules blew up")\n',
    "no-main": "VALUE = 1\n",
}

RULES_THAT_ALLOW = "def main():\n    return 0\n"


def _load_rules():
    spec = importlib.util.spec_from_file_location("gate_rules_for_the_starter", GATE_RULES)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


RULES = _load_rules()


def start(payload, fmt, script=STARTER, cwd=REPO_ROOT):
    """Start the gate the way every wiring does and return (returncode, stdout, stderr).

    Raises:
        subprocess.TimeoutExpired: when the gate is still running after the timeout.
    """
    result = run_bounded(
        [sys.executable, *WIRING_FLAGS, str(script), "--format", fmt],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(cwd),
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )

    return result.returncode, result.stdout, result.stderr


def decide_in_process(monkeypatch, payload, fmt, cwd=REPO_ROOT):
    """The answer of the rules' own main(), with its streams and working directory swapped for the call."""
    stdout, stderr = io.StringIO(), io.StringIO()

    with monkeypatch.context() as patch:
        patch.chdir(cwd)
        patch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(json.dumps(payload).encode("utf-8")), encoding="utf-8"))
        patch.setattr(sys, "stdout", stdout)
        patch.setattr(sys, "stderr", stderr)
        code = RULES.main(["--format", fmt])

    return code, stdout.getvalue(), stderr.getvalue()


def is_denial(result, fmt):
    code, out, err = result

    if fmt == "plain":
        return code == 2 and out == "" and err.startswith("PREFLIGHT:")

    return code == 0 and err == "" and out != "" and json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()

    return root


def installed_gate(tmp_path):
    """The starter and the rules in a folder of their own, outside the project they judge."""
    folder = tmp_path / "install" / PREFLIGHT_GATE.parent.name
    folder.mkdir(parents=True)

    return copy_gate(folder)


def compiled_rules(folder):
    return sorted((folder / "__pycache__").glob(f"{GATE_RULES.stem}.*.pyc"))


@pytest.mark.parametrize(
    ("fmt", "payload", "denied"),
    [
        pytest.param("claude", WRITE, True, id="claude-deny"),
        pytest.param("claude", STATUS, False, id="claude-allow"),
        pytest.param("codex", WRITE, True, id="codex-deny"),
        pytest.param("codex", STATUS, False, id="codex-allow"),
        pytest.param("plain", RUNNER_WRITE, True, id="plain-deny"),
        pytest.param("plain", RUNNER_STATUS, False, id="plain-allow"),
    ],
)
def test_the_starter_answers_as_the_rules_do_when_started_the_way_the_wiring_starts_it(monkeypatch, fmt, payload, denied):
    # Given the answer the rules give in-process
    expected = decide_in_process(monkeypatch, payload, fmt)

    # When the starter runs with the wiring's flags on its project-relative path
    started = start(payload, fmt)

    # Then both give the same exit code and the same output, and the decision is the known one
    assert started == expected
    assert is_denial(started, fmt) is denied
    assert denied or started == ALLOWED


def claude_handler():
    (handler,) = wiring.wired("PreToolUse", PREFLIGHT_GATE.name)

    return handler


def claude_command():
    """The gate plugin's command, with the environment Claude Code gives a plugin loaded in place."""
    handler = claude_handler()

    return handler.command, wiring.hook_environment(handler, REPO_ROOT, dict(os.environ))


def codex_command():
    config = tomllib.loads((REPO_ROOT / ".codex" / "config.toml").read_text(encoding="utf-8"))
    command = next(
        entry["command"]
        for group in config["hooks"]["PreToolUse"]
        for entry in group["hooks"]
        if PREFLIGHT_GATE.name in entry["command"]
    )

    return command, {**os.environ, "CLAUDE_PROJECT_DIR": str(REPO_ROOT)}


@pytest.mark.skipif(SHELL is None, reason="needs a POSIX shell")
@pytest.mark.parametrize("command", [claude_command, codex_command], ids=["claude", "codex"])
@pytest.mark.parametrize(("payload", "denied"), [(WRITE, True), (STATUS, False)], ids=["deny", "allow"])
def test_the_wiring_s_own_command_denies_and_allows_through_the_starter(command, payload, denied):
    # Given the command a shipped wiring file or the gate plugin holds, word for word
    wired, environment = command()

    # When the shell runs it from the project with a main-thread payload
    result = run_bounded(
        [SHELL, "-c", wired],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO_ROOT),
        env=environment,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )

    # Then the write is denied and the read-only command passes in silence
    assert is_denial((result.returncode, result.stdout, ""), "claude") is denied
    assert denied or (result.returncode, result.stdout) == (0, "")


@pytest.mark.parametrize("fmt", sorted(WRITES))
@pytest.mark.parametrize("rules", BROKEN_RULES.values(), ids=BROKEN_RULES.keys())
def test_a_starter_whose_rules_cannot_be_imported_allows(tmp_path, rules, fmt):
    # Given the starter in a folder whose rules file is missing or broken
    starter = tmp_path / PREFLIGHT_GATE.name
    shutil.copy2(PREFLIGHT_GATE, starter)

    if rules is not None:
        (tmp_path / GATE_RULES.name).write_text(rules, encoding="utf-8")

    # When a main-thread write arrives, which the rules would deny
    result = start(WRITES[fmt], fmt, script=starter, cwd=project(tmp_path))

    # Then the call is allowed the way every allow looks: exit 0 and nothing printed
    assert result == ALLOWED


def test_the_first_start_keeps_a_compiled_copy_of_the_rules_and_the_next_start_answers_the_same(tmp_path):
    # Given a freshly installed gate with no compiled copy yet
    starter = installed_gate(tmp_path)
    root = project(tmp_path)

    assert compiled_rules(starter.parent) == []

    # When it runs twice
    first = start(WRITE, "claude", script=starter, cwd=root)
    kept = compiled_rules(starter.parent)
    second = start(WRITE, "claude", script=starter, cwd=root)

    # Then the first run left the compiled rules and the second, which loads them, denies the same way
    assert len(kept) == 1
    assert is_denial(first, "claude")
    assert second == first


def test_a_replaced_rules_file_takes_effect_on_the_next_start(tmp_path):
    # Given an installed gate that has already compiled its rules
    starter = installed_gate(tmp_path)
    root = project(tmp_path)

    assert is_denial(start(WRITE, "claude", script=starter, cwd=root), "claude")

    # When an update replaces the rules file
    (starter.parent / GATE_RULES.name).write_text(RULES_THAT_ALLOW, encoding="utf-8")

    # Then the new rules decide, never the compiled copy of the old ones
    assert start(WRITE, "claude", script=starter, cwd=root) == ALLOWED


@pytest.mark.skipif(not hasattr(os, "geteuid") or os.geteuid() == 0, reason="needs a user that a folder mode can stop")
def test_a_gate_in_a_folder_that_cannot_be_written_still_decides(tmp_path):
    # Given an installed gate whose folder is read-only, so no compiled copy can be kept
    starter = installed_gate(tmp_path)
    root = project(tmp_path)
    starter.parent.chmod(stat.S_IRUSR | stat.S_IXUSR)

    # When it runs
    try:
        denied = start(WRITE, "claude", script=starter, cwd=root)
        allowed = start(STATUS, "claude", script=starter, cwd=root)
        kept = compiled_rules(starter.parent)
    finally:
        starter.parent.chmod(stat.S_IRWXU)

    # Then it decides as usual and complains about nothing
    assert is_denial(denied, "claude")
    assert allowed == ALLOWED
    assert kept == []


@pytest.mark.skipif(GIT is None, reason="git is not installed")
def test_git_ignores_the_compiled_copy_in_this_repository():
    cached = (PREFLIGHT_GATE.parent / "__pycache__" / f"{GATE_RULES.stem}.cpython-314.pyc").relative_to(REPO_ROOT)

    result = run_bounded([GIT, "check-ignore", "--quiet", "--no-index", cached.as_posix()], cwd=str(REPO_ROOT), timeout=SUBPROCESS_TIMEOUT_SECONDS)

    assert result.returncode == 0


@pytest.mark.skipif(GIT is None, reason="git is not installed")
def test_a_project_that_imported_the_hooks_never_sees_the_compiled_copy_as_an_untracked_file(tmp_path):
    # Given a new repository with no ignore file of its own, holding the imported hooks folder
    root = project(tmp_path)
    hooks = root / HOOKS_DIR.relative_to(REPO_ROOT)
    (hooks / PREFLIGHT_GATE.parent.name).mkdir(parents=True)
    shutil.copy2(HOOKS_DIR / ".gitignore", hooks / ".gitignore")
    starter = copy_gate(hooks / PREFLIGHT_GATE.parent.name)

    for arguments in (["init", "--quiet"], ["add", "--all"]):
        run_bounded([GIT, *arguments], cwd=str(root), check=True, timeout=SUBPROCESS_TIMEOUT_SECONDS)

    # When the gate has run and kept its compiled rules
    assert is_denial(start(WRITE, "claude", script=starter.relative_to(root), cwd=root), "claude")
    assert len(compiled_rules(starter.parent)) == 1

    # Then git lists no untracked file
    untracked = run_bounded(
        [GIT, "ls-files", "--others", "--exclude-standard"], cwd=str(root), capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_SECONDS
    )

    assert (untracked.returncode, untracked.stdout) == (0, "")
