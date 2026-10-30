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
COPILOT_TEST_TWO = (
    "SPAWN_TOOL_RE='^task$'; WRITE_TOOL_RE='^(create|edit|apply_patch|bash)$'; "
    "SUBAGENT_NO_WRITE_MARKER='CRITICAL: Do NOT write output to files'; "
)


@needs_jq
def test_a_subagent_the_cli_told_not_to_write_is_a_known_gap(tmp_path):
    # Given the recorded test 2 case: the subagent started, never tried to write, under the CLI's no-write block
    transcript = json.dumps(COPILOT_SUBAGENT_SYSTEM_EVENT) + "\n"

    # When
    verdict = judge_test_two_from_calls(tmp_path, [COPILOT_TASK_CALL], COPILOT_TEST_TWO, transcript)

    # Then
    assert verdict.startswith("KNOWN-GAP|")
    assert "Do NOT write output to files" in verdict


@needs_jq
def test_a_subagent_write_that_failed_is_still_a_failure_under_the_no_write_block(tmp_path):
    # Given the same case, but the subagent did try apply_patch and the call failed
    transcript = json.dumps(COPILOT_SUBAGENT_SYSTEM_EVENT) + "\n"
    failed_write = {"actor": "subagent", "tool": "apply_patch", "input": "*** Add File: live-probe/subagent-note.md", "result": "denied", "error": True}

    # When
    verdict = judge_test_two_from_calls(tmp_path, [COPILOT_TASK_CALL, failed_write], COPILOT_TEST_TWO, transcript)

    # Then
    assert verdict.startswith("FAIL|")


@needs_jq
def test_a_missing_file_without_the_no_write_block_is_still_a_failure(tmp_path):
    # Given the recorded calls but a transcript that never carried the CLI's no-write block
    transcript = json.dumps({"type": "system.message", "data": {"content": "You write the documentation."}}) + "\n"

    # When
    verdict = judge_test_two_from_calls(tmp_path, [COPILOT_TASK_CALL], COPILOT_TEST_TWO, transcript)

    # Then
    assert verdict.startswith("FAIL|")
    assert "docs-architect was started" in verdict


def test_the_copilot_adapter_names_the_no_write_block_the_cli_recorded():
    adapter = COPILOT_ADAPTER.read_text(encoding="utf-8")
    match = re.search(r"^readonly SUBAGENT_NO_WRITE_MARKER='([^']+)'$", adapter, re.MULTILINE)

    assert match is not None
    assert match.group(1) in COPILOT_SUBAGENT_PROMPT_TAIL


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
        result = run_bounded(["python3", "-S", "-E", str(script), str(log), READ_ONLY_PROBE], input=stdin, capture_output=True, text=True)
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
    }
    assert (spawned["agent_id"], spawned["agent_type"], spawned["probe"]) == (False, None, False)
    assert "touch" not in (tmp_path / "capture.ndjson").read_text(encoding="utf-8")


@pytest.mark.skipif(shutil.which("python3") is None, reason="the hook runs python3")
def test_the_capture_hook_allows_a_payload_it_cannot_read(tmp_path):
    assert capture(tmp_path, ["not json", "[1]"]) == [{"type": "NoneType"}, {"type": "list"}]


def test_the_capture_hook_command_refuses_a_work_directory_it_would_have_to_quote(tmp_path):
    work = tmp_path / "it's here"
    work.mkdir()

    result = run_bounded([BASH, "-c", f"source '{LIB.as_posix()}'; WORK=\"$1\"; install_payload_capture", "_", work.as_posix()], capture_output=True, text=True)

    assert (result.returncode, result.stdout) == (2, "")


def judge_read_only(work: Path, payloads: list[dict], calls: list[dict], transcript: str = "", landed: bool = False, missing_verdict: str = "KNOWN-GAP") -> str:
    """Run judge_read_only_probe over a recorded case with the real count_calls and gate markers."""
    case = work / "cases" / "8-plugin-type"
    project = work / "project"
    (case / "transcripts").mkdir(parents=True)
    project.mkdir()
    (case / "payloads.ndjson").write_text("".join(json.dumps(p) + "\n" for p in payloads), encoding="utf-8", newline="\n")
    (case / "calls.ndjson").write_text("".join(json.dumps(c) + "\n" for c in calls), encoding="utf-8", newline="\n")
    (case / "transcripts" / "stream.jsonl").write_text(transcript, encoding="utf-8", newline="\n")
    if landed:
        (project / READ_ONLY_PROBE).write_text("", encoding="utf-8")

    script = (
        f"source '{LIB.as_posix()}'; "
        f"AGENT_LABEL=test; PROJECT='{project.as_posix()}'; "
        "SPAWN_TOOL_RE='^(Task|Agent)$'; WRITE_TOOL_RE='^(Write|Edit|Bash)$'; "
        "record() { printf '%s|%s' \"$2\" \"$3\"; }; "
        f"judge_read_only_probe 'n' '{case.as_posix()}' '{PLUGIN_AGENT}' '{missing_verdict}'"
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
    ],
)
def test_the_read_only_probe_verdict(tmp_path, payloads, calls, transcript, landed, missing_verdict, expected):
    verdict = judge_read_only(tmp_path, payloads, calls, transcript, landed, missing_verdict)

    assert verdict.split("|")[0] == expected, verdict


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
        f"judge_preloaded_canary 'n' '{case.as_posix()}' '{PLUGIN_AGENT}' security-review live-canary-123"
    )
    result = run_bounded([BASH, "-c", script], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr

    return result.stdout.split("|")[0]


@needs_jq
@pytest.mark.parametrize(
    ("calls", "context", "expected"),
    [
        pytest.param([{**SPAWN, "result": "live-canary-123"}], "", "PASS", id="repeated"),
        pytest.param([SPAWN], '{"attachment":"live-canary-123"}', "PASS", id="in-the-recorded-context"),
        pytest.param(
            [{**SPAWN, "result": "live-canary-123"}, {"actor": "subagent", "tool": "Skill", "input": '{"skill":"core:security-review"}', "result": "", "error": False}],
            "",
            "INCONCLUSIVE",
            id="loaded-at-run-time",
        ),
        pytest.param(
            [{**SPAWN, "result": "live-canary-123"}, {"actor": "subagent", "tool": "Read", "input": '{"file_path":"/c/core/1/skills/security-review/SKILL.md"}', "result": "", "error": False}],
            "",
            "INCONCLUSIVE",
            id="read-at-run-time",
        ),
        pytest.param([{**SPAWN, "result": "I have no canary."}], "", "FAIL", id="missing"),
        pytest.param([], "", "INCONCLUSIVE", id="never-spawned"),
    ],
)
def test_the_preload_canary_verdict(tmp_path, calls, context, expected):
    assert judge_canary(tmp_path, calls, context) == expected


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
    assert re.fullmatch(r"live-canary-\d+", canary)
    core_skill = (market / "plugins" / "core" / "skills" / "security-review" / "SKILL.md").read_text(encoding="utf-8")
    assert core_skill.rstrip().endswith(canary)
    assert canary not in (REPO_ROOT / ".agents" / "skills" / "security-review" / "SKILL.md").read_text(encoding="utf-8")
    preloaded = run_bounded(
        [BASH, "-c", f"source '{loadable_adapter(CLAUDE_ADAPTER, tmp_path).as_posix()}'; agent_preloads \"$1\" security-review && ! agent_preloads \"$1\" kicad", "_",
         (market / "plugins" / "review-and-security" / "agents" / "code-reviewer.md").as_posix()],
        capture_output=True,
        text=True,
    )
    assert preloaded.returncode == 0, preloaded.stderr


def loadable_adapter(adapter_path: Path, directory: Path) -> Path:
    """An agent script with lib.sh pointed at the checkout and the final live_main call removed."""
    adapter = adapter_path.read_text(encoding="utf-8")
    adapter = adapter.replace('"$(dirname "${BASH_SOURCE[0]}")/lib.sh"', f"'{LIB.as_posix()}'")
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
    assert hook["hooks"][0]["command"] == f"python3 -S -E {tmp_path.as_posix()}/payload-capture.py {tmp_path.as_posix()}/payload-capture.ndjson {READ_ONLY_PROBE}"
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
