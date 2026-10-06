#!/usr/bin/env python3
"""Task watchdog, reply Tasks line must match live tool todo state.

Main thread only, subagents fully exempt. Compares the reply Tasks line
against the live tool todo state. On mismatch prints one short reminder
ordering a sync and exits 2, aborting that single call. Match proceeds
silently. Every failure path allows.
"""

import json
import re
import sys
from typing import Any, Dict, List

HOOK_ORDER = 20

CONTRACTS = frozenset({3})

TASKS_RE = re.compile(r"Tasks:\s*(\d+)\s*/\s*(\d+)")

REMINDER = (
    "Task sync mismatch: reply Tasks line does not match live todo state. "
    "Sync widget, tasks file and reply Tasks line, then retry the call."
)


def _flag(argv: List[str], name: str) -> str:
    for index, token in enumerate(argv):
        if token == name and index + 1 < len(argv):
            return argv[index + 1]
        if token.startswith(name + "="):
            return token.split("=", 1)[1]
    return ""


def _payload() -> Dict[str, Any]:
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace") or "{}")
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _reply_counts(text: str):
    if not isinstance(text, str) or not text:
        return None
    match = TASKS_RE.search(text)
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)))


def _live_counts(payload: Dict[str, Any]):
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    todos = tool_input.get("todos")
    if not isinstance(todos, list) or not todos:
        return None
    total = 0
    done = 0
    for item in todos:
        if not isinstance(item, dict):
            continue
        total += 1
        status = str(item.get("status", "")).strip().lower().replace("_", " ").replace("-", " ")
        if status in ("completed", "complete", "done"):
            done += 1
    return (done, total)


def main(argv: List[str]) -> int:
    try:
        fmt = _flag(argv, "--format").lower()
        if fmt and fmt != "plain":
            return 0
        payload = _payload()
        if payload.get("contract") not in CONTRACTS:
            return 0
        if payload.get("is_subagent") is True:
            return 0
        if "is_subagent" not in payload:
            return 0
        reply = _reply_counts(str(payload.get("assistant_text", "")))
        live = _live_counts(payload)
        if reply is None or live is None:
            return 0
        if reply == live:
            return 0
        sys.stderr.write(REMINDER + "\n")
        return 2
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
