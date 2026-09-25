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
import shutil
import sys

import pytest

from tests.conftest import NO_AI_MARKERS_HOOK, REPO_ROOT
from tests.process_tree import run_bounded

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
    result = run_bounded(
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
    result = run_bounded(
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


def test_text_mode_reason_asks_for_correction_lines_only():
    _code, _out, err = run_text("First clause; second clause.")

    assert 'each starting with "Correction:"' in err
    assert "write nothing else" in err


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

    result = run_bounded(
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
        "contract": 3,
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


@pytest.mark.parametrize("contract", [2, 4, "3", None], ids=["older", "newer", "string", "null"])
def test_runner_mode_allows_an_envelope_version_it_does_not_recognise(contract):
    # Given prose that would block under the contract this hook speaks
    payload = envelope("A sentence " + EM_DASH + " with a long dash.")
    payload["contract"] = contract

    # When
    code, out, err = run_runner(payload)

    # Then
    assert (code, out, err) == (0, "", "")


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
    result = run_bounded(
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
    result = run_bounded(
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


# The NOW line of the status block is the one bold line a reply may carry.

STATUS_BLOCK = (
    "Running: `Run containerised sandbox suite`\n"
    "\n"
    "~~DONE: Fix code review findings~~\n"
    "~~DONE: First Docker test run (2 checks failed)~~\n"
    "\n"
    "**NOW: fix the two Docker checks and rerun the suite**\n"
    "\n"
    "Next: build the live test pipeline once you answer 3.6\n"
    "Then: build the research skill once you answer 13.1\n"
    "\n"
    "Waiting on: your answers to 3.6, 10.1, 11.1, 12.1 and 13.1"
)


def test_the_status_block_now_line_is_allowed_bold():
    assert run_text("Done with the review.\n\n" + STATUS_BLOCK) == (0, "", "")


def test_several_now_lines_are_all_allowed():
    prose = "**NOW: fix the gate**\n**NOW: rerun the sandbox suite**"

    assert run_text(prose) == (0, "", "")


@pytest.mark.parametrize(
    "prose",
    [
        "This is **bold** text.\n\n" + STATUS_BLOCK,
        "Current step **NOW: fix the gate** in the middle of a sentence.",
        "**NOW: fix the gate** and more prose after it.",
        "**now: fix the gate**",
        "__NOW: fix the gate__",
        "**Next: fix the gate**",
    ],
    ids=["other-bold-beside-block", "inline-now", "now-with-trailing-prose", "lowercase", "underscore", "other-label"],
)
def test_bold_other_than_the_now_line_still_blocks(prose):
    code, _out, err = run_text(prose)

    assert code == 2
    assert "bold" in err


def test_the_now_line_is_still_checked_for_other_markers():
    code, _out, err = run_text("**NOW: fix the gate; then rerun it**")

    assert code == 2
    assert "semicolon" in err
    assert "bold in " not in err


@pytest.mark.parametrize("fmt", ["claude", "codex", "plain"])
def test_the_reason_forbids_repeating_the_reply_that_is_already_on_screen(fmt):
    """A blocked reply is already shown, so a full rewrite shows it twice."""
    if fmt == "plain":
        _code, _out, reason = run_runner(envelope("One clause; another."))
    else:
        _code, out, _err = run_stop({"last_assistant_message": "One clause; another."}, fmt)
        reason = json.loads(out)["reason"]

    assert "already on screen" in reason
    assert "do not repeat it" in reason
    assert "Rewrite the whole reply" not in reason
    assert "Output only the corrected reply" not in reason
    assert "semicolon in " in reason


# A user-level copy of the hook stays silent in a project that wires the same
# check itself, so one reply is never blocked twice with the same reason.

CLAUDE_PROJECT_WIRING = {
    "hooks": {
        "Stop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "python -S -E .agents/hooks/no_ai_markers_check.py --format claude",
                    }
                ]
            }
        ]
    }
}

CODEX_PROJECT_WIRING = (
    '[[hooks.Stop]]\n\n[[hooks.Stop.hooks]]\ntype = "command"\n'
    'command = "python -S -E .agents/hooks/no_ai_markers_check.py --format codex"\n'
)


def global_copy(tmp_path):
    """Install the hook the way docs/GLOBAL_SETUP.md does, under a home directory."""
    target = tmp_path / "home" / ".agents" / "hooks" / NO_AI_MARKERS_HOOK.name
    target.parent.mkdir(parents=True)
    shutil.copyfile(NO_AI_MARKERS_HOOK, target)

    return target


def project(tmp_path, relative=None, content=None):
    root = tmp_path / "project"
    (root / ".git").mkdir(parents=True)

    if relative:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    return root


def run_copy(script, fmt, payload, project_dir=None):
    env = {key: value for key, value in os.environ.items() if key != "CLAUDE_PROJECT_DIR"}

    if project_dir is not None:
        env["CLAUDE_PROJECT_DIR"] = str(project_dir)

    result = run_bounded(
        [sys.executable, str(script), "--format", fmt],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )

    return result.returncode, result.stdout, result.stderr


def bad_stop(cwd, **extra):
    payload = {"last_assistant_message": "One clause; another.", "cwd": str(cwd)}
    payload.update(extra)

    return payload


@pytest.mark.parametrize(
    "fmt,relative,content",
    [
        ("claude", ".claude/settings.json", json.dumps(CLAUDE_PROJECT_WIRING)),
        ("claude", ".claude/settings.local.json", json.dumps(CLAUDE_PROJECT_WIRING)),
        ("codex", ".codex/config.toml", CODEX_PROJECT_WIRING),
        ("codex", ".codex/hooks.json", json.dumps(CLAUDE_PROJECT_WIRING)),
    ],
    ids=["claude-settings", "claude-settings-local", "codex-config-toml", "codex-hooks-json"],
)
def test_a_global_copy_stays_silent_where_the_project_wires_the_check(tmp_path, fmt, relative, content):
    root = project(tmp_path, relative, content)

    assert run_copy(global_copy(tmp_path), fmt, bad_stop(root)) == (0, "", "")


def test_a_global_copy_finds_the_project_from_claude_project_dir(tmp_path):
    root = project(tmp_path, ".claude/settings.json", json.dumps(CLAUDE_PROJECT_WIRING))

    code, out, _err = run_copy(global_copy(tmp_path), "claude", bad_stop(tmp_path), project_dir=root)

    assert (code, out) == (0, "")


def test_a_global_copy_finds_the_project_root_from_a_subdirectory_cwd(tmp_path):
    root = project(tmp_path, ".codex/config.toml", CODEX_PROJECT_WIRING)
    nested = root / "src" / "pkg"
    nested.mkdir(parents=True)

    assert run_copy(global_copy(tmp_path), "codex", bad_stop(nested)) == (0, "", "")


@pytest.mark.parametrize("fmt", ["claude", "codex"])
def test_a_global_copy_checks_where_the_project_does_not_wire_the_check(tmp_path, fmt):
    root = project(tmp_path)

    _code, out, _err = run_copy(global_copy(tmp_path), fmt, bad_stop(root))

    assert json.loads(out)["decision"] == "block"


def test_a_global_copy_checks_an_event_the_project_does_not_wire(tmp_path):
    root = project(tmp_path, ".claude/settings.json", json.dumps(CLAUDE_PROJECT_WIRING))

    _code, out, _err = run_copy(
        global_copy(tmp_path), "claude", bad_stop(root, hook_event_name="SubagentStop")
    )

    assert json.loads(out)["decision"] == "block"


def test_a_global_copy_checks_where_the_project_wires_a_different_hook(tmp_path):
    other = json.loads(json.dumps(CLAUDE_PROJECT_WIRING).replace("no_ai_markers_check", "task_list_sync"))
    root = project(tmp_path, ".claude/settings.json", json.dumps(other))

    _code, out, _err = run_copy(global_copy(tmp_path), "claude", bad_stop(root))

    assert json.loads(out)["decision"] == "block"


def test_the_project_copy_always_checks_even_where_the_project_wires_it(tmp_path):
    root = project(tmp_path, ".claude/settings.json", json.dumps(CLAUDE_PROJECT_WIRING))
    own = root / ".agents" / "hooks" / NO_AI_MARKERS_HOOK.name
    own.parent.mkdir(parents=True)
    shutil.copyfile(NO_AI_MARKERS_HOOK, own)

    _code, out, _err = run_copy(own, "claude", bad_stop(root), project_dir=root)

    assert json.loads(out)["decision"] == "block"


@pytest.mark.parametrize(
    "fmt,relative,content",
    [
        ("claude", ".claude/settings.json", "{ not json, no_ai_markers_check.py"),
        ("claude", ".claude/settings.json", '["no_ai_markers_check.py"]'),
        ("codex", ".codex/config.toml", "[[hooks.Stop] no_ai_markers_check.py"),
    ],
    ids=["unparsable-json", "wrong-shape", "unparsable-toml"],
)
def test_a_global_copy_checks_when_the_project_wiring_cannot_be_read(tmp_path, fmt, relative, content):
    root = project(tmp_path, relative, content)

    _code, out, _err = run_copy(global_copy(tmp_path), fmt, bad_stop(root))

    assert json.loads(out)["decision"] == "block"


def test_a_global_copy_checks_when_the_payload_names_no_project(tmp_path):
    payload = {"last_assistant_message": "One clause; another."}

    _code, out, _err = run_copy(global_copy(tmp_path), "claude", payload)

    assert json.loads(out)["decision"] == "block"


# The mechanical fix. Claude Code shows it through MessageDisplay, OpenCode and
# Kilo Code store it through experimental.text.complete, and both entry points
# run the one function, so the same case table drives both.

ESCAPED_QUOTE = (
    'The model wrote "The plan is simple ' + EM_DASH + ' \\*\\*delegate\\*\\* the work." You would have seen...'
)

FIX_CASES = [
    (
        "escaped-markers-in-a-quote",
        ESCAPED_QUOTE,
        'The model wrote "The plan is simple, \\*\\*delegate\\*\\* the work." You would have seen...',
    ),
    ("escaped-underscores", "Write \\_name\\_ and \\*x\\* as is.", "Write \\_name\\_ and \\*x\\* as is."),
    ("escaped-marker-inside-bold", "**a \\* b**", "a \\* b"),
    ("escaped-backslash-then-italic", "A \\\\*real* one.", "A \\\\real one."),
    ("em-dash-spaced", "The plan is simple " + EM_DASH + " delegate the work.", "The plan is simple, delegate the work."),
    ("em-dash-tight", "simple" + EM_DASH + "delegate", "simple, delegate"),
    ("en-dash-spaced", "one " + EN_DASH + " two", "one, two"),
    ("paired-dashes", "The tool " + EM_DASH + " which is fast " + EM_DASH + " works.", "The tool, which is fast, works."),
    ("digit-range", "Pages 3" + EN_DASH + "5 matter.", "Pages 3-5 matter."),
    ("after-a-comma", "First, " + EM_DASH + " then", "First, then"),
    ("after-a-colon", "Note: " + EM_DASH + " this", "Note: this"),
    ("before-a-period", "It ends " + EM_DASH + ".", "It ends."),
    ("inside-parentheses", "(" + EM_DASH + " aside " + EM_DASH + ")", "(aside)"),
    ("line-start", EM_DASH + " a bullet", "a bullet"),
    ("indented-line-start", "  " + EN_DASH + " a bullet", "  a bullet"),
    ("line-end", "Wait for it " + EM_DASH, "Wait for it"),
    ("dash-run", "a " + EM_DASH + EM_DASH + " b", "a, b"),
    ("bold", "This is **bold** text.", "This is bold text."),
    ("underscore-bold", "This is __bold__ text.", "This is bold text."),
    ("italic", "An *italic* word and _another_ one.", "An italic word and another one."),
    ("bold-italic", "***both***", "both"),
    ("now-line-kept", "**NOW: fix the hook**", "**NOW: fix the hook**"),
    ("now-line-inner-dash", "**NOW: fix " + EM_DASH + " the hook**", "**NOW: fix, the hook**"),
    (
        "inline-code-untouched",
        "Run `a " + EM_DASH + " **b**` now " + EM_DASH + " please.",
        "Run `a " + EM_DASH + " **b**` now, please.",
    ),
    (
        "link-target-untouched",
        "[**docs**](https://x.io/_a_/b" + EM_DASH + "c)",
        "[docs](https://x.io/_a_/b" + EM_DASH + "c)",
    ),
    ("bare-url-untouched", "See https://x.io/_a_/ " + EM_DASH + " ok", "See https://x.io/_a_/, ok"),
    (
        "fenced-block-untouched",
        "Intro " + EM_DASH + " here.\n```py\nx = 2**3 + 4**5  # " + EM_DASH + " _n_\n```\nOutro **done**.",
        "Intro, here.\n```py\nx = 2**3 + 4**5  # " + EM_DASH + " _n_\n```\nOutro done.",
    ),
    (
        "not-emphasis",
        "* item\n2 * 3 * 4\nsnake_case_name and docs/*.md or tools/*.py",
        "* item\n2 * 3 * 4\nsnake_case_name and docs/*.md or tools/*.py",
    ),
    ("crlf", "a " + EM_DASH + " b\r\nc **d**\r\n", "a, b\r\nc d\r\n"),
    ("semicolon-untouched", "One; two.", "One; two."),
    ("table-row", "| a " + EM_DASH + " b | **c** |", "| a, b | c |"),
    ("clean", "Nothing to fix here.", "Nothing to fix here."),
]

FIX_IDS = [case[0] for case in FIX_CASES]


def run_display(payload, env=None, script=NO_AI_MARKERS_HOOK):
    """Drive the MessageDisplay mode and return what Claude Code would show."""
    result = run_bounded(
        [sys.executable, str(script), "--format", "claude", "--display"],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, **env} if env else None,
    )

    assert result.returncode == 0

    if not result.stdout:
        return payload["delta"]

    output = json.loads(result.stdout)["hookSpecificOutput"]

    assert output["hookEventName"] == "MessageDisplay"

    return output["displayContent"]


def batch(delta, index=0, final=True, message_id="m1", **extra):
    payload = {
        "hook_event_name": "MessageDisplay",
        "message_id": message_id,
        "index": index,
        "final": final,
        "delta": delta,
    }
    payload.update(extra)

    return payload


def run_text_complete(text):
    """Drive the runner's experimental.text.complete event and return the stored text."""
    payload = {"contract": 3, "event": "experimental.text.complete", "text": text, "cwd": "."}
    code, out, _err = run_runner(payload)

    assert code == 0

    return json.loads(out)["text"] if out else text


@pytest.mark.parametrize("name,text,fixed", FIX_CASES, ids=FIX_IDS)
def test_the_display_fix_rewrites_what_it_can_fix(name, text, fixed):
    assert run_display(batch(text)) == fixed


@pytest.mark.parametrize("name,text,fixed", FIX_CASES, ids=FIX_IDS)
def test_the_text_complete_fix_matches_the_display_fix(name, text, fixed):
    assert run_text_complete(text) == fixed == run_display(batch(text))


@pytest.mark.parametrize("name,text,fixed", FIX_CASES, ids=FIX_IDS)
def test_the_fix_is_idempotent(name, text, fixed):
    assert run_display(batch(fixed)) == fixed


def test_a_clean_batch_prints_nothing():
    result = run_bounded(
        [sys.executable, str(NO_AI_MARKERS_HOOK), "--format", "claude", "--display"],
        input=json.dumps(batch("Nothing to fix.\n")),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert (result.returncode, result.stdout) == (0, "")


def display_state(directory, session="s1"):
    return json.loads((directory / ("no-ai-markers-display-" + session + ".json")).read_text(encoding="utf-8"))


def test_a_fence_that_spans_batches_stays_untouched(tmp_path):
    scratch = {"scratchpad_dir": str(tmp_path), "session_id": "s1"}
    first = batch("Intro " + EM_DASH + " a\n```py\n", index=0, final=False, **scratch)
    middle = batch("x = 2**3 + 4**5 " + EM_DASH + " y\n", index=1, final=False, **scratch)
    last = batch("```\nOutro " + EM_DASH + " b", index=2, final=True, **scratch)

    shown = [run_display(first), run_display(middle), run_display(last)]

    assert shown == [
        "Intro, a\n```py\n",
        "x = 2**3 + 4**5 " + EM_DASH + " y\n",
        "```\nOutro, b",
    ]
    assert display_state(tmp_path) == {"fixed": {"m1": ["Intro " + EM_DASH + " a", "Outro " + EM_DASH + " b"]}}


def test_a_session_without_a_scratchpad_keeps_its_state_in_the_per_test_temp_directory(isolated_temp_directory):
    # Given no scratchpad and no temp override of the test's own
    payload = batch("```sh\n", index=0, final=False, session_id="isolation-probe")

    # When
    run_display(payload)

    # Then the state lands in the directory this test owns, never the machine's real temp directory
    written = sorted(path.name for path in isolated_temp_directory.rglob("no-ai-markers-*.json"))
    assert written == ["no-ai-markers-display-isolation-probe.json"]


def test_without_a_scratchpad_the_fence_state_lives_in_the_temp_directory(tmp_path):
    env = {"TMPDIR": str(tmp_path), "TEMP": str(tmp_path), "TMP": str(tmp_path)}

    run_display(batch("```sh\n", index=0, final=False), env=env)
    shown = run_display(batch("a **b** " + EM_DASH + " c\n", index=1, final=False), env=env)

    assert shown == "a **b** " + EM_DASH + " c\n"


def test_a_whole_message_in_one_batch_writes_no_state_without_a_session(tmp_path):
    env = {"TMPDIR": str(tmp_path), "TEMP": str(tmp_path), "TMP": str(tmp_path)}

    shown = run_display(batch("a " + EM_DASH + " b\n```sh\nx\n```\n"), env=env)

    assert shown == "a, b\n```sh\nx\n```\n"
    assert list(tmp_path.iterdir()) == []


def test_a_whole_message_in_one_batch_records_its_fixes_and_no_fence(tmp_path):
    scratch = {"scratchpad_dir": str(tmp_path), "session_id": "s1"}

    run_display(batch("a " + EM_DASH + " b\r\nclean\n```sh\nx " + EM_DASH + " y\n```\n", **scratch))

    assert display_state(tmp_path) == {"fixed": {"m1": ["a " + EM_DASH + " b"]}}


def test_a_clean_batch_records_nothing(tmp_path):
    run_display(batch("Nothing to fix, `a*b*c`.\n", scratchpad_dir=str(tmp_path), session_id="s1"))

    assert list(tmp_path.iterdir()) == []


def test_the_display_record_keeps_only_the_newest_messages(tmp_path):
    scratch = {"scratchpad_dir": str(tmp_path), "session_id": "s1"}

    for number in range(20):
        run_display(batch("line " + str(number) + " " + EM_DASH + " x", message_id="m" + str(number), **scratch))

    assert list(display_state(tmp_path)["fixed"]) == ["m" + str(number) for number in range(4, 20)]


def test_fence_state_belongs_to_one_message(tmp_path):
    scratch = {"scratchpad_dir": str(tmp_path)}

    run_display(batch("```sh\n", index=0, final=False, message_id="m1", **scratch))
    shown = run_display(batch("a " + EM_DASH + " b\n", index=1, final=False, message_id="m2", **scratch))

    assert shown == "a, b\n"


@pytest.mark.parametrize(
    "payload",
    ["not json", "[]", json.dumps({"delta": 7}), json.dumps({"delta": None}), ""],
    ids=["garbage", "list", "number", "null", "empty"],
)
def test_the_display_fix_fails_open(payload):
    result = run_bounded(
        [sys.executable, str(NO_AI_MARKERS_HOOK), "--format", "claude", "--display"],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert (result.returncode, result.stdout) == (0, "")


def own_copy(root):
    """The project's own copy of the hook, which always runs."""
    target = root / ".agents" / "hooks" / NO_AI_MARKERS_HOOK.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(NO_AI_MARKERS_HOOK, target)

    return target


def test_a_global_display_copy_stays_silent_where_the_project_wires_it(tmp_path):
    wiring = json.loads(json.dumps(CLAUDE_PROJECT_WIRING).replace('"Stop"', '"MessageDisplay"'))
    root = project(tmp_path, ".claude/settings.json", json.dumps(wiring))
    env = {"CLAUDE_PROJECT_DIR": str(root)}
    text = "a " + EM_DASH + " b"

    assert run_display(batch(text, cwd=str(root)), env=env, script=global_copy(tmp_path)) == text
    assert run_display(batch(text, cwd=str(root)), env=env, script=own_copy(root)) == "a, b"


# The Stop check behind a display fix blocks only what the fix leaves behind.


def run_display_fixed(payload):
    result = run_bounded(
        [sys.executable, str(NO_AI_MARKERS_HOOK), "--format", "claude", "--display-fixed"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    return result.returncode, result.stdout


def displayed_then_stopped(tmp_path, text, stopped=None):
    """Show `text` through the display fix, then run the Stop check on `stopped`."""
    scratch = {"scratchpad_dir": str(tmp_path), "session_id": "s1"}
    run_display(batch(text, **scratch))

    return run_display_fixed({"last_assistant_message": text if stopped is None else stopped, **scratch})


@pytest.mark.parametrize(
    "text",
    [
        "A pause " + EM_DASH + " then more.",
        "Range 3" + EN_DASH + "5.",
        "This is **bold** and *italic*.",
    ],
    ids=["em-dash", "en-dash", "emphasis"],
)
def test_behind_a_display_fix_a_fixed_marker_does_not_block(tmp_path, text):
    assert displayed_then_stopped(tmp_path, text) == (0, "")


@pytest.mark.parametrize(
    "scratch",
    [{}, {"session_id": "s1"}],
    ids=["no-session", "no-record"],
)
def test_behind_a_display_fix_a_reply_the_display_never_recorded_is_checked_in_full(tmp_path, scratch):
    payload = {"last_assistant_message": "A pause " + EM_DASH + " then **more**.", "scratchpad_dir": str(tmp_path)}

    _code, out = run_display_fixed({**payload, **scratch})
    reason = json.loads(out)["reason"]

    assert "em dash (U+2014) in " in reason and "bold in " in reason


def test_behind_a_display_fix_a_line_the_display_did_not_fix_still_blocks(tmp_path):
    shown = "A pause " + EM_DASH + " then more."
    stopped = shown + "\nA line never shown " + EN_DASH + " here."

    _code, out = displayed_then_stopped(tmp_path, shown, stopped)
    reason = json.loads(out)["reason"]

    assert "en dash (U+2013) in " in reason
    assert "em dash (U+2014) in " not in reason


def test_the_stop_check_clears_the_display_record(tmp_path):
    text = "A pause " + EM_DASH + " then more."

    assert displayed_then_stopped(tmp_path, text) == (0, "")
    assert list(tmp_path.iterdir()) == []

    _code, out = run_display_fixed({"last_assistant_message": text, "scratchpad_dir": str(tmp_path), "session_id": "s1"})

    assert json.loads(out)["decision"] == "block"


def test_behind_a_display_fix_a_semicolon_still_blocks_alone(tmp_path):
    text = "One clause; another " + EM_DASH + " and **bold**."

    code, out = displayed_then_stopped(tmp_path, text)
    reason = json.loads(out)["reason"]

    assert code == 0
    assert "semicolon in " in reason
    assert "em dash (U+2014) in " not in reason
    assert "bold in " not in reason
    assert "Correction:" in reason


def test_behind_a_display_fix_escaped_markers_in_a_quote_do_not_block(tmp_path):
    assert displayed_then_stopped(tmp_path, ESCAPED_QUOTE) == (0, "")


def test_without_a_display_fix_escaped_markers_are_not_emphasis():
    _code, _out, err = run_text(ESCAPED_QUOTE)

    assert "em dash (U+2014) in " in err
    assert "bold in " not in err and "italic in " not in err


def test_behind_a_display_fix_bold_across_lines_still_blocks(tmp_path):
    _code, out = displayed_then_stopped(tmp_path, "Start **bold\nacross lines** end.")

    assert "bold in " in json.loads(out)["reason"]


# A block forces another turn, so a block nobody can satisfy must not repeat.


def stop_in_session(tmp_path, fmt, **extra):
    payload = {"last_assistant_message": "One; two.", "scratchpad_dir": str(tmp_path)}
    payload.update(extra)

    _code, out, _err = run_stop(payload, fmt)

    return json.loads(out)["decision"] if out else "allow"


@pytest.mark.parametrize("flag", ["stop_hook_active", "stopHookActive"])
def test_either_spelling_of_the_loop_flag_short_circuits(tmp_path, flag):
    assert stop_in_session(tmp_path, "copilot", sessionId="c1", **{flag: True}) == "allow"


@pytest.mark.parametrize(
    "fmt,session",
    [("claude", {"session_id": "s1"}), ("copilot", {"sessionId": "c1"})],
    ids=["claude", "copilot"],
)
def test_a_session_is_blocked_once_in_a_row_without_any_loop_flag(tmp_path, fmt, session):
    decisions = [stop_in_session(tmp_path, fmt, **session) for _ in range(4)]

    assert decisions == ["block", "allow", "block", "allow"]


def test_a_clean_reply_resets_the_block_counter(tmp_path):
    first = stop_in_session(tmp_path, "copilot", sessionId="c1")
    clean = stop_in_session(tmp_path, "copilot", sessionId="c1", last_assistant_message="Clean.")
    again = stop_in_session(tmp_path, "copilot", sessionId="c1")

    assert (first, clean, again) == ("block", "allow", "block")
    assert list(tmp_path.iterdir()) != []


def test_the_block_counter_is_per_session(tmp_path):
    decisions = [stop_in_session(tmp_path, "copilot", sessionId=name) for name in ("a", "b")]

    assert decisions == ["block", "block"]


def test_a_payload_with_no_session_blocks_every_time(tmp_path):
    assert [stop_in_session(tmp_path, "copilot") for _ in range(2)] == ["block", "block"]


# GitHub Copilot: agentStop names only the transcript, and the CLI also runs the
# Claude wiring it borrows from .claude/settings.json.


def copilot_events(tmp_path, *events):
    path = tmp_path / "events.jsonl"
    path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    return path


def copilot_message(content, tools=None):
    return {"type": "assistant.message", "data": {"content": content, "toolRequests": tools or []}}


def run_copilot(payload, script=NO_AI_MARKERS_HOOK):
    result = run_bounded(
        [sys.executable, str(script), "--format", "copilot"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    return result.returncode, result.stdout


def test_copilot_agent_stop_blocks_on_the_last_assistant_message(tmp_path):
    path = copilot_events(
        tmp_path,
        {"type": "user.message", "data": {"content": "go"}},
        copilot_message("A reply " + EM_DASH + " with a dash."),
        copilot_message("", tools=[{"name": "bash"}]),
    )

    code, out = run_copilot({"transcriptPath": str(path), "stop_hook_active": False})
    decision = json.loads(out)

    assert code == 0
    assert decision["decision"] == "block"
    assert "em dash" in decision["reason"]
    assert "Correction:" in decision["reason"]


def test_copilot_agent_stop_passes_clean_prose(tmp_path):
    path = copilot_events(tmp_path, copilot_message("A clean reply."))

    assert run_copilot({"transcriptPath": str(path)}) == (0, "")


def test_copilot_agent_stop_does_not_block_twice(tmp_path):
    path = copilot_events(tmp_path, copilot_message("One; two."))

    assert run_copilot({"transcriptPath": str(path), "stop_hook_active": True}) == (0, "")


@pytest.mark.parametrize(
    "lines",
    ["not json at all\n", '{"type": "assistant.message", "data": "oops"}\n', ""],
    ids=["garbage", "wrong-shape", "empty"],
)
def test_copilot_agent_stop_fails_open_on_an_unreadable_transcript(tmp_path, lines):
    path = tmp_path / "events.jsonl"
    path.write_text(lines, encoding="utf-8")

    assert run_copilot({"transcriptPath": str(path)}) == (0, "")
    assert run_copilot({"transcriptPath": str(tmp_path / "missing.jsonl")}) == (0, "")


# Recorded by Copilot CLI 1.0.81 in live run 36168529868, test 2. The subagent's
# agentStop fired before its final reply reached the session log, so the newest
# prose in the log was the subagent's first message, which the hook then judged.
COPILOT_MAIN_SESSION = "60ba3979-2a9c-43a4-8db6-de3b93e440d6"
COPILOT_SUBAGENT_SESSION = "2ca19017-d867-4e4a-baa0-6555b9bf0207"
COPILOT_STALE_SUBAGENT_PROSE = (
    "Preflight: `markdown-writer` is the applicable skill for this documentation task; no subagent is "
    "applicable because I am the delegated owner and this is a single bounded file operation."
)


def copilot_session_log(tmp_path, *events):
    log_dir = tmp_path / "session-state" / COPILOT_MAIN_SESSION
    log_dir.mkdir(parents=True)

    return copilot_events(log_dir, *events)


def copilot_agent_stop(path, session):
    return {
        "sessionId": session,
        "transcriptPath": str(path),
        "stopReason": "end_turn",
        "stop_hook_active": False,
        "timestamp": 1790358173796,
    }


def test_a_copilot_subagent_stop_does_not_judge_an_older_message_from_the_session_log(tmp_path):
    # Given the session log as it stood when the docs-architect subagent's agentStop fired
    path = copilot_session_log(
        tmp_path,
        {"type": "user.message", "data": {"content": "Delegate this task to the docs-architect subagent."}},
        copilot_message(COPILOT_STALE_SUBAGENT_PROSE, tools=[{"name": "bash"}]),
        copilot_message("", tools=[{"name": "view"}, {"name": "view"}]),
    )

    # When the hook receives the subagent's own session id with the main session's log
    result = run_copilot(copilot_agent_stop(path, COPILOT_SUBAGENT_SESSION))

    # Then it stays silent, because the reply it would judge is not this subagent's last one
    assert result == (0, "")


def test_a_copilot_main_thread_stop_still_judges_its_own_session_log(tmp_path):
    path = copilot_session_log(tmp_path, copilot_message(COPILOT_STALE_SUBAGENT_PROSE))

    code, out = run_copilot(copilot_agent_stop(path, COPILOT_MAIN_SESSION))

    assert code == 0
    assert json.loads(out)["decision"] == "block"


def test_a_global_copilot_copy_stays_silent_where_the_project_wires_agent_stop(tmp_path):
    command = "python .agents/hooks/no_ai_markers_check.py --format copilot"
    wiring = {"version": 1, "hooks": {"agentStop": [{"type": "command", "bash": command}]}}
    root = project(tmp_path, ".github/hooks/preflight.json", json.dumps(wiring))
    path = copilot_events(tmp_path, copilot_message("One; two."))
    payload = {"transcriptPath": str(path), "cwd": str(root)}

    assert run_copilot(payload, script=global_copy(tmp_path)) == (0, "")
    assert json.loads(run_copilot(payload, script=own_copy(root))[1])["decision"] == "block"


def copilot_vscode_stop(tmp_path):
    """The VS Code compatible Stop payload the hooks reference documents for the CLI."""
    return {
        "hook_event_name": "Stop",
        "session_id": "c1",
        "timestamp": "2026-09-24T18:00:00.000Z",
        "cwd": str(tmp_path),
        "transcript_path": str(copilot_events(tmp_path, copilot_message("One; two."))),
        "stop_reason": "end_turn",
        "stop_hook_active": False,
        "scratchpad_dir": str(tmp_path),
    }


def test_the_claude_stop_wiring_stays_silent_when_copilot_borrows_it(tmp_path):
    assert run_stop(copilot_vscode_stop(tmp_path), "claude") == (0, "", "")


@pytest.mark.parametrize(
    "change",
    [
        {"last_assistant_message": "One; two."},
        {"timestamp": 1790000000000},
        {"stop_reason": None, "drop": "stop_reason"},
    ],
    ids=["carries-the-reply", "numeric-timestamp", "no-stop-reason"],
)
def test_a_stop_payload_that_is_not_copilots_documented_shape_is_checked(tmp_path, change):
    payload = copilot_vscode_stop(tmp_path)
    payload.pop(change.pop("drop", ""), None)
    payload.update({key: value for key, value in change.items() if value is not None})

    _code, out, _err = run_stop(payload, "claude")

    assert json.loads(out)["decision"] == "block"


def test_the_claude_subagent_stop_wiring_still_checks_under_copilot():
    payload = {
        "hook_event_name": "SubagentStop",
        "stop_reason": "end_turn",
        "last_assistant_message": "One; two.",
    }

    _code, out, _err = run_stop(payload, "claude")

    assert json.loads(out)["decision"] == "block"


# The shipped wiring: a display fix only where the surface has one.

CLAUDE_SETTINGS = REPO_ROOT / ".claude" / "settings.json"
COPILOT_HOOKS = REPO_ROOT / ".github" / "hooks" / "preflight.json"
CODEX_CONFIG = REPO_ROOT / ".codex" / "config.toml"


def claude_commands(event):
    settings = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))

    return [entry["command"] for group in settings["hooks"][event] for entry in group["hooks"]]


def test_claude_code_wires_the_display_fix():
    commands = claude_commands("MessageDisplay")

    assert len(commands) == 1
    assert "no_ai_markers_check.py --format claude --display ;" in commands[0]


def test_claude_code_stop_checks_only_what_the_display_fix_leaves():
    stop = [command for command in claude_commands("Stop") if "no_ai_markers_check.py" in command]
    subagent = [command for command in claude_commands("SubagentStop") if "no_ai_markers_check.py" in command]

    assert len(stop) == 1 and "--format claude --display-fixed" in stop[0]
    assert len(subagent) == 1 and "--display" not in subagent[0]


def test_codex_keeps_the_full_check():
    config = CODEX_CONFIG.read_text(encoding="utf-8")

    assert "no_ai_markers_check.py --format codex" in config
    assert "--display" not in config


@pytest.mark.parametrize("shell", ["bash", "powershell"])
def test_copilot_wires_the_check_on_agent_stop(shell):
    wiring = json.loads(COPILOT_HOOKS.read_text(encoding="utf-8"))
    commands = [entry[shell] for entry in wiring["hooks"]["agentStop"]]

    assert len(commands) == 1
    assert "-S -E .agents/hooks/no_ai_markers_check.py --format copilot" in commands[0]
