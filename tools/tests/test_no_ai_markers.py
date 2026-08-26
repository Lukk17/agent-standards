"""Tests for the formatting hook at .agents/hooks/no_ai_markers_check.py.

Driven as a subprocess, because the hook contract is the process contract. The
default mode takes a Stop payload on stdin against a synthetic JSONL transcript
and answers with a decision on stdout at exit 0. The --text mode takes raw prose
on stdin and answers with a reason on stderr at exit 2.
"""

import json
import subprocess
import sys

import pytest

from tests.conftest import NO_AI_MARKERS_HOOK

EM_DASH = "—"
EN_DASH = "–"


def transcript(tmp_path, *entries):
    path = tmp_path / "transcript.jsonl"
    path.write_text(
        "\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8"
    )

    return path


def assistant(text):
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }


def run(payload):
    result = subprocess.run(
        [sys.executable, str(NO_AI_MARKERS_HOOK)],
        input=json.dumps(payload) if not isinstance(payload, str) else payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    return result.returncode, result.stdout, result.stderr


def check(tmp_path, text, **extra):
    path = transcript(tmp_path, {"type": "user", "content": "go"}, assistant(text))
    payload = {"transcript_path": str(path)}
    payload.update(extra)

    return run(payload)


def test_clean_prose_passes(tmp_path):
    code, out, _err = check(tmp_path, "All good here. Nothing banned, only commas.")

    assert (code, out) == (0, "")


@pytest.mark.parametrize(
    "text,label",
    [
        ("A sentence " + EM_DASH + " with a long dash.", "em dash"),
        ("Range 3" + EN_DASH + "5 items.", "en dash"),
        ("First clause; second clause.", "semicolon"),
        ("This is **bold** text.", "bold"),
    ],
)
def test_banned_markers_block(tmp_path, text, label):
    code, out, _err = check(tmp_path, text)

    assert code == 0

    decision = json.loads(out)

    assert decision["decision"] == "block"
    assert label in decision["reason"]


def test_all_markers_are_reported_together(tmp_path):
    text = "One " + EM_DASH + " two " + EN_DASH + " three; **four**."
    _code, out, _err = check(tmp_path, text)

    reason = json.loads(out)["reason"]

    for label in ("em dash", "en dash", "semicolon", "bold"):
        assert label in reason


def test_fenced_code_is_ignored(tmp_path):
    text = "Clean prose.\n\n```python\nx = 1; y = 2  " + EM_DASH + "\n```\n\nStill clean."
    code, out, _err = check(tmp_path, text)

    assert (code, out) == (0, "")


def test_tilde_fenced_code_is_ignored(tmp_path):
    text = "Clean prose.\n\n~~~sh\necho a; echo b\n~~~\n\nStill clean."
    code, out, _err = check(tmp_path, text)

    assert (code, out) == (0, "")


def test_nested_four_backtick_fence_is_ignored(tmp_path):
    text = "Prose.\n\n````md\n```sh\necho a; echo b\n```\n````\n\nMore prose."
    code, out, _err = check(tmp_path, text)

    assert (code, out) == (0, "")


def test_inline_code_is_ignored(tmp_path):
    code, out, _err = check(tmp_path, "Run `a; b` and ``c; d`` now.")

    assert (code, out) == (0, "")


def test_semicolon_inside_a_link_target_is_ignored(tmp_path):
    text = "See [the docs](https://example.com/x?a=1;b=2) for details."
    code, out, _err = check(tmp_path, text)

    assert (code, out) == (0, "")


def test_semicolon_inside_a_bare_url_is_ignored(tmp_path):
    text = "See https://example.com/x?a=1;b=2 for details."
    code, out, _err = check(tmp_path, text)

    assert (code, out) == (0, "")


def test_tool_only_final_turn_falls_back_to_the_last_prose(tmp_path):
    path = transcript(
        tmp_path,
        assistant("Prose with a semicolon; here."),
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [{"type": "tool_use", "name": "Bash", "input": {}}],
            },
        },
    )

    code, out, _err = run({"transcript_path": str(path)})

    assert code == 0
    assert json.loads(out)["decision"] == "block"


def test_string_content_is_understood(tmp_path):
    path = transcript(
        tmp_path, {"role": "assistant", "content": "One clause; another clause."}
    )

    _code, out, _err = run({"transcript_path": str(path)})

    assert json.loads(out)["decision"] == "block"


def test_stop_hook_active_short_circuits(tmp_path):
    code, out, _err = check(tmp_path, "Bad; prose.", stop_hook_active=True)

    assert (code, out) == (0, "")


@pytest.mark.parametrize(
    "payload",
    [
        "",
        "not json",
        "[]",
        json.dumps({}),
        json.dumps({"transcript_path": ""}),
        json.dumps({"transcript_path": "does/not/exist.jsonl"}),
        json.dumps({"transcript_path": 42}),
    ],
)
def test_malformed_payloads_fail_open(payload):
    code, out, err = run(payload)

    assert (code, out, err) == (0, "", "")


def test_unparsable_transcript_lines_are_skipped(tmp_path):
    path = tmp_path / "transcript.jsonl"
    path.write_text(
        "garbage\n" + json.dumps(assistant("Bad; prose.")) + "\nmore garbage\n",
        encoding="utf-8",
    )

    _code, out, _err = run({"transcript_path": str(path)})

    assert json.loads(out)["decision"] == "block"


def test_transcript_without_assistant_text_passes(tmp_path):
    path = transcript(tmp_path, {"type": "user", "content": "hello; there"})

    code, out, _err = run({"transcript_path": str(path)})

    assert (code, out) == (0, "")


def run_text(prose):
    result = subprocess.run(
        [sys.executable, str(NO_AI_MARKERS_HOOK), "--text"],
        input=prose,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    return result.returncode, result.stdout, result.stderr


def test_text_mode_clean_prose_passes():
    code, out, err = run_text("All good here. Nothing banned, only commas.")

    assert (code, out, err) == (0, "", "")


def test_text_mode_empty_input_passes():
    code, out, err = run_text("")

    assert (code, out, err) == (0, "", "")


@pytest.mark.parametrize(
    "prose,label",
    [
        ("A sentence " + EM_DASH + " with a long dash.", "em dash"),
        ("Range 3" + EN_DASH + "5 items.", "en dash"),
        ("First clause; second clause.", "semicolon"),
        ("This is **bold** text.", "bold"),
    ],
)
def test_text_mode_banned_markers_exit_two(prose, label):
    code, out, err = run_text(prose)

    assert (code, out) == (2, "")
    assert label in err


def test_text_mode_reason_asks_for_a_rewrite():
    _code, _out, err = run_text("First clause; second clause.")

    assert "Rewrite the whole reply" in err


def test_text_mode_ignores_a_semicolon_in_a_fenced_block():
    prose = "Clean prose.\n\n```sh\necho a; echo b\n```\n\nStill clean."
    code, out, err = run_text(prose)

    assert (code, out, err) == (0, "", "")


def test_text_mode_catches_a_semicolon_outside_a_fenced_block():
    prose = "```sh\necho a\n```\n\nOne clause; another clause."
    code, _out, err = run_text(prose)

    assert code == 2
    assert "semicolon" in err
