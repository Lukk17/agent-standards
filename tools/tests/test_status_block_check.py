"""Tests for the status block hook at .agents/hooks/status-block-check/status_block_check.py.

Driven as a subprocess with --format plain and the envelope JSON on stdin. The
block is the one section 3 of .agents/instructions/reply-rules.md defines. Only
a user-reply event can deny, so every deny case drives one. A tool event and a
subagent payload only log the violation, and their own cases assert that.
"""

import json
import subprocess
import sys

import pytest

from tests.conftest import HOOKS_DIR, REPO_ROOT
from tests.process_tree import run_bounded
from tests.reminder_support import STATUS_BLOCK_LINES, canonical_status_block

HOOK = HOOKS_DIR / "status-block-check" / "status_block_check.py"

REPLY_EVENT = "stop"
TOOL_EVENT = "tool.execute.before"

BLOCK_LINES = (
    "Running: `sandbox build`",
    "",
    "~~DONE: fix the gate~~",
    "~~DONE: run the unit tests~~",
    "",
    "NOW: run the sandbox suite",
    "",
    "Next: raise the versions",
    "Then: write the changelog",
    "",
    "Waiting on: nothing",
)

OLD_BLOCK_LINES = (
    "---",
    "",
    "Skills: agent-engineer",
    "",
    "```Tasks: 1/2 completed```",
    "",
    "~~DONE: older finished task~~",
    "",
    "~~DONE: most recent finished task~~",
    "",
    "```NOW: what is being done right now```",
    "",
    "Running: sandbox build (agent: `agent-engineer`)",
    "",
    "Next: the next task",
    "",
    "Then: the task after that",
    "",
    "```State: WAITING FOR YOU```",
    "",
    "Waiting on: nothing",
)


def block(lines=BLOCK_LINES) -> str:
    return "\n".join(lines)


def reply(lines=BLOCK_LINES, body: str = "Done, the build is green.") -> str:
    return body + "\n\n" + block(lines)


def replaced(index: int, line: str) -> tuple[str, ...]:
    return BLOCK_LINES[:index] + (line,) + BLOCK_LINES[index + 1 :]


def dropped(index: int) -> tuple[str, ...]:
    return BLOCK_LINES[:index] + BLOCK_LINES[index + 1 :]


def run(stdin: bytes, *arguments: str) -> subprocess.CompletedProcess:
    return run_bounded(
        [sys.executable, "-S", "-E", str(HOOK), *(arguments or ("--format", "plain"))],
        input=stdin,
        capture_output=True,
        check=False,
    )


def payload(
    assistant_text: object,
    subagent: bool = False,
    cwd: object = REPO_ROOT,
    event: str = REPLY_EVENT,
    contract: object = 3,
) -> bytes:
    body = {
        "contract": contract,
        "event": event,
        "tool_name": "Edit",
        "tool_input": {},
        "agent_type": "general",
        "is_subagent": subagent,
        "assistant_text": assistant_text,
        "cwd": str(cwd),
    }

    return json.dumps(body).encode("utf-8")


def denied(text: str) -> bool:
    result = run(payload(text))
    assert result.returncode in (0, 2), result.stderr

    if result.returncode == 2:
        assert "Status block violation" in result.stderr.decode("utf-8")

    return result.returncode == 2


def test_reply_ending_with_the_block_exits_zero():
    result = run(payload(reply()))

    assert result.returncode == 0
    assert result.stderr == b""


def test_the_block_the_reply_rules_show_exits_zero():
    shown = canonical_status_block().split("\n\n", 1)[1].rsplit("\n\n", 1)[0]

    assert shown == "\n".join(STATUS_BLOCK_LINES)
    assert not denied("Done.\n\n" + shown)


def test_a_reply_that_is_only_the_block_exits_zero():
    assert not denied(block())


def test_trailing_blank_lines_after_the_block_exit_zero():
    assert not denied(reply() + "\n\n  \n")


def test_windows_line_endings_exit_zero():
    assert not denied(reply().replace("\n", "\r\n"))


def test_nothing_running_exits_zero():
    assert not denied(reply(replaced(0, "Running: nothing")))


def test_several_running_tasks_in_backticks_exit_zero():
    assert not denied(reply(replaced(0, "Running: `sandbox build`, `unit tests`, `lint`")))


def test_a_note_in_parentheses_after_the_running_tasks_exits_zero():
    assert not denied(reply(replaced(0, "Running: `sandbox build`, `lint` (2 of 5 steps done)")))


def test_a_body_ending_in_a_closed_code_block_exits_zero():
    assert not denied(reply(body="Run this:\n\n```bash\npython -m pytest tools/\n```"))


def test_a_body_line_that_opens_with_inline_code_in_three_backticks_exits_zero():
    assert not denied(reply(body="```pytest tools/``` is the command to run."))


def test_a_body_with_a_closed_tilde_fence_exits_zero():
    assert not denied(reply(body="~~~text\nRunning: nothing\n~~~"))


def test_a_rule_line_above_the_block_exits_zero():
    assert not denied(reply(body="Done.\n\n---"))


def test_corrections_plus_the_block_exit_zero():
    assert not denied(reply(body='Correction: "Fixed."'))


def test_reply_without_a_block_denies():
    assert denied("Done, the build is green.")


def test_the_old_block_with_skills_tasks_and_state_lines_denies():
    assert denied(reply(OLD_BLOCK_LINES))


@pytest.mark.parametrize(
    "extra",
    ["Skills: agent-engineer", "Tasks: 1/2 completed", "State: WAITING FOR YOU"],
    ids=["skills", "tasks", "state"],
)
def test_a_line_the_block_does_not_have_denies(extra):
    assert denied(reply(BLOCK_LINES[:-1] + (extra, "", BLOCK_LINES[-1])))


@pytest.mark.parametrize(
    "heading",
    ["### Status", "# Status", "Status\n---", "Status\n==="],
    ids=["level-three", "level-one", "underlined-dashes", "underlined-equals"],
)
def test_a_heading_above_the_block_denies(heading):
    assert denied(reply(body="Done.\n\n" + heading))


@pytest.mark.parametrize("marker", ["- ", "* ", "+ ", "1. ", "1) ", "> ", "  ", "### "], ids=repr)
def test_a_marker_before_every_line_denies(marker):
    assert denied(reply(tuple(marker + line if line else line for line in BLOCK_LINES)))


@pytest.mark.parametrize("index", [0, 2, 3, 5, 7, 8, 10], ids=lambda index: BLOCK_LINES[index].split(":")[0])
def test_a_marker_before_one_line_denies(index):
    assert denied(reply(replaced(index, "- " + BLOCK_LINES[index])))


@pytest.mark.parametrize("index", [0, 2, 3, 5, 7, 8, 10], ids=lambda index: BLOCK_LINES[index].split(":")[0])
def test_a_missing_line_denies(index):
    assert denied(reply(dropped(index)))


@pytest.mark.parametrize("index", [1, 4, 6, 9], ids=["after-running", "after-done", "after-now", "after-then"])
def test_a_missing_blank_line_denies(index):
    assert denied(reply(dropped(index)))


def test_no_blank_line_between_the_text_and_the_block_denies():
    assert denied("Done, the build is green.\n" + block())


@pytest.mark.parametrize("index", [3, 8], ids=["between-done-lines", "between-next-and-then"])
def test_an_added_blank_line_denies(index):
    assert denied(reply(BLOCK_LINES[:index] + ("",) + BLOCK_LINES[index:]))


def test_text_after_the_block_denies():
    assert denied(reply() + "\n\nLet me know if you want more.")


def test_a_block_inside_a_code_fence_denies():
    assert denied("Done.\n\n```\n" + block() + "\n```")


def test_a_block_inside_an_unclosed_code_fence_denies():
    assert denied("Done.\n\n```text\n\n" + block())


def test_a_block_in_the_middle_of_the_reply_denies():
    assert denied(block() + "\n\nDone, the build is green.")


def test_lines_in_another_order_deny():
    swapped = replaced(7, BLOCK_LINES[8])[:8] + (BLOCK_LINES[7],) + BLOCK_LINES[9:]

    assert denied(reply(swapped))


@pytest.mark.parametrize(
    "line",
    [
        "Running:",
        "Running: sandbox build",
        "Running: `sandbox build` and `lint`",
        "Running: `sandbox build` agent `agent-engineer`",
        "Running: (nothing)",
        "**Running:** nothing",
        "running: nothing",
    ],
)
def test_a_running_line_in_another_shape_denies(line):
    assert denied(reply(replaced(0, line)))


@pytest.mark.parametrize(
    ("index", "line"),
    [
        (2, "DONE: fix the gate"),
        (2, "~~DONE:~~"),
        (3, "~~Done: run the unit tests~~"),
        (5, "```NOW: run the sandbox suite```"),
        (5, "**NOW: run the sandbox suite**"),
        (5, "NOW:"),
        (7, "Next:"),
        (8, "Then:"),
        (10, "Waiting on:"),
        (10, "Waiting for: nothing"),
    ],
)
def test_a_line_in_another_shape_denies(index, line):
    assert denied(reply(replaced(index, line)))


def test_a_fenced_now_line_denies():
    fenced = BLOCK_LINES[:5] + ("```text", BLOCK_LINES[5], "```") + BLOCK_LINES[6:]

    assert denied(reply(fenced))


def test_the_reason_shows_the_block():
    result = run(payload("Done, the build is green."))

    assert result.returncode == 2
    assert result.stderr.decode("utf-8").endswith(canonical_status_block())


def test_tasks_in_the_project_ask_for_no_tasks_line(tmp_path):
    (tmp_path / "tasks.md").write_text("- [open] fix hook\n- [open] add test\n", encoding="utf-8")
    result = run(payload(reply(), cwd=str(tmp_path)))

    assert result.returncode == 0
    assert result.stderr == b""


def test_empty_prose_exits_zero():
    result = run(payload(""))

    assert result.returncode == 0


@pytest.mark.parametrize("text", [None, 42, ["Done."], "   \n\n"], ids=["none", "number", "list", "blank"])
def test_prose_that_is_no_text_exits_zero(text):
    result = run(payload(text))

    assert result.returncode == 0
    assert result.stderr == b""


def test_subagent_payload_without_block_exits_zero():
    result = run(payload("Done, the build is green.", subagent=True))

    assert result.returncode == 0
    assert "Subagent footer note (not blocking)" in result.stderr.decode("utf-8")


def test_subagent_payload_with_block_logs_nothing():
    result = run(payload(reply(), subagent=True))

    assert result.returncode == 0
    assert result.stderr == b""


def test_tool_event_without_block_logs_and_exits_zero():
    result = run(payload("Done, the build is green.", event=TOOL_EVENT))

    assert result.returncode == 0
    assert "Tool-event footer note (not blocking)" in result.stderr.decode("utf-8")


def test_tool_event_with_block_logs_nothing():
    result = run(payload(reply(), event=TOOL_EVENT))

    assert result.returncode == 0
    assert result.stderr == b""


@pytest.mark.parametrize("event", ["assistant.reply.complete", "experimental.text.complete", "reply.complete", "stop"])
def test_every_reply_event_denies_a_reply_without_a_block(event):
    result = run(payload("Done, the build is green.", event=event))

    assert result.returncode == 2


def test_an_event_that_is_no_reply_exits_zero():
    result = run(payload("Done, the build is green.", event="session.idle"))

    assert result.returncode == 0
    assert result.stderr == b""


@pytest.mark.parametrize(
    "stdin",
    [b"", b"not json", b"[]", b'"text"', b"\xff\xfe", b"{"],
    ids=["empty", "not-json", "list", "string", "not-utf8", "cut-off"],
)
def test_an_unreadable_payload_exits_zero(stdin):
    result = run(stdin)

    assert result.returncode == 0
    assert result.stderr == b""


@pytest.mark.parametrize("contract", [2, 4, "3", True, None], ids=repr)
def test_a_contract_the_hook_does_not_speak_exits_zero(contract):
    result = run(payload("Done, the build is green.", contract=contract))

    assert result.returncode == 0
    assert result.stderr == b""


@pytest.mark.parametrize(
    "arguments",
    [("--format", "claude"), ("--format=codex",), ("--format", "copilot"), ("--format",), ("--other",)],
    ids=["claude", "codex", "copilot", "no-value", "no-format"],
)
def test_any_format_but_plain_exits_zero(arguments):
    result = run(payload("Done, the build is green."), *arguments)

    assert result.returncode == 0
    assert result.stderr == b""


def test_the_format_written_with_an_equals_sign_is_read():
    result = run(payload("Done, the build is green."), "--format=plain")

    assert result.returncode == 2
