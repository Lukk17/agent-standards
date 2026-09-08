"""Tests for the task-list hook at .agents/hooks/task_list_sync.py.

Driven as a subprocess, because the hook contract is the process contract:
stdin payload, --event and --format flags, stdout shape, exit code. Every run
gets its own project root, because the hook writes a real file at that root and
finds it by the working directory it was started in.
"""

import json
import subprocess
import sys

import pytest

from tests.conftest import TASK_LIST_SYNC_HOOK

TASK_LIST = "tasks.md"


@pytest.fixture
def project(tmp_path):
    """A throwaway project root the hook will recognise as one."""
    (tmp_path / ".agents" / "hooks").mkdir(parents=True)

    return tmp_path


def run(project, event, fmt="claude", payload=None):
    result = subprocess.run(
        [sys.executable, str(TASK_LIST_SYNC_HOOK), "--event", event, "--format", fmt],
        input=json.dumps(payload if payload is not None else {}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(project),
    )

    return result.returncode, result.stdout, result.stderr


def task(task_id, subject):
    return {"task_id": task_id, "task_subject": subject}


def lines(project):
    path = project / TASK_LIST

    if not path.is_file():
        return []

    return path.read_text(encoding="utf-8").splitlines()


def context(out):
    """The additionalContext string out of whichever shape carried it."""
    payload = json.loads(out)

    if "additionalContext" in payload:
        return payload["additionalContext"]

    return payload["hookSpecificOutput"]["additionalContext"]


# TaskCreated and TaskCompleted upsert one line each, keyed on task_id.


def test_a_created_task_is_written_as_open(project):
    # When
    code, out, err = run(project, "taskcreated", payload=task("task-001", "Implement auth"))

    # Then the record modes print nothing at all
    assert (code, out, err) == (0, "", "")
    assert lines(project) == ["- [open] `task-001`: Implement auth"]


def test_a_completed_task_is_written_as_done(project):
    run(project, "taskcreated", payload=task("task-001", "Implement auth"))

    run(project, "taskcompleted", payload=task("task-001", "Implement auth"))

    assert lines(project) == ["- [done] `task-001`: Implement auth"]


def test_completing_a_task_updates_in_place_rather_than_appending(project):
    # Given three tasks in a known order
    for index in range(1, 4):
        run(project, "taskcreated", payload=task("task-00" + str(index), "Job " + str(index)))

    # When the middle one completes
    run(project, "taskcompleted", payload=task("task-002", "Job 2"))

    # Then the line changes where it stood, and nothing is duplicated
    assert lines(project) == [
        "- [open] `task-001`: Job 1",
        "- [done] `task-002`: Job 2",
        "- [open] `task-003`: Job 3",
    ]


def test_a_completion_without_a_subject_keeps_the_recorded_one(project):
    # Given a task recorded with a subject
    run(project, "taskcreated", payload=task("task-001", "Implement auth"))

    # When the completion event carries no subject
    run(project, "taskcompleted", payload={"task_id": "task-001"})

    # Then the subject already on the line survives
    assert lines(project) == ["- [done] `task-001`: Implement auth"]


def test_a_subject_is_flattened_to_one_line(project):
    run(project, "taskcreated", payload=task("task-001", "Implement\nauth   and   login"))

    assert lines(project) == ["- [open] `task-001`: Implement auth and login"]


def test_a_status_the_model_wrote_by_hand_survives_a_later_event(project):
    # Given a status only the model can set, written straight into the file
    (project / TASK_LIST).write_text("- [blocked] task-001: Implement auth\n", encoding="utf-8")

    # When an unrelated task is created
    run(project, "taskcreated", payload=task("task-002", "Write tests"))

    # Then the hand-written status is left exactly as it was
    assert lines(project)[0] == "- [blocked] task-001: Implement auth"


def test_an_in_progress_line_is_updated_in_place_on_completion(project):
    (project / TASK_LIST).write_text("- [in progress] task-001: Implement auth\n", encoding="utf-8")

    run(project, "taskcompleted", payload=task("task-001", "Implement auth"))

    assert lines(project) == ["- [done] `task-001`: Implement auth"]


def test_an_id_carrying_a_colon_is_closed_rather_than_duplicated(project):
    # Given a tracker id of the kind that used to split on its own colon
    run(project, "taskcreated", payload=task("feat:001", "Implement auth"))

    assert lines(project) == ["- [open] `feat:001`: Implement auth"]

    # When the same task completes
    run(project, "taskcompleted", payload=task("feat:001", "Implement auth"))

    # Then the one line changed status, and no open item is left behind
    assert lines(project) == ["- [done] `feat:001`: Implement auth"]
    assert run(project, "stop") == (0, "", "")


def test_an_id_carrying_the_delimiter_is_refused(project):
    # Given an id that cannot be written back without breaking the delimiter
    code, out, err = run(project, "taskcreated", payload=task("feat`001", "Implement auth"))

    # Then nothing is written rather than a line that can never be read back
    assert (code, out, err) == (0, "", "")
    assert lines(project) == []


def test_a_bare_id_written_before_the_delimiter_still_parses(project):
    # Given a line in the older spelling, or one a human typed
    (project / TASK_LIST).write_text("- [open] task-001: Implement auth\n", encoding="utf-8")

    # When the task completes
    run(project, "taskcompleted", payload=task("task-001", "Implement auth"))

    # Then it is matched in place and rewritten in the delimited spelling
    assert lines(project) == ["- [done] `task-001`: Implement auth"]


def test_an_event_without_a_task_id_writes_nothing(project):
    code, out, err = run(project, "taskcreated", payload={"task_subject": "No identity"})

    assert (code, out, err) == (0, "", "")
    assert lines(project) == []


def test_unrelated_lines_in_the_file_are_left_alone(project):
    # Given a file the model has written notes into around the task lines
    (project / TASK_LIST).write_text(
        "Notes for this session.\n\n- [open] task-001: Implement auth\n", encoding="utf-8"
    )

    # When
    run(project, "taskcompleted", payload=task("task-001", "Implement auth"))

    # Then
    assert lines(project) == [
        "Notes for this session.",
        "",
        "- [done] `task-001`: Implement auth",
    ]


# SessionStart and PreCompact put the stored list back into context.


def test_session_start_injects_the_stored_list(project):
    run(project, "taskcreated", payload=task("task-001", "Implement auth"))

    code, out, err = run(project, "sessionstart")

    assert (code, err) == (0, "")
    assert "- [open] `task-001`: Implement auth" in context(out)


def test_the_claude_and_codex_shape_names_the_event(project):
    run(project, "taskcreated", payload=task("task-001", "Implement auth"))

    for event, name in (("sessionstart", "SessionStart"), ("precompact", "PreCompact")):
        _code, out, _err = run(project, event)

        assert json.loads(out)["hookSpecificOutput"]["hookEventName"] == name


def test_the_copilot_shape_is_flat(project):
    run(project, "taskcreated", payload=task("task-001", "Implement auth"))

    _code, out, _err = run(project, "sessionstart", fmt="copilot")

    payload = json.loads(out)

    assert list(payload) == ["additionalContext"]
    assert "task-001" in payload["additionalContext"]


def test_injection_is_silent_when_there_is_no_list(project):
    assert run(project, "sessionstart") == (0, "", "")


def test_injection_is_silent_when_the_list_is_only_blank_lines(project):
    (project / TASK_LIST).write_text("\n\n   \n", encoding="utf-8")

    assert run(project, "sessionstart") == (0, "", "")


# Stop blocks once while anything is still unfinished.


@pytest.mark.parametrize("status", ["open", "in progress"])
def test_stop_blocks_while_an_item_is_unfinished(project, status):
    # Given
    (project / TASK_LIST).write_text(
        "- [" + status + "] task-001: Implement auth\n", encoding="utf-8"
    )

    # When
    code, out, err = run(project, "stop")

    # Then
    assert (code, err) == (0, "")

    payload = json.loads(out)

    assert payload["decision"] == "block"
    assert "task-001" in payload["reason"]
    assert status in payload["reason"]


def test_stop_names_a_delimited_id_without_its_delimiters(project):
    (project / TASK_LIST).write_text("- [open] `feat:001`: Implement auth\n", encoding="utf-8")

    _code, out, _err = run(project, "stop")

    assert "feat:001" in json.loads(out)["reason"]


@pytest.mark.parametrize("status", ["done", "blocked"])
def test_stop_allows_once_nothing_is_unfinished(project, status):
    (project / TASK_LIST).write_text(
        "- [" + status + "] task-001: Implement auth\n", encoding="utf-8"
    )

    assert run(project, "stop") == (0, "", "")


def test_stop_names_every_unfinished_item(project):
    (project / TASK_LIST).write_text(
        "- [open] task-001: One\n- [done] task-002: Two\n- [in progress] task-003: Three\n",
        encoding="utf-8",
    )

    _code, out, _err = run(project, "stop")

    reason = json.loads(out)["reason"]

    assert "task-001" in reason
    assert "task-003" in reason
    assert "task-002" not in reason


def test_stop_allows_when_there_is_no_list_at_all(project):
    assert run(project, "stop") == (0, "", "")


def test_the_loop_guard_stops_a_second_block(project):
    """One forced continuation is the point, an unbounded loop is not."""
    # Given a list that would block, on a turn already continued by a stop hook
    (project / TASK_LIST).write_text("- [open] task-001: Implement auth\n", encoding="utf-8")

    # When
    result = run(project, "stop", payload={"stop_hook_active": True})

    # Then
    assert result == (0, "", "")


def test_a_line_that_is_not_a_task_never_counts_as_unfinished(project):
    (project / TASK_LIST).write_text(
        "- [todo] task-001: Unknown status\nplain prose about open work\n", encoding="utf-8"
    )

    assert run(project, "stop") == (0, "", "")


# Everything unrecognised, malformed, or not applicable allows in silence.


@pytest.mark.parametrize(
    "argv",
    [
        ["--event", "stop", "--format", "plain"],
        ["--event", "notanevent", "--format", "claude"],
        ["--event", "stop"],
        ["--format", "claude"],
        [],
        ["--bogus"],
    ],
    ids=["runner-format", "unknown-event", "no-format", "no-event", "nothing", "unknown-flag"],
)
def test_an_inapplicable_invocation_allows_in_silence(project, argv):
    """Nothing here may exit 2: that is the deny code in the runner contract."""
    # Given a list that would otherwise block
    (project / TASK_LIST).write_text("- [open] task-001: Implement auth\n", encoding="utf-8")

    # When
    result = subprocess.run(
        [sys.executable, str(TASK_LIST_SYNC_HOOK), *argv],
        input=json.dumps({}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(project),
    )

    # Then
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


@pytest.mark.parametrize(
    "raw",
    ["", "not json", "[]", "null", '"a string"'],
    ids=["empty", "garbage", "list", "null", "string"],
)
def test_a_malformed_payload_allows(project, raw):
    result = subprocess.run(
        [sys.executable, str(TASK_LIST_SYNC_HOOK), "--event", "taskcreated", "--format", "claude"],
        input=raw,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(project),
    )

    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")
    assert lines(project) == []


def test_a_non_ascii_subject_survives_the_round_trip(project):
    run(project, "taskcreated", payload=task("task-001", "Wdroz uwierzytelnianie zurueck"))

    _code, out, _err = run(project, "sessionstart")

    assert "Wdroz uwierzytelnianie zurueck" in context(out)
