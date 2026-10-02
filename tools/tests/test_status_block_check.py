"""Tests for the status tail hook at .agents/hooks/status_block_check.py.

Driven as a subprocess with --format plain and the envelope JSON on stdin.
"""

import json
import subprocess
import sys

from tests.conftest import HOOKS_DIR, REPO_ROOT
from tests.process_tree import run_bounded

HOOK = HOOKS_DIR / "status_block_check.py"

TAIL = (
    "---\n"
    "\n"
    "Skills: agent-engineer\n"
    "\n"
    "Owners: agent-engineer\n"
    "\n"
    "Status\n"
    "\n"
    "~~DONE: older finished task~~\n"
    "\n"
    "~~DONE: most recent finished task~~\n"
    "\n"
    "Running: nothing\n"
    "\n"
    "```text\n"
    "NOW: what is being done right now\n"
    "```\n"
    "\n"
    "Next: the next task\n"
    "\n"
    "Then: the task after that\n"
    "\n"
    "```text\n"
    "State: WAITING FOR YOU\n"
    "```\n"
    "\n"
    "Waiting on: nothing\n"
)


def run(stdin: bytes) -> subprocess.CompletedProcess:
    return run_bounded(
        [sys.executable, "-S", "-E", str(HOOK), "--format", "plain"],
        input=stdin,
        capture_output=True,
        check=False,
    )


def payload(assistant_text: object, subagent: bool = False, cwd: object = REPO_ROOT) -> bytes:
    body = {
        "contract": 3,
        "event": "tool.execute.before",
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


def test_corrections_plus_tail_exits_zero():
    result = run(payload('Correction: "Fixed."\n' + TAIL))

    assert result.returncode == 0


def test_fully_fenced_tail_denies():
    result = run(payload("```\nStatus\n\nState: DONE\n```"))

    assert result.returncode == 2


def test_missing_dash_run_denies():
    tail_without_dash = "\n".join(
        line for line in TAIL.splitlines() if line.strip() != "---"
    ) + "\n"
    result = run(payload("Done.\n" + tail_without_dash))

    assert result.returncode == 2


def test_missing_skills_line_denies():
    tail_without_skills = "\n".join(
        line for line in TAIL.splitlines() if not line.lstrip().startswith("Skills:")
    ) + "\n"
    result = run(payload("Done.\n" + tail_without_skills))

    assert result.returncode == 2


def test_missing_owners_line_denies():
    tail_without_owners = "\n".join(
        line for line in TAIL.splitlines() if not line.lstrip().startswith("Owners:")
    ) + "\n"
    result = run(payload("Done.\n" + tail_without_owners))

    assert result.returncode == 2


def test_missing_status_denies():
    tail_without_status = "\n".join(
        line for line in TAIL.splitlines() if line.strip() != "Status"
    ) + "\n"
    result = run(payload("Done.\n" + tail_without_status))

    assert result.returncode == 2


def test_state_before_status_denies_full_tail():
    swapped = TAIL.replace("Status\n", "__STATUS__\n").replace(
        "State: WAITING FOR YOU", "Status"
    )
    swapped = swapped.replace("__STATUS__", "State: WAITING FOR YOU")
    result = run(payload("Done.\n" + swapped))

    assert result.returncode == 2


def test_tasks_present_with_tasks_line_exits_zero(tmp_path):
    (tmp_path / "tasks.md").write_text("- [open] fix hook\n- [done] prior work\n", encoding="utf-8")
    result = run(payload("Done.\n" + TAIL + "Tasks: 1/2 completed\n", cwd=str(tmp_path)))

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
