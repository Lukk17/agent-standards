#!/usr/bin/env python3
"""Footer shape gate for user-facing replies.

Footer shape is mandatory for user-facing replies in the exact order: dash
rule line, Skills line, inline Tasks single line, two crossed DONE lines,
inline NOW single line, Running lines with agent names in inline code, Next
line, Then line, inline State single line, Waiting on line last, blank lines
skipped never breaking the sequence. The hook never denies a tool or
subagent call over it: tool and subagent events log the violation and exit 0.
Exit 2 applies only on a user-reply event if the runner provides one.
"""

import json
import re
import sys

HOOK_ORDER = 35

HOOK_TEXT_EVENT = False

CONTRACTS = frozenset({3})

REPLY_EVENTS = frozenset({
    "assistant.reply.complete",
    "experimental.text.complete",
    "reply.complete",
    "stop",
})

TOOL_EVENTS = frozenset({
    "tool.execute.before",
})

SEPARATOR_RE = re.compile(r"^\s*-{2,}\s*$")
SKILLS_RE = re.compile(r"^\s*Skills:")
TASK_RE = re.compile(r"^\s*`{3}.*Tasks:\s*\d+\s*/\s*\d+.*`{3}\s*$")
DONE_RE = re.compile(r"^\s*~~DONE:.*~~\s*$")
NOW_RE = re.compile(r"^\s*`{3}.*NOW:.*`{3}\s*$")
RUNNING_RE = re.compile(r"^\s*Running:\s*\S.*\(agent:\s*`[^`]+`\)\s*$")
NEXT_RE = re.compile(r"^\s*Next:")
THEN_RE = re.compile(r"^\s*Then:")
STATE_RE = re.compile(r"^\s*`{3}.*State:\s*(WAITING FOR YOU|WORKING|DONE).*`{3}\s*$", re.IGNORECASE)
WAITING_RE = re.compile(r"^\s*Waiting on:")

REASON = (
    "Status block violation in your last reply. End every reply with the "
    "Status tail in order: dash rule line, Skills line, fenced Tasks line "
    "directly below Skills, two crossed DONE lines, fenced one-line NOW "
    "above Running lines, Running lines, Next line, Then line, fenced "
    "one-line State line, Waiting on line last. Fix what was flagged and "
    "anything else other hooks asked you to fix, then end with the status block."
)

TASK_LINE_RE = re.compile(r"^\s*`{0,3}.*Tasks:\s*\d+\s*/\s*\d+")
TASK_ITEM_RE = re.compile(r"^\s*-\s*\[(open|in progress|done|blocked)\]", re.IGNORECASE)
TASK_REASON = ("Task list violation in your last reply. The project task file holds items, so add a Tasks: N/M completed line with the pending items and their priorities.")


def has_status_tail(text: str) -> bool:
    lines = text.splitlines()
    start = None

    for index, line in enumerate(lines):
        if SEPARATOR_RE.match(line):
            start = index

    if start is None:
        return False

    tail = lines[start:]
    if start == 0 or lines[start - 1].strip():
        return False
    stage = 0

    for line in tail:
        if not line.strip():
            continue

        if stage == 0:
            if SEPARATOR_RE.match(line):
                stage = 1
            else:
                return False
        elif stage == 1:
            if SKILLS_RE.match(line):
                stage = 2
            else:
                return False
        elif stage == 2:
            if TASK_RE.match(line):
                stage = 3
            elif DONE_RE.match(line):
                stage = 4
            else:
                return False
        elif stage == 3:
            if DONE_RE.match(line):
                stage = 4
            else:
                return False
        elif stage == 4:
            if DONE_RE.match(line):
                stage = 5
            else:
                return False
        elif stage == 5:
            if NOW_RE.match(line):
                stage = 6
            else:
                return False
        elif stage == 6:
            if RUNNING_RE.match(line):
                stage = 7
            elif NEXT_RE.match(line):
                stage = 8
            else:
                return False
        elif stage == 7:
            if RUNNING_RE.match(line):
                pass
            elif NEXT_RE.match(line):
                stage = 8
            else:
                return False
        elif stage == 8:
            if THEN_RE.match(line):
                stage = 9
            else:
                return False
        elif stage == 9:
            if STATE_RE.match(line):
                stage = 10
            else:
                return False
        elif stage == 10:
            if WAITING_RE.match(line):
                return True

            return False

    return False


def _stdin_text() -> str:
    return sys.stdin.buffer.read().decode("utf-8", errors="replace")


def _speaks_contract(payload: dict[str, object]) -> bool:
    version = payload.get("contract", max(CONTRACTS))

    return type(version) is int and version in CONTRACTS


def tasks_present(root: str) -> bool:
    try:
        from pathlib import Path

        candidate = Path(root) / "tasks.md"

        if not candidate.is_file():
            return False

        text = candidate.read_text(encoding="utf-8", errors="replace")

        return any(TASK_ITEM_RE.match(line) for line in text.splitlines())
    except Exception:
        return False


def _runner_mode() -> int:
    try:
        payload = json.loads(_stdin_text() or "{}")

        if not isinstance(payload, dict) or not _speaks_contract(payload):
            return 0

        if payload.get("is_subagent") is True:
            text = payload.get("assistant_text")

            if isinstance(text, str) and text.strip() and not has_status_tail(text):
                sys.stderr.buffer.write(("Subagent footer note (not blocking): " + REASON).encode("utf-8"))
                sys.stderr.buffer.flush()

            return 0

        event = payload.get("event")

        if event in TOOL_EVENTS:
            text = payload.get("assistant_text")

            if isinstance(text, str) and text.strip() and not has_status_tail(text):
                sys.stderr.buffer.write(("Tool-event footer note (not blocking): " + REASON).encode("utf-8"))
                sys.stderr.buffer.flush()

            return 0

        if event not in REPLY_EVENTS:
            return 0

        text = payload.get("assistant_text")

        if not isinstance(text, str) or not text.strip():
            return 0

        if has_status_tail(text):
            root = payload.get("cwd") if isinstance(payload.get("cwd"), str) else ""

            if tasks_present(root) and not any(TASK_LINE_RE.match(line) for line in text.splitlines()):
                sys.stderr.buffer.write(TASK_REASON.encode("utf-8"))
                sys.stderr.buffer.flush()

                return 2

            return 0

        sys.stderr.buffer.write(REASON.encode("utf-8"))
        sys.stderr.buffer.flush()

        return 2
    except Exception:
        return 0


def _format(argv: list[str]) -> str:
    for index, token in enumerate(argv):
        if token == "--format" and index + 1 < len(argv):
            return argv[index + 1]

        if token.startswith("--format="):
            return token.split("=", 1)[1]

    return ""


def main(argv: list[str]) -> int:
    if _format(argv) != "plain":
        return 0

    return _runner_mode()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
