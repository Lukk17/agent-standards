"""Tests for the task watchdog at .agents/hooks/task-watchdog/task_watchdog.py.

Driven as a subprocess with --format plain and the envelope JSON on stdin. The
status block of .agents/instructions/reply-rules.md has no Tasks line, so the
watchdog compares only a Tasks line a reply still writes in its text.
"""

import json
import subprocess
import sys

from tests.conftest import HOOKS_DIR
from tests.process_tree import run_bounded
from tests.reminder_support import STATUS_BLOCK_LINES

HOOK = HOOKS_DIR / "task-watchdog" / "task_watchdog.py"

STATUS_BLOCK = "\n".join(STATUS_BLOCK_LINES)

TODOS = [
    {"content": "fix the gate", "status": "completed"},
    {"content": "run the suite", "status": "in_progress"},
    {"content": "write the changelog", "status": "pending"},
]


def run(assistant_text: str, subagent: object = False) -> subprocess.CompletedProcess:
    body = {
        "contract": 3,
        "event": "tool.execute.before",
        "tool_name": "todowrite",
        "tool_input": {"todos": TODOS},
        "agent_type": "general",
        "assistant_text": assistant_text,
    }
    if subagent is not None:
        body["is_subagent"] = subagent

    return run_bounded(
        [sys.executable, "-S", "-E", str(HOOK), "--format", "plain"],
        input=json.dumps(body).encode("utf-8"),
        capture_output=True,
        check=False,
    )


def test_a_reply_ending_with_the_status_block_and_no_tasks_line_exits_zero():
    result = run("The gate is fixed.\n\n" + STATUS_BLOCK)

    assert result.returncode == 0
    assert result.stderr == b""


def test_a_tasks_line_that_matches_the_live_list_exits_zero():
    result = run("Tasks: 1/3 completed\n\n" + STATUS_BLOCK)

    assert result.returncode == 0
    assert result.stderr == b""


def test_a_tasks_line_that_differs_from_the_live_list_denies():
    result = run("Tasks: 2/3 completed\n\n" + STATUS_BLOCK)

    assert result.returncode == 2
    assert "Task sync mismatch" in result.stderr.decode("utf-8")


def test_a_subagent_is_never_blocked_over_a_tasks_line():
    result = run("Tasks: 2/3 completed\n\n" + STATUS_BLOCK, subagent=True)

    assert result.returncode == 0


def test_a_caller_that_could_not_be_placed_is_never_blocked():
    result = run("Tasks: 2/3 completed\n\n" + STATUS_BLOCK, subagent=None)

    assert result.returncode == 0
