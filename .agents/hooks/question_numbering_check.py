#!/usr/bin/env python3
"""Blocks a reply that asks the user an unnumbered question.

Runner (--format plain) only. The contract at
https://github.com/Lukk17/agent-standards/blob/master/docs/hooks-contract.md
defines one envelope as JSON on stdin. On `tool.execute.before` the prose comes
from its `assistant_text` field, and blocking prints the reason on stderr and
exits 2.
"""

import json
import re
import sys

HOOK_ORDER = 30

HOOK_TEXT_EVENT = False

CONTRACTS = frozenset({3})

FENCE_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")
INLINE_CODE_RE = re.compile(r"``[^\n]+?``|`[^`\n]*`")
NUMBERED_RE = re.compile(r"^\d+(\.\d+)*([.)]\s|\s)", re.IGNORECASE)
QUESTION_WORD_RE = re.compile(r"^Question \d+", re.IGNORECASE)
STATUS_LINE_RE = re.compile(
    r"^\s*(Running:|Done:|NOW:|Next:|Then:|Waiting on:|State:)", re.IGNORECASE
)
SEPARATOR_RE = re.compile(r"^\s*(-{2,}|_{2,}|\*{2,})\s*$")
STATE_VALUES = frozenset({"WAITING FOR YOU", "WORKING", "DONE"})

REASON = (
    "Question numbering violation in your last reply. Every question to the user "
    "must be numbered, one continuous sequence per conversation, with subpoints "
    "like 13.1. Write only the corrected questions, one per line, each starting "
    'with "Correction:" followed by the fixed text in quotes, and write nothing else.'
)


def _step_fence(line: str, fence: str) -> tuple[bool, str]:
    match = FENCE_RE.match(line)

    if not match:
        return bool(fence), fence

    marker = match.group(2)

    if not fence:
        return True, marker

    if marker[0] == fence[0] and len(marker) >= len(fence) and not match.group(3).strip():
        return True, ""

    return True, fence


def _strip_inline(text: str) -> str:
    return INLINE_CODE_RE.sub(" ", text)


def _is_question(line: str) -> bool:
    stripped = line.strip()

    if not stripped or not _strip_inline(line).strip():
        return False

    if "?" not in stripped:
        return False

    after = stripped.rsplit("?", 1)[1].strip()

    if not after:
        return True

    return all(char in "\"'`)}])>»”’" for char in after)


def _is_numbered(line: str) -> bool:
    stripped = line.strip()

    return bool(NUMBERED_RE.match(stripped) or QUESTION_WORD_RE.match(stripped))


def _is_status_line(line: str) -> bool:
    stripped = line.strip()

    if SEPARATOR_RE.match(line):
        return True

    if not STATUS_LINE_RE.match(line):
        return False

    if stripped.upper().startswith("STATE:"):
        value = stripped[6:].strip().upper().strip("`\"'*_ ")

        if value in STATE_VALUES:
            return True

    return True


def find_unnumbered(text: str) -> list[str]:
    prose: list[str] = []
    fence = ""

    for line in text.splitlines():
        code, fence = _step_fence(line, fence)

        if code:
            continue

        if line.lstrip().startswith(">"):
            continue

        if _is_status_line(line):
            continue

        cleaned = _strip_inline(line)

        if _is_question(cleaned) and not _is_numbered(cleaned):
            prose.append(line.strip())

    return prose


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

        text = payload.get("assistant_text")

        if not isinstance(text, str) or not text.strip():
            return 0

        if not find_unnumbered(text):
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
