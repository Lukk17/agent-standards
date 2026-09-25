"""Tests for the project import and the verdicts of live tests 1 and 2 in sandbox-agent/live/lib.sh.

Test 1 passes only when the gate denied a main-thread write and the file is
absent. Every deny reason the gate can give counts as a denial, and a write
that landed is a failure whatever the transcript says. Test 2 passes only when
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
from pathlib import Path

import pytest

from tests.conftest import PREFLIGHT_GATE, REPO_ROOT
from tests.process_tree import run_bounded
from tests.test_prompt_reminder import canonical_reminder, canonical_subagent_reminder

LIB = REPO_ROOT / "sandbox-agent" / "live" / "lib.sh"
BASH = shutil.which("bash")
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


def judge_test_one(work: Path, transcript: str, landed: bool) -> str:
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
        "run_case() { :; }; count_calls() { printf '1'; }; record() { printf '%s' \"$2\"; }; "
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


def judge_test_two_from_calls(work: Path, calls: list[dict]) -> str:
    """Run test_subagent_writes_file over recorded calls with the real count_calls, the probe file absent."""
    cases = work / "cases"
    (cases / "2-subagent").mkdir(parents=True)
    (work / "project").mkdir()
    lines = "".join(json.dumps(call) + "\n" for call in calls)
    (cases / "2-subagent" / "calls.ndjson").write_text(lines, encoding="utf-8", newline="\n")

    script = (
        f"source '{LIB.as_posix()}'; "
        f"AGENT_LABEL=test; CASES='{cases.as_posix()}'; PROJECT='{(work / 'project').as_posix()}'; "
        "SPAWN_TOOL_RE='^spawn_agent$'; WRITE_TOOL_RE='^write$'; "
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
