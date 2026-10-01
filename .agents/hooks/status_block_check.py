#!/usr/bin/env python3
"""Blocks a reply that ends without the Status tail.

Runner (--format plain) only. Subagent reports are exempt: the caller owns
status. A valid tail is a Status header line followed later by a State line
holding WAITING FOR YOU, WORKING, or DONE. Blocking prints the reason on
stderr and exits 2.
"""

import json
import re
import sys

HOOK_ORDER = 35

HOOK_TEXT_EVENT = False

CONTRACTS = frozenset({3})

STATUS_RE = re.compile(r"^\s*Status\s*$")
STATE_RE = re.compile(r"^\s*State:\s*(WAITING FOR YOU|WORKING|DONE)\s*$", re.IGNORECASE)

REASON = (
    "Status block violation in your last reply. End every reply with the "
    "Status tail: the Status header plus a State line holding WAITING FOR YOU, "
    "WORKING, or DONE. Fix what was flagged and anything else other hooks "
    "asked you to fix, then end with the status block."
)


def has_status_tail(text: str) -> bool:
    status_seen = False

    for line in text.splitlines():
        if not status_seen:
            if STATUS_RE.match(line):
                status_seen = True

            continue

        if STATE_RE.match(line):
            return True

    return False


def _stdin_text() -> str:
    return sys.stdin.buffer.read().decode("utf-8", errors="replace")


def _speaks_contract(payload: dict[str, object]) -> bool:
    version = payload.get("contract", max(CONTRACTS))

    return type(version) is int and version in CONTRACTS


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
