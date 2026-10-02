#!/usr/bin/env python3
"""Blocks a reply that ends without the Status tail.

Runner (--format plain) only. Subagent reports are exempt: the caller owns
status. A valid tail holds in order: a dash run line, a Skills line, an
Owners line, a Status header line, then a State line holding WAITING FOR
YOU, WORKING, or DONE. Blocking prints the reason on stderr and exits 2.
"""

import json
import re
import sys

HOOK_ORDER = 35

HOOK_TEXT_EVENT = False

CONTRACTS = frozenset({3})

SEPARATOR_RE = re.compile(r"^\s*-{2,}\s*$")
SKILLS_RE = re.compile(r"^\s*Skills:")
OWNERS_RE = re.compile(r"^\s*Owners:")
STATUS_RE = re.compile(r"^\s*Status\s*$")
STATE_RE = re.compile(r"^\s*State:\s*(WAITING FOR YOU|WORKING|DONE)\s*$", re.IGNORECASE)

REASON = (
    "Status block violation in your last reply. End every reply with the "
    "Status tail in order: a dash run line, a Skills line, an Owners line, "
    "the Status header, plus a State line holding WAITING FOR YOU, WORKING, "
    "or DONE. Fix what was flagged and anything else other hooks asked you "
    "to fix, then end with the status block."
)

TASK_LINE_RE = re.compile(r"^\s*Tasks:\s*\d+\s*/\s*\d+")
TASK_ITEM_RE = re.compile(r"^\s*-\s*\[(open|in progress|done|blocked)\]", re.IGNORECASE)
TASK_REASON = ("Task list violation in your last reply. The project task file holds items, so add a Tasks: N/M completed line with the pending items and their priorities.")


def has_status_tail(text: str) -> bool:
    stage = 0

    for line in text.splitlines():
        if stage == 0:
            if SEPARATOR_RE.match(line):
                stage = 1
        elif stage == 1:
            if SKILLS_RE.match(line):
                stage = 2
        elif stage == 2:
            if OWNERS_RE.match(line):
                stage = 3
        elif stage == 3:
            if STATUS_RE.match(line):
                stage = 4
        elif stage == 4:
            if STATE_RE.match(line):
                return True

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

        if payload.get("event") != "tool.execute.before":
            return 0

        if payload.get("is_subagent") is True:
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
