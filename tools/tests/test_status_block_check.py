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
    "----------------------\n"
    "Skills: agent-engineer\n"
    "\n"
    "Status\n"
    "\n"
    "```text\n"
    "Running: nothing\n"
    "```\n"
    "\n"
    "```text\n"
    "State: WAITING FOR YOU\n"
    "```\n"
)


def run(stdin: bytes) -> subprocess.CompletedProcess:
    return run_bounded(
        [sys.executable, "-S", "-E", str(HOOK), "--format", "plain"],
        input=stdin,
        capture_output=True,
        check=False,
    )


def payload(assistant_text: object, subagent: bool = False) -> bytes:
    body = {
        "contract": 3,
        "event": "tool.execute.before",
        "tool_name": "Edit",
        "tool_input": {},
        "agent_type": "general",
        "is_subagent": subagent,
        "assistant_text": assistant_text,
        "cwd": str(REPO_ROOT),
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


def test_fully_fenced_tail_passes():
    result = run(payload("```\nStatus\n\nState: DONE\n```"))

    assert result.returncode == 0
