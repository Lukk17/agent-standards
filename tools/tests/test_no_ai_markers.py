"""Tests for the formatting hook at .agents/hooks/no_ai_markers_check.py.

Driven as a subprocess, because the hook contract is the process contract. The
default mode takes a Stop or SubagentStop payload on stdin, reading the reply
from `last_assistant_message` and falling back to a synthetic JSONL transcript,
and answers with a decision on stdout at exit 0. The --text mode takes raw prose
on stdin and answers with a reason on stderr at exit 2. The --format plain mode
takes the runner envelope from docs/hooks-contract.md and answers the same way.
"""

import json
import os
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


def run_runner(payload, env=None):
    """Drive the hook the way the OpenCode and Kilo Code plugin does."""
    if isinstance(payload, str):
        stdin = payload
    else:
        stdin = json.dumps(payload, ensure_ascii=False)

    result = subprocess.run(
        [sys.executable, str(NO_AI_MARKERS_HOOK), "--format", "plain"],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, **env} if env else None,
    )

    return result.returncode, result.stdout, result.stderr


def envelope(assistant_text=""):
    """The runner envelope described in docs/hooks-contract.md."""
    return {
        "contract": 2,
        "event": "tool.execute.before",
        "tool_name": "Edit",
        "tool_input": {"file_path": "src/app.py"},
        "agent_type": "",
        "is_subagent": False,
        "assistant_text": assistant_text,
        "cwd": "",
    }


def test_runner_mode_blocks_on_the_envelope_prose():
    # Given
    payload = envelope("A sentence " + EM_DASH + " with a long dash.")

    # When
    code, out, err = run_runner(payload)

    # Then
    assert (code, out) == (2, "")
    assert "em dash" in err


def test_runner_mode_allows_clean_prose():
    # Given
    payload = envelope("All good here. Nothing banned, only commas.")

    # When
    code, out, err = run_runner(payload)

    # Then
    assert (code, out, err) == (0, "", "")


@pytest.mark.parametrize(
    "payload",
    [
        {"assistant_text": ""},
        {"assistant_text": "   "},
        {"assistant_text": None},
        {"assistant_text": ["not", "a", "string"]},
        {},
        "not json at all",
        "",
        "[1, 2, 3]",
    ],
    ids=[
        "empty",
        "whitespace",
        "null",
        "wrong-type",
        "missing-key",
        "garbage",
        "no-input",
        "not-an-object",
    ],
)
def test_runner_mode_allows_when_there_is_no_prose_to_check(payload):
    # When
    code, out, err = run_runner(payload)

    # Then
    assert (code, out, err) == (0, "", "")


def test_runner_mode_does_not_read_the_stop_payload():
    """The envelope is the only input in this mode.

    A Stop payload happens to be a JSON object too, so the mode has to key off
    assistant_text rather than guessing which shape it was handed.
    """
    # Given
    payload = {"stop_hook_active": False, "transcript_path": "/does/not/exist"}

    # When
    code, out, err = run_runner(payload)

    # Then
    assert (code, out, err) == (0, "", "")


def test_runner_mode_survives_a_hostile_stdin_encoding():
    """Every marker this hook hunts for is non-ASCII or arrives beside one.

    Text-mode stdin follows the locale or PYTHONIOENCODING. Decoding UTF-8 by
    hand is what stops the check from silently allowing on a machine whose
    console is not UTF-8.
    """
    # Given
    payload = envelope("A sentence " + EM_DASH + " with a long dash.")

    # When
    code, out, err = run_runner(payload, env={"PYTHONIOENCODING": "ascii"})

    # Then
    assert (code, out) == (2, "")
    assert "em dash" in err


# The payload field is the primary source and the transcript is the fallback,
# because Claude Code documents the transcript as not guaranteed to hold the
# final message yet when Stop fires.


def test_the_payload_field_is_read_without_any_transcript():
    # Given a Stop payload carrying the reply and naming no transcript at all
    _code, out, _err = run({"last_assistant_message": "One clause; another clause."})

    # When/Then
    assert json.loads(out)["decision"] == "block"


def test_the_payload_field_wins_over_the_transcript(tmp_path):
    # Given a transcript holding clean prose and a payload holding bad prose
    path = transcript(tmp_path, assistant("All good here, only commas."))
    payload = {
        "transcript_path": str(path),
        "last_assistant_message": "One clause; another clause.",
    }

    # When
    _code, out, _err = run(payload)

    # Then the field decides, so a stale transcript cannot mask the real reply
    assert json.loads(out)["decision"] == "block"


@pytest.mark.parametrize(
    "message",
    [None, "", "   ", 42, ["not", "a", "string"]],
    ids=["null", "empty", "whitespace", "wrong-type", "list"],
)
def test_an_unusable_payload_field_falls_back_to_the_transcript(tmp_path, message):
    # Given a payload whose field carries nothing usable
    path = transcript(tmp_path, assistant("One clause; another clause."))

    # When
    _code, out, _err = run({"transcript_path": str(path), "last_assistant_message": message})

    # Then the walk still finds the reply
    assert json.loads(out)["decision"] == "block"


def test_a_subagent_stop_reads_the_subagent_transcript_first(tmp_path):
    """On SubagentStop, transcript_path is the parent session's file.

    The subagent's own prose is in agent_transcript_path, so reading the
    parent's file would check somebody else's reply.
    """
    # Given both transcripts, only the subagent's carrying a violation
    parent = transcript(tmp_path, assistant("Parent prose, all commas."))
    child = tmp_path / "agent.jsonl"
    child.write_text(
        json.dumps(assistant("One clause; another clause.")) + "\n", encoding="utf-8"
    )

    # When
    _code, out, _err = run(
        {
            "hook_event_name": "SubagentStop",
            "transcript_path": str(parent),
            "agent_transcript_path": str(child),
        }
    )

    # Then
    assert json.loads(out)["decision"] == "block"


def test_a_missing_subagent_transcript_falls_through_to_the_session_one(tmp_path):
    parent = transcript(tmp_path, assistant("One clause; another clause."))
    payload = {
        "hook_event_name": "SubagentStop",
        "transcript_path": str(parent),
        "agent_transcript_path": str(tmp_path / "gone.jsonl"),
    }

    _code, out, _err = run(payload)

    assert json.loads(out)["decision"] == "block"


def run_stop(payload, fmt):
    """Drive the Stop mode with an explicit format, the way both CLIs wire it."""
    result = subprocess.run(
        [sys.executable, str(NO_AI_MARKERS_HOOK), "--format", fmt],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    return result.returncode, result.stdout, result.stderr


@pytest.mark.parametrize("fmt", ["claude", "codex"])
def test_the_stop_shape_is_the_same_on_both_stop_surfaces(fmt):
    """Codex documents the same field and the same decision shape as Claude Code."""
    code, out, err = run_stop({"last_assistant_message": "One clause; another."}, fmt)

    assert (code, err) == (0, "")
    assert json.loads(out)["decision"] == "block"


@pytest.mark.parametrize("fmt", ["claude", "codex"])
def test_the_stop_shape_stays_silent_on_clean_prose(fmt):
    assert run_stop({"last_assistant_message": "All good, only commas."}, fmt) == (0, "", "")


def test_an_unknown_flag_never_exits_two():
    """Two is the deny code in the plain format, so no flag may produce it."""
    result = subprocess.run(
        [sys.executable, str(NO_AI_MARKERS_HOOK), "--bogus"],
        input=json.dumps({"last_assistant_message": "All good, only commas."}),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


# Emphasis is matched as a paired delimiter in both spellings, so the markers
# that merely look like one are left alone.


@pytest.mark.parametrize(
    "prose,label",
    [
        ("This is **bold** text.", "bold"),
        ("This is __bold__ text.", "bold"),
        ("This is *italic* text.", "italic"),
        ("This is _italic_ text.", "italic"),
        ("A whole *run of several words* in italics.", "italic"),
        ("A whole __run of several words__ in bold.", "bold"),
    ],
    ids=["star-bold", "underscore-bold", "star-italic", "underscore-italic", "run", "bold-run"],
)
def test_emphasis_blocks_in_every_spelling(prose, label):
    code, out, err = run_text(prose)

    assert (code, out) == (2, "")
    assert label in err


@pytest.mark.parametrize(
    "prose",
    [
        "* item one\n* item two",
        "Compute a * b and then c * d.",
        "Call my_var_name and other_thing_here.",
        "The rate is 3 * 4 * 5 per hour.",
        "A line ending in an asterisk *",
        "Leading _ and trailing _ on their own.",
        "Covers docs/*.md and tools/*.py today.",
        "Paths like _docs/api_ and _docs/cli_ go unbackticked here.",
    ],
    ids=[
        "bullet-marker",
        "multiplication",
        "snake-case",
        "spaced-operators",
        "lone-asterisk",
        "lone-underscores",
        "unbackticked-globs",
        "unbackticked-underscore-paths",
    ],
)
def test_things_that_only_look_like_emphasis_pass(prose):
    assert run_text(prose) == (0, "", "")


def test_a_bare_dunder_name_is_bold_and_is_flagged():
    """CommonMark renders a whitespace-bounded __word__ as bold.

    A dunder written as prose really does come out bold, so the fix is the
    backticks it should have had, which the inline-code strip then honours.
    """
    code, _out, err = run_text("The __init__ method runs first.")

    assert code == 2
    assert "bold" in err

    assert run_text("The `__init__` method runs first.") == (0, "", "")


# Table rows and HTML entities are markup, not punctuation.


def test_a_table_row_is_not_prose():
    prose = "Intro line.\n\n| a; b | c &amp; d |\n| --- | --- |\n| e | f |\n\nOutro line."

    assert run_text(prose) == (0, "", "")


def test_an_html_entity_semicolon_is_not_a_semicolon():
    assert run_text("Write it as &amp; in the body text.") == (0, "", "")


@pytest.mark.parametrize(
    "entity",
    ["&amp;", "&nbsp;", "&#8212;", "&#x2014;"],
    ids=["named", "nbsp", "decimal", "hex"],
)
def test_every_entity_spelling_is_stripped(entity):
    assert run_text("An entity " + entity + " in prose.") == (0, "", "")


def test_a_real_semicolon_beside_an_entity_still_blocks():
    code, _out, err = run_text("An entity &amp; here; and a real clause after it.")

    assert code == 2
    assert "semicolon" in err


def test_a_table_row_does_not_hide_the_prose_around_it():
    prose = "| a | b |\n| --- | --- |\n\nOne clause; another clause."
    code, _out, err = run_text(prose)

    assert code == 2
    assert "semicolon" in err


def test_a_url_with_underscores_is_not_italic():
    assert run_text("See https://example.com/foo_bar_baz for details.") == (0, "", "")


def test_inline_code_hides_emphasis_markers():
    assert run_text("Use `**not bold**` and `_not italic_` literally.") == (0, "", "")


def test_a_fenced_block_hides_emphasis_markers():
    prose = "Clean prose.\n\n```md\n**bold** and _italic_\n```\n\nStill clean."

    assert run_text(prose) == (0, "", "")


def test_italic_is_reported_alongside_the_other_markers():
    _code, _out, err = run_text("One " + EM_DASH + " two; **three** and *four*.")

    for label in ("em dash", "semicolon", "bold", "italic"):
        assert label in err
