"""Tests for the markdown lint hook at .agents/hooks/markdown-lint-check/markdown_lint_check.py.

Driven as a subprocess, because the hook contract is the process contract:
stdin payload, --format flag, stdout shape, exit code. Every run gets its own
project root shaped like a consumer checkout, holding a real copy of
.agents/hooks/markdown-lint-check/_check_markdown.py and no tools/ directory, so the hook shells
out to the same linter CI runs rather than to a stub, and the scope decision is
made against a tree the test controls.
"""

import json
import shutil
import sys

import pytest

from tests.conftest import MARKDOWN_LINT_HOOK, MARKDOWN_LINT_RULES
from tests.process_tree import run_bounded

EM_DASH = "—"

DIRTY = "### Heading\n\nProse carrying an em dash " + EM_DASH + " which the lint bans.\n"

CLEAN = "### Heading\n\nProse carrying no banned character at all.\n"

LONG_PROSE = "### Heading\n\n" + " ".join(["word"] * 60) + "\n"


@pytest.fixture
def project(tmp_path):
    """A consumer-shaped project root: the imported hooks directory and no tools/."""
    hooks = tmp_path / ".agents" / "hooks" / MARKDOWN_LINT_RULES.parent.name
    hooks.mkdir(parents=True)
    shutil.copy(MARKDOWN_LINT_RULES, hooks)

    return tmp_path


def write(project, relative, body):
    path = project / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")

    return path


def run(project, payload, fmt="claude"):
    result = run_bounded(
        [sys.executable, str(MARKDOWN_LINT_HOOK), "--format", fmt],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(project),
    )

    return result.returncode, result.stdout, result.stderr


def edit(path):
    return {"tool_name": "Edit", "tool_input": {"file_path": str(path)}}


def context(out):
    return json.loads(out)["hookSpecificOutput"]["additionalContext"]


# A file inside the lint scope is linted, and its violations come back.


def test_a_dirty_in_scope_file_reports_its_violations(project):
    path = write(project, "docs/GUIDE.md", DIRTY)

    code, out, err = run(project, edit(path))

    assert (code, err) == (0, "")
    assert "em-dash or en-dash found" in context(out)


def test_the_report_names_the_offending_file_and_line(project):
    path = write(project, "docs/GUIDE.md", DIRTY)

    code, out, err = run(project, edit(path))

    assert "docs/GUIDE.md,line=3" in context(out).replace("\\", "/")


@pytest.mark.parametrize(
    "relative",
    ["README.md", "AGENTS.md.example", "docs/GUIDE.md", ".agents/skills/x/SKILL.md", "subagents/x.md", ".metrics/tools/README.md"],
)
def test_every_scoped_location_is_linted(project, relative):
    path = write(project, relative, DIRTY)

    code, out, err = run(project, edit(path))

    assert "em-dash or en-dash found" in context(out)


def test_a_batched_edit_payload_is_read_from_its_edits_list(project):
    path = write(project, "docs/GUIDE.md", DIRTY)
    payload = {"tool_name": "MultiEdit", "tool_input": {"edits": [{"file_path": str(path)}]}}

    code, out, err = run(project, payload)

    assert "em-dash or en-dash found" in context(out)


# Everything else stays silent at exit 0.


def test_a_clean_in_scope_file_reports_nothing(project):
    path = write(project, "docs/GUIDE.md", CLEAN)

    assert run(project, edit(path)) == (0, "", "")


def test_a_file_outside_the_lint_scope_reports_nothing(project):
    path = write(project, "tools/notes.md", DIRTY)

    assert run(project, edit(path)) == (0, "", "")


@pytest.mark.parametrize("tool", ["crapper", "dryer", "mutator"])
def test_a_vendored_quality_tool_file_reports_nothing(project, tool):
    path = write(project, f".metrics/tools/{tool}/README.md", DIRTY)

    assert run(project, edit(path)) == (0, "", "")


def test_a_file_outside_the_project_root_reports_nothing(project, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside")
    path = write(outside, "docs/GUIDE.md", DIRTY)

    assert run(project, edit(path)) == (0, "", "")


def test_a_payload_without_a_file_path_reports_nothing(project):
    assert run(project, {"tool_name": "Edit", "tool_input": {}}) == (0, "", "")


def test_malformed_json_reports_nothing(project):
    assert run(project, "{not json at all") == (0, "", "")


@pytest.mark.parametrize("fmt", ["codex", "copilot", ""], ids=["codex", "copilot", "empty"])
def test_a_format_other_than_claude_reports_nothing(project, fmt):
    path = write(project, "docs/GUIDE.md", DIRTY)

    assert run(project, edit(path), fmt=fmt) == (0, "", "")


def test_no_format_flag_at_all_reports_nothing(project):
    """There is no default format: the flag is the whole opt-in."""
    path = write(project, "docs/GUIDE.md", DIRTY)

    result = run_bounded(
        [sys.executable, str(MARKDOWN_LINT_HOOK)],
        input=json.dumps(edit(path)),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(project),
    )

    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


# The runner contract is not this hook's surface, and neither is any tool that
# does not write a file.


def test_the_plain_format_reports_nothing_and_never_blocks(project):
    """The runner discards stderr unless the hook exits 2, so this is a no-op.

    Exiting 2 here would block every OpenCode and Kilo Code tool call, so the
    one thing this must never do is fail.
    """
    path = write(project, "docs/GUIDE.md", DIRTY)

    assert run(project, edit(path), fmt="plain") == (0, "", "")


def test_the_plain_format_allows_an_envelope_version_it_does_not_recognise(project):
    path = write(project, "docs/GUIDE.md", DIRTY)
    payload = {**edit(path), "contract": 99}

    assert run(project, payload, fmt="plain") == (0, "", "")


@pytest.mark.parametrize("tool", ["Read", "Bash", "Grep", ""], ids=["read", "bash", "grep", "none"])
def test_a_tool_that_writes_nothing_is_not_linted(project, tool):
    path = write(project, "docs/GUIDE.md", DIRTY)

    payload = {"tool_name": tool, "tool_input": {"file_path": str(path)}}

    assert run(project, payload) == (0, "", "")


def test_a_consumer_checkout_without_tools_is_linted(project):
    # Given a project that pulled .agents/hooks and never had a tools/ directory
    assert not (project / "tools").exists()
    path = write(project, "docs/GUIDE.md", DIRTY)

    # When
    code, out, err = run(project, edit(path))

    # Then the shipped rules beside the hook are found and run
    assert (code, err) == (0, "")
    assert "em-dash or en-dash found" in context(out)


def test_a_long_unwrapped_prose_line_reports_nothing(project):
    # Given a paragraph written as one physical line, the way the owner writes prose
    path = write(project, "docs/GUIDE.md", LONG_PROSE)

    # When / Then
    assert run(project, edit(path)) == (0, "", "")


def hook_copy(folder, with_rules):
    """A copy of the hook in folder, with or without the rules module beside it."""
    folder.mkdir(parents=True)
    shutil.copy(MARKDOWN_LINT_HOOK, folder)
    if with_rules:
        shutil.copy(MARKDOWN_LINT_RULES, folder)

    return folder / MARKDOWN_LINT_HOOK.name


def run_copy(hook, project, payload, env=None):
    import os

    environment = {key: value for key, value in os.environ.items() if key not in ("CLAUDE_PROJECT_DIR", "CLAUDE_PLUGIN_ROOT")}
    environment.update(env or {})
    result = run_bounded(
        [sys.executable, str(hook), "--format", "claude"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(project),
        env=environment,
    )

    return result.returncode, result.stdout, result.stderr


def test_a_copy_with_no_rules_beside_it_or_in_the_project_reports_nothing(tmp_path):
    # Given a hook copy that lost its rules module, in a project that imported none
    hook = hook_copy(tmp_path / "elsewhere", with_rules=False)
    project = tmp_path / "project"
    path = write(project, "docs/GUIDE.md", DIRTY)

    assert run_copy(hook, project, edit(path)) == (0, "", "")


def plugin_copy(tmp_path):
    return hook_copy(tmp_path / "config" / "plugins" / "cache" / "agent-standards" / "hook-markdown-lint-check" / "1.0.0", with_rules=True)


def test_a_plugin_copy_lints_a_project_that_imported_no_hooks_with_the_rules_beside_it(tmp_path):
    # Given the hook-markdown-lint-check plugin layout and a project with no .agents at all
    hook = plugin_copy(tmp_path)
    project = tmp_path / "project"
    path = write(project, "docs/GUIDE.md", DIRTY)
    env = {"CLAUDE_PROJECT_DIR": str(project), "CLAUDE_PLUGIN_ROOT": str(hook.parent), "CLAUDE_CONFIG_DIR": str(tmp_path / "config")}

    # When
    code, out, err = run_copy(hook, project, {**edit(path), "hook_event_name": "PostToolUse"}, env)

    # Then
    assert (code, err) == (0, "")
    assert "em-dash or en-dash found" in context(out)


def test_a_plugin_copy_stands_down_when_the_project_wiring_runs_the_lint(tmp_path):
    # Given a project whose own .claude/settings.json runs the lint after an edit
    hook = plugin_copy(tmp_path)
    project = tmp_path / "project"
    path = write(project, "docs/GUIDE.md", DIRTY)
    command = 'cd "${CLAUDE_PROJECT_DIR}" && python3 -S -E .agents/hooks/markdown-lint-check/markdown_lint_check.py --format claude ; exit 0'
    write(project, ".claude/settings.json", json.dumps({"hooks": {"PostToolUse": [{"matcher": "Edit", "hooks": [{"type": "command", "command": command}]}]}}))
    write(project, ".agents/hooks/markdown-lint-check/markdown_lint_check.py", "# own\n")
    env = {"CLAUDE_PROJECT_DIR": str(project), "CLAUDE_PLUGIN_ROOT": str(hook.parent), "CLAUDE_CONFIG_DIR": str(tmp_path / "config")}

    # When / Then
    assert run_copy(hook, project, {**edit(path), "hook_event_name": "PostToolUse"}, env) == (0, "", "")
