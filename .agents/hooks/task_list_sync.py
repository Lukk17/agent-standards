#!/usr/bin/env python3
"""Keeps the task list on disk and puts it back in context.

The model's own task list lives only in the session, so a compaction loses it
and a finished turn can leave items open with nothing to show for them. This
hook mirrors it into TASK_LIST_NAME at the project root, one line per task:

    - [open] `task-001`: Implement user authentication

The identifier is written inside backticks so that an id carrying a colon,
which several trackers use, still reads back as one field. A line written
before that, or by hand, with a bare id is still parsed, but an id holding a
backtick is refused rather than written, because it would break the delimiter
and leave an item that can never be closed.

Statuses are open, in progress, done, and blocked. The hook itself writes only
open (on TaskCreated) and done (on TaskCompleted), because no task-updated
event exists on any surface today. The model writes the other two by editing
the file, which the preflight gate exempts from Rule A for this one path.

Three modes, chosen with --event, and an output shape chosen with --format:

Record (--event taskcreated, --event taskcompleted). Reads `task_id` and
`task_subject` out of the payload and upserts the matching line. Prints
nothing.

Inject (--event sessionstart, --event precompact). Prints the file as
`additionalContext` so the list survives a compaction. Claude Code and Codex
take it nested under `hookSpecificOutput`, Copilot takes it flat. Only
SessionStart actually delivers it on all three: none of the three documents
PreCompact as a delivery point, and the working path after a compaction is
SessionStart firing again with source "compact".

Guard (--event stop). Blocks once when the file still holds an open or an
in-progress item, naming them. `stop_hook_active` short-circuits the check so
the block cannot loop. Every format that has a stop event takes the same flat
`decision` and `reason` pair, Claude Code and Codex on `Stop` and Copilot on
`agentStop`, so the guard has one shape and no per-format branch.

--format plain is the runner contract, which this hook never applies to, so it
returns 0 before reading anything.

Every failure path allows: a broken hook must never break a session.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Runner order. After the gate and the formatting check, both of which decide
# whether the call or the reply may stand at all.
HOOK_ORDER = 30

TASK_LIST_NAME = "tasks.md"

OPEN = "open"
IN_PROGRESS = "in progress"
DONE = "done"
BLOCKED = "blocked"

UNFINISHED = (OPEN, IN_PROGRESS)

FORMATS = ("claude", "codex", "copilot")

EVENT_NAMES = {
    "taskcreated": "TaskCreated",
    "taskcompleted": "TaskCompleted",
    "sessionstart": "SessionStart",
    "precompact": "PreCompact",
    "stop": "Stop",
}

RECORDED_STATUS = {"taskcreated": OPEN, "taskcompleted": DONE}

ID_DELIMITER = "`"

# The id is read out of backticks first, which is how this hook writes it, and
# out of a bare run with no colon in it second, which is how an older or a
# hand-written line spells it.
TASK_LINE_RE = re.compile(
    r"^- \[(?P<status>"
    + "|".join((OPEN, IN_PROGRESS, DONE, BLOCKED))
    + r")\] (?:`(?P<quoted>[^`]+)`|(?P<bare>[^:`]+)): ?(?P<subject>.*)$"
)

INJECTION_HEAD = "The task list mirrored in " + TASK_LIST_NAME + " at the project root holds:\n"

GUARD_HEAD = "The task list in " + TASK_LIST_NAME + " still holds unfinished items: "

GUARD_TAIL = (
    ". Update each one to done or blocked, or say which of them is still running, "
    "before finishing the turn."
)


def _stdin_text() -> str:
    """Decode stdin as UTF-8 explicitly, never through the system code page."""
    return sys.stdin.buffer.read().decode("utf-8", errors="replace")


def _flag(argv: List[str], name: str) -> str:
    """Read one --flag value by hand.

    argparse exits 2 on a usage error and 2 is the deny code in the runner
    contract, so no hook in this directory may use it.
    """
    for index, token in enumerate(argv):
        if token == name and index + 1 < len(argv):
            return argv[index + 1]

        if token.startswith(name + "="):
            return token.split("=", 1)[1]

    return ""


def _task_list() -> Path:
    """The list's path at the project root.

    Every wiring moves to the project root before invoking a hook, so the
    working directory is the contract. It is trusted only once it holds the
    hooks directory that proves it is a project root, because that guarantee
    has broken silently before (see AGENTS.md "Required opening move"). The
    hook's own location two parents up is the fallback.
    """
    cwd = Path.cwd().resolve()
    anchored = Path(__file__).resolve().parents[2]
    root = cwd if (cwd / ".agents" / "hooks").is_dir() else anchored

    return root / TASK_LIST_NAME


def _read_lines(path: Path) -> List[str]:
    if not path.is_file():
        return []

    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def _parse(line: str) -> Optional[Tuple[str, str, str]]:
    match = TASK_LINE_RE.match(line)

    if not match:
        return None

    task_id = match.group("quoted") or match.group("bare")

    return match.group("status"), task_id.strip(), match.group("subject").strip()


def _entry(status: str, task_id: str, subject: str) -> str:
    return (
        "- [" + status + "] " + ID_DELIMITER + task_id + ID_DELIMITER + ": " + subject
    )


def _field(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)

    if not isinstance(value, str):
        return ""

    return " ".join(value.split())


def _record(event: str, payload: Dict[str, Any]) -> int:
    """Upsert one task line, keeping the stored subject when none is sent."""
    task_id = _field(payload, "task_id")

    if not task_id or ID_DELIMITER in task_id:
        return 0

    subject = _field(payload, "task_subject")
    status = RECORDED_STATUS[event]
    path = _task_list()
    lines = _read_lines(path)

    for index, line in enumerate(lines):
        parsed = _parse(line)

        if parsed is None or parsed[1] != task_id:
            continue

        lines[index] = _entry(status, task_id, subject or parsed[2])
        break
    else:
        lines.append(_entry(status, task_id, subject))

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return 0


def _emit_context(event: str, fmt: str, text: str) -> None:
    if fmt == "copilot":
        sys.stdout.write(json.dumps({"additionalContext": text}))
        return

    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": EVENT_NAMES[event],
                    "additionalContext": text,
                }
            }
        )
    )


def _inject(event: str, fmt: str) -> int:
    """Put the stored list back into context, or stay silent when it is empty."""
    body = "\n".join(line for line in _read_lines(_task_list()) if line.strip())

    if not body:
        return 0

    _emit_context(event, fmt, INJECTION_HEAD + body)

    return 0


def _unfinished(lines: List[str]) -> List[str]:
    items = []

    for line in lines:
        parsed = _parse(line)

        if parsed is not None and parsed[0] in UNFINISHED:
            items.append(parsed[1] + " (" + parsed[0] + ")")

    return items


def _guard(payload: Dict[str, Any]) -> int:
    """Block a finished turn that left the list holding unfinished items.

    The output takes no format argument because every stop event that exists
    takes the same flat pair: Claude Code and Codex on `Stop`, and Copilot on
    `agentStop`, which documents `decision` and `reason` exactly as the other
    two spell them.
    """
    if payload.get("stop_hook_active") is True:
        return 0

    items = _unfinished(_read_lines(_task_list()))

    if not items:
        return 0

    reason = GUARD_HEAD + ", ".join(items) + GUARD_TAIL
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}))

    return 0


def main(argv: List[str]) -> int:
    try:
        event = _flag(argv, "--event").lower()
        fmt = _flag(argv, "--format").lower()

        if event not in EVENT_NAMES or fmt not in FORMATS:
            return 0

        payload = json.loads(_stdin_text() or "{}")

        if not isinstance(payload, dict):
            return 0

        if event in RECORDED_STATUS:
            return _record(event, payload)

        if event == "stop":
            return _guard(payload)

        return _inject(event, fmt)
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
