"""Tests for the question numbering hook at .agents/hooks/question_numbering_check.py.

Driven as a subprocess with --format plain and the envelope JSON on stdin.
"""

import json
import subprocess
import sys

from tests.conftest import HOOKS_DIR, REPO_ROOT
from tests.process_tree import run_bounded

HOOK = HOOKS_DIR / "question_numbering_check.py"


def run(stdin: bytes) -> subprocess.CompletedProcess:
    return run_bounded(
        [sys.executable, "-S", "-E", str(HOOK), "--format", "plain"],
        input=stdin,
        capture_output=True,
        check=False,
    )


def payload(assistant_text: object) -> bytes:
    body = {
        "contract": 3,
        "event": "tool.execute.before",
        "tool_name": "Edit",
        "tool_input": {},
        "agent_type": "general",
        "is_subagent": False,
        "assistant_text": assistant_text,
        "cwd": str(REPO_ROOT),
    }

    return json.dumps(body).encode("utf-8")


def test_reply_with_no_questions_exits_zero():
    result = run(payload("The build is green and the docs are updated."))

    assert result.returncode == 0


def test_reply_with_only_numbered_questions_exits_zero():
    result = run(payload("1. Should we ship today?\n2. Should we tag the release?"))

    assert result.returncode == 0


def test_reply_with_one_unnumbered_question_denies():
    result = run(payload("Should we ship today?"))

    assert result.returncode == 2
    assert "Question numbering violation" in result.stderr.decode("utf-8")


def test_reply_with_mixed_numbered_and_unnumbered_denies():
    result = run(payload("1. Should we ship today?\nShould we tag the release?"))

    assert result.returncode == 2


def test_question_inside_fenced_code_block_is_ignored():
    result = run(payload("```\nShould we ship today?\n```\nThe build is green."))

    assert result.returncode == 0


def test_question_on_blockquote_line_is_ignored():
    result = run(payload("> Should we ship today?\nThe build is green."))

    assert result.returncode == 0


def test_status_block_with_waiting_state_exits_zero():
    text = "Running: nothing\n\nNOW: check the build\n\nState: WAITING FOR YOU"
    result = run(payload(text))

    assert result.returncode == 0


def test_subpoint_counts_as_numbered():
    result = run(payload("13.1 Should we ship today?"))

    assert result.returncode == 0


def test_empty_assistant_text_exits_zero():
    result = run(payload(""))

    assert result.returncode == 0


def test_malformed_json_exits_zero():
    result = run(b"not json")

    assert result.returncode == 0
    assert result.stdout == b""
