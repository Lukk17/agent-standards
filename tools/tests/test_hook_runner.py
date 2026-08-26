"""Tests for the hook runner in .agents/plugin/hooks.js.

The plugin is exercised through node, against a throwaway project root holding
stub hooks, because its contract is the process contract: discover every hook in
.agents/hooks/, feed each one the envelope on stdin, treat exit code 2 as the
only denial.

Stub hooks record the envelope they were handed, so a test can assert both that
a hook ran and what it saw.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
from contextlib import contextmanager

import pytest

from tests.conftest import NO_AI_MARKERS_HOOK, PLUGIN, PREFLIGHT_GATE, RUNNER_DRIVER

NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")

RECORDER = """import json
import sys

HOOK_ORDER = {order}

LOG = {log}
NAME = {name}
DENY = {deny}


def main():
    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    envelope = json.loads(raw or "{{}}")

    with open(LOG, "a", encoding="utf-8") as handle:
        handle.write(json.dumps({{"hook": NAME, "envelope": envelope}}) + "\\n")

    if DENY:
        sys.stderr.buffer.write(("denied by " + NAME).encode("utf-8"))
        return 2

    return 0


sys.exit(main())
"""

UNDECLARED = """import sys

sys.stderr.write("denied by the hook that declares no order")
sys.exit(2)
"""

CRASHES = """import sys

sys.stderr.write("boom, but this is not a denial")
sys.exit(1)
"""

RAISES = 'raise RuntimeError("the hook blew up")\n'

NOT_PYTHON = "\x00\x01 this is not python at all \x02\n"

SILENT_DENIAL = "import sys\nsys.exit(2)\n"

NO_OP = "import sys\nsys.exit(0)\n"

EM_DASH_PROSE = "The plan is simple — delegate the work."


def write_hook(root, name, source):
    """Drop a file into the project's .agents/hooks/ and return its path."""
    hooks = root / ".agents" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    path = hooks / name
    path.write_text(source, encoding="utf-8")

    return path


def recorder_source(name, order, log, deny=False):
    return RECORDER.format(
        order=order,
        log=json.dumps(str(log)),
        name=json.dumps(name),
        deny="True" if deny else "False",
    )


def recorder(root, name, order, log, deny=False):
    return write_hook(root, name, recorder_source(name, order, log, deny))


def call(tool="Edit", args=None, agent="", session="s1", text=None):
    """One scripted tool call for the driver."""
    messages = []

    if text is not None:
        messages = [
            {"info": {"role": "assistant"}, "parts": [{"type": "text", "text": text}]}
        ]

    return {
        "kind": "call",
        "input": {"tool": tool, "agent": agent, "sessionID": session},
        "output": {"args": args if args is not None else {}},
        "messages": messages,
    }


def drive(root, steps):
    """Run the scripted steps against one plugin instance and return results."""
    job = {"plugin": str(PLUGIN), "root": str(root), "steps": steps}

    result = subprocess.run(
        [NODE, str(RUNNER_DRIVER)],
        input=json.dumps(job),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stderr

    return json.loads(result.stdout)


def read_log(log):
    """Every envelope recorded so far, in the order the hooks ran."""
    if not log.exists():
        return []

    lines = log.read_text(encoding="utf-8").splitlines()

    return [json.loads(line) for line in lines if line.strip()]


def hooks_run(log):
    return [entry["hook"] for entry in read_log(log)]


@contextmanager
def deny_reads(path):
    """Make one file unreadable for the length of the block, on either OS.

    POSIX drops the mode to zero. Windows has no mode to drop, so the current
    user gets an explicit deny entry, which is the only way to stop the owner
    reading their own file.
    """
    user = os.environ.get("USERNAME") or os.environ.get("USER") or ""

    if sys.platform == "win32":
        subprocess.run(
            ["icacls", str(path), "/deny", user + ":(R)"],
            capture_output=True,
            check=True,
        )
    else:
        os.chmod(path, 0)

    try:
        yield path
    finally:
        if sys.platform == "win32":
            subprocess.run(
                ["icacls", str(path), "/remove:d", user], capture_output=True
            )
        else:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def real_hooks(root):
    """A project root holding copies of the two hooks this repo ships."""
    hooks = root / ".agents" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)

    for source in (PREFLIGHT_GATE, NO_AI_MARKERS_HOOK):
        shutil.copy(source, hooks / source.name)

    return root


def test_two_hooks_are_both_consulted(tmp_path):
    # Given
    log = tmp_path / "log.jsonl"
    recorder(tmp_path, "a_first.py", 10, log)
    recorder(tmp_path, "b_second.py", 20, log)

    # When
    results = drive(tmp_path, [call()])

    # Then
    assert results == [{"ok": True}]
    assert hooks_run(log) == ["a_first.py", "b_second.py"]


def test_declared_order_beats_file_name(tmp_path):
    # Given
    log = tmp_path / "log.jsonl"
    recorder(tmp_path, "a_first.py", 90, log)
    recorder(tmp_path, "b_second.py", 10, log)

    # When
    drive(tmp_path, [call()])

    # Then
    assert hooks_run(log) == ["b_second.py", "a_first.py"]


def test_hook_without_declared_order_runs_last(tmp_path):
    # Given
    log = tmp_path / "log.jsonl"
    recorder(tmp_path, "zzz_declared.py", 10, log)
    write_hook(tmp_path, "aaa_undeclared.py", UNDECLARED)

    # When
    results = drive(tmp_path, [call()])

    # Then
    expected = "denied by the hook that declares no order"

    assert results == [{"ok": False, "error": expected}]
    assert hooks_run(log) == ["zzz_declared.py"]


def test_equal_order_falls_back_to_file_name(tmp_path):
    # Given
    log = tmp_path / "log.jsonl"
    recorder(tmp_path, "zebra.py", 50, log)
    recorder(tmp_path, "alpha.py", 50, log)

    # When
    drive(tmp_path, [call()])

    # Then
    assert hooks_run(log) == ["alpha.py", "zebra.py"]


def test_first_denial_stops_the_chain(tmp_path):
    # Given
    log = tmp_path / "log.jsonl"
    recorder(tmp_path, "first.py", 10, log, deny=True)
    recorder(tmp_path, "second.py", 20, log)

    # When
    results = drive(tmp_path, [call()])

    # Then
    assert results == [{"ok": False, "error": "denied by first.py"}]
    assert hooks_run(log) == ["first.py"]


def test_single_hook_is_enough(tmp_path):
    # Given
    log = tmp_path / "log.jsonl"
    recorder(tmp_path, "only.py", 10, log, deny=True)

    # When
    results = drive(tmp_path, [call()])

    # Then
    assert results == [{"ok": False, "error": "denied by only.py"}]
    assert hooks_run(log) == ["only.py"]


def test_empty_hooks_directory_allows(tmp_path):
    # Given
    (tmp_path / ".agents" / "hooks").mkdir(parents=True)

    # When
    results = drive(tmp_path, [call()])

    # Then
    assert results == [{"ok": True}]


def test_missing_hooks_directory_allows(tmp_path):
    # Given a project root with no .agents/ at all

    # When
    results = drive(tmp_path, [call()])

    # Then
    assert results == [{"ok": True}]


@pytest.mark.parametrize(
    "name,source",
    [
        ("crashes.py", CRASHES),
        ("raises.py", RAISES),
        ("garbage.py", NOT_PYTHON),
    ],
)
def test_non_denial_failure_allows(tmp_path, name, source):
    # Given
    write_hook(tmp_path, name, source)

    # When
    results = drive(tmp_path, [call()])

    # Then
    assert results == [{"ok": True}]


def test_broken_hook_does_not_stop_the_next_one(tmp_path):
    # Given
    log = tmp_path / "log.jsonl"
    write_hook(tmp_path, "a_broken.py", RAISES)
    recorder(tmp_path, "b_healthy.py", 20, log, deny=True)

    # When
    results = drive(tmp_path, [call()])

    # Then
    assert results == [{"ok": False, "error": "denied by b_healthy.py"}]


def test_hook_without_the_executable_bit_still_runs(tmp_path):
    # Given
    log = tmp_path / "log.jsonl"
    path = recorder(tmp_path, "plain.py", 10, log, deny=True)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)

    # When
    results = drive(tmp_path, [call()])

    # Then
    assert results == [{"ok": False, "error": "denied by plain.py"}]


def test_python_exits_two_when_it_cannot_open_a_script(tmp_path):
    """The hazard the unreadable-hook guard exists for.

    Exit code 2 is the denial code, and it is also what the interpreter returns
    for a script it cannot open. Without a guard, a hook the runner cannot read
    would block every tool call in the session.
    """
    # Given
    missing = tmp_path / "not_here.py"

    # When
    result = subprocess.run(
        [sys.executable, str(missing)], capture_output=True, text=True
    )

    # Then
    assert result.returncode == 2


def test_unreadable_hook_is_skipped_rather_than_read_as_a_denial(tmp_path):
    # Given a hook the process cannot open
    log = tmp_path / "log.jsonl"
    path = recorder(tmp_path, "a_unreadable.py", 10, log, deny=True)
    recorder(tmp_path, "b_healthy.py", 20, log)

    with deny_reads(path):
        # When
        results = drive(tmp_path, [call()])

    # Then
    assert results == [{"ok": True}]
    assert hooks_run(log) == ["b_healthy.py"]


def test_a_hook_deleted_mid_session_is_skipped(tmp_path):
    # Given
    log = tmp_path / "log.jsonl"
    recorder(tmp_path, "temporary.py", 10, log, deny=True)

    # When
    steps = [call(), {"kind": "remove", "path": ".agents/hooks/temporary.py"}, call()]
    results = drive(tmp_path, steps)

    # Then
    assert results[0] == {"ok": False, "error": "denied by temporary.py"}
    assert results[2] == {"ok": True}


def test_a_new_hook_is_picked_up_without_a_code_change(tmp_path):
    # Given one hook and a plugin instance already running
    log = tmp_path / "log.jsonl"
    recorder(tmp_path, "existing.py", 10, log)
    added = recorder_source("added_later.py", 20, log, deny=True)

    # When a second hook appears between two tool calls
    steps = [
        call(),
        {"kind": "write", "path": ".agents/hooks/added_later.py", "content": added},
        call(),
    ]
    results = drive(tmp_path, steps)

    # Then
    assert results[0] == {"ok": True}
    assert results[2] == {"ok": False, "error": "denied by added_later.py"}
    assert hooks_run(log) == ["existing.py", "existing.py", "added_later.py"]


@pytest.mark.parametrize("name", ["_private.py", ".hidden.py", "notes.txt", "README.md"])
def test_non_hook_files_are_ignored(tmp_path, name):
    # Given
    write_hook(tmp_path, name, UNDECLARED)
    write_hook(tmp_path, "real.py", NO_OP)

    # When
    results = drive(tmp_path, [call()])

    # Then
    assert results == [{"ok": True}]


def test_subdirectories_are_ignored(tmp_path):
    # Given a __pycache__-shaped directory whose name would otherwise match
    (tmp_path / ".agents" / "hooks" / "cached.py").mkdir(parents=True)

    # When
    results = drive(tmp_path, [call()])

    # Then
    assert results == [{"ok": True}]


def test_envelope_carries_the_documented_fields(tmp_path):
    # Given
    log = tmp_path / "log.jsonl"
    recorder(tmp_path, "watcher.py", 10, log)

    # When
    step = call(
        tool="Write",
        args={"file_path": "src/app.py"},
        agent="python-pro",
        text="Hello.",
    )
    drive(tmp_path, [step])

    # Then
    envelope = read_log(log)[0]["envelope"]

    assert envelope["contract"] == 1
    assert envelope["event"] == "tool.execute.before"
    assert envelope["tool_name"] == "Write"
    assert envelope["tool_input"] == {"file_path": "src/app.py"}
    assert envelope["agent_type"] == "python-pro"
    assert envelope["is_subagent"] is True
    assert envelope["assistant_text"] == "Hello."
    assert envelope["cwd"] == str(tmp_path)


def test_main_thread_envelope_reports_no_subagent(tmp_path):
    # Given
    log = tmp_path / "log.jsonl"
    recorder(tmp_path, "watcher.py", 10, log)

    # When
    drive(tmp_path, [call()])

    # Then
    envelope = read_log(log)[0]["envelope"]

    assert (envelope["agent_type"], envelope["is_subagent"]) == ("", False)


def test_assistant_text_survives_a_round_trip_of_non_ascii(tmp_path):
    # Given
    log = tmp_path / "log.jsonl"
    recorder(tmp_path, "watcher.py", 10, log)

    # When
    drive(tmp_path, [call(text=EM_DASH_PROSE)])

    # Then
    assert read_log(log)[0]["envelope"]["assistant_text"] == EM_DASH_PROSE


def test_assistant_text_is_delivered_once_per_session(tmp_path):
    # Given
    log = tmp_path / "log.jsonl"
    recorder(tmp_path, "watcher.py", 10, log)

    # When the same prose backs two consecutive tool calls
    steps = [call(text="Same reply."), call(text="Same reply."), call(text="New reply.")]
    drive(tmp_path, steps)

    # Then
    seen = [entry["envelope"]["assistant_text"] for entry in read_log(log)]

    assert seen == ["Same reply.", "", "New reply."]


def test_shipped_gate_denies_a_main_thread_source_edit(tmp_path):
    # Given
    real_hooks(tmp_path)

    # When
    results = drive(tmp_path, [call(tool="Edit", args={"file_path": "src/app.py"})])

    # Then
    assert results[0]["ok"] is False
    assert results[0]["error"].startswith("PREFLIGHT:")
    assert "src/app.py" in results[0]["error"]


def test_shipped_formatting_check_denies_an_em_dash(tmp_path):
    # Given
    real_hooks(tmp_path)

    # When
    step = call(tool="Read", args={"file_path": "README.md"}, text=EM_DASH_PROSE)
    results = drive(tmp_path, [step])

    # Then
    assert results[0]["ok"] is False
    assert "em dash" in results[0]["error"]


def test_shipped_hooks_allow_when_neither_applies(tmp_path):
    # Given
    real_hooks(tmp_path)

    # When
    step = call(tool="Read", args={"file_path": "README.md"}, text="A clean reply.")
    results = drive(tmp_path, [step])

    # Then
    assert results == [{"ok": True}]


def test_shipped_gate_wins_over_the_formatting_check(tmp_path):
    # Given a call that both shipped hooks would block
    real_hooks(tmp_path)

    # When
    step = call(tool="Edit", args={"file_path": "src/app.py"}, text=EM_DASH_PROSE)
    results = drive(tmp_path, [step])

    # Then the lower HOOK_ORDER decides
    assert results[0]["ok"] is False
    assert results[0]["error"].startswith("PREFLIGHT:")


def test_a_project_with_only_the_gate_still_works(tmp_path):
    # Given a checkout that pulled one of the two shipped hooks
    hooks = tmp_path / ".agents" / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy(PREFLIGHT_GATE, hooks / PREFLIGHT_GATE.name)

    # When
    steps = [
        call(tool="Edit", args={"file_path": "src/app.py"}, text=EM_DASH_PROSE),
        call(tool="Read", args={"file_path": "README.md"}, text="A clean reply."),
    ]
    results = drive(tmp_path, steps)

    # Then
    assert results[0]["ok"] is False
    assert results[0]["error"].startswith("PREFLIGHT:")
    assert results[1] == {"ok": True}


def test_a_project_with_only_the_formatting_check_still_works(tmp_path):
    # Given the other half of the same split
    hooks = tmp_path / ".agents" / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy(NO_AI_MARKERS_HOOK, hooks / NO_AI_MARKERS_HOOK.name)

    # When
    steps = [
        call(tool="Edit", args={"file_path": "src/app.py"}, text=EM_DASH_PROSE),
        call(tool="Edit", args={"file_path": "src/other.py"}, text="A clean reply."),
    ]
    results = drive(tmp_path, steps)

    # Then
    assert results[0]["ok"] is False
    assert "em dash" in results[0]["error"]
    assert results[1] == {"ok": True}


def test_denial_without_stderr_names_the_hook(tmp_path):
    # Given
    write_hook(tmp_path, "silent.py", SILENT_DENIAL)

    # When
    results = drive(tmp_path, [call()])

    # Then
    assert results == [{"ok": False, "error": "Blocked by silent.py."}]
