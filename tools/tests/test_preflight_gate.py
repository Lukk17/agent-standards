"""Tests for the shared preflight gate at .agents/hooks/preflight_gate.py.

The gate is exercised as a subprocess because its contract is the process
contract: stdin payload, --format flag, stdout shape, exit code.
"""

import json
import subprocess
import sys

import pytest

from tests.conftest import PREFLIGHT_GATE, REPO_ROOT

WITH_SKILLS = """---
name: {name}
description: A specialist.
skills:
  - python-patterns
  - python-testing
---

Body.
"""

WITHOUT_SKILLS = """---
name: {name}
description: A generalist with nothing declared.
---

Body.
"""

BODY_SKILLS = """---
description: An OpenCode-format definition for {name}.
mode: subagent
---

Persona text.

## Preloaded skills

Load and follow these before acting.

- `python-testing`
- `coding-standards`
"""

EMPTY_SKILLS_KEY = """---
name: {name}
skills: []
---

Body.
"""


def run(payload, fmt, cwd=None, extra=()):
    """Run the gate and return (returncode, stdout, stderr)."""
    if isinstance(payload, str):
        stdin = payload
    else:
        stdin = json.dumps(payload)

    result = subprocess.run(
        [sys.executable, str(PREFLIGHT_GATE), "--format", fmt, *extra],
        input=stdin,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else str(REPO_ROOT),
    )

    return result.returncode, result.stdout, result.stderr


def project_with_agent(tmp_path, name, template, agent_dir=".claude/agents"):
    """Create a throwaway project root holding one agent definition."""
    agents = tmp_path.joinpath(*agent_dir.split("/"))
    agents.mkdir(parents=True, exist_ok=True)
    (agents / (name + ".md")).write_text(template.format(name=name), encoding="utf-8")

    return tmp_path


def edit(path, agent_id=None, agent_type=None):
    payload = {"tool_name": "Edit", "tool_input": {"file_path": path}}

    if agent_id:
        payload["agent_id"] = agent_id
    if agent_type:
        payload["agent_type"] = agent_type

    return payload


def test_main_thread_editing_source_is_denied():
    code, out, err = run(edit("src/app.py"), "claude")

    assert code == 0
    assert err == ""

    decision = json.loads(out)["hookSpecificOutput"]

    assert decision["permissionDecision"] == "deny"
    assert "src/app.py" in decision["permissionDecisionReason"]


def test_main_thread_editing_markdown_is_allowed():
    code, out, err = run(edit("docs/guide.md"), "claude")

    assert (code, out, err) == (0, "", "")


@pytest.mark.parametrize(
    "path",
    [
        "notes.txt",
        "config.yaml",
        "settings.toml",
        "package.json",
        ".gitignore",
        "LICENSE",
        ".env.example",
        "docs/architecture.py",
    ],
)
def test_non_source_targets_are_allowed(path):
    code, out, _err = run(edit(path), "claude")

    assert (code, out) == (0, "")


@pytest.mark.parametrize(
    "path",
    ["app.ts", "Main.java", "lib/util.go", "deploy.ps1", "styles/app.scss"],
)
def test_other_code_extensions_are_denied(path):
    code, out, _err = run(edit(path), "claude")

    assert code == 0
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_subagent_with_declared_skills_may_edit_source(tmp_path):
    root = project_with_agent(tmp_path, "python-pro", WITH_SKILLS)
    payload = edit("src/app.py", agent_id="sub-1", agent_type="python-pro")

    code, out, err = run(payload, "claude", cwd=root)

    assert (code, out, err) == (0, "", "")


def test_subagent_without_declared_skills_is_denied(tmp_path):
    root = project_with_agent(tmp_path, "drifter", WITHOUT_SKILLS)
    payload = edit("src/app.py", agent_id="sub-1", agent_type="drifter")

    code, out, _err = run(payload, "claude", cwd=root)

    assert code == 0

    reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]

    assert "drifter" in reason


@pytest.mark.parametrize(
    "agent_dir", [".claude/agents", ".agents/agents", ".opencode/agents"]
)
def test_body_declared_skills_count_as_declared(tmp_path, agent_dir):
    root = project_with_agent(tmp_path, "opencoder", BODY_SKILLS, agent_dir)
    payload = edit("src/app.py", agent_id="sub-1", agent_type="opencoder")

    code, out, err = run(payload, "claude", cwd=root)

    assert (code, out, err) == (0, "", "")


def test_empty_skills_list_counts_as_no_skills(tmp_path):
    root = project_with_agent(tmp_path, "hollow", EMPTY_SKILLS_KEY)
    payload = edit("src/app.py", agent_id="sub-1", agent_type="hollow")

    code, out, _err = run(payload, "claude", cwd=root)

    assert code == 0
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_claude_definition_wins_over_the_later_paths(tmp_path):
    project_with_agent(tmp_path, "mixed", WITH_SKILLS, ".claude/agents")
    project_with_agent(tmp_path, "mixed", WITHOUT_SKILLS, ".agents/agents")
    payload = edit("src/app.py", agent_id="sub-1", agent_type="mixed")

    code, out, err = run(payload, "claude", cwd=tmp_path)

    assert (code, out, err) == (0, "", "")


def test_real_repo_subagent_definitions_are_recognised():
    payload = edit("src/app.py", agent_id="sub-1", agent_type="python-pro")

    code, out, err = run(payload, "claude")

    assert (code, out, err) == (0, "", "")


def test_subagent_without_a_definition_file_is_allowed(tmp_path):
    payload = edit("src/app.py", agent_id="sub-1", agent_type="ghost")

    code, out, err = run(payload, "claude", cwd=tmp_path)

    assert (code, out, err) == (0, "", "")


def test_copilot_subagent_flag_drives_the_subagent_branch(tmp_path):
    root = project_with_agent(tmp_path, "drifter", WITHOUT_SKILLS)
    payload = {
        "toolName": "Edit",
        "toolArgs": {"filePath": "src/app.py"},
        "agent_type": "drifter",
    }

    code, out, _err = run(payload, "copilot", cwd=root, extra=("--subagent",))

    assert code == 0
    assert json.loads(out)["permissionDecision"] == "deny"


def test_copilot_alias_keys_are_understood():
    payload = {"toolName": "Write", "toolArgs": {"filePath": "src/app.py"}}

    code, out, _err = run(payload, "copilot")

    assert code == 0

    decision = json.loads(out)

    assert decision["permissionDecision"] == "deny"
    assert "src/app.py" in decision["permissionDecisionReason"]


def test_notebook_path_key_is_understood():
    payload = {"tool_name": "NotebookEdit", "tool_input": {"notebook_path": "a.ipynb"}}

    code, out, _err = run(payload, "claude")

    assert code == 0
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.mark.parametrize(
    "command",
    [
        "echo x > src/app.py",
        "cat foo >> lib/util.go",
        "echo x | tee src/app.py",
        "sed -i 's/a/b/' src/app.py",
        "cat <<EOF > src/app.py",
    ],
)
def test_shell_writes_to_source_are_denied(command):
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}

    code, out, _err = run(payload, "claude")

    assert code == 0
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.mark.parametrize(
    "command",
    ["pytest -q 2>/dev/null", "cat src/app.py", "echo hi > notes.md"],
)
def test_harmless_shell_commands_are_allowed(command):
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}

    code, out, _err = run(payload, "claude")

    assert (code, out) == (0, "")


@pytest.mark.parametrize(
    "raw",
    ["", "not json at all", "[]", "null", '{"tool_name": 5, "tool_input": "oops"}'],
)
def test_malformed_input_is_allowed(raw):
    code, out, err = run(raw, "claude")

    assert (code, out, err) == (0, "", "")


def test_codex_format_shape():
    code, out, _err = run(edit("src/app.py"), "codex")

    assert code == 0

    hook = json.loads(out)["hookSpecificOutput"]

    assert hook["hookEventName"] == "PreToolUse"
    assert hook["permissionDecision"] == "deny"


def test_plain_format_writes_stderr_and_exits_two():
    code, out, err = run(edit("src/app.py"), "plain")

    assert code == 2
    assert out == ""
    assert "PREFLIGHT" in err


def test_plain_format_allows_quietly():
    code, out, err = run(edit("README.md"), "plain")

    assert (code, out, err) == (0, "", "")
