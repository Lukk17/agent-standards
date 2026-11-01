"""Tests for sandbox-agent/e2e-mock/records.py, the agent-record witness.

Each test lays out the on-disk record one agent keeps, in the shape measured on
the pinned binaries, and checks that a write naming the proof path is counted
for the session that made it and that a spawn call naming the same path is not
counted as a write.
"""

import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

from tests.conftest import REPO_ROOT

TARGET = "/work/project/e2e-subagent-proof.txt"

spec = importlib.util.spec_from_file_location("e2e_records", REPO_ROOT / "sandbox-agent" / "e2e-mock" / "records.py")
records = importlib.util.module_from_spec(spec)
spec.loader.exec_module(records)


def write_lines(path: Path, lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")


def tool_use(name: str, arguments: dict) -> dict:
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": arguments}]}}


def test_claude_counts_the_write_in_the_subagents_transcript_and_not_the_spawn(tmp_path):
    session = tmp_path / "claude-config" / "projects" / "-work-project"
    write_lines(session / "s1.jsonl", [tool_use("Agent", {"prompt": f"E2E-SUBAGENT-WRITE {TARGET} t"})])
    write_lines(session / "s1" / "subagents" / "agent-a1.jsonl", [tool_use("Write", {"file_path": TARGET})])
    assert records.count_writes("claude-code", tmp_path, TARGET) == (1, 0)


def test_codex_places_a_rollout_by_its_session_meta_source(tmp_path):
    sessions = tmp_path / "codex-home" / "sessions" / "2026" / "11" / "01"
    call = {"type": "response_item", "payload": {"type": "function_call", "name": "exec_command",
                                                 "arguments": json.dumps({"cmd": f"printf x > '{TARGET}'"})}}
    write_lines(sessions / "rollout-main.jsonl", [{"type": "session_meta", "payload": {"source": "exec"}}, call])
    write_lines(sessions / "rollout-sub.jsonl", [
        {"type": "session_meta", "payload": {"source": {"subagent": {"thread_spawn": {"agent_role": "python-pro"}}}}}, call])
    assert records.count_writes("codex", tmp_path, TARGET) == (1, 1)


def test_copilot_counts_a_call_carrying_a_parent_tool_call_id_once(tmp_path):
    start = {"type": "tool.execution_start", "data": {"toolCallId": "c2", "parentToolCallId": "c1",
                                                      "toolName": "create", "arguments": {"path": TARGET}}}
    write_lines(tmp_path / "copilot-home" / "session-state" / "s1" / "events.jsonl", [start, start])
    assert records.count_writes("copilot", tmp_path, TARGET) == (1, 0)


@pytest.mark.parametrize("agent", ["opencode", "kilo-code"])
def test_opencode_family_reads_a_child_session_from_its_export(tmp_path, agent):
    exports = tmp_path / "exports"
    exports.mkdir()
    part = {"type": "tool", "tool": "write", "state": {"input": {"filePath": TARGET}}}
    (exports / "spawn-ses_child.json").write_text(
        json.dumps({"info": {"id": "ses_child", "parentID": "ses_main"}, "messages": [{"parts": [part]}]}), encoding="utf-8")
    (exports / "spawn-ses_main.json").write_text(
        json.dumps({"info": {"id": "ses_main"}, "messages": [{"parts": [{**part, "tool": "task"}]}]}), encoding="utf-8")
    assert records.count_writes(agent, tmp_path, TARGET) == (1, 0)


def test_opencode2_reads_the_parent_of_each_session_from_its_database(tmp_path):
    database = tmp_path / "data" / "opencode" / "opencode.db"
    database.parent.mkdir(parents=True)
    with sqlite3.connect(database) as connection:
        connection.execute("create table session_v2 (id text, parent_id text)")
        connection.execute("create table session_message (session_id text, data text)")
        connection.executemany("insert into session_v2 values (?, ?)", [("main", None), ("child", "main")])
        content = {"content": [{"type": "tool", "name": "write", "state": {"input": {"path": TARGET}}}]}
        connection.execute("insert into session_message values (?, ?)", ("child", json.dumps(content)))
    connection.close()
    assert records.count_writes("opencode2", tmp_path, TARGET) == (1, 0)


def test_a_missing_opencode2_database_is_a_record_error(tmp_path):
    with pytest.raises(records.RecordError, match="no OpenCode 2.x database"):
        records.count_writes("opencode2", tmp_path, TARGET)


def test_an_unknown_agent_is_a_record_error(tmp_path):
    with pytest.raises(records.RecordError, match="unknown agent 'nope'"):
        records.count_writes("nope", tmp_path, TARGET)
