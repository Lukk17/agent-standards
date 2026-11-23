#!/usr/bin/env python3
"""Status block gate for user-facing replies.

A reply to the user ends with the block section 3 of
.agents/instructions/reply-rules.md defines: a Running line, two crossed DONE
lines, a NOW line, a Next line, a Then line and a Waiting on line, as plain
lines with every blank line of the block kept and nothing after the last one.
The Running line names each running task in backticks, separated by commas, or
says nothing, and may end with a note in parentheses. A blank line stands
between the reply text and the block.

A heading right above the block, a bullet, a number or any other marker before
a line, a code fence around the block, a missing or an added blank line, a line
the block does not have and text after the block all fail.

The hook never denies a tool or subagent call over it: tool and subagent events
log the violation and exit 0. Exit 2 applies only on a user-reply event if the
runner provides one. Every failure path allows.
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

BLANK_RE = re.compile(r"[ \t]*")
DONE_RE = re.compile(r"~~DONE: \S.*~~[ \t]*")

BLOCK = (
    re.compile(r"Running: (?:nothing|`[^`]+`(?:, `[^`]+`)*)(?: \(.*\))?[ \t]*"),
    BLANK_RE,
    DONE_RE,
    DONE_RE,
    BLANK_RE,
    re.compile(r"NOW: \S.*"),
    BLANK_RE,
    re.compile(r"Next: \S.*"),
    re.compile(r"Then: \S.*"),
    BLANK_RE,
    re.compile(r"Waiting on: \S.*"),
)

HEADING_RE = re.compile(r" {0,3}#{1,6}(?:[ \t]|$)")
UNDERLINE_RE = re.compile(r" {0,3}(?:=+|-+)[ \t]*")
FENCE_RE = re.compile(r" {0,3}(`{3,}|~{3,})(.*)")

REASON = (
    "Status block violation in your last reply. Fix what was flagged and anything else other hooks "
    "asked you to fix. "
    "End every reply to the user with this block, exactly as shown: no heading, no bullets, no numbered "
    "list, plain lines only, keeping every blank line:\n"
    "\n"
    "Running: `running task name` (or: nothing)\n"
    "\n"
    "~~DONE: older finished task~~\n"
    "~~DONE: most recent finished task~~\n"
    "\n"
    "NOW: what is being done right now\n"
    "\n"
    "Next: the next task\n"
    "Then: the task after that\n"
    "\n"
    "Waiting on: what you wait for (or: nothing)\n"
    "\n"
    "When several tasks run, list each name in backticks on the Running line, separated by commas."
)


def _inside_fence(lines: list[str]) -> bool:
    fence = ""

    for line in lines:
        match = FENCE_RE.match(line)

        if not match:
            continue

        marker = match.group(1)

        if not fence:
            fence = "" if marker[0] == "`" and "`" in match.group(2) else marker
        elif marker[0] == fence[0] and len(marker) >= len(fence) and not match.group(2).strip():
            fence = ""

    return bool(fence)


def _is_heading(lines: list[str], index: int) -> bool:
    if HEADING_RE.match(lines[index]):
        return True

    return index > 0 and bool(lines[index - 1].strip()) and UNDERLINE_RE.fullmatch(lines[index]) is not None


def _stands_free(above: list[str]) -> bool:
    if not above:
        return True

    if above[-1].strip() or _inside_fence(above):
        return False

    written = [index for index, line in enumerate(above) if line.strip()]

    return not written or not _is_heading(above, written[-1])


def has_status_block(text: str) -> bool:
    lines = text.splitlines()

    while lines and not lines[-1].strip():
        lines.pop()

    if len(lines) < len(BLOCK):
        return False

    above, block = lines[: -len(BLOCK)], lines[-len(BLOCK) :]

    if not all(pattern.fullmatch(line) for pattern, line in zip(BLOCK, block)):
        return False

    return _stands_free(above)


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

        if payload.get("is_subagent") is True:
            text = payload.get("assistant_text")

            if isinstance(text, str) and text.strip() and not has_status_block(text):
                sys.stderr.buffer.write(("Subagent footer note (not blocking): " + REASON).encode("utf-8"))
                sys.stderr.buffer.flush()

            return 0

        event = payload.get("event")

        if event in TOOL_EVENTS:
            text = payload.get("assistant_text")

            if isinstance(text, str) and text.strip() and not has_status_block(text):
                sys.stderr.buffer.write(("Tool-event footer note (not blocking): " + REASON).encode("utf-8"))
                sys.stderr.buffer.flush()

            return 0

        if event not in REPLY_EVENTS:
            return 0

        text = payload.get("assistant_text")

        if not isinstance(text, str) or not text.strip():
            return 0

        if has_status_block(text):
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
