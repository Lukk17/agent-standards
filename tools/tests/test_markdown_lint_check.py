"""Tests for the markdown lint hook at .agents/hooks/markdown_lint_check.py.

Driven as a subprocess, because the hook contract is the process contract:
stdin payload, --format flag, stdout shape, exit code. Every run gets its own
project root holding a real copy of tools/check-markdown.py, so the hook shells
out to the same linter CI runs rather than to a stub, and the scope decision is
made against a tree the test controls.
"""

import json
import shutil
import subprocess
import sys

import pytest

from tests.conftest import MARKDOWN_LINT_HOOK, REPO_ROOT

EM_DASH = "—"

DIRTY = "### Heading\n\nProse carrying an em dash " + EM_DASH + " which the lint bans.\n"

CLEAN = "### Heading\n\nProse carrying no banned character at all.\n"


@pytest.fixture
def project(tmp_path):
    """A throwaway project root the hook will recognise, lint script included."""
    (tmp_path / ".agents" / "hooks").mkdir(parents=True)
    (tmp_path / "tools").mkdir()
    shutil.copy(REPO_ROOT / "tools" / "check-markdown.py", tmp_path / "tools")

    return tmp_path


def write(project, relative, body):
    path = project / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")

    return path


def run(project, payload, fmt="claude"):
    result = subprocess.run(
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
    ["README.md", "AGENTS.md.example", "docs/GUIDE.md", ".agents/skills/x/SKILL.md", "subagents/x.md"],
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

    result = subprocess.run(
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


@pytest.mark.parametrize("tool", ["Read", "Bash", "Grep", ""], ids=["read", "bash", "grep", "none"])
def test_a_tool_that_writes_nothing_is_not_linted(project, tool):
    path = write(project, "docs/GUIDE.md", DIRTY)

    payload = {"tool_name": tool, "tool_input": {"file_path": str(path)}}

    assert run(project, payload) == (0, "", "")


def test_a_project_without_the_lint_script_reports_nothing(tmp_path):
    # Given a consumer checkout, which pulls the hooks but not tools/
    (tmp_path / ".agents" / "hooks").mkdir(parents=True)
    path = write(tmp_path, "docs/GUIDE.md", DIRTY)

    assert run(tmp_path, edit(path)) == (0, "", "")
