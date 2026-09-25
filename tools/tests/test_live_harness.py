"""Tests for the verdicts of live tests 1 and 2 in sandbox-agent/live/lib.sh.

Test 1 passes only when the gate denied a main-thread write and the file is
absent. Every deny reason the gate can give counts as a denial, and a write
that landed is a failure whatever the transcript says. Test 2 passes only when
the subagent wrote the file and its own transcript carries the subagent text
and not the main-thread reminder.
"""

import importlib.util
import json
import re
import shutil
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
