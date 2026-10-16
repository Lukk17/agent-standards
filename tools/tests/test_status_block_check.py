"""Tests for the status tail hook at .agents/hooks/status_block_check.py.

Driven as a subprocess with --format plain and the envelope JSON on stdin. The
tail shape is the one in .agents/instructions/reply-rules.md, rule 3. Only a
user-reply event can deny, so every deny case drives one. A tool event and a
subagent payload only log the violation, and their own cases assert that.
"""

import json
import subprocess
import sys

from tests.conftest import HOOKS_DIR, REPO_ROOT
from tests.process_tree import run_bounded

HOOK = HOOKS_DIR / "status_block_check.py"

REPLY_EVENT = "stop"
TOOL_EVENT = "tool.execute.before"

TASKS_LINE = "```Tasks: 1/2 completed```"
NOW_LINE = "```NOW: what is being done right now```"
STATE_LINE = "```State: WAITING FOR YOU```"

TAIL_LINES = (
    "---",
    "Skills: agent-engineer",
    "~~DONE: older finished task~~",
    "~~DONE: most recent finished task~~",
    NOW_LINE,
    "Running: sandbox build (agent: `agent-engineer`)",
    "Next: the next task",
    "Then: the task after that",
    STATE_LINE,
    "Waiting on: nothing",
)


def tail(lines=TAIL_LINES) -> str:
    return "\n" + "\n\n".join(lines) + "\n"


TAIL = tail()


def without(prefix: str) -> str:
    return tail(tuple(line for line in TAIL_LINES if not line.startswith(prefix)))


def run(stdin: bytes) -> subprocess.CompletedProcess:
    return run_bounded(
        [sys.executable, "-S", "-E", str(HOOK), "--format", "plain"],
        input=stdin,
        capture_output=True,
        check=False,
    )


def payload(
    assistant_text: object,
    subagent: bool = False,
    cwd: object = REPO_ROOT,
    event: str = REPLY_EVENT,
) -> bytes:
    body = {
        "contract": 3,
        "event": event,
        "tool_name": "Edit",
        "tool_input": {},
        "agent_type": "general",
        "is_subagent": subagent,
        "assistant_text": assistant_text,
        "cwd": str(cwd),
    }

    return json.dumps(body).encode("utf-8")


def test_reply_with_full_tail_exits_zero():
    result = run(payload("Done, the build is green.\n" + TAIL))

    assert result.returncode == 0


def test_reply_with_tail_and_no_running_lines_exits_zero():
    result = run(payload("Done.\n" + without("Running:")))

    assert result.returncode == 0


def test_reply_without_status_denies():
    result = run(payload("Done, the build is green."))

    assert result.returncode == 2
    assert "Status block violation" in result.stderr.decode("utf-8")


def test_status_header_without_state_denies():
    result = run(payload("Done.\nStatus\n\nNo state here."))

    assert result.returncode == 2


def test_state_before_status_denies():
    result = run(payload("State: DONE\nSome text.\nStatus\n"))

    assert result.returncode == 2


def test_empty_prose_exits_zero():
    result = run(payload(""))

    assert result.returncode == 0


def test_subagent_payload_without_tail_exits_zero():
    result = run(payload("Done, the build is green.", subagent=True))

    assert result.returncode == 0
    assert "Subagent footer note (not blocking)" in result.stderr.decode("utf-8")


def test_tool_event_without_tail_logs_and_exits_zero():
    result = run(payload("Done, the build is green.", event=TOOL_EVENT))

    assert result.returncode == 0
    assert "Tool-event footer note (not blocking)" in result.stderr.decode("utf-8")


def test_corrections_plus_tail_exits_zero():
    result = run(payload('Correction: "Fixed."\n' + TAIL))

    assert result.returncode == 0


def test_fully_fenced_tail_denies():
    result = run(payload("```\nStatus\n\nState: DONE\n```"))

    assert result.returncode == 2


def test_missing_dash_run_denies():
    result = run(payload("Done.\n" + without("---")))

    assert result.returncode == 2


def test_rule_line_without_blank_line_above_denies():
    result = run(payload("Done." + TAIL.lstrip("\n")))

    assert result.returncode == 2


def test_missing_skills_line_denies():
    result = run(payload("Done.\n" + without("Skills:")))

    assert result.returncode == 2


def test_missing_now_line_denies():
    result = run(payload("Done.\n" + without(NOW_LINE)))

    assert result.returncode == 2


def test_missing_state_line_denies():
    result = run(payload("Done.\n" + without(STATE_LINE)))

    assert result.returncode == 2


def test_state_before_now_denies_full_tail():
    swapped = tuple(
        STATE_LINE if line == NOW_LINE else NOW_LINE if line == STATE_LINE else line
        for line in TAIL_LINES
    )
    result = run(payload("Done.\n" + tail(swapped)))

    assert result.returncode == 2


def test_tasks_present_with_tasks_line_exits_zero(tmp_path):
    (tmp_path / "tasks.md").write_text("- [open] fix hook\n- [done] prior work\n", encoding="utf-8")
    with_tasks = TAIL_LINES[:2] + (TASKS_LINE,) + TAIL_LINES[2:]
    result = run(payload("Done.\n" + tail(with_tasks), cwd=str(tmp_path)))

    assert result.returncode == 0


def test_tasks_present_without_tasks_line_denies(tmp_path):
    (tmp_path / "tasks.md").write_text("- [open] fix hook\n- [open] add test\n", encoding="utf-8")
    result = run(payload("Done.\n" + TAIL, cwd=str(tmp_path)))

    assert result.returncode == 2
    assert "Task list violation" in result.stderr.decode("utf-8")


def test_empty_dir_without_tasks_line_exits_zero(tmp_path):
    result = run(payload("Done.\n" + TAIL, cwd=str(tmp_path)))

    assert result.returncode == 0


def test_tasks_file_without_items_exits_zero(tmp_path):
    (tmp_path / "tasks.md").write_text("No items here.\n", encoding="utf-8")
    result = run(payload("Done.\n" + TAIL, cwd=str(tmp_path)))

    assert result.returncode == 0
