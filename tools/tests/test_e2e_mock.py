"""Routing tests for the scripted model in sandbox-agent/e2e-mock/server.mjs.

The server is started through node on a free port, the same way the sandbox
starts it, and every test posts one request in the wire format an agent uses,
with the headers that agent sends, and reads back both the answer and the log
line the suite asserts on. The shell driver beside it is checked with bash -n
and, where it is installed, ShellCheck.
"""

import json
import re
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.conftest import REPO_ROOT, SUBPROCESS_TIMEOUT_SECONDS

E2E_DIR = REPO_ROOT / "sandbox-agent" / "e2e-mock"
SERVER = E2E_DIR / "server.mjs"
DRIVER = E2E_DIR / "subagent-write.sh"
NODE = shutil.which("node")
PATH = "/work/project/e2e-subagent-proof.txt"
TOKEN = "written-by-the-python-pro-subagent"

CLAUDE_MAIN = {"user-agent": "claude-cli/2.1.314 (external, sdk-cli)"}
CLAUDE_SUBAGENT = {**CLAUDE_MAIN, "x-claude-code-agent-id": "a1"}
CODEX_MAIN = {"x-codex-turn-metadata": json.dumps({"agent_name": "/root", "thread_source": "user"})}
CODEX_SUBAGENT = {"x-codex-turn-metadata": json.dumps({"agent_name": "/root", "thread_source": "subagent"})}
COPILOT_SUBAGENT = {"x-initiator": "agent", "x-interaction-type": "conversation-subagent"}
OPENCODE_MAIN = {"x-session-id": "ses_main"}
OPENCODE_SUBAGENT = {"x-session-id": "ses_child", "x-parent-session-id": "ses_main"}

needs_node = pytest.mark.skipif(NODE is None, reason="node is not installed")


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class Mock:
    """A running server.mjs and the request log it appends to."""

    def __init__(self, port: int, log: Path) -> None:
        self.port = port
        self.log = log

    def post(self, path: str, body: dict, headers: dict[str, str] | None = None) -> tuple[str, dict]:
        """Posts one request and returns the raw answer and its log line."""
        before = len(self.lines())
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=json.dumps(body).encode("utf-8"),
            headers={"content-type": "application/json", **(headers or {})},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=SUBPROCESS_TIMEOUT_SECONDS) as response:
            text = response.read().decode("utf-8")
        return text, self.lines()[before]

    def lines(self) -> list[dict]:
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines() if line]


@pytest.fixture(scope="module")
def mock(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Mock]:
    if NODE is None:
        pytest.skip("node is not installed")
    log = tmp_path_factory.mktemp("e2e-mock") / "requests.jsonl"
    log.write_text("", encoding="utf-8")
    port = free_port()
    process = subprocess.Popen([NODE, str(SERVER), str(port), str(log)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + SUBPROCESS_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            try:
                socket.create_connection(("127.0.0.1", port), timeout=1).close()
                break
            except OSError:
                if process.poll() is not None:
                    pytest.fail(f"server.mjs exited: {process.stderr.read().decode()}")
                time.sleep(0.05)
        yield Mock(port, log)
    finally:
        process.terminate()
        process.wait(timeout=SUBPROCESS_TIMEOUT_SECONDS)


def sse_events(text: str) -> list[dict]:
    return [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: ") and line != "data: [DONE]"]


def anthropic_tool_use(text: str) -> dict:
    events = sse_events(text)
    start = next(event["content_block"] for event in events if event["type"] == "content_block_start")
    delta = next(event["delta"] for event in events if event["type"] == "content_block_delta")
    return {"name": start.get("name"), "input": json.loads(delta["partial_json"]) if "partial_json" in delta else None}


def responses_item(text: str) -> dict:
    return next(event["item"] for event in sse_events(text) if event["type"] == "response.output_item.done")


def chat_call(text: str) -> dict:
    for event in sse_events(text):
        for call in event["choices"][0]["delta"].get("tool_calls") or []:
            return {"name": call["function"]["name"], "args": json.loads(call["function"]["arguments"])}
    return {}


def anthropic_tools(*names: str) -> list[dict]:
    schemas = {
        "Agent": {"description": {}, "prompt": {}, "subagent_type": {}},
        "Write": {"file_path": {}, "content": {}},
    }
    return [{"name": name, "input_schema": {"properties": schemas[name]}} for name in names]


def codex_tools() -> list[dict]:
    spawn = {"type": "function", "name": "spawn_agent", "parameters": {"properties": {"agent_type": {}, "message": {}, "fork_context": {}}}}
    wait = {"type": "function", "name": "wait_agent", "parameters": {"properties": {"targets": {}, "timeout_ms": {}}}}
    shell = {"type": "function", "name": "exec_command", "parameters": {"properties": {"cmd": {}, "workdir": {}}}}
    return [shell, {"type": "namespace", "name": "multi_agent_v1", "tools": [spawn, wait]}]


def chat_tools(*names: str) -> list[dict]:
    schemas = {
        "task": {"description": {}, "prompt": {}, "subagent_type": {}},
        "write": {"filePath": {}, "content": {}},
    }
    return [{"type": "function", "function": {"name": name, "parameters": {"properties": schemas[name]}}} for name in names]


@needs_node
def test_claude_main_thread_marker_starts_the_named_subagent_with_the_subagent_marker(mock):
    body = {"stream": True, "tools": anthropic_tools("Agent", "Write"),
            "messages": [{"role": "user", "content": [{"type": "text", "text": f"E2E-SPAWN python-pro {PATH} {TOKEN}"}]}]}
    text, line = mock.post("/v1/messages?beta=true", body, CLAUDE_MAIN)
    call = anthropic_tool_use(text)
    assert call["name"] == "Agent"
    assert call["input"]["subagent_type"] == "python-pro"
    assert call["input"]["prompt"] == f"E2E-SUBAGENT-WRITE {PATH} {TOKEN}"
    assert (line["role"], line["header_role"], line["format"]) == ("main", "main", "anthropic")


@needs_node
def test_claude_subagent_writes_the_exact_content_with_its_write_tool(mock):
    body = {"stream": True, "tools": anthropic_tools("Agent", "Write"),
            "messages": [{"role": "user", "content": f"PREFLIGHT for a subagent: x\nE2E-SUBAGENT-WRITE {PATH} {TOKEN}"}]}
    text, line = mock.post("/v1/messages", body, CLAUDE_SUBAGENT)
    assert anthropic_tool_use(text) == {"name": "Write", "input": {"file_path": PATH, "content": f"{TOKEN}\n"}}
    assert (line["role"], line["header_role"]) == ("subagent", "subagent")
    assert "PREFLIGHT for a subagent:" in line["context"]


@needs_node
def test_a_subagent_marker_without_the_subagent_header_is_answered_with_text_only(mock):
    body = {"stream": False, "tools": anthropic_tools("Write"),
            "messages": [{"role": "user", "content": f"E2E-SUBAGENT-WRITE {PATH} {TOKEN}"}]}
    text, line = mock.post("/v1/messages", body, CLAUDE_MAIN)
    assert json.loads(text)["content"] == [{"type": "text", "text": "E2E: role conflict, marker says subagent, headers say main"}]
    assert line["reply"]["kind"] == "text"


@needs_node
def test_the_spawn_prompt_inside_the_main_thread_history_keeps_the_session_main(mock):
    body = {"stream": True, "tools": anthropic_tools("Agent", "Write"), "messages": [
        {"role": "user", "content": f"E2E-SPAWN python-pro {PATH} {TOKEN}"},
        {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "Agent",
                                           "input": {"prompt": f"E2E-SUBAGENT-WRITE {PATH} {TOKEN}"}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": f"E2E-SUBAGENT-WRITE {PATH} {TOKEN}"}]},
    ]}
    text, line = mock.post("/v1/messages", body, CLAUDE_MAIN)
    assert line["role"] == "main"
    assert line["calls"][0]["name"] == "Agent"
    assert [event["delta"]["text"] for event in sse_events(text) if event["type"] == "content_block_delta"] == ["E2E main thread finished"]


@needs_node
def test_a_subagent_that_inherits_the_parent_history_is_placed_by_its_newest_marker(mock):
    body = {"stream": True, "tools": codex_tools(), "input": [
        {"type": "message", "role": "user", "content": f"E2E-SPAWN python-pro {PATH} {TOKEN}"},
        {"type": "function_call", "call_id": "c1", "name": "spawn_agent", "arguments": "{}"},
        {"type": "message", "role": "user", "content": f"E2E-SUBAGENT-WRITE {PATH} {TOKEN}"},
    ]}
    text, line = mock.post("/v1/responses", body, CODEX_SUBAGENT)
    assert line["role"] == "subagent"
    assert line["calls"] == []
    assert responses_item(text)["name"] == "exec_command"


@needs_node
def test_codex_spawn_uses_the_namespaced_tool_without_forking_the_history(mock):
    body = {"stream": True, "tools": codex_tools(),
            "input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": f"E2E-SPAWN python-pro {PATH} {TOKEN}"}]}]}
    text, line = mock.post("/v1/responses", body, CODEX_MAIN)
    item = responses_item(text)
    assert (item["type"], item["name"], item["namespace"]) == ("function_call", "spawn_agent", "multi_agent_v1")
    assert json.loads(item["arguments"]) == {"agent_type": "python-pro", "message": f"E2E-SUBAGENT-WRITE {PATH} {TOKEN}", "fork_context": False}
    assert line["header_role"] == "main"


@needs_node
def test_codex_main_thread_waits_for_the_agent_its_spawn_returned(mock):
    agent = "01a19494-3fc9-7253-99fb-a3afb0ce2c29"
    body = {"stream": True, "tools": codex_tools(), "input": [
        {"type": "message", "role": "user", "content": f"E2E-SPAWN python-pro {PATH} {TOKEN}"},
        {"type": "function_call", "call_id": "c1", "name": "spawn_agent", "namespace": "multi_agent_v1", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "c1", "output": json.dumps({"agent_id": agent, "nickname": "Cicero"})},
    ]}
    text, _line = mock.post("/v1/responses", body, CODEX_MAIN)
    item = responses_item(text)
    assert item["name"] == "wait_agent"
    assert json.loads(item["arguments"])["targets"] == [agent]


@needs_node
def test_codex_subagent_writes_through_its_shell_with_a_redirect(mock):
    body = {"stream": True, "tools": codex_tools(),
            "input": [{"type": "message", "role": "user", "content": f"E2E-SUBAGENT-WRITE {PATH} {TOKEN}"}]}
    text, line = mock.post("/v1/responses", body, CODEX_SUBAGENT)
    item = responses_item(text)
    assert item["name"] == "exec_command"
    assert json.loads(item["arguments"]) == {"cmd": f"printf '%s\\n' '{TOKEN}' > '{PATH}'"}
    assert (line["role"], line["header_role"]) == ("subagent", "subagent")


@needs_node
def test_copilot_subagent_writes_with_create_and_the_task_tool_waits_in_sync_mode(mock):
    create = {"type": "function", "name": "create", "parameters": {"properties": {"path": {}, "file_text": {}}}}
    task = {"type": "function", "name": "task", "parameters": {"properties": {"name": {}, "prompt": {}, "agent_type": {}, "description": {}, "mode": {}}}}
    sub = {"stream": True, "tools": [task, create], "input": [{"type": "message", "role": "user", "content": f"E2E-SUBAGENT-WRITE {PATH} {TOKEN}"}]}
    main = {"stream": True, "tools": [task, create], "input": [{"type": "message", "role": "user", "content": f"E2E-SPAWN python-pro {PATH} {TOKEN}"}]}
    sub_text, sub_line = mock.post("/v1/responses", sub, COPILOT_SUBAGENT)
    main_text, _main_line = mock.post("/v1/responses", main, {"x-initiator": "user", "x-interaction-type": "conversation-user"})
    assert json.loads(responses_item(sub_text)["arguments"]) == {"path": PATH, "file_text": f"{TOKEN}\n"}
    assert json.loads(responses_item(main_text)["arguments"])["mode"] == "sync"
    assert sub_line["header_role"] == "subagent"


@needs_node
def test_opencode_subagent_writes_with_the_file_path_key_its_schema_names(mock):
    body = {"stream": True, "tools": chat_tools("task", "write"), "messages": [
        {"role": "system", "content": "You write modern Python"},
        {"role": "user", "content": f"E2E-SUBAGENT-WRITE {PATH} {TOKEN}"},
    ]}
    text, line = mock.post("/v1/chat/completions", body, OPENCODE_SUBAGENT)
    assert chat_call(text) == {"name": "write", "args": {"filePath": PATH, "content": f"{TOKEN}\n"}}
    assert line["system"] == "You write modern Python"
    assert line["header_role"] == "subagent"


@needs_node
def test_a_subagent_finishes_with_text_once_its_write_has_a_result_and_the_log_pairs_them(mock):
    body = {"stream": True, "tools": chat_tools("task", "write"), "messages": [
        {"role": "user", "content": f"E2E-SUBAGENT-WRITE {PATH} {TOKEN}"},
        {"role": "assistant", "tool_calls": [{"id": "w1", "function": {"name": "write", "arguments": json.dumps({"filePath": PATH})}}]},
        {"role": "tool", "tool_call_id": "w1", "content": "Wrote file successfully."},
    ]}
    text, line = mock.post("/v1/chat/completions", body, OPENCODE_SUBAGENT)
    assert chat_call(text) == {}
    assert line["calls"] == [{"name": "write", "args": {"filePath": PATH}, "result": "Wrote file successfully."}]
    assert line["reply"] == {"kind": "text", "text": "E2E subagent finished"}


@needs_node
def test_a_chat_request_without_an_e2e_marker_gets_the_sandbox_mock_model_answer(mock):
    body = {"stream": True, "tools": chat_tools("write"), "messages": [{"role": "user", "content": "SANDBOX-WRITE-PROBE probe.txt"}]}
    text, line = mock.post("/v1/chat/completions", body, OPENCODE_MAIN)
    assert chat_call(text) == {"name": "write", "args": {"filePath": "probe.txt", "content": "written by the sandbox probe\n"}}
    assert (line["role"], line["reply"]["legacy"]) == ("other", True)


@needs_node
def test_count_tokens_answers_and_an_unknown_route_is_refused_but_logged(mock):
    text, line = mock.post("/v1/messages/count_tokens", {"messages": []})
    assert json.loads(text) == {"input_tokens": 1}
    with pytest.raises(urllib.error.HTTPError) as refused:
        mock.post("/v1/embeddings", {"input": "x"})
    assert refused.value.code == 404
    assert mock.lines()[-1]["url"] == "/v1/embeddings"
    assert line["format"] == "count_tokens"


@needs_node
def test_the_log_never_records_the_authorization_header(mock):
    body = {"stream": False, "messages": [{"role": "user", "content": "hello"}]}
    _text, line = mock.post("/v1/messages", body, {**CLAUDE_MAIN, "authorization": "Bearer secret-value"})
    assert "authorization" not in line["headers"]
    assert "secret-value" not in json.dumps(line)


@needs_node
def test_the_review_marker_starts_the_named_subagent_with_the_report_marker(mock):
    body = {"stream": True, "tools": anthropic_tools("Agent", "Write"),
            "messages": [{"role": "user", "content": f"E2E-REVIEW code-reviewer {PATH} e2e-review"}]}
    text, line = mock.post("/v1/messages", body, CLAUDE_MAIN)
    call = anthropic_tool_use(text)
    assert (call["name"], call["input"]["subagent_type"]) == ("Agent", "code-reviewer")
    assert call["input"]["prompt"] == f"E2E-SUBAGENT-REPORT {PATH} e2e-review"
    assert (line["role"], line["marker"], line["agent"]) == ("main", "REVIEW", "code-reviewer")


@needs_node
def test_a_reporting_subagent_finishes_with_text_and_makes_no_call(mock):
    body = {"stream": False, "tools": anthropic_tools("Write"),
            "messages": [{"role": "user", "content": f"E2E-SUBAGENT-REPORT {PATH} e2e-review"}]}
    text, line = mock.post("/v1/messages", body, CLAUDE_SUBAGENT)
    assert json.loads(text)["content"] == [{"type": "text", "text": "E2E subagent finished"}]
    assert (line["role"], line["header_role"], line["marker"]) == ("subagent", "subagent", "SUBAGENT-REPORT")


@needs_node
def test_the_log_names_every_tool_a_codex_request_offers_namespaces_included(mock):
    body = {"stream": False, "tools": codex_tools(),
            "input": [{"type": "message", "role": "user", "content": f"E2E-SUBAGENT-REPORT {PATH} e2e-no-shell"}]}
    _text, line = mock.post("/v1/responses", body, CODEX_SUBAGENT)
    assert line["tools"] == ["exec_command", "spawn_agent", "wait_agent"]


def driver(script: str) -> subprocess.CompletedProcess:
    """Sources the driver and runs script after it, with the check helpers stubbed."""
    stubs = "pass() { printf 'PASS %s\\n' \"$*\"; }; fail() { printf 'FAIL %s\\n' \"$*\"; }; note() { :; }; "
    return subprocess.run(
        ["bash", "-c", f"source '{DRIVER.as_posix()}'; {stubs}{script}"],
        capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )


def log_line(role: str, header_role: str, context: str, system: str = "", calls: list | None = None) -> str:
    return json.dumps({"role": role, "header_role": header_role, "tool_count": 2, "context": context,
                       "system": system, "calls": calls or [], "reply": {"kind": "text", "text": "ok"}}) + "\n"


NEEDLES = (
    "E2E_SUBAGENT_TEXT='PREFLIGHT for a subagent:'; E2E_MAIN_TEXTS='[\"PREFLIGHT: before\",\"Before code work\"]'; "
    "E2E_DEFINITION='You write Python'; E2E_GATE_TEXT='may not write'; "
)


def test_the_facts_count_main_thread_turns_carrying_the_agent_own_reminder(tmp_path):
    # Given two main-thread turns, one carrying the shared reminder, and one subagent turn carrying none
    log = tmp_path / "requests.jsonl"
    log.write_text(
        log_line("main", "main", "E2E-SPAWN x\nBefore code work, name it")
        + log_line("main", "main", "E2E-SPAWN x")
        + log_line("subagent", "subagent", "PREFLIGHT for a subagent: go", "You write Python"),
        encoding="utf-8",
    )

    # When
    result = driver(f"{NEEDLES}e2e_facts '{log.as_posix()}' /p 'Before code work'")

    # Then: 1 subagent turn with the subagent text and the definition, 2 main turns, 1 with the reminder
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["0", "0", "0", "0", "1", "1", "0", "1", "2", "1", "0"]


def test_the_facts_count_a_main_thread_reminder_leaked_into_a_subagent_turn(tmp_path):
    log = tmp_path / "requests.jsonl"
    log.write_text(log_line("subagent", "subagent", "PREFLIGHT for a subagent: go\nPREFLIGHT: before code work"), encoding="utf-8")

    result = driver(f"{NEEDLES}e2e_facts '{log.as_posix()}' /p 'Before code work'")

    assert result.stdout.split()[4:7] == ["1", "1", "1"]


def test_an_unreadable_log_gives_all_zero_facts(tmp_path):
    result = driver(f"{NEEDLES}e2e_facts '{(tmp_path / 'missing.jsonl').as_posix()}' /p x; e2e_review_facts /nope")

    assert result.stdout.split() == ["0"] * 15


def test_the_review_facts_tell_the_project_skill_from_the_built_in_command(tmp_path):
    # Given one subagent turn with the project skill line and one with the built-in prompt
    log = tmp_path / "requests.jsonl"
    spawn = [{"name": "Agent", "args": {}, "result": "done"}]
    log.write_text(
        log_line("main", "main", "E2E-REVIEW code-reviewer", calls=spawn)
        + log_line("subagent", "subagent", "Check application code against the failure modes")
        + log_line("subagent", "subagent", "You are a senior security engineer conducting a focused security review of the changes on this branch."),
        encoding="utf-8",
    )

    # When
    result = driver(f"E2E_SKILL_LINE='Check application code'; e2e_review_facts '{log.as_posix()}'")

    # Then: 2 subagent turns, 1 with the skill line, 1 with the built-in prompt, 1 spawn answered
    assert result.stdout.split() == ["2", "1", "1", "1"]


def offered(role: str, tools: list[str], calls: list | None = None) -> str:
    return json.dumps({"role": role, "header_role": role, "tool_count": len(tools), "tools": tools, "context": "",
                       "system": "", "calls": calls or [], "reply": {"kind": "text", "text": "ok"}}) + "\n"


def test_the_shell_facts_count_subagent_turns_that_offer_a_shell(tmp_path):
    # Given a spawn answered, two subagent turns, one offering exec_command, and a main turn offering a shell
    log = tmp_path / "requests.jsonl"
    spawn = [{"name": "spawn_agent", "args": {}, "result": "done"}]
    log.write_text(
        offered("main", ["exec_command", "spawn_agent"], spawn)
        + offered("subagent", ["apply_patch", "exec_command", "write_stdin"])
        + offered("subagent", ["apply_patch", "view_image"]),
        encoding="utf-8",
    )

    # When
    result = driver(f"e2e_shell_facts '{log.as_posix()}'")

    # Then: 2 subagent turns, 1 offering a shell, 1 spawn answered
    assert result.stdout.split() == ["2", "1", "1"]


def test_an_unreadable_log_gives_all_zero_shell_facts(tmp_path):
    assert driver(f"e2e_shell_facts '{(tmp_path / 'missing.jsonl').as_posix()}'").stdout.split() == ["0", "0", "0"]


def test_the_driver_proves_on_codex_that_an_agent_without_bash_gets_no_shell():
    source = DRIVER.read_text(encoding="utf-8")
    agent = re.search(r'^readonly E2E_NO_SHELL_AGENT="([\w-]+)"$', source, re.M).group(1)
    definition = (REPO_ROOT / "subagents" / f"{agent}.md").read_text(encoding="utf-8")

    assert "bash" not in re.search(r"^tools: \[(.*)\]$", definition, re.M).group(1)
    assert re.search(r'"\$agent" == "codex"[^\n]*\n\s*e2e_check_no_shell\b', source)


def test_the_needles_are_read_from_the_project_itself():
    result = driver(f"e2e_read_needles '{REPO_ROOT.as_posix()}' && printf '%s\\n' \"$E2E_SKILL_LINE\" \"$(e2e_own_main_text codex)\" \"$(e2e_own_main_text claude-code)\"")

    skill_line, shared, claude = result.stdout.splitlines()
    assert skill_line.startswith("Check application code against the failure modes")
    assert skill_line in (REPO_ROOT / ".agents" / "skills" / "security-review" / "SKILL.md").read_text(encoding="utf-8")
    assert shared.startswith("Before code work, name the skills")
    assert claude.startswith("PREFLIGHT: before code work, name the skills")


def test_the_driver_has_no_copilot_subagent_no_write_allowance():
    assert "NO_WRITE" not in DRIVER.read_text(encoding="utf-8")


def test_the_driver_parses_as_bash():
    result = subprocess.run(["bash", "-n", str(DRIVER)], capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_SECONDS)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck is not installed")
def test_the_driver_passes_shellcheck():
    result = subprocess.run(
        ["shellcheck", "-x", DRIVER.name], cwd=E2E_DIR, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_SECONDS
    )
    assert result.returncode == 0, result.stdout
