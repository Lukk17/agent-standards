"""Tests for the starter of the preflight gate, .agents/hooks/preflight-gate/preflight_gate.py.

Every wiring runs the starter, and the starter loads the rules from
gate_rules.py beside it by that file's path, so the interpreter loads the
compiled copy it keeps in __pycache__ instead of compiling the rules on every
tool call, and no other file in the folder or the working directory can stand
in for them. The cases start the gate the way the wirings do, with -S -E and a
path relative to the project root, and hold each answer to the one the rules
give in-process.
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
    "exits-on-import": "import sys\nsys.exit(2)\n",
}
BROKEN_RULES_ERRORS = {
    "missing": "FileNotFoundError",
    "not-python": "SyntaxError",
    "raises-on-import": "RuntimeError",
    "no-main": "AttributeError",
    "exits-on-import": "SystemExit",
}
LOAD_FAILURE_PREFIX = "preflight-gate: gate_rules failed to load: "
MESSAGE_CAP = 300
LOAD_WARNING_TEXT = "Preflight gate rules failed to load, so every tool call is allowed. Run the gate by hand to see the error."
CLAUDE_LOAD_WARNING = '{"systemMessage": "' + LOAD_WARNING_TEXT + '"}'
LOAD_FAILURE_STDOUT = {"claude": CLAUDE_LOAD_WARNING, "codex": "", "copilot": "", "plain": ""}

RULES_THAT_ALLOW = "def main():\n    return 0\n"
ENDS_THE_PROCESS_AND_ALLOWS = "import os\nos._exit(0)\n"
SHADOWED_STANDARD_MODULES = ("json", "re", "shlex", "ast", "pathlib")


def _load_rules():
    spec = importlib.util.spec_from_file_location("gate_rules_for_the_starter", GATE_RULES)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


RULES = _load_rules()


def start(payload, fmt, script=STARTER, cwd=REPO_ROOT, flags=WIRING_FLAGS):
    """Start the gate the way every wiring does and return (returncode, stdout, stderr).

    Raises:
        subprocess.TimeoutExpired: when the gate is still running after the timeout.
    """
    result = run_bounded(
        [sys.executable, *flags, str(script), "--format", fmt],
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


def starter_with_rules(tmp_path, rules):
    """The starter in a folder of its own, beside the given rules text, or beside no rules file for None."""
    starter = tmp_path / PREFLIGHT_GATE.name
    shutil.copy2(PREFLIGHT_GATE, starter)

    if rules is not None:
        (tmp_path / GATE_RULES.name).write_text(rules, encoding="utf-8")

    return starter


@pytest.mark.parametrize("fmt", sorted(WRITES))
@pytest.mark.parametrize("case", BROKEN_RULES)
def test_a_starter_whose_rules_cannot_be_imported_allows_and_names_the_failure_on_stderr(tmp_path, case, fmt):
    # Given the starter in a folder whose rules file is missing or broken
    starter = starter_with_rules(tmp_path, BROKEN_RULES[case])

    # When a main-thread write arrives, which the rules would deny
    code, out, err = start(WRITES[fmt], fmt, script=starter, cwd=project(tmp_path))

    # Then the call is allowed with exit 0 and no decision, stdout holds only the format's warning, and stderr carries one line naming the failure
    assert (code, out) == (0, LOAD_FAILURE_STDOUT[fmt])
    assert err.endswith("\n") and err.count("\n") == 1
    assert err.startswith(f"{LOAD_FAILURE_PREFIX}{BROKEN_RULES_ERRORS[case]}: ")


@pytest.mark.parametrize("case", BROKEN_RULES)
def test_a_claude_starter_whose_rules_cannot_be_loaded_prints_only_a_fixed_system_message(tmp_path, case):
    # Given the starter in a folder whose rules file is missing or broken
    starter = starter_with_rules(tmp_path, BROKEN_RULES[case])

    # When a main-thread write arrives on the claude format
    code, out, _ = start(WRITE, "claude", script=starter, cwd=project(tmp_path))

    # Then stdout is one JSON object holding only the fixed warning, with no decision and no exception text
    assert code == 0
    assert json.loads(out) == {"systemMessage": LOAD_WARNING_TEXT}


@pytest.mark.parametrize(
    ("arguments", "warned"),
    [
        (["--format=claude"], True),
        (["--format", "codex", "--format", "claude"], True),
        (["--format", "claude", "--format=plain"], False),
        (["--format"], False),
        ([], False),
    ],
    ids=["equals-form", "last-claude-wins", "last-plain-wins", "no-value", "no-format"],
)
def test_the_starter_reads_the_format_for_its_warning_the_way_the_rules_read_it(tmp_path, arguments, warned):
    # Given the starter beside a rules file that raises while it is imported
    starter = starter_with_rules(tmp_path, BROKEN_RULES["raises-on-import"])

    # When it starts with the given arguments
    result = run_bounded(
        [sys.executable, *WIRING_FLAGS, str(starter), *arguments],
        input=json.dumps(WRITE),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(project(tmp_path)),
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )

    # Then only a last format of claude prints the warning, and the call is allowed either way
    assert (result.returncode, result.stdout) == (0, CLAUDE_LOAD_WARNING if warned else "")


def test_the_load_failure_line_carries_the_exception_message(tmp_path):
    # Given rules that raise while they are imported
    starter = starter_with_rules(tmp_path, BROKEN_RULES["raises-on-import"])

    # When a main-thread write arrives
    result = start(WRITE, "claude", script=starter, cwd=project(tmp_path))

    # Then the call is allowed and stderr names the exception type and its message
    assert result == (0, CLAUDE_LOAD_WARNING, f"{LOAD_FAILURE_PREFIX}RuntimeError: the rules blew up\n")


def test_a_multi_line_exception_message_stays_on_one_line(tmp_path):
    # Given rules whose import error message spans several lines
    starter = starter_with_rules(tmp_path, 'raise RuntimeError("first\\nsecond")\n')

    # When a main-thread write arrives
    result = start(WRITE, "claude", script=starter, cwd=project(tmp_path))

    # Then the message is joined into the one line
    assert result == (0, CLAUDE_LOAD_WARNING, f"{LOAD_FAILURE_PREFIX}RuntimeError: first second\n")


def test_a_message_whose_text_cannot_be_read_still_allows_and_never_crashes_the_starter(tmp_path):
    # Given rules that raise an exception whose own text raises
    unreadable = 'class Unreadable(Exception):\n    def __str__(self):\n        raise ValueError("no text")\n\nraise Unreadable()\n'
    starter = starter_with_rules(tmp_path, unreadable)

    # When a main-thread write arrives
    result = start(WRITE, "claude", script=starter, cwd=project(tmp_path))

    # Then the call is allowed with the warning, and no traceback reaches stderr
    assert result == (0, CLAUDE_LOAD_WARNING, "")


def test_characters_that_cannot_be_printed_are_replaced_in_the_load_failure_line(tmp_path):
    # Given rules whose import error message holds an escape sequence and a null character
    starter = starter_with_rules(tmp_path, 'raise RuntimeError("a\\x1b[31mb\\x00c\\u200bd")\n')

    # When a main-thread write arrives
    result = start(WRITE, "claude", script=starter, cwd=project(tmp_path))

    # Then each of them is a question mark
    assert result == (0, CLAUDE_LOAD_WARNING, f"{LOAD_FAILURE_PREFIX}RuntimeError: a?[31mb?c?d\n")


def test_a_long_load_failure_message_is_cut_to_its_cap(tmp_path):
    # Given rules whose import error message is far longer than the cap
    starter = starter_with_rules(tmp_path, f'raise RuntimeError("{"x" * (MESSAGE_CAP * 4)}")\n')

    # When a main-thread write arrives
    result = start(WRITE, "claude", script=starter, cwd=project(tmp_path))

    # Then the message keeps only its first MESSAGE_CAP characters
    assert result == (0, CLAUDE_LOAD_WARNING, f"{LOAD_FAILURE_PREFIX}RuntimeError: {'x' * MESSAGE_CAP}\n")


@pytest.mark.skipif(SHELL is None, reason="needs a POSIX shell to start the gate with stderr closed")
def test_a_starter_started_with_no_stderr_still_allows_on_broken_rules(tmp_path):
    # Given broken rules that report what sys.stderr is, on stdout
    starter = starter_with_rules(tmp_path, 'import sys\nsys.stdout.write(repr(sys.stderr))\nraise RuntimeError("no stderr")\n')

    # When the starter runs with its stderr file descriptor closed
    result = run_bounded(
        [SHELL, "-c", 'exec "$0" -S -E "$1" --format claude 2>&-', sys.executable, str(starter)],
        input=json.dumps(WRITE),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(project(tmp_path)),
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )

    # Then sys.stderr was None and the starter still allowed the call with exit 0 and printed its warning
    assert (result.returncode, result.stdout) == (0, "None" + CLAUDE_LOAD_WARNING)


@pytest.mark.skipif(SHELL is None, reason="needs a POSIX shell to start the gate with stdout closed")
def test_a_claude_starter_started_with_no_stdout_still_allows_on_broken_rules(tmp_path):
    # Given the starter beside a rules file that raises while it is imported
    starter = starter_with_rules(tmp_path, BROKEN_RULES["raises-on-import"])

    # When the starter runs on the claude format with its stdout file descriptor closed
    result = run_bounded(
        [SHELL, "-c", 'exec "$0" -S -E "$1" --format claude >&-', sys.executable, str(starter)],
        input=json.dumps(WRITE),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(project(tmp_path)),
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )

    # Then the warning has nowhere to go, and the call is still allowed with exit 0 and only the load failure line
    assert (result.returncode, result.stderr) == (0, f"{LOAD_FAILURE_PREFIX}RuntimeError: the rules blew up\n")


def broken_gate_in_a_repository(tmp_path, rules):
    """A git project holding the starter beside the given rules text in .agents/hooks/preflight-gate/."""
    root = project(tmp_path)
    folder = root / PREFLIGHT_GATE.parent.relative_to(REPO_ROOT)
    folder.mkdir(parents=True)
    shutil.copy2(PREFLIGHT_GATE, folder / PREFLIGHT_GATE.name)

    if rules is not None:
        (folder / GATE_RULES.name).write_text(rules, encoding="utf-8")

    run_bounded([GIT, "init", "--quiet"], cwd=str(root), check=True, timeout=SUBPROCESS_TIMEOUT_SECONDS)

    return root, folder


def claude_command_for(root, folder):
    """The gate plugin's command, with the plugin root at folder and the session in root."""
    environment = {**os.environ, wiring.PLUGIN_ROOT_VARIABLE: str(folder), wiring.PROJECT_DIR_VARIABLE: str(root)}

    return claude_handler().command, environment


def codex_command_for(root, folder):
    """The Codex wiring's command, which finds the gate from the git top level of root."""
    command, _ = codex_command()

    return command, dict(os.environ)


def copilot_command_for(root, folder):
    """The GitHub Copilot wiring's bash command, which starts the gate on its path relative to the project."""
    wiring_file = json.loads((REPO_ROOT / ".github" / "hooks" / "preflight.json").read_text(encoding="utf-8"))
    command = next(entry["bash"] for entry in wiring_file["hooks"]["preToolUse"] if PREFLIGHT_GATE.name in entry["bash"])

    return command, dict(os.environ)


WIRED_COMMANDS = {"claude": claude_command_for, "codex": codex_command_for, "copilot": copilot_command_for}
WIRED_LOAD_FAILURE_STDERR = {"claude": True, "codex": False, "copilot": False}


@pytest.mark.skipif(SHELL is None or GIT is None, reason="needs a POSIX shell and git")
@pytest.mark.parametrize("name", WIRED_COMMANDS)
@pytest.mark.parametrize("case", BROKEN_RULES)
def test_the_wiring_s_own_command_allows_when_the_rules_cannot_be_loaded(tmp_path, name, case):
    # Given a project whose gate rules are missing or broken, and the command a shipped wiring holds
    root, folder = broken_gate_in_a_repository(tmp_path, BROKEN_RULES[case])
    wired, environment = WIRED_COMMANDS[name](root, folder)

    # When the shell runs it from the project with a main-thread write
    result = run_bounded(
        [SHELL, "-c", wired],
        input=json.dumps(WRITE),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(root),
        env=environment,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )

    # Then the call is allowed, only Claude Code gets the warning on stdout, and the load failure line reaches stderr only where the wiring keeps it
    assert (result.returncode, result.stdout) == (0, LOAD_FAILURE_STDOUT[name])

    if WIRED_LOAD_FAILURE_STDERR[name]:
        assert result.stderr == result.stderr.splitlines()[0] + "\n"
        assert result.stderr.startswith(f"{LOAD_FAILURE_PREFIX}{BROKEN_RULES_ERRORS[case]}: ")
    else:
        assert result.stderr == ""


def planted_beside(starter, relative, text):
    planted = starter.parent / relative
    planted.parent.mkdir(parents=True, exist_ok=True)
    planted.write_text(text, encoding="utf-8")


def test_a_package_planted_beside_the_rules_never_stands_in_for_them(tmp_path):
    # Given an installed gate with a gate_rules package beside the real rules file, which would allow everything
    starter = installed_gate(tmp_path)
    planted_beside(starter, f"{GATE_RULES.stem}/__init__.py", ENDS_THE_PROCESS_AND_ALLOWS)

    # When a main-thread write arrives
    result = start(WRITE, "claude", script=starter, cwd=project(tmp_path))

    # Then the real rules decide and deny it
    assert is_denial(result, "claude")


def test_a_rules_file_in_the_working_directory_never_stands_in_for_the_real_rules(tmp_path):
    # Given an installed gate, and a decoy rules file that allows everything in the project the session runs in
    starter = installed_gate(tmp_path)
    root = project(tmp_path)
    (root / GATE_RULES.name).write_text(RULES_THAT_ALLOW, encoding="utf-8")

    # When a main-thread write arrives
    result = start(WRITE, "claude", script=starter, cwd=root)

    # Then the real rules decide and deny it
    assert is_denial(result, "claude")


@pytest.mark.parametrize("module", SHADOWED_STANDARD_MODULES)
def test_a_standard_module_planted_beside_the_rules_never_shadows_the_real_one(tmp_path, module):
    # Given an installed gate with a file named after a standard module the rules import, which would allow everything
    starter = installed_gate(tmp_path)
    planted_beside(starter, f"{module}.py", ENDS_THE_PROCESS_AND_ALLOWS)

    # When a main-thread write arrives
    result = start(WRITE, "claude", script=starter, cwd=project(tmp_path))

    # Then the standard module is the one the rules get, and they deny it
    assert is_denial(result, "claude")


def test_rules_loaded_by_path_still_protect_the_project_the_gate_is_installed_in(tmp_path):
    # Given a gate installed in a project, and a session started in a folder outside that project
    root = project(tmp_path)
    folder = root / PREFLIGHT_GATE.parent.relative_to(REPO_ROOT)
    folder.mkdir(parents=True)
    starter = copy_gate(folder)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    write = {**WRITE, "tool_input": {"file_path": str(root / "src" / "app.py"), "content": "x"}}

    # When a main-thread write into the installed project arrives
    result = start(write, "claude", script=starter, cwd=elsewhere)

    # Then the rules found their install root from their own location and deny it
    assert is_denial(result, "claude")


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


def test_the_second_start_loads_the_compiled_copy_without_writing_it_again(tmp_path):
    # Given an installed gate that has already compiled its rules
    starter = installed_gate(tmp_path)
    root = project(tmp_path)

    assert is_denial(start(WRITE, "claude", script=starter, cwd=root), "claude")
    (compiled,) = compiled_rules(starter.parent)
    kept = compiled.stat().st_mtime_ns

    # When it starts again, with the interpreter reporting every module it loads
    code, out, err = start(WRITE, "claude", script=starter, cwd=root, flags=(*WIRING_FLAGS, "-v"))

    # Then it denies as before, the compiled copy was read as valid, and it was never written again
    assert is_denial((code, out, ""), "claude")
    assert f"{compiled} matches {starter.parent / GATE_RULES.name}" in err
    assert compiled.stat().st_mtime_ns == kept


def test_a_rules_file_replaced_by_one_of_the_same_size_takes_effect_on_the_next_start(tmp_path):
    # Given an installed gate that has already compiled its rules
    starter = installed_gate(tmp_path)
    root = project(tmp_path)
    rules = starter.parent / GATE_RULES.name

    assert is_denial(start(WRITE, "claude", script=starter, cwd=root), "claude")
    old = rules.stat()

    # When an update replaces the rules file with one of exactly the same size, written a second later
    padding = old.st_size - len(RULES_THAT_ALLOW) - 1
    rules.write_bytes(f"{RULES_THAT_ALLOW}#{'x' * (padding - 1)}\n".encode())
    os.utime(rules, ns=(old.st_atime_ns, old.st_mtime_ns + 1_000_000_000))

    assert rules.stat().st_size == old.st_size

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
