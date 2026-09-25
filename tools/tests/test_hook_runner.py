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
import re
import shutil
import stat
import sys
import time
from contextlib import contextmanager

import pytest

from tests.conftest import (
    MARKDOWN_LINT_HOOK,
    NO_AI_MARKERS_HOOK,
    PLUGIN,
    PREFLIGHT_GATE,
    REPO_ROOT,
    RUNNER_DRIVER,
    TASK_LIST_SYNC_HOOK,
)
from tests.process_tree import run_bounded

NODE = shutil.which("node")

SHIPPED_HOOKS = (PREFLIGHT_GATE, NO_AI_MARKERS_HOOK, TASK_LIST_SYNC_HOOK, MARKDOWN_LINT_HOOK)

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")

RECORDER = """import json
import sys
import time

HOOK_ORDER = {order}
{text}
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

HANGS = """import sys
import time

HOOK_ORDER = 10

time.sleep(60)
sys.exit(2)
"""

EM_DASH_PROSE = "The plan is simple — delegate the work."


def write_hook(root, name, source):
    """Drop a file into the project's .agents/hooks/ and return its path."""
    hooks = root / ".agents" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    path = hooks / name
    path.write_text(source, encoding="utf-8")

    return path


def recorder_source(name, order, log, deny=False, text=False):
    return RECORDER.format(
        order=order,
        text="HOOK_TEXT_EVENT = True\n" if text else "",
        log=json.dumps(str(log)),
        name=json.dumps(name),
        deny="True" if deny else "False",
    )


def recorder(root, name, order, log, deny=False, text=False):
    return write_hook(root, name, recorder_source(name, order, log, deny, text))


ROOT_SESSION = "s1"
CHILD_SESSION = "s2"

SESSIONS = {
    ROOT_SESSION: {"id": ROOT_SESSION},
    CHILD_SESSION: {"id": CHILD_SESSION, "parentID": ROOT_SESSION},
}


def call(tool="Edit", args=None, agent="", session=None, text=None):
    """One scripted tool call for the driver.

    Args:
        agent: the agent named on the session's user message, "" for none.
        session: defaults to the child session when an agent is named, else the root.
    """
    messages = []

    if agent:
        messages.append({"info": {"role": "user", "agent": agent}, "parts": []})

    if text is not None:
        messages.append(
            {"info": {"role": "assistant"}, "parts": [{"type": "text", "text": text}]}
        )

    if session is None:
        session = CHILD_SESSION if agent else ROOT_SESSION

    return {
        "kind": "call",
        "input": {"tool": tool, "sessionID": session, "callID": "c1"},
        "output": {"args": args if args is not None else {}},
        "messages": messages,
    }


def isolated_home(root):
    """An empty home directory beside the project, so no real global hook ever runs."""
    home = root.parent / (root.name + ".home")
    home.mkdir(exist_ok=True)

    return home


def drive(root, steps, sessions=None, wrapped=False, path=None, home=None):
    """Run the scripted steps against one plugin instance and return results.

    Args:
        path: the PATH the plugin spawns hooks under, the driver's own when None.
        home: the home directory the plugin sees, an empty one beside root when None.
    """
    job = {
        "plugin": str(PLUGIN),
        "root": str(root),
        "sessions": SESSIONS if sessions is None else sessions,
        "wrapped": wrapped,
        "steps": steps,
        "home": str(home if home is not None else isolated_home(root)),
        **({} if path is None else {"path": path}),
    }

    result = run_bounded(
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
        run_bounded(
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
            run_bounded(
                ["icacls", str(path), "/remove:d", user], capture_output=True
            )
        else:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def real_hooks(root):
    """A project root holding copies of every hook this repo ships."""
    hooks = root / ".agents" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)

    for source in SHIPPED_HOOKS:
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


# A project without its own .agents/hooks/ falls back to the global install
# under ~/.agents/hooks/, unless it holds the opt-out file.

OPT_OUT = (".agents", "no-global-hooks")


def global_home(tmp_path):
    """A home directory holding a global hooks directory, and that directory."""
    home = tmp_path / "home"
    hooks = home / ".agents" / "hooks"
    hooks.mkdir(parents=True)

    return home, hooks


def global_recorder(hooks, name, log, deny=False):
    path = hooks / name
    path.write_text(recorder_source(name, 10, log, deny), encoding="utf-8")

    return path


def test_the_project_hooks_win_over_the_global_ones(tmp_path):
    # Given a project with its own hooks and a global install beside it
    project = tmp_path / "project"
    log = tmp_path / "log.jsonl"
    home, hooks = global_home(tmp_path)
    recorder(project, "project_hook.py", 10, log)
    global_recorder(hooks, "global_hook.py", log, deny=True)

    # When
    results = drive(project, [call()], home=home)

    # Then only the project's own hook ran
    assert results == [{"ok": True}]
    assert hooks_run(log) == ["project_hook.py"]


def test_an_empty_project_hooks_directory_still_wins(tmp_path):
    # Given a project whose own hooks directory is empty
    project = tmp_path / "project"
    (project / ".agents" / "hooks").mkdir(parents=True)
    log = tmp_path / "log.jsonl"
    home, hooks = global_home(tmp_path)
    global_recorder(hooks, "global_hook.py", log, deny=True)

    # When
    results = drive(project, [call()], home=home)

    # Then
    assert results == [{"ok": True}]
    assert hooks_run(log) == []


def test_a_project_without_hooks_falls_back_to_the_global_ones(tmp_path):
    # Given a project with no .agents/ at all and a global install
    project = tmp_path / "project"
    project.mkdir()
    log = tmp_path / "log.jsonl"
    home, hooks = global_home(tmp_path)
    global_recorder(hooks, "global_hook.py", log, deny=True)

    # When
    results = drive(project, [call()], home=home)

    # Then the global hook ran, against the project rather than the home directory
    assert results == [{"ok": False, "error": "denied by global_hook.py"}]
    assert read_log(log)[0]["envelope"]["cwd"] == str(project)


def test_the_shipped_gate_installed_globally_protects_a_bare_project(tmp_path):
    # Given the shipped gate under ~/.agents/hooks/ and a project that imported nothing
    project = tmp_path / "project"
    project.mkdir()
    home, hooks = global_home(tmp_path)
    shutil.copy(PREFLIGHT_GATE, hooks / PREFLIGHT_GATE.name)

    # When the main thread edits a project file, then a file under the home directory
    edit_inside = call(tool="Edit", args={"file_path": "src/app.py"}, session=ROOT_SESSION)
    edit_home = call(tool="Edit", args={"file_path": str(home / "notes.md")}, session=ROOT_SESSION)
    results = drive(project, [edit_inside, edit_home], home=home)

    # Then
    assert results[0]["ok"] is False
    assert "src/app.py" in results[0]["error"]
    assert results[1] == {"ok": True}


def test_no_project_hooks_and_no_global_hooks_allows(tmp_path):
    # Given neither a project hooks directory nor a global one
    project = tmp_path / "project"
    project.mkdir()
    home = tmp_path / "home"
    home.mkdir()

    # When
    results = drive(project, [call()], home=home)

    # Then
    assert results == [{"ok": True}]


def test_the_opt_out_file_turns_the_global_fallback_off(tmp_path):
    # Given a project holding only the opt-out file, and a global install
    project = tmp_path / "project"
    opt_out = project.joinpath(*OPT_OUT)
    opt_out.parent.mkdir(parents=True)
    opt_out.write_text("", encoding="utf-8")
    log = tmp_path / "log.jsonl"
    home, hooks = global_home(tmp_path)
    global_recorder(hooks, "global_hook.py", log, deny=True)

    # When
    results = drive(project, [call()], home=home)

    # Then no hook ran at all
    assert results == [{"ok": True}]
    assert hooks_run(log) == []


def test_the_opt_out_file_never_switches_off_the_project_hooks(tmp_path):
    # Given a project with its own hook and the opt-out file
    project = tmp_path / "project"
    log = tmp_path / "log.jsonl"
    recorder(project, "project_hook.py", 10, log, deny=True)
    project.joinpath(*OPT_OUT).write_text("", encoding="utf-8")

    # When
    results = drive(project, [call()])

    # Then
    assert results == [{"ok": False, "error": "denied by project_hook.py"}]


def test_the_fallback_is_decided_on_every_call(tmp_path):
    # Given a project that starts without hooks and a global install
    project = tmp_path / "project"
    project.mkdir()
    log = tmp_path / "log.jsonl"
    home, hooks = global_home(tmp_path)
    global_recorder(hooks, "global_hook.py", log)

    # When the opt-out file appears mid-session
    steps = [call(), {"kind": "write", "path": "/".join(OPT_OUT), "content": ""}, call()]
    results = drive(project, steps, home=home)

    # Then only the first call reached the global hook
    assert results == [{"ok": True}] * 3
    assert hooks_run(log) == ["global_hook.py"]


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


def test_a_hook_past_the_timeout_is_killed_and_allows(tmp_path):
    # Given a hook that would deny, but only after the 10 second budget
    log = tmp_path / "log.jsonl"
    write_hook(tmp_path, "a_hangs.py", HANGS)
    recorder(tmp_path, "b_after.py", 20, log)

    # When
    started = time.monotonic()
    results = drive(tmp_path, [call()])
    elapsed = time.monotonic() - started

    # Then the runner moved on to the next hook instead of waiting it out
    assert results == [{"ok": True}]
    assert hooks_run(log) == ["b_after.py"]
    assert elapsed < 30


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
    result = run_bounded(
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


def test_a_hook_file_inside_a_subdirectory_is_never_run(tmp_path):
    # Given a per-agent helper one level down that would deny if it ran, and a
    # hook beside it at the top level
    log = tmp_path / "log.jsonl"
    (tmp_path / ".agents" / "hooks" / "copilot").mkdir(parents=True)
    recorder(tmp_path, "copilot/helper.py", 1, log, deny=True)
    recorder(tmp_path, "top.py", 10, log)

    # When
    results = drive(tmp_path, [call()])

    # Then only the top-level hook was spawned
    assert results == [{"ok": True}]
    assert hooks_run(log) == ["top.py"]


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

    assert envelope["contract"] == 3
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


def test_root_session_is_the_main_thread_whatever_its_agent(tmp_path):
    # Given
    log = tmp_path / "log.jsonl"
    recorder(tmp_path, "watcher.py", 10, log)

    # When the primary agent is named on a session with no parent
    drive(tmp_path, [call(agent="build", session=ROOT_SESSION)])

    # Then
    envelope = read_log(log)[0]["envelope"]

    assert (envelope["agent_type"], envelope["is_subagent"]) == ("build", False)


def test_agent_name_comes_from_the_newest_message_that_names_one(tmp_path):
    # Given a user message naming one agent and a later assistant message naming another
    log = tmp_path / "log.jsonl"
    recorder(tmp_path, "watcher.py", 10, log)
    step = call(session=CHILD_SESSION)
    step["messages"] = [
        {"info": {"role": "user", "agent": "general"}, "parts": []},
        {"info": {"role": "assistant", "mode": "python-pro"}, "parts": []},
        {"info": {"role": "assistant"}, "parts": []},
    ]

    # When
    drive(tmp_path, [step])

    # Then
    assert read_log(log)[0]["envelope"]["agent_type"] == "python-pro"


def test_a_wrapped_session_reply_is_read_the_same_way(tmp_path):
    # Given a client whose responseStyle wraps every reply in { data }
    log = tmp_path / "log.jsonl"
    recorder(tmp_path, "watcher.py", 10, log)

    # When
    drive(tmp_path, [call(agent="general"), call(session=ROOT_SESSION)], wrapped=True)

    # Then
    placed = [entry["envelope"]["is_subagent"] for entry in read_log(log)]

    assert placed == [True, False]


@pytest.mark.parametrize(
    "sessions",
    [
        {},
        {ROOT_SESSION: {"error": "not found"}},
        {ROOT_SESSION: {"id": "someone-else"}},
    ],
    ids=["lookup-throws", "error-body", "other-session"],
)
def test_a_failed_session_lookup_leaves_is_subagent_out(tmp_path, sessions):
    # Given
    log = tmp_path / "log.jsonl"
    recorder(tmp_path, "watcher.py", 10, log)

    # When
    drive(tmp_path, [call(agent="build", session=ROOT_SESSION)], sessions=sessions)

    # Then
    envelope = read_log(log)[0]["envelope"]

    assert "is_subagent" not in envelope
    assert envelope["agent_type"] == "build"


def test_a_session_is_looked_up_once_and_a_failure_is_retried(tmp_path):
    # Given
    recorder(tmp_path, "watcher.py", 10, tmp_path / "log.jsonl")
    steps = [
        call(session=ROOT_SESSION),
        call(session=ROOT_SESSION),
        call(session="missing"),
        call(session="missing"),
        {"kind": "lookups"},
    ]

    # When
    results = drive(tmp_path, steps)

    # Then one lookup for the placed session, one per call for the unplaced one
    assert results[-1] == {"ok": True, "count": 3}


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


def long_history(text_at_start=False, length=40):
    """A session history longer than the plugin's message window, oldest first."""
    history = [{"info": {"role": "user", "agent": "general"}, "parts": []} for _ in range(length)]
    prose = {"info": {"role": "assistant"}, "parts": [{"type": "text", "text": "Old reply."}]}

    if text_at_start:
        history[0] = prose
    else:
        history[-1] = prose

    return history


def test_repeated_tool_calls_fetch_only_the_newest_messages(tmp_path):
    # Given a long session whose newest messages already answer both questions
    recorder(tmp_path, "watcher.py", 10, tmp_path / "log.jsonl")
    steps = []

    for _ in range(3):
        step = call(session=ROOT_SESSION)
        step["messages"] = long_history()
        steps.append(step)

    # When three tool calls run
    results = drive(tmp_path, [*steps, {"kind": "fetches"}])

    # Then each made one bounded messages call and none read the whole history
    limits = results[-1]["limits"]

    assert len(limits) == 3
    assert None not in limits
    assert all(limit < 40 for limit in limits)


def test_prose_older_than_the_window_is_still_read_from_the_full_history(tmp_path):
    # Given the only assistant prose sits before the newest-message window
    log = tmp_path / "log.jsonl"
    recorder(tmp_path, "watcher.py", 10, log)
    step = call(session=ROOT_SESSION)
    step["messages"] = long_history(text_at_start=True)

    # When
    results = drive(tmp_path, [step, {"kind": "fetches"}])

    # Then the window was widened to the whole history, and the prose delivered
    assert results[-1]["limits"][-1] is None
    assert read_log(log)[0]["envelope"]["assistant_text"] == "Old reply."


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


def test_the_reporting_hooks_never_deny_a_tool_call(tmp_path):
    """Exit 2 from either of these would block every tool call on this surface.

    Both are wired at `tool.execute.before` like the rest, both have plenty to
    report here, and the runner throws away their stderr unless they deny, so
    the only correct answer from either is a silent 0.
    """
    # Given every shipped hook, a lint script to reach for, a docs file that
    # fails that lint, and a task list holding an unfinished item
    real_hooks(tmp_path)
    (tmp_path / "tools").mkdir()
    shutil.copy(REPO_ROOT / "tools" / "check-markdown.py", tmp_path / "tools")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "GUIDE.md").write_text(
        "### Heading\n\n" + EM_DASH_PROSE + "\n", encoding="utf-8"
    )
    (tmp_path / "tasks.md").write_text(
        "- [open] `task-001`: Still running\n", encoding="utf-8"
    )

    # When a subagent edits that file, so the gate itself has nothing to say
    step = call(
        tool="Edit",
        args={"file_path": "docs/GUIDE.md"},
        agent="markdown-writer",
        session=CHILD_SESSION,
    )
    results = drive(tmp_path, [step])

    # Then
    assert results == [{"ok": True}]


@pytest.mark.parametrize(
    "hook",
    [MARKDOWN_LINT_HOOK, TASK_LIST_SYNC_HOOK],
    ids=["markdown-lint", "task-list"],
)
def test_a_reporting_hook_exits_zero_on_the_plain_format(tmp_path, hook):
    # Given the envelope the runner hands every hook, on a docs path
    real_hooks(tmp_path)
    (tmp_path / "tools").mkdir()
    shutil.copy(REPO_ROOT / "tools" / "check-markdown.py", tmp_path / "tools")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "GUIDE.md").write_text(
        "### Heading\n\n" + EM_DASH_PROSE + "\n", encoding="utf-8"
    )
    (tmp_path / "tasks.md").write_text(
        "- [open] `task-001`: Still running\n", encoding="utf-8"
    )

    envelope = {
        "contract": 3,
        "event": "tool.execute.before",
        "tool_name": "Edit",
        "tool_input": {"file_path": "docs/GUIDE.md"},
        "agent_type": "",
        "is_subagent": False,
        "assistant_text": "",
        "cwd": str(tmp_path),
    }

    # When
    result = run_bounded(
        [sys.executable, "-S", "-E", str(hook), "--format", "plain"],
        input=json.dumps(envelope),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(tmp_path),
    )

    # Then
    assert (result.returncode, result.stdout) == (0, "")


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


def test_shipped_gate_denies_a_root_session_write(tmp_path):
    # Given
    real_hooks(tmp_path)

    # When the primary agent of a session with no parent edits a file
    step = call(tool="Write", args={"file_path": "src/app.py"}, agent="code", session=ROOT_SESSION)
    results = drive(tmp_path, [step])

    # Then
    assert results[0]["ok"] is False
    assert results[0]["error"].startswith("PREFLIGHT:")


def test_shipped_gate_allows_a_child_session_write(tmp_path):
    # Given
    real_hooks(tmp_path)

    # When a built-in subagent in a child session edits the same file
    step = call(tool="Write", args={"file_path": "src/app.py"}, agent="general", session=CHILD_SESSION)
    results = drive(tmp_path, [step])

    # Then
    assert results == [{"ok": True}]


def test_shipped_gate_allows_when_the_session_cannot_be_placed(tmp_path):
    # Given
    real_hooks(tmp_path)

    # When the session lookup fails
    step = call(tool="Write", args={"file_path": "src/app.py"}, session="unknown")
    results = drive(tmp_path, [step])

    # Then the gate fails open
    assert results == [{"ok": True}]


def user_message(parts=None, message_id="msg_1", session=ROOT_SESSION):
    """The chat.message input and output for one user prompt."""
    return {
        "kind": "message",
        "input": {"sessionID": session, "agent": "build", "messageID": message_id},
        "output": {
            "message": {"id": message_id, "sessionID": session, "role": "user"},
            "parts": parts if parts is not None else [],
        },
    }


def test_every_prompt_gets_the_reminder_as_a_synthetic_part(tmp_path):
    # Given the user's own text part
    typed = {"id": "prt_0", "sessionID": ROOT_SESSION, "messageID": "msg_1", "type": "text", "text": "Hi"}

    # When
    results = drive(tmp_path, [user_message([typed])])

    # Then the reminder follows the user's part, on the same message
    parts = results[0]["parts"]
    added = parts[-1]

    assert parts[0] == typed
    assert len(parts) == 2
    assert (added["type"], added["synthetic"]) == ("text", True)
    assert (added["sessionID"], added["messageID"]) == (ROOT_SESSION, "msg_1")
    assert added["id"].startswith("prt_") and len(added["id"]) == 30


def test_reminder_part_ids_are_unique_and_ascending(tmp_path):
    # Given
    steps = [user_message(message_id="msg_" + str(n)) for n in range(5)]

    # When
    ids = [result["parts"][0]["id"] for result in drive(tmp_path, steps)]

    # Then
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)


@pytest.mark.parametrize(
    "output,expected",
    [({}, None), ({"parts": "not a list"}, "not a list"), ({"parts": []}, [])],
    ids=["no-parts", "bad-parts", "no-message-id"],
)
def test_a_malformed_message_gets_no_reminder_and_no_error(tmp_path, output, expected):
    # Given a payload the plugin cannot attach a part to
    step = {"kind": "message", "input": {}, "output": output}

    # When
    results = drive(tmp_path, [step])

    # Then
    assert results == [{"ok": True, "parts": expected}]


MAIN_MARKER = "PREFLIGHT: before code work"
SUBAGENT_MARKER = "PREFLIGHT for a subagent:"


def test_a_subagent_task_prompt_gets_the_subagent_text_and_not_the_reminder(tmp_path):
    # Given the task prompt a subagent receives in its child session
    typed = {"id": "prt_0", "sessionID": CHILD_SESSION, "messageID": "msg_1", "type": "text", "text": "Write x"}

    # When
    parts = drive(tmp_path, [user_message([typed], session=CHILD_SESSION)])[0]["parts"]

    # Then the task is followed by the subagent text alone, on the same message
    added = parts[-1]

    assert parts[0] == typed
    assert len(parts) == 2
    assert (added["type"], added["synthetic"]) == ("text", True)
    assert (added["sessionID"], added["messageID"]) == (CHILD_SESSION, "msg_1")
    assert added["text"].startswith(SUBAGENT_MARKER)
    assert "Delegate investigation" not in added["text"]


@pytest.mark.parametrize("wrapped", [False, True], ids=["bare", "wrapped"])
def test_the_text_follows_the_session_parent_in_either_response_style(tmp_path, wrapped):
    # Given one root prompt and one child prompt
    steps = [user_message(session=ROOT_SESSION), user_message(message_id="msg_2", session=CHILD_SESSION)]

    # When
    results = drive(tmp_path, steps, wrapped=wrapped)

    # Then the root prompt gets the reminder and the child prompt the subagent text, one part each
    [root_parts, child_parts] = [result["parts"] for result in results]

    assert [len(root_parts), len(child_parts)] == [1, 1]
    assert root_parts[0]["text"].startswith(MAIN_MARKER)
    assert child_parts[0]["text"].startswith(SUBAGENT_MARKER)


def test_a_prompt_in_a_session_that_cannot_be_placed_gets_no_reminder(tmp_path):
    # When the session lookup throws
    results = drive(tmp_path, [user_message(session="unknown")])

    # Then
    assert results == [{"ok": True, "parts": []}]


def test_a_placed_session_is_looked_up_once_across_prompts(tmp_path):
    # Given
    steps = [user_message(), user_message(message_id="msg_2"), {"kind": "lookups"}]

    # When
    results = drive(tmp_path, steps)

    # Then
    assert results[-1] == {"ok": True, "count": 1}


# experimental.text.complete hands every finished text part to the same hooks,
# and a hook that prints {"text": ...} on a clean exit replaces the stored text.

APPENDS = """import json
import sys

HOOK_ORDER = {order}
HOOK_TEXT_EVENT = True

envelope = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{{}}")

if envelope.get("event") == "experimental.text.complete":
    sys.stdout.write(json.dumps({{"text": envelope["text"] + {suffix}}}))
"""

PRINTS_THEN = """import sys

HOOK_ORDER = 10
HOOK_TEXT_EVENT = True

sys.stdout.write({stdout})
sys.exit({code})
"""


def finished_text(text):
    return {
        "kind": "text",
        "input": {"sessionID": ROOT_SESSION, "messageID": "msg_1", "partID": "prt_1"},
        "output": {"text": text},
    }


def test_the_shipped_formatting_check_fixes_a_finished_text_part(tmp_path):
    # Given
    real_hooks(tmp_path)

    # When
    results = drive(tmp_path, [finished_text("The plan is simple — delegate **now**.")])

    # Then
    assert results == [{"ok": True, "text": "The plan is simple, delegate now."}]


def test_every_hook_that_declares_the_text_event_sees_it(tmp_path):
    # Given
    log = tmp_path / "log.jsonl"
    recorder(tmp_path, "a_first.py", 10, log, deny=True, text=True)
    recorder(tmp_path, "b_second.py", 20, log, text=True)

    # When
    results = drive(tmp_path, [finished_text("Some prose.")])

    # Then a text event cannot be denied, so both ran and the text is unchanged
    envelope = read_log(log)[0]["envelope"]

    assert results == [{"ok": True, "text": "Some prose."}]
    assert hooks_run(log) == ["a_first.py", "b_second.py"]
    assert envelope["event"] == "experimental.text.complete"
    assert envelope["text"] == "Some prose."
    assert envelope["contract"] == 3
    assert "is_subagent" not in envelope


def test_each_hook_sees_the_text_the_previous_one_left(tmp_path):
    # Given
    write_hook(tmp_path, "a.py", APPENDS.format(order=10, suffix=json.dumps(" A")))
    write_hook(tmp_path, "b.py", APPENDS.format(order=20, suffix=json.dumps(" B")))

    # When
    results = drive(tmp_path, [finished_text("start")])

    # Then
    assert results == [{"ok": True, "text": "start A B"}]


@pytest.mark.parametrize(
    "stdout,code",
    [
        ('\'{"text": "replaced"}\'', 1),
        ('\'{"text": "replaced"}\'', 2),
        ("'not json'", 0),
        ('\'{"text": 7}\'', 0),
        ("'[]'", 0),
    ],
    ids=["crash-exit", "deny-exit", "not-json", "not-a-string", "not-an-object"],
)
def test_a_text_part_is_kept_unless_a_hook_answers_cleanly(tmp_path, stdout, code):
    # Given
    write_hook(tmp_path, "odd.py", PRINTS_THEN.format(stdout=stdout, code=code))

    # When
    results = drive(tmp_path, [finished_text("keep me")])

    # Then
    assert results == [{"ok": True, "text": "keep me"}]


@pytest.mark.parametrize("output", [{}, {"text": ""}, {"text": 5}], ids=["missing", "empty", "number"])
def test_an_unusable_text_part_is_left_alone(tmp_path, output):
    # Given
    log = tmp_path / "log.jsonl"
    recorder(tmp_path, "only.py", 10, log)
    step = {"kind": "text", "input": {}, "output": output}

    # When
    results = drive(tmp_path, [step])

    # Then
    assert results == [{"ok": True, "text": output.get("text")}]
    assert hooks_run(log) == []


def test_a_hook_that_does_not_declare_the_text_event_is_not_run_for_it(tmp_path):
    # Given
    log = tmp_path / "log.jsonl"
    recorder(tmp_path, "declares.py", 10, log, text=True)
    recorder(tmp_path, "silent.py", 20, log)
    write_hook(tmp_path, "commented.py", "# HOOK_TEXT_EVENT = True\n" + NO_OP)

    # When
    drive(tmp_path, [finished_text("Some prose.")])

    # Then
    assert hooks_run(log) == ["declares.py"]


def test_only_the_formatting_check_among_the_shipped_hooks_takes_the_text_event():
    declares = [hook.name for hook in SHIPPED_HOOKS if "\nHOOK_TEXT_EVENT = True\n" in hook.read_text(encoding="utf-8")]

    assert declares == [NO_AI_MARKERS_HOOK.name]


def test_every_shipped_declaration_sits_inside_the_part_the_runner_reads():
    head = int(re.search(r"^const HEAD_CHARS = (\d+)$", PLUGIN.read_text(encoding="utf-8"), re.M).group(1))

    for hook in SHIPPED_HOOKS:
        source = hook.read_text(encoding="utf-8")[:head]

        assert re.search(r"^HOOK_ORDER\s*=\s*\d+\s*$", source, re.M), hook.name


# The interpreter is resolved python3 first, then python, and a candidate that
# does not answer the probe is skipped.


def interpreter_dir(tmp_path, python3=None, python=None):
    """A PATH directory holding only the named interpreters, as symlinks or failing stubs."""
    directory = tmp_path / "bin"
    directory.mkdir()

    for name, kind in (("python3", python3), ("python", python)):
        if kind == "real":
            (directory / name).symlink_to(sys.executable)
        elif kind == "stub":
            stub = directory / name
            stub.write_text("#!/bin/sh\necho 'Python was not found'\nexit 9009\n", encoding="utf-8")
            stub.chmod(0o755)

    return directory


def gate_decision_with_path(tmp_path, path):
    """Drive a main-thread source edit through the shipped gate with PATH set to `path`."""
    real_hooks(tmp_path)
    step = call(tool="Edit", args={"file_path": "src/app.py"}, session=ROOT_SESSION)

    return drive(tmp_path, [step], path=path)[0]["ok"]


@pytest.mark.skipif(sys.platform == "win32", reason="interpreter stubs need a POSIX shell and symlinks")
@pytest.mark.parametrize(
    "python3,python",
    [("real", None), ("real", "stub"), (None, "real"), ("stub", "real")],
    ids=["python3-only", "python3-before-a-broken-python", "python-only", "broken-python3-falls-back"],
)
def test_the_runner_finds_a_working_interpreter(tmp_path, python3, python):
    assert gate_decision_with_path(tmp_path, str(interpreter_dir(tmp_path, python3, python))) is False


@pytest.mark.skipif(sys.platform != "win32", reason="the python.org Windows layout names only python.exe")
def test_the_runner_falls_back_to_python_on_windows(tmp_path):
    path = os.pathsep.join([os.path.dirname(sys.executable), os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")])

    assert gate_decision_with_path(tmp_path, path) is False


def test_the_runner_allows_when_no_interpreter_answers(tmp_path):
    assert gate_decision_with_path(tmp_path, str(tmp_path / "empty")) is True
