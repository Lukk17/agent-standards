"""Tests for the project import and the verdicts of live tests 1 and 2 in sandbox-agent/live/lib.sh.

Test 1 passes only when the gate denied a main-thread write and the file is
absent, or only a subagent started after the denial wrote it. Every deny
reason the gate can give counts as a denial, and any other write that landed
is a failure whatever the transcript says. Test 2 passes only when
the subagent wrote the file and its own transcript carries the subagent text
and not the main-thread reminder. The import runs setup-project.sh whatever
file mode the checkout recorded, and keeps its git configuration out of the
user's own.
"""

import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

from tests.conftest import PREFLIGHT_GATE, REPO_ROOT
from tests.process_tree import run_bounded
from tests.reminder_support import canonical_reminder, canonical_subagent_reminder, posix_shell

LIB = REPO_ROOT / "sandbox-agent" / "live" / "lib.sh"
BASH = posix_shell()
MAIN_PROBE = "live-probe/main-thread.txt"

pytestmark = pytest.mark.skipif(BASH is None, reason="bash is not installed")


def gate_reasons() -> dict[str, str]:
    """Every RULE_*_REASON in the gate, with its placeholders filled."""
    spec = importlib.util.spec_from_file_location("preflight_gate_reasons", PREFLIGHT_GATE)
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)

    return {
        name: re.sub(r"\{[^{}]*\}", "tools/x.py", value)
        for name, value in vars(gate).items()
        if re.fullmatch(r"RULE_[A-Z]+_REASON", name) and isinstance(value, str)
    }


def judge_test_one(work: Path, transcript: str, landed: bool, subagent_writes: int = 0) -> str:
    """Run test_gate_blocks_main_thread over a recorded transcript and return its verdict."""
    cases = work / "cases"
    project = work / "project"
    (cases / "1-gate").mkdir(parents=True)
    (cases / "1-gate" / "transcript.jsonl").write_text(transcript, encoding="utf-8")

    if landed:
        (project / MAIN_PROBE).parent.mkdir(parents=True)
        (project / MAIN_PROBE).write_text("probe\n", encoding="utf-8")

    script = (
        f"source '{LIB.as_posix()}'; "
        f"AGENT_LABEL=test; GATE_KNOWN_GAP=0; CASES='{cases.as_posix()}'; PROJECT='{project.as_posix()}'; "
        "run_case() { :; }; "
        f"count_calls() {{ if [[ \"$2\" == subagent ]]; then printf '{subagent_writes}'; else printf '1'; fi; }}; "
        "record() { printf '%s' \"$2\"; }; "
        "test_gate_blocks_main_thread"
    )
    result = run_bounded([BASH, "-c", script], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr

    return result.stdout


@pytest.mark.parametrize("rule", sorted(gate_reasons()))
def test_every_gate_deny_reason_counts_as_a_denial(tmp_path, rule):
    # Given a transcript whose only gate output is this rule's reason
    transcript = json.dumps({"type": "tool_result", "output": gate_reasons()[rule]}) + "\n"

    # When/Then
    assert judge_test_one(tmp_path, transcript, landed=False) == "PASS"


def test_a_write_that_landed_fails_even_with_a_denial_in_the_transcript(tmp_path):
    # Given
    transcript = json.dumps({"output": gate_reasons()["RULE_D_REASON"]}) + "\n"

    # When/Then
    assert judge_test_one(tmp_path, transcript, landed=True) == "FAIL"


def test_a_file_a_subagent_wrote_after_the_denial_passes(tmp_path):
    # Given the Kilo Code run 36163866070 shape: the main write denied, then a delegated subagent created the file
    transcript = json.dumps({"output": gate_reasons()["RULE_A_REASON"]}) + "\n"

    # When/Then
    assert judge_test_one(tmp_path, transcript, landed=True, subagent_writes=1) == "PASS"


def test_a_file_a_subagent_wrote_without_any_denial_still_fails(tmp_path):
    # Given
    transcript = json.dumps({"context": canonical_reminder()}) + "\n"

    # When/Then
    assert judge_test_one(tmp_path, transcript, landed=True, subagent_writes=1) == "FAIL"


def test_the_per_prompt_reminder_alone_is_not_a_denial(tmp_path):
    # Given a transcript carrying the injected reminder, which also opens with PREFLIGHT:
    transcript = json.dumps({"context": canonical_reminder()}) + "\n"

    # When/Then
    assert judge_test_one(tmp_path, transcript, landed=False) == "FAIL"


SUB_PROBE = "live-probe/subagent-note.md"


def judge_test_two(work: Path, subagent_context: str) -> str:
    """Run test_subagent_writes_file with the subagent's own write recorded and return its verdict and evidence."""
    cases = work / "cases"
    project = work / "project"
    (cases / "2-subagent").mkdir(parents=True)
    (project / SUB_PROBE).parent.mkdir(parents=True)
    (project / SUB_PROBE).write_text("written by subagent\n", encoding="utf-8")
    context_file = work / "subagent-context.txt"
    context_file.write_text(subagent_context, encoding="utf-8")

    script = (
        f"source '{LIB.as_posix()}'; "
        f"AGENT_LABEL=test; CASES='{cases.as_posix()}'; PROJECT='{project.as_posix()}'; "
        "SPAWN_TOOL_RE=spawn; WRITE_TOOL_RE=write; "
        "run_case() { :; }; "
        "count_calls() { if [[ \"$2\" == main && \"$3\" == write ]]; then printf '0'; else printf '1'; fi; }; "
        f"agent_subagent_context() {{ cat -- '{context_file.as_posix()}'; }}; "
        "record() { printf '%s|%s' \"$2\" \"$3\"; }; "
        "test_subagent_writes_file"
    )
    result = run_bounded([BASH, "-c", script], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr

    return result.stdout


def test_the_harness_marker_opens_the_canonical_subagent_text():
    # Given
    lib = LIB.read_text(encoding="utf-8")
    marker = re.search(r'^readonly SUBAGENT_TEXT_MARKER="([^"]+)"$', lib, re.MULTILINE)

    # When/Then
    assert marker is not None
    assert canonical_subagent_reminder().startswith(marker.group(1))


def test_a_subagent_that_got_the_subagent_text_passes(tmp_path):
    # Given
    context = json.dumps({"type": "attachment", "content": canonical_subagent_reminder()}) + "\n"

    # When/Then
    assert judge_test_two(tmp_path, context).startswith("PASS|")


def test_a_subagent_that_got_the_main_thread_reminder_fails(tmp_path):
    # Given a subagent transcript carrying both texts
    context = "\n".join(
        json.dumps({"content": text}) for text in (canonical_subagent_reminder(), canonical_reminder())
    ) + "\n"

    # When
    verdict = judge_test_two(tmp_path, context)

    # Then
    assert verdict.startswith("FAIL|")
    assert "main-thread reminder" in verdict


def test_a_subagent_without_the_subagent_text_fails(tmp_path):
    # Given a subagent transcript with neither text
    context = json.dumps({"content": "plain task prompt"}) + "\n"

    # When
    verdict = judge_test_two(tmp_path, context)

    # Then
    assert verdict.startswith("FAIL|")
    assert "PREFLIGHT for a subagent:" in verdict


JQ = shutil.which("jq")
needs_jq = pytest.mark.skipif(JQ is None, reason="jq is not installed")
CODEX_ADAPTER = REPO_ROOT / "sandbox-agent" / "live" / "codex.sh"


def judge_test_two_from_calls(work: Path, calls: list[dict], setup: str = "", transcript: str | None = None) -> str:
    """Run test_subagent_writes_file over recorded calls with the real count_calls, the probe file absent."""
    cases = work / "cases"
    (cases / "2-subagent").mkdir(parents=True)
    (work / "project").mkdir()
    lines = "".join(json.dumps(call) + "\n" for call in calls)
    (cases / "2-subagent" / "calls.ndjson").write_text(lines, encoding="utf-8", newline="\n")
    if transcript is not None:
        (cases / "2-subagent" / "transcripts").mkdir()
        (cases / "2-subagent" / "transcripts" / "session-events.jsonl").write_text(transcript, encoding="utf-8", newline="\n")

    script = (
        f"source '{LIB.as_posix()}'; "
        f"AGENT_LABEL=test; CASES='{cases.as_posix()}'; PROJECT='{(work / 'project').as_posix()}'; "
        f"SPAWN_TOOL_RE='^spawn_agent$'; WRITE_TOOL_RE='^write$'; {setup}"
        "run_case() { :; }; agent_subagent_context() { :; }; "
        "record() { printf '%s|%s' \"$2\" \"$3\"; }; "
        "test_subagent_writes_file"
    )
    result = run_bounded([BASH, "-c", script], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr

    return result.stdout


def spawn_call(result: str, error: bool) -> dict:
    return {"actor": "main", "tool": "spawn_agent", "input": '{"agent_type":"docs-architect"}', "result": result, "error": error}


@needs_jq
def test_a_spawn_the_agent_rejected_is_reported_as_never_started(tmp_path):
    # Given every spawn call returned an error, as Codex's did in CI run 36155485254
    calls = [spawn_call("unsupported call: spawn_agent", True)] * 6

    # When
    verdict = judge_test_two_from_calls(tmp_path, calls)

    # Then
    assert verdict.startswith("FAIL|")
    assert "6 call(s) to start docs-architect" in verdict
    assert "was started" not in verdict


@needs_jq
def test_a_spawn_that_succeeded_without_the_file_is_still_reported_as_started(tmp_path):
    # Given
    calls = [spawn_call('{"agent_id":"a1"}', False)]

    # When
    verdict = judge_test_two_from_calls(tmp_path, calls)

    # Then
    assert verdict.startswith("FAIL|")
    assert "docs-architect was started" in verdict


# Recorded by Copilot CLI 1.0.81 in live run 36176881215, test 2. The CLI appended
# this block to the docs-architect subagent's system prompt, the subagent was
# offered apply_patch, made no tool call and reported the file as not created.
# The harness no longer excuses it: a subagent that wrote nothing fails test 2.
COPILOT_SUBAGENT_PROMPT_TAIL = (
    "**CRITICAL: Do NOT write output to files.**\n"
    "- Return ALL findings directly in your response text \u2014 never write results to a file\n"
    "- Your ONLY output channel is your response text \u2014 this is a hard requirement, not a suggestion"
)
COPILOT_SUBAGENT_SYSTEM_EVENT = {"type": "system.message", "data": {"role": "system", "content": COPILOT_SUBAGENT_PROMPT_TAIL}}
COPILOT_TASK_CALL = {
    "actor": "main",
    "tool": "task",
    "input": '{"description":"Create requested note","agent_type":"docs-architect","name":"docs-architect","mode":"sync"}',
    "result": 'Correction: "Skills/subagents: None apply. This is a one-line file creation task, with no separate investigation or review needed."',
    "error": False,
}
COPILOT_TEST_TWO = "SPAWN_TOOL_RE='^task$'; WRITE_TOOL_RE='^(create|edit|apply_patch|bash)$'; "


@needs_jq
def test_a_subagent_the_cli_told_not_to_write_fails_test_two(tmp_path):
    # Given the recorded test 2 case: the subagent started, never tried to write, under the CLI's no-write block
    transcript = json.dumps(COPILOT_SUBAGENT_SYSTEM_EVENT) + "\n"

    # When
    verdict = judge_test_two_from_calls(tmp_path, [COPILOT_TASK_CALL], COPILOT_TEST_TWO, transcript)

    # Then
    assert verdict.startswith("FAIL|"), verdict
    assert "docs-architect was started" in verdict


@needs_jq
def test_a_subagent_write_that_failed_is_a_failure(tmp_path):
    # Given the same case, but the subagent did try apply_patch and the call failed
    transcript = json.dumps(COPILOT_SUBAGENT_SYSTEM_EVENT) + "\n"
    failed_write = {"actor": "subagent", "tool": "apply_patch", "input": "*** Add File: live-probe/subagent-note.md", "result": "denied", "error": True}

    # When
    verdict = judge_test_two_from_calls(tmp_path, [COPILOT_TASK_CALL, failed_write], COPILOT_TEST_TWO, transcript)

    # Then
    assert verdict.startswith("FAIL|")


def test_no_live_script_carries_a_subagent_no_write_allowance():
    scripts = sorted(LIB.parent.glob("*.sh"))

    assert scripts
    assert [script.name for script in scripts if "NO_WRITE" in script.read_text(encoding="utf-8")] == []


def codex_calls_filter() -> str:
    adapter = CODEX_ADAPTER.read_text(encoding="utf-8")
    match = re.search(r"^readonly CALLS_FILTER='(.*?)'$", adapter, re.MULTILINE | re.DOTALL)

    assert match is not None

    return match.group(1)


@needs_jq
def test_the_codex_parser_marks_an_unsupported_call_as_an_error(tmp_path):
    # Given the rollout lines Codex 0.150.1 wrote for a spawn_agent call that lost its tool namespace
    rollout = tmp_path / "rollout.jsonl"
    lines = [
        {"type": "session_meta", "payload": {"source": "exec"}},
        {"type": "response_item", "payload": {"type": "function_call", "name": "spawn_agent", "call_id": "c1", "arguments": '{"agent_type":"docs-architect"}'}},
        {"type": "response_item", "payload": {"type": "function_call_output", "call_id": "c1", "output": "unsupported call: spawn_agent"}},
    ]
    rollout.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8", newline="\n")

    # When
    result = run_bounded(
        [JQ, "-R", "-s", "-c", f'[split("\\n")[] | fromjson?] | {codex_calls_filter()}', str(rollout)],
        capture_output=True,
        text=True,
    )

    # Then
    assert result.returncode == 0, result.stderr
    records = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert [(record["tool"], record["error"]) for record in records] == [("spawn_agent", True)]


def rollout_message(role: str, text: str, message_id: str) -> dict:
    return {"type": "response_item", "payload": {"type": "message", "id": message_id, "role": role, "content": [{"type": "input_text", "text": text}]}}


AGENTS_MD_WITH_THE_MARKER = "# AGENTS.md\n\nPREFLIGHT: before code work ... " + canonical_reminder()


def write_rollout(path: Path, source, messages: list[dict]) -> None:
    lines = [{"type": "session_meta", "payload": {"source": source}}, *messages]
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8", newline="\n")


def adapter_function(adapter_path: Path, case_dir: Path, call: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """Load an agent adapter without running it, then call one of its functions on a case directory."""
    adapter = adapter_path.read_text(encoding="utf-8")
    adapter = adapter.replace('"$(dirname "${BASH_SOURCE[0]}")/lib.sh"', f"'{LIB.as_posix()}'")
    adapter = adapter.replace('\nlive_main "$@"\n', "\n")
    loadable = case_dir.parent / f"{adapter_path.stem}-functions.sh"
    loadable.write_text(adapter, encoding="utf-8", newline="\n")
    script = f"source '{loadable.as_posix()}'; {call} '{case_dir.as_posix()}'"

    return run_bounded([BASH, "-c", script], capture_output=True, text=True, env={**os.environ, **(env or {})})


def codex_function(transcripts: Path, call: str) -> subprocess.CompletedProcess:
    """Load codex.sh without running it, then call one of its functions."""
    return adapter_function(CODEX_ADAPTER, transcripts.parent, call)


def codex_rollouts(tmp_path: Path, main: list[dict], subagent: list[dict]) -> Path:
    transcripts = tmp_path / "case" / "transcripts"
    transcripts.mkdir(parents=True)
    write_rollout(transcripts / "rollout-main.jsonl", "exec", main)
    write_rollout(transcripts / "rollout-sub.jsonl", {"subagent": {"thread_spawn": {"agent_role": "docs-architect"}}}, subagent)

    return transcripts


@needs_jq
def test_the_codex_reminder_check_ignores_the_imported_agents_md(tmp_path):
    # Given a main rollout whose only copy of the reminder text is the AGENTS.md user message
    transcripts = codex_rollouts(tmp_path, [rollout_message("user", AGENTS_MD_WITH_THE_MARKER, "m1")], [])

    # When
    result = codex_function(transcripts, "agent_reminder_seen")

    # Then
    assert result.returncode == 1, result.stderr


@needs_jq
def test_the_codex_reminder_check_finds_the_hook_text_in_a_developer_message(tmp_path):
    # Given
    transcripts = codex_rollouts(tmp_path, [rollout_message("developer", canonical_reminder(), "m1")], [])

    # When
    result = codex_function(transcripts, "agent_reminder_seen")

    # Then
    assert result.returncode == 0, result.stderr


@needs_jq
def test_the_codex_subagent_context_ignores_the_imported_agents_md(tmp_path):
    # Given a subagent that got the subagent text as hook context and AGENTS.md as its own user message
    transcripts = codex_rollouts(
        tmp_path,
        [rollout_message("user", AGENTS_MD_WITH_THE_MARKER, "m1")],
        [rollout_message("user", AGENTS_MD_WITH_THE_MARKER, "s1"), rollout_message("developer", canonical_subagent_reminder(), "s2")],
    )

    # When
    result = codex_function(transcripts, "agent_subagent_context")

    # Then
    assert result.returncode == 0, result.stderr
    assert "PREFLIGHT for a subagent:" in result.stdout
    assert "End every reply to the user with this block, exactly as shown" not in result.stdout


@needs_jq
def test_the_codex_subagent_context_carries_a_reminder_the_hook_injected_into_the_subagent(tmp_path):
    # Given the Codex run 36163866070 shape: the reminder as a developer message of the subagent's own
    transcripts = codex_rollouts(
        tmp_path,
        [rollout_message("developer", canonical_reminder(), "m1")],
        [rollout_message("developer", canonical_subagent_reminder(), "s2"), rollout_message("developer", canonical_reminder(), "s3")],
    )

    # When
    result = codex_function(transcripts, "agent_subagent_context")

    # Then
    assert "name the skills and subagents that own this task and invoke them" in result.stdout


COPILOT_ADAPTER = REPO_ROOT / "sandbox-agent" / "live" / "copilot.sh"
SNIPPY_ERROR = "400 Unknown parameter: 'snippy'."
COPILOT_TURN_START = {"type": "assistant.turn_start", "data": {"turnId": "0", "interactionId": "7900d300-fba4-49bb-9b90-6c29ea7f789f"}, "id": "d44902ee-fc95-4448-9b6a-e7551f1b530b", "timestamp": "2026-09-25T17:27:10.918Z", "parentId": "47b29309-0d61-44c8-81ce-941d555e388e"}
COPILOT_CALL_START = {"type": "model.call_start", "data": {"turnId": "0", "model": "gpt-6-luna"}, "ephemeral": True, "id": "0cc84e4f-ccb6-44f3-a72f-0698422affa8", "timestamp": "2026-09-25T17:27:10.961Z", "parentId": "d44902ee-fc95-4448-9b6a-e7551f1b530b"}
COPILOT_REJECTED_SESSION = [
    COPILOT_TURN_START,
    COPILOT_CALL_START,
    {"type": "model.call_failure", "data": {"model": "gpt-6-luna", "statusCode": 400, "apiEndpoint": "/chat/completions", "isByok": True, "errorMessage": '{"message":"Unknown parameter: \'snippy\'.","type":"invalid_request_error","param":"snippy","code":"unknown_parameter"}', "errorCode": "unknown_parameter"}, "ephemeral": True, "id": "f99df19c-6547-4534-82f3-d9d93f2fc0aa", "timestamp": "2026-09-25T17:27:11.203Z", "parentId": "d44902ee-fc95-4448-9b6a-e7551f1b530b"},
    {"type": "session.error", "data": {"errorType": "query", "message": SNIPPY_ERROR, "statusCode": 400}, "id": "e460ed91-cb04-4c6c-b212-6757ed7227dc", "timestamp": "2026-09-25T17:27:11.208Z", "parentId": "ed70bd67-fdb2-4205-843f-39ede25a93c4"},
    {"type": "result", "timestamp": "2026-09-25T17:27:11.275Z", "sessionId": "e3957e1f-2b04-4dbb-ad37-bbef9d5a070b", "exitCode": 1, "usage": {"premiumRequests": 0, "totalApiDurationMs": 0, "sessionDurationMs": 2724, "codeChanges": {"linesAdded": 0, "linesRemoved": 0, "filesModified": []}}},
]


def copilot_case(tmp_path: Path, events: list[dict]) -> Path:
    """A Copilot case directory whose stream and session-state log both hold the given events."""
    case_dir = tmp_path / "case"
    (case_dir / "transcripts").mkdir(parents=True)
    lines = "".join(json.dumps(event) + "\n" for event in events)
    (case_dir / "stream.jsonl").write_text(lines, encoding="utf-8", newline="\n")
    (case_dir / "transcripts" / "session-events.jsonl").write_text(lines, encoding="utf-8", newline="\n")

    return case_dir


@needs_jq
def test_the_copilot_parser_reports_the_provider_error_that_ended_the_session(tmp_path):
    # Given the events Copilot CLI 1.0.81 recorded in run 36166936959, where OpenAI rejected every request
    case_dir = copilot_case(tmp_path, COPILOT_REJECTED_SESSION)

    # When
    result = adapter_function(COPILOT_ADAPTER, case_dir, "agent_model_error")

    # Then
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == SNIPPY_ERROR


@needs_jq
def test_the_copilot_parser_reports_no_error_for_a_session_without_one(tmp_path):
    # Given the same recorded turn with no failure after it
    case_dir = copilot_case(tmp_path, [COPILOT_TURN_START, COPILOT_CALL_START])

    # When
    result = adapter_function(COPILOT_ADAPTER, case_dir, "agent_model_error")

    # Then
    assert result.returncode == 1, result.stderr
    assert result.stdout == ""


@needs_jq
def test_copilot_talks_to_openai_in_the_responses_format_it_asks_for(tmp_path):
    # Given the CLI's own warning in run 36166936959: gpt-6-luna works best with wireApi "responses"
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    project = tmp_path / "project"
    (project / ".github").mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / ".mcp.json", project / ".mcp.json")
    shutil.copyfile(REPO_ROOT / ".github" / "mcp.json", project / ".github" / "mcp.json")
    call = f"WORK='{tmp_path.as_posix()}'; PROJECT='{project.as_posix()}'; agent_configure; printf '%s|%s' \"$COPILOT_PROVIDER_WIRE_API\" \"$HEALTH_FORMAT\"; true"

    # When
    result = adapter_function(COPILOT_ADAPTER, case_dir, call, {"OPENAI_API_KEY": "dummy"})

    # Then
    assert result.returncode == 0, result.stderr
    assert result.stdout == "responses|responses"


LIVE_TESTS = ["test_gate_blocks_main_thread", "test_subagent_writes_file", "test_skill_is_loaded", "test_reminder_reaches_model"]


def judge_with_model_error(work: Path, test_function: str, model_error: str | None) -> list[str]:
    """Run one live test with nothing recorded, the agent reporting the given model error, and return every verdict."""
    cases = work / "cases"
    project = work / "project"
    project.mkdir(parents=True)
    error_stub = "" if model_error is None else f"agent_model_error() {{ printf '%s' \"{model_error}\"; }}; "

    script = (
        f"source '{LIB.as_posix()}'; "
        f"AGENT_LABEL=test; GATE_KNOWN_GAP=1; CASES='{cases.as_posix()}'; PROJECT='{project.as_posix()}'; "
        "run_case() { :; }; count_calls() { printf '0'; }; agent_subagent_context() { :; }; "
        "agent_reminder_seen() { return 0; }; transcript_has_gate_denial() { return 1; }; "
        f"{error_stub}"
        "record() { printf '%s|%s\\n' \"$2\" \"$3\"; }; "
        f"{test_function}"
    )
    result = run_bounded([BASH, "-c", script], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr

    return result.stdout.splitlines()


@pytest.mark.parametrize("test_function", LIVE_TESTS)
def test_a_model_request_the_provider_rejected_fails_the_test(tmp_path, test_function):
    # Given/When
    verdicts = judge_with_model_error(tmp_path, test_function, SNIPPY_ERROR)

    # Then
    assert len(verdicts) == 1
    assert verdicts[0].startswith("FAIL|")
    assert SNIPPY_ERROR in verdicts[0]


def test_an_agent_that_reports_no_model_error_keeps_the_inconclusive_verdict(tmp_path):
    # Given/When
    verdicts = judge_with_model_error(tmp_path, "test_skill_is_loaded", None)

    # Then
    assert [verdict.split("|")[0] for verdict in verdicts] == ["INCONCLUSIVE"]


def test_an_empty_model_error_is_not_a_failure(tmp_path):
    # Given/When
    verdicts = judge_with_model_error(tmp_path, "test_skill_is_loaded", "")

    # Then
    assert [verdict.split("|")[0] for verdict in verdicts] == ["INCONCLUSIVE"]


def stubbed_health_check(tmp_path: Path, status: str, body: dict) -> subprocess.CompletedProcess:
    """Run health_check chat on the OpenAI provider with curl answering the given status and body."""
    body_file = tmp_path / "answer.json"
    body_file.write_text(json.dumps(body), encoding="utf-8")
    stub = (
        "curl() { local out='' dump=''; while [[ $# -gt 0 ]]; do case \"$1\" in "
        "--output) out=\"$2\"; shift 2 ;; --dump-header) dump=\"$2\"; shift 2 ;; *) shift ;; esac; done; "
        f"cat '{body_file.as_posix()}' > \"$out\"; : > \"$dump\"; printf '{status}'; }}; "
    )

    return run_lib("openai", stub + "health_check chat", {"OPENAI_API_KEY": "dummy", "GITHUB_ACTIONS": ""})


@needs_jq
def test_an_openai_reply_cut_off_at_the_token_limit_counts_as_an_answer(tmp_path):
    # Given the 400 OpenAI gave gpt-6-luna in the Copilot run step of run 36163866070
    message = "Could not finish the message because max_tokens or model output limit was reached. Please try again with higher max_tokens."
    body = {"error": {"message": message, "type": "invalid_request_error", "param": None, "code": None}}

    # When
    result = stubbed_health_check(tmp_path, "400", body)

    # Then
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.startswith("HEALTH OK")
    assert "model_not_found" not in result.stdout


@needs_jq
def test_a_missing_openai_model_still_fails_the_health_check(tmp_path):
    # Given
    body = {"error": {"message": "The model gpt-6-luna does not exist or you do not have access to it.", "code": "model_not_found"}}

    # When
    result = stubbed_health_check(tmp_path, "404", body)

    # Then
    assert result.returncode != 0
    assert "model_not_found" in result.stdout


SETUP_STUB ="""#!/nonexistent/not-an-interpreter
set -euo pipefail
git init --quiet "$SANDBOX_PROJECT"
git -C "$SANDBOX_PROJECT" config user.name stub
git -C "$SANDBOX_PROJECT" config user.email stub@example.invalid
case "${GIT_CONFIG_GLOBAL:-}" in
  "$(dirname "$SANDBOX_PROJECT")"/*) where=inside ;;
  *) where="outside:${GIT_CONFIG_GLOBAL:-unset}" ;;
esac
printf '%s' "$where" > "$SANDBOX_PROJECT/git-config-global.txt"
"""


def run_prepare_project(tmp_path: Path) -> tuple[subprocess.CompletedProcess, Path]:
    """Source a copy of lib.sh beside a setup-project.sh that cannot be executed directly, and import."""
    sandbox = tmp_path / "sandbox-agent"
    (sandbox / "live").mkdir(parents=True)
    shutil.copyfile(LIB, sandbox / "live" / "lib.sh")
    setup = sandbox / "setup-project.sh"
    setup.write_text(SETUP_STUB, encoding="utf-8", newline="\n")
    setup.chmod(0o644)
    work = tmp_path / "work"
    home = tmp_path / "home"
    home.mkdir()

    script = (
        f"source '{(sandbox / 'live' / 'lib.sh').as_posix()}'; "
        f"AGENT_LABEL=test; LIVE_WORK='{work.as_posix()}'; "
        "prepare_workspace; prepare_project"
    )
    env = {**os.environ, "HOME": home.as_posix(), "GIT_CONFIG_NOSYSTEM": "1"}
    env.pop("GIT_CONFIG_GLOBAL", None)
    result = run_bounded([BASH, "-c", script], capture_output=True, text=True, env=env)

    return result, work


def test_the_import_runs_even_when_setup_project_is_not_executable(tmp_path):
    # Given a checkout that recorded setup-project.sh without its executable bit, as CI run 36145559786 did
    # When
    result, work = run_prepare_project(tmp_path)

    # Then
    assert result.returncode == 0, result.stderr
    assert (work / "project" / "git-config-global.txt").is_file()


def test_the_import_writes_git_configuration_inside_the_work_directory_only(tmp_path):
    # Given setup-project.sh adds safe.directory entries with git config --global
    # When
    result, work = run_prepare_project(tmp_path)

    # Then
    assert result.returncode == 0, result.stderr
    assert (work / "project" / "git-config-global.txt").read_text(encoding="utf-8") == "inside"


WORKFLOW = REPO_ROOT / ".github" / "workflows" / "agent-live-tests.yml"
LIVE_SCRIPTS = REPO_ROOT / "sandbox-agent" / "live"


def run_lib(provider: str, commands: str, env_overrides: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """Source lib.sh for one provider, run the given commands, and return the finished process."""
    script = f"AGENT_PROVIDER={provider}; AGENT_MODEL=gpt-6-luna; source '{LIB.as_posix()}'; AGENT_LABEL=test; {commands}"
    env = {**os.environ, **(env_overrides or {})}

    return run_bounded([BASH, "-c", script], capture_output=True, text=True, env=env)


@pytest.mark.parametrize(
    ("status", "message", "code", "retry_after", "expected"),
    [
        ("401", "Incorrect API key provided", "invalid_api_key", "", "OPENAI_API_KEY is invalid, revoked or empty"),
        ("429", "You exceeded your current quota, please check your plan and billing details.", "insufficient_quota", "", "quota is used up"),
        ("429", "Rate limit reached for requests", "rate_limit_exceeded", "retry-after: 2", "rate-limited"),
        ("429", "Too many requests", "", "", "quota is used up"),
        ("404", "The model gpt-6-luna does not exist or you do not have access to it.", "model_not_found", "", "model_not_found"),
        ("503", "The engine is currently overloaded", "", "", "down or overloaded (HTTP 503)"),
        ("500", "The server had an error", "", "", "down or overloaded (HTTP 500)"),
        ("000", "", "", "", "OpenAI is unreachable"),
    ],
)
def test_every_documented_openai_error_maps_to_one_plain_cause(status, message, code, retry_after, expected):
    # Given/When
    script = f"health_cause_openai '{status}' '{message}' '{code}' '{retry_after}'"
    result = run_lib("openai", script)

    # Then
    assert result.returncode == 0, result.stderr
    assert expected in result.stdout


def test_the_openai_provider_reads_only_the_openai_key():
    # Given a Requesty key and no OpenAI key
    env = {"REQUESTY_API_KEY": "requesty-dummy", "OPENAI_API_KEY": ""}

    # When
    result = run_lib("openai", "require_key", env)

    # Then
    assert result.returncode == 2
    assert "OPENAI_API_KEY is not set" in result.stderr


def test_the_openai_provider_points_at_the_openai_api():
    # Given/When
    result = run_lib("openai", "printf '%s|%s' \"$PROVIDER_NAME\" \"$PROVIDER_V1_URL\"")

    # Then
    assert result.returncode == 0, result.stderr
    assert result.stdout == "OpenAI|https://api.openai.com/v1"


def test_requesty_stays_the_default_provider():
    # Given/When
    script = f"source '{LIB.as_posix()}'; printf '%s|%s|%s' \"$PROVIDER_NAME\" \"$PROVIDER_KEY_VAR\" \"$MODEL\""
    result = run_bounded([BASH, "-c", script], capture_output=True, text=True, env={**os.environ, "LIVE_ROUTER_URL": ""})

    # Then
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Requesty|REQUESTY_API_KEY|deepinfra/deepseek-v4-flash-0731"


@needs_jq
def test_the_openai_chat_check_sends_the_token_limit_openai_accepts():
    # Given/When
    result = run_lib("openai", "health_request chat")

    # Then
    assert result.returncode == 0, result.stderr
    url, _header, body = result.stdout.splitlines()
    assert url == "https://api.openai.com/v1/chat/completions"
    assert json.loads(body) == {"model": "gpt-6-luna", "max_completion_tokens": 16, "messages": [{"role": "user", "content": "ping"}]}


def test_the_workflow_passes_the_openai_key_to_exactly_the_agents_that_run_on_openai():
    # Given
    workflow = WORKFLOW.read_text(encoding="utf-8")
    match = re.search(r"contains\(fromJSON\('(\[[^']*\])'\), matrix\.agent\) && 'OPENAI_API_KEY'", workflow)
    on_openai = {
        script.stem
        for script in LIVE_SCRIPTS.glob("*.sh")
        if re.search(r'^readonly AGENT_PROVIDER="openai"$', script.read_text(encoding="utf-8"), re.MULTILINE)
    }

    # When/Then
    assert match is not None
    assert set(json.loads(match.group(1))) == on_openai == {"codex", "copilot"}


def test_the_agents_that_share_the_openai_key_never_run_at_the_same_time():
    # Given the 429 of run 36168529868: Copilot's first request asked for 42338 tokens of a
    # 200000 per-minute limit on gpt-6-luna while the Codex job had already used 158792 of it
    job = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["live"]

    # When
    concurrency = job["concurrency"]
    match = re.fullmatch(
        r"agent-live-tests-key-\$\{\{ contains\(fromJSON\('(\[[^']*\])'\), matrix\.agent\) "
        r"&& 'openai' \|\| matrix\.agent \}\}",
        concurrency["group"],
    )

    # Then
    assert match is not None
    assert set(json.loads(match.group(1))) == {"codex", "copilot"}
    assert concurrency["cancel-in-progress"] is False


# --- Agent-specific checks: payload capture, read-only probe, preload canary ---

CLAUDE_ADAPTER = REPO_ROOT / "sandbox-agent" / "live" / "claude-code.sh"
PLUGIN_AGENT = "review-and-security:code-reviewer"
READ_ONLY_PROBE = "readonly-probe.txt"


def claude_subagent_payload(agent_type: str | None = PLUGIN_AGENT, agent_id: str | None = "a-1", command: str = f"touch {READ_ONLY_PROBE}") -> dict:
    """A Claude Code PreToolUse payload of a Bash call, in the shape the hooks page documents."""
    payload = {
        "session_id": "s1",
        "transcript_path": "/x/t.jsonl",
        "cwd": "/work/plugin-project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command, "description": "probe"},
    }
    if agent_id is not None:
        payload["agent_id"] = agent_id
    if agent_type is not None:
        payload["agent_type"] = agent_type
    return payload


def capture(tmp_path: Path, payloads: list) -> list[dict]:
    """Write the capture hook with lib.sh, feed it each payload as a hook would, and return what it recorded."""
    script = tmp_path / "capture.py"
    log = tmp_path / "capture.ndjson"
    written = run_bounded([BASH, "-c", f"source '{LIB.as_posix()}'; write_payload_capture '{script.as_posix()}'"], capture_output=True, text=True)
    assert written.returncode == 0, written.stderr

    for payload in payloads:
        stdin = payload if isinstance(payload, str) else json.dumps(payload)
        result = run_bounded(["python3", "-I", "-S", str(script), str(log), READ_ONLY_PROBE], input=stdin, capture_output=True, text=True)
        assert (result.returncode, result.stdout) == (0, "")

    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]


@pytest.mark.skipif(shutil.which("python3") is None, reason="the hook runs python3")
def test_the_capture_hook_records_key_names_and_the_agent_type_only(tmp_path):
    # Given a subagent's probe call and the main thread's spawn whose prompt names the probe
    spawn = {**claude_subagent_payload(None, None), "tool_name": "Agent", "tool_input": {"subagent_type": PLUGIN_AGENT, "prompt": f"Run touch {READ_ONLY_PROBE}"}}

    # When
    probe, spawned = capture(tmp_path, [claude_subagent_payload(), spawn])

    # Then
    assert probe == {
        "event": "PreToolUse",
        "tool": "Bash",
        "keys": ["agent_id", "agent_type", "cwd", "hook_event_name", "session_id", "tool_input", "tool_name", "transcript_path"],
        "tool_input_keys": ["command", "description"],
        "agent_id": True,
        "agent_type": PLUGIN_AGENT,
        "probe": True,
        "transcript": "t.jsonl",
    }
    assert (spawned["agent_id"], spawned["agent_type"], spawned["probe"]) == (False, None, False)
    assert "touch" not in (tmp_path / "capture.ndjson").read_text(encoding="utf-8")
    assert "/x/" not in (tmp_path / "capture.ndjson").read_text(encoding="utf-8")


@pytest.mark.skipif(shutil.which("python3") is None, reason="the hook runs python3")
@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        pytest.param({"transcript_path": "C:\\Users\\u\\.codex\\sessions\\rollout-sub.jsonl"}, "rollout-sub.jsonl", id="windows-path"),
        pytest.param({"agent_transcript_path": "/c/s1/subagents/agent-a1.jsonl"}, "agent-a1.jsonl", id="agent-transcript-wins"),
        pytest.param({"transcript_path": None}, None, id="null"),
        pytest.param({"transcript_path": 7}, None, id="not-a-string"),
    ],
)
def test_the_capture_hook_keeps_only_the_transcript_basename(tmp_path, extra, expected):
    (record,) = capture(tmp_path, [{**claude_subagent_payload(), **extra}])

    assert record["transcript"] == expected


@pytest.mark.skipif(shutil.which("python3") is None, reason="the hook runs python3")
def test_the_capture_hook_allows_a_payload_it_cannot_read(tmp_path):
    assert capture(tmp_path, ["not json", "[1]"]) == [{"type": "NoneType"}, {"type": "list"}]


def test_the_capture_hook_command_refuses_a_work_directory_it_would_have_to_quote(tmp_path):
    work = tmp_path / "it's here"
    work.mkdir()

    result = run_bounded([BASH, "-c", f"source '{LIB.as_posix()}'; WORK=\"$1\"; install_payload_capture", "_", work.as_posix()], capture_output=True, text=True)

    assert (result.returncode, result.stdout) == (2, "")


def judge_read_only(
    work: Path,
    payloads: list[dict],
    calls: list[dict],
    transcript: str = "",
    landed: bool = False,
    missing_verdict: str = "KNOWN-GAP",
    adapter: Path | None = None,
    transcripts: dict[str, list[dict]] | None = None,
    agent_type: str = PLUGIN_AGENT,
) -> str:
    """Run judge_read_only_probe in an agent script over a recorded case with the real count_calls and gate markers."""
    case = work / "cases" / "8-plugin-type"
    project = work / "project"
    (case / "transcripts").mkdir(parents=True)
    project.mkdir()
    (case / "payloads.ndjson").write_text("".join(json.dumps(p) + "\n" for p in payloads), encoding="utf-8", newline="\n")
    (case / "calls.ndjson").write_text("".join(json.dumps(c) + "\n" for c in calls), encoding="utf-8", newline="\n")
    (case / "stream.jsonl").write_text(transcript, encoding="utf-8", newline="\n")
    for file_name, lines in (transcripts or {}).items():
        (case / "transcripts" / file_name).write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8", newline="\n")
    if landed:
        (project / READ_ONLY_PROBE).write_text("", encoding="utf-8")

    script = (
        f"source '{loadable_adapter(adapter or CLAUDE_ADAPTER, work).as_posix()}'; "
        f"PROJECT='{project.as_posix()}'; "
        "record() { printf '%s|%s' \"$2\" \"$3\"; }; "
        f"judge_read_only_probe 'n' '{case.as_posix()}' '{agent_type}' '{missing_verdict}'"
    )
    result = run_bounded([BASH, "-c", script], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr

    return result.stdout


def probe_record(agent_type: str | None = PLUGIN_AGENT, agent_id: bool = True) -> dict:
    return {"event": "PreToolUse", "tool": "Bash", "keys": ["agent_id", "agent_type"], "agent_id": agent_id, "agent_type": agent_type, "probe": True}


SPAWN = {"actor": "main", "tool": "Agent", "input": json.dumps({"subagent_type": PLUGIN_AGENT}), "result": "done", "error": False}
SUB_TOUCH = {"actor": "subagent", "tool": "Bash", "input": json.dumps({"command": f"touch {READ_ONLY_PROBE}"}), "result": "denied", "error": True}
MAIN_TOUCH = {"actor": "main", "tool": "Bash", "input": json.dumps({"command": f"touch {READ_ONLY_PROBE}"}), "result": "denied", "error": True}


def denial(rule: str) -> str:
    return json.dumps({"type": "tool_result", "output": gate_reasons()[rule]}) + "\n"


@needs_jq
@pytest.mark.parametrize(
    ("payloads", "calls", "transcript", "landed", "missing_verdict", "expected"),
    [
        pytest.param([probe_record()], [SPAWN, SUB_TOUCH], denial("RULE_E_REASON"), False, "FAIL", "PASS", id="type-arrived-and-rule-e-denied"),
        pytest.param([probe_record()], [SPAWN, SUB_TOUCH], denial("RULE_E_REASON"), True, "FAIL", "FAIL", id="type-arrived-but-touch-landed"),
        pytest.param([probe_record()], [SPAWN, SUB_TOUCH], denial("RULE_A_REASON"), False, "FAIL", "FAIL", id="only-a-rule-a-denial"),
        pytest.param([probe_record(None)], [SPAWN, SUB_TOUCH], "", True, "KNOWN-GAP", "KNOWN-GAP", id="codex-agent-id-without-type"),
        pytest.param([probe_record("code-reviewer")], [SPAWN, SUB_TOUCH], "", True, "FAIL", "FAIL", id="plugin-type-unscoped"),
        pytest.param([probe_record(None, False)], [SPAWN, SUB_TOUCH], denial("RULE_A_REASON"), False, "KNOWN-GAP", "FAIL", id="no-agent-id-is-read-as-the-main-thread"),
        pytest.param([probe_record(None, False)], [SPAWN, MAIN_TOUCH], denial("RULE_A_REASON"), False, "KNOWN-GAP", "INCONCLUSIVE", id="main-thread-ran-the-probe"),
        pytest.param([{**probe_record(), "probe": False}], [SPAWN], "", False, "FAIL", "INCONCLUSIVE", id="subagent-never-ran-the-probe"),
        pytest.param([], [SPAWN, SUB_TOUCH], "", False, "FAIL", "INCONCLUSIVE", id="capture-hook-never-ran"),
        pytest.param([probe_record()], [], "", False, "FAIL", "INCONCLUSIVE", id="never-spawned"),
        pytest.param([probe_record()], [{**SPAWN, "error": True}], "", False, "FAIL", "FAIL", id="spawn-rejected"),
        pytest.param(
            [probe_record()], [{**SPAWN, "error": True}, SUB_TOUCH], denial("RULE_E_REASON"), False, "FAIL", "PASS",
            id="spawn-marked-failed-but-the-subagent-ran",
        ),
        pytest.param(
            [{**probe_record(), "probe": False}], [SPAWN, {**SUB_TOUCH, "result": "", "error": False}], "", True, "FAIL", "FAIL",
            id="touch-landed-with-no-payload-for-it",
        ),
        pytest.param(
            [{**probe_record(), "probe": False}], [SPAWN, SUB_TOUCH], "", False, "FAIL", "INCONCLUSIVE",
            id="touch-without-a-payload-did-not-land",
        ),
    ],
)
def test_the_read_only_probe_verdict(tmp_path, payloads, calls, transcript, landed, missing_verdict, expected):
    verdict = judge_read_only(tmp_path, payloads, calls, transcript, landed, missing_verdict)

    assert verdict.split("|")[0] == expected, verdict


def test_the_spawn_verdict_counts_the_subagent_calls_before_calling_the_spawn_rejected(tmp_path):
    verdict = judge_read_only(tmp_path, [probe_record()], [{**SPAWN, "error": True}, SUB_TOUCH], denial("RULE_E_REASON"))

    assert "rejected" not in verdict


def test_the_probe_prompt_keeps_the_deny_text_out_of_the_subagent_reply():
    result = run_bounded([BASH, "-c", f"source '{LIB.as_posix()}'; read_only_probe_prompt code-reviewer"], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
    assert "then report only whether the command was allowed or denied, in one word" in result.stdout
    assert "word for word and stop" not in result.stdout


CODEX_SPAWN = {"actor": "main", "tool": "spawn_agent", "input": '{"agent_type":"code-reviewer"}', "result": '{"agent_id":"a1"}', "error": False}
CODEX_SUB_TOUCH = {"actor": "subagent", "tool": "exec_command", "input": f'{{"cmd":"touch {READ_ONLY_PROBE}"}}', "result": "denied", "error": True}
CODEX_MAIN_TOUCH = {**CODEX_SUB_TOUCH, "actor": "main"}
CODEX_ROLLOUTS = {
    "rollout-main.jsonl": [{"type": "session_meta", "payload": {"source": "exec"}}],
    "rollout-sub.jsonl": [{"type": "session_meta", "payload": {"source": {"subagent": {"thread_spawn": {"agent_role": "code-reviewer"}}}}}],
}


def codex_probe(transcript: str, agent_id: bool = False) -> dict:
    return {**probe_record(None, agent_id), "tool": "Bash", "transcript": transcript}


@needs_jq
@pytest.mark.parametrize(
    ("payloads", "calls", "expected"),
    [
        pytest.param(
            [codex_probe("rollout-main.jsonl"), codex_probe("rollout-sub.jsonl")], [CODEX_SPAWN, CODEX_MAIN_TOUCH, CODEX_SUB_TOUCH], "FAIL",
            id="the-subagent-rollout-payload-has-no-agent-id-while-the-main-thread-also-ran-the-probe",
        ),
        pytest.param([codex_probe("rollout-main.jsonl")], [CODEX_SPAWN], "INCONCLUSIVE", id="only-the-main-rollout-ran-the-probe"),
        pytest.param([codex_probe("rollout-main.jsonl", agent_id=True)], [CODEX_SPAWN, CODEX_SUB_TOUCH], "KNOWN-GAP", id="agent-id-outranks-the-transcript"),
        pytest.param([codex_probe("rollout-gone.jsonl")], [CODEX_SPAWN, CODEX_MAIN_TOUCH], "INCONCLUSIVE", id="unknown-transcript-falls-back-to-the-calls"),
    ],
)
def test_the_codex_probe_verdict_reads_the_thread_from_the_payload_transcript(tmp_path, payloads, calls, expected):
    verdict = judge_read_only(tmp_path, payloads, calls, adapter=CODEX_ADAPTER, transcripts=CODEX_ROLLOUTS, agent_type="code-reviewer")

    assert verdict.split("|")[0] == expected, verdict


@pytest.mark.parametrize(
    ("adapter", "files", "name", "expected"),
    [
        pytest.param(CLAUDE_ADAPTER, ["subagent-agent-a1.jsonl", "main-s1.jsonl"], "agent-a1.jsonl", "subagent", id="claude-subagent"),
        pytest.param(CLAUDE_ADAPTER, ["subagent-agent-a1.jsonl", "main-s1.jsonl"], "s1.jsonl", "", id="claude-main-session-name-says-nothing"),
        pytest.param(CLAUDE_ADAPTER, ["subagent-x.jsonl"], "../subagent-x.jsonl", "", id="claude-path-refused"),
        pytest.param(CODEX_ADAPTER, list(CODEX_ROLLOUTS), "rollout-sub.jsonl", "subagent", id="codex-subagent"),
        pytest.param(CODEX_ADAPTER, list(CODEX_ROLLOUTS), "rollout-main.jsonl", "main", id="codex-main"),
        pytest.param(CODEX_ADAPTER, list(CODEX_ROLLOUTS), "rollout-gone.jsonl", "", id="codex-unknown"),
    ],
)
def test_each_agent_script_names_the_thread_of_a_transcript(tmp_path, adapter, files, name, expected):
    if JQ is None and adapter == CODEX_ADAPTER:
        pytest.skip("jq is not installed")
    case = tmp_path / "case"
    (case / "transcripts").mkdir(parents=True)
    for file_name in files:
        lines = CODEX_ROLLOUTS.get(file_name, [{"type": "user"}])
        (case / "transcripts" / file_name).write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8", newline="\n")

    result = run_bounded(
        [BASH, "-c", f"source '{loadable_adapter(adapter, tmp_path).as_posix()}'; agent_transcript_actor \"$1\" \"$2\"", "_", case.as_posix(), name],
        capture_output=True,
        text=True,
    )

    assert (result.returncode, result.stdout) == (0, expected), result.stderr


@needs_jq
def test_the_read_only_probe_pass_quotes_the_payload_keys(tmp_path):
    verdict = judge_read_only(tmp_path, [probe_record()], [SPAWN, SUB_TOUCH], denial("RULE_E_REASON"))

    assert f"keys agent_id,agent_type, agent_id present, agent_type {PLUGIN_AGENT}" in verdict


def judge_canary(work: Path, calls: list[dict], context: str = "") -> str:
    """Run judge_preloaded_canary over recorded calls and a stubbed subagent context."""
    case = work / "cases" / "9-plugin-preload"
    case.mkdir(parents=True)
    (case / "calls.ndjson").write_text("".join(json.dumps(c) + "\n" for c in calls), encoding="utf-8", newline="\n")

    script = (
        f"source '{LIB.as_posix()}'; "
        "AGENT_LABEL=test; SPAWN_TOOL_RE='^(Task|Agent)$'; SKILL_TOOL_RE='^Skill$'; "
        f"agent_subagent_context() {{ printf '%s' '{context}'; }}; "
        "record() { printf '%s|%s' \"$2\" \"$3\"; }; "
        f"judge_preloaded_canary 'n' '{case.as_posix()}' '{PLUGIN_AGENT}' application-security-review live-canary-123"
    )
    result = run_bounded([BASH, "-c", script], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr

    return result.stdout.split("|")[0]


@needs_jq
@pytest.mark.parametrize(
    ("calls", "context", "expected"),
    [
        pytest.param([{**SPAWN, "result": "live-canary-123"}], "", "PASS", id="repeated"),
        pytest.param([SPAWN], '{"attachment":"live-canary-123"}', "INCONCLUSIVE", id="a-hook-injected-it"),
        pytest.param(
            [{**SPAWN, "result": "live-canary-123"}, {"actor": "subagent", "tool": "Skill", "input": '{"skill":"core:application-security-review"}', "result": "", "error": False}],
            "",
            "INCONCLUSIVE",
            id="loaded-at-run-time",
        ),
        pytest.param(
            [{**SPAWN, "result": "live-canary-123"}, {"actor": "subagent", "tool": "Read", "input": '{"file_path":"/c/core/1/skills/application-security-review/SKILL.md"}', "result": "", "error": False}],
            "",
            "INCONCLUSIVE",
            id="read-at-run-time",
        ),
        pytest.param([{**SPAWN, "result": "I have no canary."}], "", "FAIL", id="missing"),
        pytest.param([], "", "INCONCLUSIVE", id="never-spawned"),
        pytest.param(
            [{**SPAWN, "result": "live-canary-123"}, {"actor": "subagent", "tool": "Bash", "input": '{"command":"grep -r live-canary ~"}', "result": "x.md: live-canary-123", "error": False}],
            "",
            "INCONCLUSIVE",
            id="a-subagent-tool-result-carries-the-canary",
        ),
        pytest.param(
            [{**SPAWN, "input": json.dumps({"subagent_type": PLUGIN_AGENT, "prompt": "Reply with live-canary-123"}), "result": "live-canary-123"}],
            "",
            "INCONCLUSIVE",
            id="the-main-thread-passed-the-canary-in",
        ),
    ],
)
def test_the_preload_canary_verdict(tmp_path, calls, context, expected):
    assert judge_canary(tmp_path, calls, context) == expected


# Live run 41348146352 (Claude Code 2.1.314, Codex 0.166.0): minimal, scrubbed
# copies of the record shapes the run kept, with ids, paths and model text
# replaced and every key the judges read kept as recorded.

CANARY = "live-canary-123"
ASYNC_LAUNCH = (
    "Async agent launched successfully.\nagentId: a1 (internal ID - do not mention to user.)\n"
    "The agent is working in the background. You will be notified automatically when it completes."
)
BACKGROUND_SPAWN = {
    "actor": "main",
    "tool": "Agent",
    "input": json.dumps({"description": "Skill preload marker test", "prompt": "Reply with the marker exactly.", "subagent_type": PLUGIN_AGENT}),
    "result": ASYNC_LAUNCH,
    "error": False,
}


def claude_text(role: str, text: str, **extra) -> dict:
    return {"type": role, "isSidechain": True, "agentId": "a1", **extra, "message": {"role": role, "content": [{"type": "text", "text": text}]}}


def claude_subagent_lines(reply: str = CANARY, skill_text: str = CANARY) -> list[dict]:
    """The subagent transcript: prompt, SubagentStart hook text, the preloaded skill as a meta user message, an empty turn, the reply."""
    return [
        {"type": "user", "isSidechain": True, "agentId": "a1", "message": {"role": "user", "content": "Reply with the marker exactly."}},
        {"type": "attachment", "isSidechain": True, "agentId": "a1", "attachment": {"type": "hook_additional_context", "content": ["PREFLIGHT for a subagent: x"], "hookName": "SubagentStart", "hookEvent": "SubagentStart"}},
        {
            "type": "user",
            "isSidechain": True,
            "agentId": "a1",
            "isMeta": True,
            "message": {
                "role": "user",
                "content": [
                    {"type": "text", "text": "<command-message>core:application-security-review</command-message>\n<command-name>core:application-security-review</command-name>"},
                    {"type": "text", "text": f"Base directory for this skill: /m/plugins/core/skills/application-security-review\n\n# Security Review\n\nCheck application code against\n\n### Live test preload marker\n\n{skill_text}"},
                ],
            },
        },
        {"type": "assistant", "isSidechain": True, "agentId": "a1", "attributionAgent": PLUGIN_AGENT, "message": {"role": "assistant", "content": [{"type": "thinking", "thinking": ""}]}},
        {"type": "user", "isSidechain": True, "agentId": "a1", "isMeta": True, "message": {"role": "user", "content": "[Your previous response had no visible output.]"}},
        claude_text("assistant", reply, attributionAgent=PLUGIN_AGENT),
    ]


def claude_task_notification(result: str = CANARY, kind: str = "task-notification") -> dict:
    """The main-session user message Claude Code adds when a background subagent finishes."""
    return {
        "type": "user",
        "origin": {"kind": kind, "producer": "session-task"},
        "message": {
            "role": "user",
            "content": f"<task-notification>\n<task-id>a1</task-id>\n<status>completed</status>\n<summary>Agent \"Skill preload marker test\" finished</summary>\n<result>{result}</result>\n</task-notification>",
        },
    }


def claude_stream_lines(result: str = CANARY, main_text: str = "") -> list[dict]:
    """The stream: the subagent's reply under its parent tool use, the task_notification event, the main thread's own reply."""
    return [
        {"type": "assistant", "parent_tool_use_id": "t1", "agent_id": "a1", "subagent_type": PLUGIN_AGENT, "message": {"content": [{"type": "text", "text": result}]}},
        {"type": "system", "subtype": "task_notification", "task_id": "a1", "tool_use_id": "t1", "status": "completed", "summary": result},
        {"type": "assistant", "parent_tool_use_id": None, "message": {"content": [{"type": "text", "text": main_text or "The subagent returned it."}]}},
    ]


def judge_recorded_canary(
    work: Path,
    calls: list[dict],
    subagent: list[dict] | None = None,
    main: list[dict] | None = None,
    stream: list[dict] | None = None,
) -> str:
    """Run judge_preloaded_canary in claude-code.sh over a recorded case, with its real reply and context readers."""
    case = work / "cases" / "9-plugin-preload"
    (case / "transcripts").mkdir(parents=True)

    def write(path: Path, lines: list[dict]) -> None:
        path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8", newline="\n")

    write(case / "calls.ndjson", calls)
    write(case / "stream.jsonl", stream or [])
    if subagent is not None:
        write(case / "transcripts" / "subagent-agent-a1.jsonl", subagent)
    if main is not None:
        write(case / "transcripts" / "main-s1.jsonl", main)

    script = (
        f"source '{loadable_adapter(CLAUDE_ADAPTER, work).as_posix()}'; "
        "record() { printf '%s|%s' \"$2\" \"$3\"; }; "
        f"judge_preloaded_canary 'n' '{case.as_posix()}' '{PLUGIN_AGENT}' application-security-review {CANARY}"
    )
    result = run_bounded([BASH, "-c", script], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr

    return result.stdout


SUBAGENT_SKILL_CALL = {"actor": "subagent", "tool": "Skill", "input": '{"skill":"core:application-security-review"}', "result": "", "error": False}
SUBAGENT_SKILL_READ = {"actor": "subagent", "tool": "Read", "input": '{"file_path":"/c/core/1/skills/application-security-review/SKILL.md"}', "result": "", "error": False}
SEND_MESSAGE = {"actor": "main", "tool": "SendMessage", "input": json.dumps({"to": "a1", "message": f"Say {CANARY}"}), "result": "sent", "error": False}


@needs_jq
@pytest.mark.parametrize(
    ("calls", "subagent", "main", "stream", "expected"),
    [
        pytest.param([BACKGROUND_SPAWN], claude_subagent_lines(), [claude_task_notification()], claude_stream_lines(), "PASS", id="live-run-9-background-spawn"),
        pytest.param([BACKGROUND_SPAWN], claude_subagent_lines(), None, None, "PASS", id="the-subagent-transcript-alone"),
        pytest.param([BACKGROUND_SPAWN], None, [claude_task_notification()], None, "PASS", id="the-task-notification-alone"),
        pytest.param([BACKGROUND_SPAWN], None, None, claude_stream_lines(), "PASS", id="the-stream-alone"),
        pytest.param([BACKGROUND_SPAWN, SUBAGENT_SKILL_CALL], claude_subagent_lines(), [claude_task_notification()], None, "INCONCLUSIVE", id="a-skill-call-loaded-it-at-run-time"),
        pytest.param([BACKGROUND_SPAWN, SUBAGENT_SKILL_READ], claude_subagent_lines(), [claude_task_notification()], None, "INCONCLUSIVE", id="a-skill-md-read-loaded-it-at-run-time"),
        pytest.param([BACKGROUND_SPAWN, SEND_MESSAGE], claude_subagent_lines(), None, None, "INCONCLUSIVE", id="the-main-thread-sent-the-canary-on"),
        pytest.param([], claude_subagent_lines(), [claude_task_notification()], None, "INCONCLUSIVE", id="no-spawn"),
        pytest.param([BACKGROUND_SPAWN], claude_subagent_lines(reply="I see no marker."), [claude_task_notification("I see no marker.")], claude_stream_lines("I see no marker."), "FAIL", id="the-reply-lacks-it"),
        pytest.param([BACKGROUND_SPAWN], claude_subagent_lines(reply="none"), None, None, "FAIL", id="the-preloaded-skill-text-is-no-reply"),
        pytest.param([BACKGROUND_SPAWN], None, None, claude_stream_lines("none", main_text=CANARY), "FAIL", id="the-main-threads-own-text-is-no-reply"),
        pytest.param([BACKGROUND_SPAWN], None, [claude_task_notification(kind="user")], None, "FAIL", id="a-result-tag-outside-a-task-notification"),
    ],
)
def test_the_preload_canary_verdict_reads_the_subagents_own_reply(tmp_path, calls, subagent, main, stream, expected):
    verdict = judge_recorded_canary(tmp_path, calls, subagent, main, stream)

    assert verdict.split("|")[0] == expected, verdict


@needs_jq
def test_a_canary_a_hook_injected_cannot_prove_the_preload(tmp_path):
    subagent = claude_subagent_lines()
    subagent[1]["attachment"]["content"] = [f"PREFLIGHT for a subagent: {CANARY}"]

    verdict = judge_recorded_canary(tmp_path, [BACKGROUND_SPAWN], subagent)

    assert verdict.split("|")[0] == "INCONCLUSIVE", verdict
    assert "hook injected" in verdict


@needs_jq
def test_a_failed_preload_quotes_the_reply_rather_than_the_launch_notice(tmp_path):
    verdict = judge_recorded_canary(tmp_path, [BACKGROUND_SPAWN], claude_subagent_lines(reply="I see no marker."))

    assert verdict.startswith("FAIL|"), verdict
    assert "I see no marker." in verdict
    assert "Async agent launched" not in verdict


@needs_jq
def test_the_claude_reply_reader_prints_only_subagent_and_notification_text(tmp_path):
    case = tmp_path / "case"
    (case / "transcripts").mkdir(parents=True)
    (case / "transcripts" / "subagent-agent-a1.jsonl").write_text("".join(json.dumps(line) + "\n" for line in claude_subagent_lines(reply="sub-reply", skill_text="skill-body")), encoding="utf-8")
    (case / "transcripts" / "main-s1.jsonl").write_text(json.dumps(claude_task_notification("note-result")) + "\n", encoding="utf-8")
    (case / "stream.jsonl").write_text("".join(json.dumps(line) + "\n" for line in claude_stream_lines("stream-reply", main_text="main-text")), encoding="utf-8")

    result = run_bounded(
        [BASH, "-c", f"source '{loadable_adapter(CLAUDE_ADAPTER, tmp_path).as_posix()}'; agent_subagent_replies \"$1\"", "_", case.as_posix()],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.split("\n") == ["sub-reply", "note-result", "stream-reply", "stream-reply", ""]


CODEX_PROBE_ROLLOUTS = {
    "rollout-main.jsonl": [{"type": "session_meta", "payload": {"id": "p1", "source": "exec"}}],
    "rollout-sub.jsonl": [
        {
            "type": "session_meta",
            "payload": {
                "id": "s1",
                "source": {"subagent": {"thread_spawn": {"parent_thread_id": "p1", "depth": 1, "agent_path": "/root/probe", "agent_nickname": "N", "agent_role": "code-reviewer"}}},
            },
        }
    ],
}
CODEX_PAYLOAD_KEYS = ["cwd", "hook_event_name", "model", "permission_mode", "session_id", "tool_input", "tool_name", "tool_use_id", "transcript_path", "turn_id"]


def codex_payload(tool: str, transcript: str, agent_type: str | None = None, agent_id: bool = False, probe: bool = False) -> dict:
    """One capture-hook record as run 41348146352 wrote it."""
    keys = sorted([*CODEX_PAYLOAD_KEYS, *(["agent_id"] if agent_id else []), *(["agent_type"] if agent_type else [])])
    return {"event": "PreToolUse", "tool": tool, "keys": keys, "tool_input_keys": [], "agent_id": agent_id, "agent_type": agent_type, "probe": probe, "transcript": transcript}


CODEX_RUN9_SPAWN = {"actor": "main", "tool": "spawn_agent", "input": '{"task_name":"permission_probe","agent_type":"code-reviewer","message":"x"}', "result": '{"task_name":"/root/permission_probe"}', "error": False}
CODEX_RUN9_CALLS = [
    CODEX_RUN9_SPAWN,
    {"actor": "main", "tool": "wait_agent", "input": '{"timeout_ms":3600000}', "result": '{"message":"Wait completed.","timed_out":false}', "error": False},
    {"actor": "subagent", "tool": "send_message", "input": '{"target":"/root","message":"x"}', "result": "", "error": False},
]
CODEX_RUN9_PAYLOADS = [
    codex_payload("collaborationspawn_agent", "rollout-main.jsonl"),
    codex_payload("collaborationwait_agent", "rollout-main.jsonl"),
    codex_payload("collaborationsend_message", "rollout-sub.jsonl", "code-reviewer", agent_id=True),
]


def judge_codex_payloads(work: Path, payloads: list[dict], calls: list[dict], transcript: str = "", landed: bool = False) -> list[str]:
    """Run codex.sh's check 7 and 7b judges over a recorded case, one verdict line per check."""
    case = work / "cases" / "7-payload"
    project = work / "project"
    (case / "transcripts").mkdir(parents=True)
    project.mkdir()
    (case / "payloads.ndjson").write_text("".join(json.dumps(p) + "\n" for p in payloads), encoding="utf-8", newline="\n")
    (case / "calls.ndjson").write_text("".join(json.dumps(c) + "\n" for c in calls), encoding="utf-8", newline="\n")
    (case / "stream.jsonl").write_text(transcript, encoding="utf-8", newline="\n")
    for file_name, lines in CODEX_PROBE_ROLLOUTS.items():
        (case / "transcripts" / file_name).write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8", newline="\n")
    if landed:
        (project / READ_ONLY_PROBE).write_text("", encoding="utf-8")

    script = (
        f"source '{loadable_adapter(CODEX_ADAPTER, work).as_posix()}'; "
        f"PROJECT='{project.as_posix()}'; "
        "record() { printf '%s|%s|%s\\n' \"$2\" \"$1\" \"$3\"; }; "
        f"judge_codex_payload_checks '{case.as_posix()}'"
    )
    result = run_bounded([BASH, "-c", script], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr

    return result.stdout.splitlines()


CODEX_SUB_PROBE = {"actor": "subagent", "tool": "exec_command", "input": f'{{"cmd":"touch {READ_ONLY_PROBE}"}}', "result": "denied", "error": True}


@needs_jq
@pytest.mark.parametrize(
    ("payloads", "calls", "expected"),
    [
        pytest.param(CODEX_RUN9_PAYLOADS, CODEX_RUN9_CALLS, "PASS", id="live-run-9-send-message-from-the-subagent"),
        pytest.param(CODEX_RUN9_PAYLOADS[:2] + [codex_payload("collaborationsend_message", "rollout-sub.jsonl", agent_id=True)], CODEX_RUN9_CALLS, "FAIL", id="agent-id-without-agent-type"),
        pytest.param(CODEX_RUN9_PAYLOADS[:2] + [codex_payload("collaborationsend_message", "rollout-sub.jsonl", "code-reviewer")], CODEX_RUN9_CALLS, "FAIL", id="agent-type-without-agent-id"),
        pytest.param(CODEX_RUN9_PAYLOADS[:2] + [codex_payload("collaborationsend_message", "rollout-sub.jsonl", "default", agent_id=True)], CODEX_RUN9_CALLS, "FAIL", id="another-agent-type"),
        pytest.param(CODEX_RUN9_PAYLOADS[:2], CODEX_RUN9_CALLS, "INCONCLUSIVE", id="no-payload-from-the-subagent-rollout"),
        pytest.param(CODEX_RUN9_PAYLOADS[:2] + [codex_payload("x", "rollout-main.jsonl", "code-reviewer", agent_id=True)], CODEX_RUN9_CALLS, "INCONCLUSIVE", id="placed-by-the-rollout-not-by-agent-id"),
        pytest.param(CODEX_RUN9_PAYLOADS[:2] + [codex_payload("x", "rollout-gone.jsonl", "code-reviewer", agent_id=True)], CODEX_RUN9_CALLS, "INCONCLUSIVE", id="an-unknown-rollout-places-nothing"),
        pytest.param([], CODEX_RUN9_CALLS, "INCONCLUSIVE", id="capture-hook-never-ran"),
        pytest.param(CODEX_RUN9_PAYLOADS, [], "INCONCLUSIVE", id="never-spawned"),
    ],
)
def test_codex_check_seven_answers_from_any_payload_in_the_subagent_rollout(tmp_path, payloads, calls, expected):
    check, _ = judge_codex_payloads(tmp_path, payloads, calls)

    assert check.split("|")[:2] == [expected, "7 a Codex subagent's PreToolUse payload names its agent_type"], check


@needs_jq
def test_codex_check_seven_quotes_the_keys_of_the_payload_that_named_the_type(tmp_path):
    check, _ = judge_codex_payloads(tmp_path, CODEX_RUN9_PAYLOADS, CODEX_RUN9_CALLS)

    assert "tools collaborationsend_message" in check
    assert "agent_id present, agent_type code-reviewer" in check


@needs_jq
@pytest.mark.parametrize(
    ("payloads", "calls", "transcript", "landed", "expected"),
    [
        pytest.param(CODEX_RUN9_PAYLOADS, CODEX_RUN9_CALLS, "", False, "INCONCLUSIVE", id="live-run-9-the-probe-was-never-tried"),
        pytest.param(
            [*CODEX_RUN9_PAYLOADS, codex_payload("Bash", "rollout-sub.jsonl", "code-reviewer", agent_id=True, probe=True)],
            [*CODEX_RUN9_CALLS, CODEX_SUB_PROBE], denial("RULE_E_REASON"), False, "PASS", id="tried-and-denied-by-rule-e",
        ),
        pytest.param(
            [*CODEX_RUN9_PAYLOADS, codex_payload("Bash", "rollout-sub.jsonl", "code-reviewer", agent_id=True, probe=True)],
            [*CODEX_RUN9_CALLS, {**CODEX_SUB_PROBE, "result": "", "error": False}], "", True, "FAIL", id="tried-and-landed",
        ),
        pytest.param(
            [*CODEX_RUN9_PAYLOADS, codex_payload("Bash", "rollout-sub.jsonl", agent_id=True, probe=True)],
            [*CODEX_RUN9_CALLS, CODEX_SUB_PROBE], "", True, "FAIL", id="a-probe-payload-without-agent-type-is-no-longer-a-known-gap",
        ),
    ],
)
def test_codex_check_seven_b_reports_the_probe_on_its_own_line(tmp_path, payloads, calls, transcript, landed, expected):
    _, probe = judge_codex_payloads(tmp_path, payloads, calls, transcript, landed)

    assert probe.split("|")[:2] == [expected, "7b Rule E denies the Codex code-reviewer's probe touch"], probe


def test_the_rendered_plugin_reviewer_preloads_the_core_skill_that_carries_the_canary(tmp_path):
    # Given the marketplace the generator renders from tools/plugins.yaml
    market = tmp_path / "market"

    # When claude-code.sh renders it with this interpreter, which has the tools package, and plants the canary
    script = (
        f"source '{loadable_adapter(CLAUDE_ADAPTER, tmp_path).as_posix()}'; "
        f"LIVE_PYTHON='{Path(sys.executable).as_posix()}'; "
        f"render_plugin_marketplace '{market.as_posix()}' '{(tmp_path / 'render.log').as_posix()}' && printf '%s' \"$CANARY\""
    )
    result = run_bounded([BASH, "-c", script], capture_output=True, text=True)

    # Then
    assert result.returncode == 0, result.stderr + (tmp_path / "render.log").read_text(encoding="utf-8")
    canary = result.stdout
    assert re.fullmatch(r"preload-marker-\d+", canary)
    core_skill = (market / "plugins" / "core" / "skills" / "application-security-review" / "SKILL.md").read_text(encoding="utf-8")
    assert core_skill.rstrip().endswith(canary)
    assert canary not in (REPO_ROOT / ".agents" / "skills" / "application-security-review" / "SKILL.md").read_text(encoding="utf-8")
    preloaded = run_bounded(
        [BASH, "-c", f"source '{loadable_adapter(CLAUDE_ADAPTER, tmp_path).as_posix()}'; LIVE_PYTHON=\"$2\"; agent_preloads \"$1\" core:application-security-review && ! agent_preloads \"$1\" application-security-review && ! agent_preloads \"$1\" kicad", "_",
         (market / "plugins" / "review-and-security" / "agents" / "code-reviewer.md").as_posix(), Path(sys.executable).as_posix()],
        capture_output=True,
        text=True,
    )
    assert preloaded.returncode == 0, preloaded.stderr


@pytest.mark.parametrize(
    ("front_matter", "expected"),
    [
        pytest.param("---\nname: r\nskills:\n  - application-security-review\n---\nbody\n", 0, id="block-list"),
        pytest.param("---\nname: r\nskills: [coding-standards, application-security-review]\n---\nbody\n", 0, id="flow-list"),
        pytest.param("---\nname: r\nskills:\n- 'application-security-review'\n---\nbody\n", 0, id="quoted-unindented"),
        pytest.param("---\nname: r\nskills:\n  - application-security-review-extra\n---\nbody\n", 1, id="longer-name"),
        pytest.param("---\nname: r\ndescription: lists skills\n---\nskills:\n  - application-security-review\n", 1, id="only-in-the-body"),
        pytest.param("name: r\nskills:\n  - application-security-review\n", 1, id="no-front-matter"),
        pytest.param("---\nskills: [unclosed\n---\n", 1, id="malformed"),
    ],
)
def test_agent_preloads_reads_the_front_matter_as_yaml(tmp_path, front_matter, expected):
    agent = tmp_path / "agent.md"
    agent.write_text(front_matter, encoding="utf-8", newline="\n")

    result = run_bounded(
        [BASH, "-c", f"source '{loadable_adapter(CLAUDE_ADAPTER, tmp_path).as_posix()}'; LIVE_PYTHON=\"$2\"; agent_preloads \"$1\" application-security-review", "_",
         agent.as_posix(), Path(sys.executable).as_posix()],
        capture_output=True,
        text=True,
    )

    assert result.returncode == expected, result.stderr
    assert "Traceback" not in result.stderr


def test_agent_preloads_reports_a_missing_file_as_not_preloaded(tmp_path):
    result = run_bounded(
        [BASH, "-c", f"source '{loadable_adapter(CLAUDE_ADAPTER, tmp_path).as_posix()}'; LIVE_PYTHON=\"$2\"; agent_preloads \"$1\" application-security-review", "_",
         (tmp_path / "gone.md").as_posix(), Path(sys.executable).as_posix()],
        capture_output=True,
        text=True,
    )

    assert (result.returncode, "Traceback" in result.stderr) == (1, False)


def test_the_gate_only_project_takes_only_paths_the_readme_gate_only_import_names():
    # Given the pathspec of the gate-only import in README.md, "The gate beside the plugins"
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split("#### The gate beside the plugins", 1)[1].split("\n---\n", 1)[0]
    command = next(line for line in section.splitlines() if line.startswith("git checkout agent-standards/master -- "))
    pathspec = set(shlex.split(command.split(" -- ", 1)[1]))
    declared = re.search(r"^readonly GATE_ONLY_PATHS=\(([^)]*)\)$", CLAUDE_ADAPTER.read_text(encoding="utf-8"), re.MULTILINE)

    # When
    assert declared is not None
    gate_only_paths = set(shlex.split(declared.group(1)))

    # Then
    assert gate_only_paths
    assert gate_only_paths <= pathspec, gate_only_paths - pathspec


def loadable_adapter(adapter_path: Path, directory: Path) -> Path:
    """An agent script with lib.sh pointed at the checkout and the final live_main call removed."""
    adapter = adapter_path.read_text(encoding="utf-8")
    adapter = adapter.replace('"$(dirname "${BASH_SOURCE[0]}")/lib.sh"', f"'{LIB.as_posix()}'")
    adapter = adapter.replace('"$(dirname "${BASH_SOURCE[0]}")/opencode-family.sh"', f"'{(LIB.parent / 'opencode-family.sh').as_posix()}'")
    adapter = adapter.replace('\nlive_main "$@"\n', "\n")
    loadable = directory / f"{adapter_path.stem}-loadable.sh"
    loadable.write_text(adapter, encoding="utf-8", newline="\n")

    return loadable


def test_the_codex_capture_hook_lands_in_codex_home_as_a_pre_tool_use_hook(tmp_path):
    # Given the throwaway CODEX_HOME config agent_configure writes, which ends in a projects table
    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "config.toml").write_text('model = "m"\n\n[projects."/work/project"]\ntrust_level = "trusted"\n', encoding="utf-8")

    # When
    script = (
        f"source '{loadable_adapter(CODEX_ADAPTER, tmp_path).as_posix()}'; "
        f"WORK='{tmp_path.as_posix()}'; CODEX_HOME='{home.as_posix()}'; codex_install_payload_capture"
    )
    result = run_bounded([BASH, "-c", script], capture_output=True, text=True)

    # Then
    assert result.returncode == 0, result.stderr
    config = tomllib.loads((home / "config.toml").read_text(encoding="utf-8"))
    assert config["projects"]["/work/project"]["trust_level"] == "trusted"
    (hook,) = config["hooks"]["PreToolUse"]
    assert "matcher" not in hook
    assert hook["hooks"][0]["command"] == f"python3 -I -S {tmp_path.as_posix()}/payload-capture.py {tmp_path.as_posix()}/payload-capture.ndjson {READ_ONLY_PROBE}"
    assert (tmp_path / "payload-capture.py").is_file()


def test_run_suite_runs_the_agent_checks_after_the_shared_six():
    stubs = "; ".join(
        f"{name}() {{ printf '%s ' {name}; }}"
        for name in (
            "health_check", "record", "install_agent", "prepare_workspace", "prepare_project", "agent_configure",
            "test_gate_blocks_main_thread", "test_subagent_writes_file", "test_skill_is_loaded",
            "test_reminder_reaches_model", "test_mcp_server_answers", "agent_extra_tests", "summary",
        )
    )

    result = run_lib("requesty", f"HEALTH_FORMAT=chat; {stubs}; section() {{ :; }}; run_suite")

    assert result.returncode == 0, result.stderr
    assert result.stdout.split()[-3:] == ["test_mcp_server_answers", "agent_extra_tests", "summary"]


@pytest.mark.parametrize("adapter", [CLAUDE_ADAPTER, CODEX_ADAPTER])
def test_the_claude_code_and_codex_scripts_define_their_own_checks(tmp_path, adapter):
    result = run_bounded([BASH, "-c", f"source '{loadable_adapter(adapter, tmp_path).as_posix()}'; declare -F agent_extra_tests"], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr


def test_the_claude_code_job_installs_the_tooling_the_plugin_render_needs():
    # Given
    steps = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["live"]["steps"]
    setup = next(step for step in steps if str(step.get("uses", "")).startswith("actions/setup-python@"))
    install = next(step for step in steps if "pip install ./tools" in str(step.get("run", "")))
    run_agent = next(index for index, step in enumerate(steps) if "${{ matrix.agent }}.sh run" in str(step.get("run", "")))

    # Then
    assert re.fullmatch(r"actions/setup-python@[0-9a-f]{40}", setup["uses"])
    for step in (setup, install):
        assert step["if"] == "matrix.agent == 'claude-code'"
        assert steps.index(step) < run_agent


@pytest.mark.parametrize("install", ["codex_install_payload_capture", "claude_install_payload_capture"])
def test_a_captured_case_keeps_what_the_installed_hook_recorded(tmp_path, install):
    # Given each agent script's install step, and a case whose agent call fires the hook once
    adapter = CODEX_ADAPTER if install.startswith("codex") else CLAUDE_ADAPTER
    home = tmp_path / "home"
    home.mkdir()
    (home / "config.toml").write_text('model = "m"\n', encoding="utf-8")
    (home / "settings.json").write_text("{}\n", encoding="utf-8")
    script = (
        f"set -euo pipefail; source '{loadable_adapter(adapter, tmp_path).as_posix()}'; "
        f"WORK='{tmp_path.as_posix()}'; CASES='{(tmp_path / 'cases').as_posix()}'; "
        f"CODEX_HOME='{home.as_posix()}'; PLUGIN_CONFIG_DIR='{home.as_posix()}'; "
        "run_case() { mkdir -p \"${CASES}/$1\"; printf '%s\\n' '{\"probe\": true}' >> \"$PAYLOAD_CAPTURE\"; }; "
        f"{install}; run_captured_case 7-payload prompt"
    )

    # When
    result = run_bounded([BASH, "-c", script], capture_output=True, text=True)

    # Then
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "cases" / "7-payload" / "payloads.ndjson").read_text(encoding="utf-8") == '{"probe": true}\n'


# --- Checks 8 and 9: the plugin session, run against a stand-in claude binary ---

# Stands in for `claude plugin`: records where and how it ran, and installs from the
# marketplace it was given the cache layout Claude Code 2.1.314 writes, review-and-security
# and its core dependency, leaving out FAKE_DROP when that is set.
FAKE_CLAUDE = r"""#!/usr/bin/env bash
set -euo pipefail
printf '%s|%s|%s|%s\n' "$PWD" "$(readlink "/proc/$$/fd/0" || true)" "$(ps -o comm= -p "$PPID" | tr -d ' ')" "$*" >> "$FAKE_CLAUDE_LOG"
case "$1 $2" in
  "plugin marketplace")
    printf '%s' "$4" > "${CLAUDE_CONFIG_DIR}/fake-market"
    ;;
  "plugin install")
    market="$(cat "${CLAUDE_CONFIG_DIR}/fake-market")"
    for plugin in "${3%@*}" core; do
      mkdir -p "${CLAUDE_CONFIG_DIR}/plugins/cache/m/${plugin}/1.0.0"
      cp -R "${market}/plugins/${plugin}/." "${CLAUDE_CONFIG_DIR}/plugins/cache/m/${plugin}/1.0.0/"
    done
    if [[ -n "${FAKE_DROP:-}" ]]; then
      rm -f "${CLAUDE_CONFIG_DIR}"/plugins/cache/m/*/1.0.0/${FAKE_DROP}
    fi
    printf '{"enabledPlugins": {}}\n' > "${CLAUDE_CONFIG_DIR}/settings.json"
    ;;
esac
"""

needs_linux_proc = pytest.mark.skipif(not Path("/proc/self/fd/0").exists() or shutil.which("ps") is None, reason="the stand-in reads /proc and ps")


def run_plugin_checks(tmp_path: Path, drop: str = "", setup: str = "") -> tuple[subprocess.CompletedProcess, Path, list[str]]:
    """Run agent_extra_tests with the stand-in claude and the two checks stubbed to print what they would run in."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "claude").write_text(FAKE_CLAUDE, encoding="utf-8", newline="\n")
    (bin_dir / "claude").chmod(0o755)
    work = tmp_path / "work"
    (work / "cases").mkdir(parents=True, exist_ok=True)
    log = tmp_path / "claude.log"
    script = (
        f"source '{loadable_adapter(CLAUDE_ADAPTER, tmp_path).as_posix()}'; "
        f"WORK='{work.as_posix()}'; CASES='{(work / 'cases').as_posix()}'; PROJECT=main-project; export CLAUDE_CONFIG_DIR=main-config; "
        f"LIVE_PYTHON='{Path(sys.executable).as_posix()}'; "
        "section() { :; }; record() { printf 'record|%s|%s|%s\\n' \"$1\" \"$2\" \"$3\"; }; "
        "prepare_gate_only_project() { mkdir -p \"$1\"; }; "
        "test_plugin_subagent_type_reaches_the_gate() { printf 'ran 8|%s|%s\\n' \"$PROJECT\" \"$CLAUDE_CONFIG_DIR\"; }; "
        "test_plugin_subagent_preloads_a_core_skill() { printf 'ran 9|%s\\n' \"$CANARY\"; }; "
        f"{setup}"
        "agent_extra_tests; printf 'after|%s|%s\\n' \"$PROJECT\" \"$CLAUDE_CONFIG_DIR\""
    )
    env = {**os.environ, "PATH": f"{bin_dir.as_posix()}{os.pathsep}{os.environ['PATH']}", "FAKE_CLAUDE_LOG": log.as_posix(), "FAKE_DROP": drop}
    result = run_bounded([BASH, "-c", script], capture_output=True, text=True, env=env, timeout=120)
    calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []

    return result, work, calls


@needs_jq
@needs_linux_proc
def test_both_plugin_checks_run_in_the_plugin_session_and_the_main_session_comes_back(tmp_path):
    result, work, _ = run_plugin_checks(tmp_path)

    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[0] == f"ran 8|{(work / 'plugin-project').as_posix()}|{(work / 'claude-plugin-config').as_posix()}"
    assert re.fullmatch(r"ran 9\|preload-marker-\d+", lines[1])
    assert lines[2] == "after|main-project|main-config"
    settings = json.loads((work / "claude-plugin-config" / "settings.json").read_text(encoding="utf-8"))
    assert settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"].startswith("python3 -I -S ")


@needs_jq
@needs_linux_proc
def test_a_missing_canary_fails_check_nine_only(tmp_path):
    # Given an install whose core skill lost the planted canary
    result, work, _ = run_plugin_checks(tmp_path, drop="skills/application-security-review/SKILL.md")

    # Then check 8 still runs, with the capture hook and the gate-only project already in place
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[0].startswith("ran 8|")
    assert lines[1].startswith(f"record|9 {PLUGIN_AGENT} preloads application-security-review from core|FAIL|")
    assert "canary" in lines[1]
    assert not any(line.startswith("ran 9") for line in lines)
    assert (work / "plugin-project").is_dir()
    assert "hooks" in json.loads((work / "claude-plugin-config" / "settings.json").read_text(encoding="utf-8"))


@needs_jq
@needs_linux_proc
def test_a_missing_plugin_agent_blocks_both_checks(tmp_path):
    result, _, _ = run_plugin_checks(tmp_path, drop="agents/code-reviewer.md")

    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert [line.split("|")[:3] for line in lines[:2]] == [
        ["record", f"8 the gate sees {PLUGIN_AGENT} and denies its touch", "FAIL"],
        ["record", f"9 {PLUGIN_AGENT} preloads application-security-review from core", "FAIL"],
    ]
    assert not any(line.startswith("ran ") for line in lines)


@needs_jq
@needs_linux_proc
def test_the_plugin_commands_run_from_the_work_directory_bounded_and_without_stdin(tmp_path):
    _, work, calls = run_plugin_checks(tmp_path)

    assert len(calls) == 2
    for call in calls:
        cwd, stdin, parent, args = call.split("|")
        assert (cwd, stdin, parent) == (work.as_posix(), "/dev/null", "timeout")
        assert args.startswith("plugin ") and args.endswith(" --scope user")


# Stands in for `codex mcp list --json`: records where and how it ran, then lists one enabled server.
FAKE_CODEX = r"""#!/usr/bin/env bash
set -euo pipefail
printf '%s|%s|%s|%s\n' "$PWD" "$(readlink "/proc/$$/fd/0" || true)" "$(ps -o comm= -p "$PPID" | tr -d ' ')" "$*" >> "$FAKE_CODEX_LOG"
printf '[{"name": "context7", "enabled": true}, {"name": "playwright", "enabled": false}]\n'
"""


@needs_jq
@needs_linux_proc
def test_the_codex_mcp_list_runs_in_the_project_bounded_and_without_stdin(tmp_path):
    # Given a stand-in codex, and a caller whose stdin is an open pipe it could wait on
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "codex").write_text(FAKE_CODEX, encoding="utf-8", newline="\n")
    (bin_dir / "codex").chmod(0o755)
    project = tmp_path / "project"
    project.mkdir()
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    log = tmp_path / "codex.log"
    script = (
        f"source '{loadable_adapter(CODEX_ADAPTER, tmp_path).as_posix()}'; "
        f"PROJECT='{project.as_posix()}'; MCP_ARGS=(-c 'mcp_servers.playwright.enabled=false'); "
        f"agent_mcp_servers '{case_dir.as_posix()}'"
    )
    env = {**os.environ, "PATH": f"{bin_dir.as_posix()}{os.pathsep}{os.environ['PATH']}", "FAKE_CODEX_LOG": log.as_posix()}

    # When
    result = run_bounded([BASH, "-c", script], input="", capture_output=True, text=True, env=env)

    # Then
    assert result.returncode == 0, result.stderr
    assert result.stdout == "context7\tenabled\n"
    cwd, stdin, parent, args = log.read_text(encoding="utf-8").strip().split("|")
    assert (cwd, stdin, parent) == (project.as_posix(), "/dev/null", "timeout")
    assert args == "-c mcp_servers.playwright.enabled=false mcp list --json"


@needs_jq
@needs_linux_proc
def test_the_plugin_session_starts_from_nothing_left_by_an_earlier_run(tmp_path):
    # Given leftovers of an earlier run in the same LIVE_WORK
    work = tmp_path / "work"
    stale = [
        work / "marketplace" / "stale.txt",
        work / "claude-plugin-config" / "plugins" / "cache" / "old" / "stale.txt",
        work / "plugin-project" / "stale.txt",
        work / "cases" / "8-plugin-type" / "payloads.ndjson",
        work / "cases" / "9-plugin-preload" / "calls.ndjson",
    ]
    for path in stale:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("stale\n", encoding="utf-8")
    kept = work / "cases" / "1-gate" / "calls.ndjson"
    kept.parent.mkdir(parents=True)
    kept.write_text("kept\n", encoding="utf-8")

    # When the checks run again in the same work directory
    result, _, _ = run_plugin_checks(tmp_path)

    # Then
    assert result.returncode == 0, result.stderr
    assert [path for path in stale if path.exists()] == []
    assert kept.read_text(encoding="utf-8") == "kept\n"


# --- Time limits and the key scrub of the live workflow ---

def live_steps() -> list[dict]:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["live"]["steps"]


def test_every_agent_prompt_fits_the_job_time_limit():
    # Given the job limit and the per-prompt limit the run step sets
    job = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["live"]
    run_agent = next(step for step in live_steps() if "${{ matrix.agent }}.sh run" in str(step.get("run", "")))
    per_prompt = int(run_agent["env"]["LIVE_AGENT_TIMEOUT"])

    # When the busiest script, claude-code.sh, runs its five shared prompts, checks 8 and 9 and two plugin commands
    plugin_command = int(re.search(r"^readonly PLUGIN_COMMAND_TIMEOUT=(\d+)$", CLAUDE_ADAPTER.read_text(encoding="utf-8"), re.MULTILINE).group(1))
    worst = 7 * per_prompt + 2 * plugin_command

    # Then it ends before the job limit cancels it, with five minutes left for install and upload
    assert worst + 300 <= job["timeout-minutes"] * 60


def test_the_transcripts_are_scrubbed_before_upload_even_on_cancel():
    steps = live_steps()
    scrub = next(step for step in steps if str(step.get("run", "")).endswith(".sh scrub"))
    upload = next(step for step in steps if str(step.get("uses", "")).startswith("actions/upload-artifact@"))

    assert scrub["if"] == "always()"
    assert steps.index(scrub) == steps.index(upload) - 1
    assert set(scrub["env"]) == {"REQUESTY_API_KEY", "OPENAI_API_KEY", "LIVE_WORK"}
    assert scrub["env"]["LIVE_WORK"] == "${{ runner.temp }}/live-${{ matrix.agent }}"
    assert upload["if"] == f"always() && steps.{scrub['id']}.outcome == 'success'"
    assert upload["with"]["path"].startswith(scrub["env"]["LIVE_WORK"] + "/")


def test_the_scrub_subcommand_drops_every_file_that_holds_the_key(tmp_path):
    # Given a work directory where one transcript logged the key
    key = "rq-live-secret-1234567890"
    leaked = tmp_path / "cases" / "1-gate" / "stderr.log"
    clean = tmp_path / "cases" / "1-gate" / "stream.jsonl"
    leaked.parent.mkdir(parents=True)
    leaked.write_text(f"Authorization: Bearer {key}\n", encoding="utf-8")
    clean.write_text("{}\n", encoding="utf-8")

    # When
    result = run_lib("requesty", "live_main scrub", {"REQUESTY_API_KEY": key, "LIVE_WORK": tmp_path.as_posix()})

    # Then
    assert result.returncode == 0, result.stderr
    assert (leaked.exists(), clean.exists()) == (False, True)
    assert key not in result.stdout + result.stderr


def test_the_scrub_subcommand_with_no_work_directory_does_nothing(tmp_path):
    result = run_lib("requesty", "live_main scrub", {"REQUESTY_API_KEY": "k", "LIVE_WORK": (tmp_path / "never-made").as_posix()})

    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "never-made").exists()


# --- Test 2 and 4 on the shapes live run 41255837007 recorded ---
#
# Every agent's subagent read or was handed the project's AGENTS.md, which
# quotes the reminder's opening, and each adapter used to hand the judge that
# text as if a hook had injected it. The subagent context is now the hook
# output alone, so these cases hold a recorded AGENTS.md copy beside the
# injected text and expect the verdict the injected text alone deserves.

OPENCODE_ADAPTER = REPO_ROOT / "sandbox-agent" / "live" / "opencode.sh"
KILO_ADAPTER = REPO_ROOT / "sandbox-agent" / "live" / "kilo-code.sh"
AGENTS_MD_EXAMPLE = (REPO_ROOT / "AGENTS.md.example").read_text(encoding="utf-8")
CLAUDE_MAIN_REMINDER = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]


def lib_constant(name: str) -> str:
    return re.search(rf'^readonly {name}="([^"]+)"$', LIB.read_text(encoding="utf-8"), re.MULTILINE).group(1)


def test_the_project_agents_md_quotes_the_reminder_marker_so_it_must_never_count_as_hook_output():
    assert lib_constant("REMINDER_MARKER") in AGENTS_MD_EXAMPLE


def adapter_subagent_context(tmp_path: Path, adapter: Path, files: dict[str, str]) -> str:
    case = tmp_path / "case"
    (case / "transcripts").mkdir(parents=True)
    for name, content in files.items():
        target = case / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")

    result = run_bounded(
        [BASH, "-c", f"source '{loadable_adapter(adapter, tmp_path).as_posix()}'; agent_subagent_context \"$1\"", "_", case.as_posix()],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    return result.stdout


def verdict_for(tmp_path: Path, adapter: Path, files: dict[str, str]) -> str:
    context = adapter_subagent_context(tmp_path / "adapter", adapter, files)
    (tmp_path / "judge").mkdir()

    return judge_test_two(tmp_path / "judge", context)


def jsonl(*objects: dict) -> str:
    return "".join(json.dumps(item) + "\n" for item in objects)


CLAUDE_SUBAGENT_RECORD = [
    {"type": "attachment", "attachment": {"type": "hook_additional_context", "hookEvent": "SubagentStart", "hookName": "SubagentStart", "content": [canonical_subagent_reminder()]}},
    {"type": "attachment", "attachment": {"type": "instructions", "content": [{"path": "/project/AGENTS.md", "type": "Project", "content": AGENTS_MD_EXAMPLE}]}},
    {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": AGENTS_MD_EXAMPLE}]}},
]


@needs_jq
def test_claude_code_check_two_passes_on_the_recorded_subagent_that_loaded_agents_md(tmp_path):
    verdict = verdict_for(tmp_path, CLAUDE_ADAPTER, {"transcripts/subagent-agent-a1.jsonl": jsonl(*CLAUDE_SUBAGENT_RECORD)})

    assert verdict.startswith("PASS|"), verdict


@needs_jq
def test_claude_code_check_two_still_fails_a_reminder_a_hook_put_into_the_subagent(tmp_path):
    leaked = {"type": "attachment", "attachment": {"type": "hook_success", "hookEvent": "UserPromptSubmit", "content": CLAUDE_MAIN_REMINDER}}

    verdict = verdict_for(tmp_path, CLAUDE_ADAPTER, {"transcripts/subagent-agent-a1.jsonl": jsonl(*CLAUDE_SUBAGENT_RECORD, leaked)})

    assert verdict.startswith("FAIL|") and "main-thread reminder" in verdict, verdict


def codex_line(ordinal: int, role: str, text: str, message_id: str, inherited: bool = False) -> dict:
    line = {"timestamp": f"2026-11-01T00:14:{ordinal:02d}.000Z", "ordinal": ordinal, **rollout_message(role, text, message_id)}
    if inherited:
        line["metadata"] = {"client_authored": False, "inherited_user_message": True}
    return line


CODEX_MAIN_RECORD = [
    {"type": "session_meta", "ordinal": 0, "payload": {"source": "exec"}},
    codex_line(7, "user", AGENTS_MD_EXAMPLE, "msg-agents"),
    codex_line(13, "developer", canonical_reminder(), "msg-reminder"),
]
CODEX_FORK_RECORD = [
    {"type": "session_meta", "ordinal": 0, "payload": {"source": {"subagent": {"thread_spawn": {"agent_role": "docs-architect"}}}}},
    codex_line(8, "user", AGENTS_MD_EXAMPLE, "msg-agents", inherited=True),
    codex_line(12, "developer", canonical_reminder(), "msg-reminder", inherited=True),
    codex_line(33, "developer", canonical_subagent_reminder(), "msg-subagent"),
]


@needs_jq
def test_codex_check_two_passes_on_the_recorded_full_history_fork(tmp_path):
    # Given the Codex 0.166.0 fork shape: the parent's reminder replayed with its own ordinal and the inherited mark
    files = {"transcripts/rollout-main.jsonl": jsonl(*CODEX_MAIN_RECORD), "transcripts/rollout-sub.jsonl": jsonl(*CODEX_FORK_RECORD)}

    # When/Then
    assert verdict_for(tmp_path, CODEX_ADAPTER, files).startswith("PASS|")


@needs_jq
def test_codex_check_two_drops_a_replayed_parent_line_that_carries_no_inherited_mark(tmp_path):
    unmarked = [{k: v for k, v in line.items() if k != "metadata"} for line in CODEX_FORK_RECORD]
    files = {"transcripts/rollout-main.jsonl": jsonl(*CODEX_MAIN_RECORD), "transcripts/rollout-sub.jsonl": jsonl(*unmarked)}

    assert verdict_for(tmp_path, CODEX_ADAPTER, files).startswith("PASS|")


@needs_jq
def test_codex_check_two_fails_a_reminder_the_hook_injected_into_the_subagent_itself(tmp_path):
    own = codex_line(34, "developer", canonical_reminder(), "msg-own-reminder")
    files = {"transcripts/rollout-main.jsonl": jsonl(*CODEX_MAIN_RECORD), "transcripts/rollout-sub.jsonl": jsonl(*CODEX_FORK_RECORD, own)}

    verdict = verdict_for(tmp_path, CODEX_ADAPTER, files)

    assert verdict.startswith("FAIL|") and "main-thread reminder" in verdict, verdict


COPILOT_AGENT = "07f799cf-82f3-4408-b0d5-ad5787573cce"
COPILOT_SUBAGENT_RECORD = [
    {"type": "hook.end", "agentId": None, "data": {"hookType": "subagentStart", "success": True, "output": {"additionalContext": canonical_subagent_reminder()}}},
    {"type": "user.message", "agentId": COPILOT_AGENT, "data": {"content": canonical_subagent_reminder() + "\n\nCreate the note.", "transformedContent": canonical_subagent_reminder() + "\n\nCreate the note."}},
    {"type": "tool.execution_complete", "agentId": COPILOT_AGENT, "data": {"toolCallId": "c1", "success": True, "result": {"content": AGENTS_MD_EXAMPLE}}},
    {"type": "user.message", "agentId": None, "data": {"content": "Delegate this task.\n" + canonical_reminder()}},
]


@needs_jq
def test_copilot_check_two_passes_on_the_recorded_subagent_that_read_agents_md(tmp_path):
    events = jsonl(*COPILOT_SUBAGENT_RECORD)

    verdict = verdict_for(tmp_path, COPILOT_ADAPTER, {"stream.jsonl": events, "transcripts/session-events.jsonl": events})

    assert verdict.startswith("PASS|"), verdict


@needs_jq
def test_copilot_check_two_fails_a_reminder_appended_to_the_subagent_prompt(tmp_path):
    leaked = {"type": "user.message", "agentId": COPILOT_AGENT, "data": {"content": "Fix the format.\n" + canonical_reminder()}}
    events = jsonl(*COPILOT_SUBAGENT_RECORD, leaked)

    verdict = verdict_for(tmp_path, COPILOT_ADAPTER, {"stream.jsonl": events, "transcripts/session-events.jsonl": events})

    assert verdict.startswith("FAIL|") and "main-thread reminder" in verdict, verdict


def opencode_child(*parts: dict) -> str:
    return json.dumps({
        "info": {"id": "ses_child", "parentID": "ses_main"},
        "messages": [
            {"info": {"role": "user", "agent": "docs-architect"}, "parts": [{"type": "text", "text": "Create the note."}, *parts]},
            {"info": {"role": "assistant", "agent": "docs-architect"}, "parts": [{"type": "tool", "tool": "read", "state": {"output": AGENTS_MD_EXAMPLE}}, {"type": "text", "text": "Done."}]},
        ],
    })


@needs_jq
@pytest.mark.parametrize("adapter", [OPENCODE_ADAPTER, KILO_ADAPTER], ids=["opencode", "kilo-code"])
def test_opencode_family_check_two_passes_when_the_plugin_added_the_subagent_text(tmp_path, adapter):
    part = {"type": "text", "synthetic": True, "text": canonical_subagent_reminder()}

    verdict = verdict_for(tmp_path, adapter, {"transcripts/subagent-ses_child.json": opencode_child(part)})

    assert verdict.startswith("PASS|"), verdict


@needs_jq
@pytest.mark.parametrize("adapter", [OPENCODE_ADAPTER, KILO_ADAPTER], ids=["opencode", "kilo-code"])
def test_opencode_family_check_two_fails_the_recorded_child_session_with_no_subagent_text(tmp_path, adapter):
    # Given the run 41255837007 child session: the task prompt alone, then a tool result holding AGENTS.md
    verdict = verdict_for(tmp_path, adapter, {"transcripts/subagent-ses_child.json": opencode_child()})

    assert verdict.startswith("FAIL|") and "PREFLIGHT for a subagent:" in verdict, verdict


def judge_test_four(tmp_path: Path, adapter: Path, main_session: dict) -> str:
    """Run test_reminder_reaches_model over one exported main session, "{nonce}" replaced by the case's nonce."""
    cases = tmp_path / "cases"
    (cases / "4-reminder" / "transcripts").mkdir(parents=True)
    template = tmp_path / "main-session.json"
    template.write_text(json.dumps(main_session), encoding="utf-8")
    exported = cases / "4-reminder" / "transcripts" / "main-ses_main.json"
    script = (
        f"source '{loadable_adapter(adapter, tmp_path).as_posix()}'; "
        f"CASES='{cases.as_posix()}'; "
        f"run_case() {{ local n; n=\"$(grep -o 'live-nonce-[0-9]*' <<< \"$2\")\"; "
        f"sed \"s/{{nonce}}/${{n}}/g\" '{template.as_posix()}' > '{exported.as_posix()}'; }}; "
        "record() { printf '%s|%s' \"$2\" \"$3\"; }; "
        "test_reminder_reaches_model"
    )
    result = run_bounded([BASH, "-c", script], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr

    return result.stdout


@needs_jq
@pytest.mark.parametrize("adapter", [OPENCODE_ADAPTER, KILO_ADAPTER], ids=["opencode", "kilo-code"])
def test_opencode_family_check_four_fails_when_no_reminder_was_injected(tmp_path, adapter):
    # Given the run 41255837007 main session, plus a reply that echoes the AGENTS.md wording
    echo = "I will name the skills and subagents that own this task and invoke them."
    session = {"messages": [
        {"info": {"role": "user"}, "parts": [{"type": "text", "text": "Reply with ready. {nonce}"}]},
        {"info": {"role": "assistant"}, "parts": [{"type": "text", "text": echo}]},
    ]}

    verdict = judge_test_four(tmp_path, adapter, session)

    assert verdict.startswith("FAIL|"), verdict


@needs_jq
@pytest.mark.parametrize("adapter", [OPENCODE_ADAPTER, KILO_ADAPTER], ids=["opencode", "kilo-code"])
def test_opencode_family_check_four_passes_on_a_reminder_part_injected_on_the_nonce_prompt(tmp_path, adapter):
    part = {"type": "text", "synthetic": True, "text": canonical_reminder()}
    session = {"messages": [{"info": {"role": "user"}, "parts": [{"type": "text", "text": "Reply. {nonce}"}, part]}]}

    assert judge_test_four(tmp_path, adapter, session).startswith("PASS|")


@needs_jq
@pytest.mark.parametrize(
    "parts",
    [
        [{"type": "text", "text": "Reply. {nonce} " + canonical_reminder()}],
        [{"type": "text", "text": "Reply. {nonce}"}, {"type": "text", "synthetic": False, "text": canonical_reminder()}],
    ],
    ids=["typed-in-the-prompt", "not-synthetic"],
)
def test_opencode_family_check_four_counts_only_an_injected_part(tmp_path, parts):
    session = {"messages": [{"info": {"role": "user"}, "parts": parts}]}

    assert judge_test_four(tmp_path, OPENCODE_ADAPTER, session).startswith("FAIL|")


@needs_jq
def test_opencode_family_check_four_ignores_a_reminder_on_another_prompt(tmp_path):
    # Given the reminder injected on an earlier prompt only, not on the one carrying this case's nonce
    part = {"type": "text", "synthetic": True, "text": canonical_reminder()}
    session = {"messages": [
        {"info": {"role": "user"}, "parts": [{"type": "text", "text": "An earlier prompt."}, part]},
        {"info": {"role": "user"}, "parts": [{"type": "text", "text": "Reply. {nonce}"}]},
    ]}

    assert judge_test_four(tmp_path, OPENCODE_ADAPTER, session).startswith("FAIL|")


def test_the_probe_prompt_tells_the_subagent_to_make_the_call_rather_than_predict_it():
    # Given the Codex run 41255837007 code-reviewer, which answered "Denied" with no tool call
    result = run_bounded([BASH, "-c", f"source '{LIB.as_posix()}'; read_only_probe_prompt code-reviewer"], capture_output=True, text=True)

    assert "do not predict the answer: make the call" in result.stdout
