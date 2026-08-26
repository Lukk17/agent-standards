"""Tests for the shared preflight gate at .agents/hooks/preflight_gate.py.

The gate is exercised as a subprocess because its contract is the process
contract: stdin payload, --format flag, stdout shape, exit code.
"""

import json
import os
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

COPILOT_BODY_SKILLS = """---
name: {name}
description: A Copilot-format definition for {name}.
---

Persona text.

## Preloaded skills

- `python-testing`
- `coding-standards`
"""

CODEX_BODY_SKILLS = """name = "{name}"
description = "A Codex-format definition."
developer_instructions = '''
Persona text.

## Preloaded skills

- `python-testing`
- `coding-standards`
'''
"""

CODEX_WITHOUT_SKILLS = """name = "{name}"
description = "A Codex-format generalist with nothing declared."
developer_instructions = '''
Body.
'''
"""

AGENT_FILENAMES = {
    ".claude/agents": "{name}.md",
    ".agents/agents": "{name}.md",
    ".opencode/agents": "{name}.md",
    ".kilo/agents": "{name}.md",
    ".codex/agents": "{name}.toml",
    ".github/agents": "{name}.agent.md",
}

DECLARING_TREES = [
    (".claude/agents", BODY_SKILLS),
    (".agents/agents", BODY_SKILLS),
    (".opencode/agents", BODY_SKILLS),
    (".kilo/agents", BODY_SKILLS),
    (".codex/agents", CODEX_BODY_SKILLS),
    (".github/agents", COPILOT_BODY_SKILLS),
]


def run(payload, fmt, cwd=None, extra=(), env=None):
    """Run the gate and return (returncode, stdout, stderr)."""
    if isinstance(payload, str):
        stdin = payload
    else:
        stdin = json.dumps(payload, ensure_ascii=False)

    result = subprocess.run(
        [sys.executable, str(PREFLIGHT_GATE), "--format", fmt, *extra],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(cwd) if cwd else str(REPO_ROOT),
        env={**os.environ, **env} if env else None,
    )

    return result.returncode, result.stdout, result.stderr


def project_with_agent(tmp_path, name, template, agent_dir=".claude/agents"):
    """Create a throwaway project root holding one agent definition."""
    agents = tmp_path.joinpath(*agent_dir.split("/"))
    agents.mkdir(parents=True, exist_ok=True)
    filename = AGENT_FILENAMES[agent_dir].format(name=name)
    (agents / filename).write_text(template.format(name=name), encoding="utf-8")

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


@pytest.mark.parametrize("agent_dir,template", DECLARING_TREES)
def test_body_declared_skills_count_as_declared(tmp_path, agent_dir, template):
    root = project_with_agent(tmp_path, "opencoder", template, agent_dir)
    payload = edit("src/app.py", agent_id="sub-1", agent_type="opencoder")

    code, out, err = run(payload, "claude", cwd=root)

    assert (code, out, err) == (0, "", "")


def test_kilo_only_definition_without_skills_is_denied(tmp_path):
    root = project_with_agent(tmp_path, "drifter", WITHOUT_SKILLS, ".kilo/agents")
    payload = edit("src/app.py", agent_id="sub-1", agent_type="drifter")

    code, out, _err = run(payload, "claude", cwd=root)

    assert code == 0

    reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]

    assert "drifter" in reason


def test_codex_only_definition_without_skills_is_denied(tmp_path):
    root = project_with_agent(tmp_path, "drifter", CODEX_WITHOUT_SKILLS, ".codex/agents")
    payload = edit("src/app.py", agent_id="sub-1", agent_type="drifter")

    code, out, _err = run(payload, "codex", cwd=root)

    assert code == 0

    reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]

    assert "drifter" in reason


def test_codex_definition_with_skills_is_allowed(tmp_path):
    root = project_with_agent(tmp_path, "codexer", CODEX_BODY_SKILLS, ".codex/agents")
    payload = edit("src/app.py", agent_id="sub-1", agent_type="codexer")

    code, out, err = run(payload, "codex", cwd=root)

    assert (code, out, err) == (0, "", "")


def test_copilot_only_definition_without_skills_is_denied(tmp_path):
    root = project_with_agent(tmp_path, "drifter", WITHOUT_SKILLS, ".github/agents")
    payload = {
        "toolName": "Edit",
        "toolArgs": {"filePath": "src/app.py"},
        "agent_type": "drifter",
    }

    code, out, _err = run(payload, "copilot", cwd=root, extra=("--subagent",))

    assert code == 0
    assert "drifter" in json.loads(out)["permissionDecisionReason"]


def test_copilot_definition_with_skills_is_allowed(tmp_path):
    root = project_with_agent(tmp_path, "copiloteer", COPILOT_BODY_SKILLS, ".github/agents")
    payload = {
        "toolName": "Edit",
        "toolArgs": {"filePath": "src/app.py"},
        "agent_type": "copiloteer",
    }

    code, out, err = run(payload, "copilot", cwd=root, extra=("--subagent",))

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


def envelope(tool="Edit", tool_input=None, agent="", assistant_text=""):
    """The runner envelope described in docs/hooks-contract.md."""
    return {
        "contract": 1,
        "event": "tool.execute.before",
        "tool_name": tool,
        "tool_input": tool_input if tool_input is not None else {},
        "agent_type": agent,
        "is_subagent": bool(agent),
        "assistant_text": assistant_text,
        "cwd": "",
    }


def test_envelope_flags_a_subagent_without_the_command_line_flag(tmp_path):
    # Given a subagent that declares no skills, named only in the envelope
    root = project_with_agent(tmp_path, "helper", WITHOUT_SKILLS)
    payload = envelope(tool_input={"file_path": "src/app.py"}, agent="helper")

    # When
    code, out, err = run(payload, "plain", cwd=root)

    # Then
    assert (code, out) == (2, "")
    assert "declares no skills" in err


def test_envelope_main_thread_is_not_treated_as_a_subagent(tmp_path):
    # Given
    root = project_with_agent(tmp_path, "helper", WITHOUT_SKILLS)
    payload = envelope(tool="Read", tool_input={"file_path": "README.md"})

    # When
    code, out, err = run(payload, "plain", cwd=root)

    # Then
    assert (code, out, err) == (0, "", "")


NON_ASCII_PROSE = "Dash — and quotes “” and żółw."


def test_envelope_with_non_ascii_prose_still_decides():
    # Given the envelope carries assistant prose, which is rarely pure ASCII
    payload = envelope(
        tool_input={"file_path": "src/app.py"},
        assistant_text=NON_ASCII_PROSE,
    )

    # When
    code, out, err = run(payload, "plain")

    # Then
    assert (code, out) == (2, "")
    assert "src/app.py" in err


def test_non_ascii_envelope_survives_a_hostile_stdin_encoding():
    """Decoding stdin has to be explicit, never the interpreter's default.

    Text-mode stdin follows the locale or PYTHONIOENCODING, and on a machine
    whose console is not UTF-8 the envelope's prose fields raise on decode. The
    gate catches that and allows, so the whole rule would silently switch off.
    Reading bytes and decoding UTF-8 by hand is what keeps it on.
    """
    # Given
    payload = envelope(
        tool_input={"file_path": "src/app.py"},
        assistant_text=NON_ASCII_PROSE,
    )

    # When
    code, out, err = run(payload, "plain", env={"PYTHONIOENCODING": "ascii"})

    # Then
    assert (code, out) == (2, "")
    assert "src/app.py" in err


def shell(command, tool="Bash"):
    """A shell tool call carrying one command."""
    return {"tool_name": tool, "tool_input": {"command": command}}


def decision(payload):
    """Run the gate in claude format and return 'deny' or 'allow'."""
    code, out, err = run(payload, "claude")

    assert (code, err) == (0, "")

    if not out:
        return "allow"

    return json.loads(out)["hookSpecificOutput"]["permissionDecision"]


SHELL_WRITE_FORMS = [
    # sed in-place, every spelling that reaches the same syscall
    'sed -i "s|a|b|" sandbox-agent/verify-project.sh',
    "sed -i 's/a/b/' src/app.py",
    "sed -i.bak 's/a/b/' src/app.py",
    "sed --in-place 's/a/b/' src/app.py",
    "sed -i '' 's/a/b/' src/app.py",
    "sed -Ei 's|a|b|' src/app.py",
    "sed -i -e 's|a|b|' -e 's|c|d|' src/app.py",
    "perl -pi -e 's/a/b/' src/app.py",
    "gawk -i inplace '{print}' src/app.py",
    # output redirection
    "echo x > src/app.py",
    "echo x >src/app.py",
    "echo x 1> src/app.py",
    "echo x &> src/app.py",
    "echo x >| src/app.py",
    "printf 'x' >> lib/util.go",
    "ls && echo x > src/app.py",
    "cd src; echo x > app.py",
    # tee
    "echo x | tee src/app.py",
    "echo x | tee -a src/app.py",
    "echo x | sudo tee src/app.py",
    # copy, move, link, install
    "cp /tmp/a.py src/app.py",
    "cp /tmp/app.py src/",
    "cp -t src/ /tmp/app.py",
    "mv /tmp/a.py src/app.py",
    "install -m 644 /tmp/a.py src/app.py",
    "ln -sf /tmp/a.py src/app.py",
    # truncate and dd
    "truncate -s 0 src/app.py",
    "dd if=/dev/null of=src/app.py",
    # inline interpreter code that opens a file for writing
    "python -c \"open('src/app.py','w').write('x')\"",
    "python3 -c \"from pathlib import Path; Path('src/app.py').write_text('x')\"",
    "node -e \"require('fs').writeFileSync('src/app.py','x')\"",
    # heredoc redirected into a file
    "cat <<EOF > src/app.py\nx\nEOF",
    "cat > src/app.py <<'EOF'\nx\nEOF",
    # git overwriting the working tree from a path
    "git checkout -- src/app.py",
    "git checkout HEAD~1 -- src/app.py",
    "git restore src/app.py",
    "git checkout .",
    # applying a patch
    "patch -p1 < /tmp/change.diff",
    "patch src/app.py < /tmp/change.diff",
    "git apply /tmp/change.diff",
    "git am /tmp/change.patch",
    # deleting a source file
    "rm src/app.py",
    "rm -f src/app.py lib/util.go",
    # nested and wrapped commands
    'bash -c "echo x > src/app.py"',
    "sh -c 'sed -i \"s|a|b|\" src/app.py'",
    r"find . -name '*.py' -exec sed -i 's/a/b/' {} \;",
    "env FOO=1 sed -i 's|a|b|' src/app.py",
    "FOO=1 sed -i 's|a|b|' src/app.py",
    "timeout 30 sed -i 's|a|b|' src/app.py",
]


@pytest.mark.parametrize("command", SHELL_WRITE_FORMS)
def test_every_shell_write_spelling_is_denied(command):
    assert decision(shell(command)) == "deny"


POWERSHELL_WRITE_FORMS = [
    "Set-Content -Path src/app.py -Value x",
    "Set-Content src/app.py 'x'",
    "Add-Content -Path src/app.py -Value x",
    "Out-File -FilePath src/app.py",
    "New-Item -Path src -Name app.py -ItemType File",
    "Copy-Item /tmp/a.py src/app.py",
    "Move-Item -Path /tmp/a.py -Destination src/app.py",
    "Remove-Item -Force src/app.py",
    "Clear-Content src/app.py",
]


@pytest.mark.parametrize("command", POWERSHELL_WRITE_FORMS)
def test_powershell_write_cmdlets_are_denied(command):
    assert decision(shell(command, tool="PowerShell")) == "deny"


ROUTINE_SHELL_COMMANDS = [
    # reading
    "cat src/app.py",
    "head -50 src/app.py",
    "wc -l src/app.py",
    "sed -n '1,20p' src/app.py",
    "awk '{print $1}' src/app.py",
    "diff -u src/a.py src/b.py",
    # searching and listing
    "grep -rn 'def ' src/",
    "grep -rn 'x > out.py' src/",
    "ls -la src/",
    "find . -name '*.py' -print",
    # running the project's own tooling
    "python -m pytest -q",
    "python tools/gen_subagents.py",
    "python tools/gen_subagents.py --check",
    "python tools/check-markdown.py",
    "npm test",
    "pytest -q 2>/dev/null",
    # git inspection and branch work
    "git status --short",
    "git diff -- src/app.py",
    "git log --oneline | head -20",
    "git checkout master",
    "git checkout -b feature/gate",
    "git restore --staged src/app.py",
    "git apply --check /tmp/change.diff",
    "git diff HEAD > /tmp/change.diff",
    # docker
    "docker compose up -d",
    'docker run --rm -v "$PWD:/app" node:20 npm test',
    # writes that land on non-source targets
    "echo hi > notes.md",
    "curl -s http://example.com/data > /tmp/out.json",
    "sed -i 's/a/b/' docs/guide.md",
    "sed 's/a/b/' src/app.py > /tmp/out.txt",
    "rm -rf build node_modules",
    # text that only looks like a redirect or an edit
    "git commit -m 'fix > app.py'",
    "echo 'see docs > app.py for details'",
    "python -c \"print('src/app.py')\"",
    "cat <<'EOF'\nsed -i 's/x/y/' app.py\nEOF",
    "echo 'x -> y' && ls",
]


@pytest.mark.parametrize("command", ROUTINE_SHELL_COMMANDS)
def test_routine_shell_commands_stay_allowed(command):
    assert decision(shell(command)) == "allow"


UNPARSEABLE_COMMANDS = [
    'echo "unterminated',
    "echo 'unterminated > src/app.py",
    "",
    "   ",
]


@pytest.mark.parametrize("command", UNPARSEABLE_COMMANDS)
def test_a_command_the_gate_cannot_parse_is_allowed(command):
    assert decision(shell(command)) == "allow"


def test_a_subagent_may_still_write_source_through_the_shell(tmp_path):
    # Given a subagent that declares its skills
    root = project_with_agent(tmp_path, "python-pro", WITH_SKILLS)
    payload = shell("sed -i 's|a|b|' src/app.py")
    payload["agent_id"] = "sub-1"
    payload["agent_type"] = "python-pro"

    # When
    code, out, err = run(payload, "claude", cwd=root)

    # Then
    assert (code, out, err) == (0, "", "")


def test_the_deny_reason_names_the_shell_target():
    # Given the reported bypass
    payload = shell('sed -i "s|a|b|" sandbox-agent/verify-project.sh')

    # When
    _code, out, _err = run(payload, "claude")

    # Then
    reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]

    assert "sandbox-agent/verify-project.sh" in reason
