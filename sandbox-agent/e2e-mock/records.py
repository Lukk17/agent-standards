"""Counts the write calls an agent recorded for one path, split by session.

Reads what the agent binary itself keeps on disk after a run, never what the
mock model was sent, so the subagent-write check has a second witness beside
the request log:

    claude-code  <state>/claude-config/projects/**/*.jsonl, a subagent's own
                 transcript sitting under a subagents/ directory
    codex        <state>/codex-home/sessions/**/*.jsonl, a rollout whose
                 session_meta source names a subagent
    copilot      <state>/copilot-home/session-state/*/events.jsonl, a
                 tool.execution_start carrying a parentToolCallId
    opencode     <state>/exports/*.json, `opencode export` of each session,
    kilo-code    a session with a parentID being a subagent
    opencode2    <state>/data/opencode/opencode.db, a session_v2 row with a
                 parent_id

Usage: python3 -I -S records.py <agent> <state dir> <path>
Prints "<subagent writes> <main-thread writes>" and exits 0, or prints why and
exits 2 when the agent is unknown or its record cannot be read.
"""

import json
import sqlite3
import sys
from collections.abc import Iterator
from pathlib import Path

# Every tool name a supported agent writes a file with, its shells included,
# so a spawn call whose prompt names the path is never counted as a write.
WRITE_TOOLS = frozenset(
    {"Write", "Edit", "MultiEdit", "Bash", "create", "edit", "write", "apply_patch", "exec_command", "shell", "bash"}
)

Call = tuple[bool, str, str]


class RecordError(Exception):
    """The agent's record is missing or unreadable."""


def json_lines(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if isinstance(value, dict):
                yield value


def claude_calls(state: Path) -> Iterator[Call]:
    for path in sorted((state / "claude-config" / "projects").glob("**/*.jsonl")):
        subagent = path.parent.name == "subagents"
        for line in json_lines(path):
            content = (line.get("message") or {}).get("content")
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    yield subagent, str(block.get("name")), json.dumps(block.get("input"))


def codex_calls(state: Path) -> Iterator[Call]:
    for path in sorted((state / "codex-home" / "sessions").glob("**/*.jsonl")):
        lines = list(json_lines(path))
        source = next((line.get("payload", {}).get("source") for line in lines if line.get("type") == "session_meta"), None)
        subagent = "subagent" in json.dumps(source).lower()
        for line in lines:
            payload = line.get("payload") or {}
            if line.get("type") == "response_item" and payload.get("type") in ("function_call", "custom_tool_call"):
                yield subagent, str(payload.get("name")), json.dumps(payload.get("arguments") or payload.get("input"))


def copilot_calls(state: Path) -> Iterator[Call]:
    seen: set[str] = set()
    for path in sorted((state / "copilot-home" / "session-state").glob("*/events.jsonl")):
        for line in json_lines(path):
            data = line.get("data") or {}
            if line.get("type") != "tool.execution_start" or data.get("toolCallId") in seen:
                continue
            seen.add(data.get("toolCallId"))
            yield data.get("parentToolCallId") is not None, str(data.get("toolName")), json.dumps(data.get("arguments"))


def opencode_export_calls(state: Path) -> Iterator[Call]:
    for path in sorted((state / "exports").glob("*.json")):
        try:
            export = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        subagent = bool((export.get("info") or {}).get("parentID"))
        for message in export.get("messages") or []:
            for part in message.get("parts") or []:
                if part.get("type") == "tool":
                    yield subagent, str(part.get("tool")), json.dumps((part.get("state") or {}).get("input"))


def opencode2_calls(state: Path) -> Iterator[Call]:
    database = state / "data" / "opencode" / "opencode.db"
    if not database.is_file():
        raise RecordError(f"no OpenCode 2.x database at {database}")
    try:
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
            parents = dict(connection.execute("select id, parent_id from session_v2"))
            rows = list(connection.execute("select session_id, data from session_message"))
    except sqlite3.Error as error:
        raise RecordError(f"cannot read {database}: {error}") from error
    for session, data in rows:
        try:
            message = json.loads(data)
        except ValueError:
            continue
        content = message.get("content") if isinstance(message, dict) else None
        for part in content if isinstance(content, list) else []:
            if isinstance(part, dict) and part.get("type") == "tool":
                yield parents.get(session) is not None, str(part.get("name")), json.dumps((part.get("state") or {}).get("input"))


READERS = {
    "claude-code": claude_calls,
    "codex": codex_calls,
    "copilot": copilot_calls,
    "opencode": opencode_export_calls,
    "kilo-code": opencode_export_calls,
    "opencode2": opencode2_calls,
}


def count_writes(agent: str, state: Path, target: str) -> tuple[int, int]:
    """Returns (subagent writes, main-thread writes) naming target.

    Raises:
        RecordError: the agent is unknown or its record cannot be read.
    """
    reader = READERS.get(agent)
    if reader is None:
        raise RecordError(f"unknown agent {agent!r}, expected one of {', '.join(sorted(READERS))}")
    counts = [0, 0]
    for subagent, tool, arguments in reader(state):
        if tool in WRITE_TOOLS and target in arguments:
            counts[0 if subagent else 1] += 1
    return counts[0], counts[1]


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("usage: records.py <agent> <state dir> <path>")
        return 2
    try:
        subagent, main_thread = count_writes(argv[1], Path(argv[2]), argv[3])
    except (RecordError, OSError) as error:
        print(error)
        return 2
    print(subagent, main_thread)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
