"""Tests for the shared preflight gate at .agents/hooks/preflight_gate.py.

The gate is exercised as a subprocess because its contract is the process
contract: stdin payload, --format flag, stdout shape, exit code.
"""

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

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


def test_main_thread_writing_under_docs_is_denied():
    code, out, err = run(edit("docs/guide.md"), "claude")

    assert code == 0
    assert err == ""
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


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
def test_previously_exempt_targets_are_now_denied(path):
    """Rule A no longer carves out any file type: see AGENTS.md "Required
    opening move" for why the per-extension exemption was removed. A
    main-thread write of documentation, configuration, or a docs/ path is
    denied exactly like a write to a .py or .ts file.
    """
    code, out, _err = run(edit(path), "claude")

    assert code == 0
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


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


def test_subagent_with_declared_skills_may_edit_markdown(tmp_path):
    # Given a specialist subagent, and a docs/ markdown target that Rule A
    # would now deny outright from the main thread
    root = project_with_agent(tmp_path, "python-pro", WITH_SKILLS)
    payload = edit("docs/guide.md", agent_id="sub-1", agent_type="python-pro")

    # When
    code, out, err = run(payload, "claude", cwd=root)

    # Then a declared subagent is unaffected by Rule A entirely
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


def test_copilot_alias_keys_are_understood_and_still_allowed():
    # Given a Copilot preToolUse payload for a source-file write, with no
    # --subagent flag and no field in Copilot's own payload shape that could
    # identify the caller (see AGENTS.md "Required opening move" on why
    # Copilot cannot tell a subagent from the main thread today)
    payload = {"toolName": "Write", "toolArgs": {"filePath": "src/app.py"}}

    # When
    code, out, err = run(payload, "copilot")

    # Then the alias keys are still parsed (toolName/toolArgs/filePath), but
    # since the caller cannot be positively identified as the main thread,
    # Rule A stays silent rather than denying blind
    assert (code, out, err) == (0, "", "")


def test_copilot_source_edit_is_allowed_when_identity_is_unknown():
    # Given a Copilot payload using the canonical (non-alias) keys, still
    # with no --subagent flag and no identifying field
    payload = edit("src/app.py")

    # When
    code, out, err = run(payload, "copilot")

    # Then Rule A does not fire: denying here would risk blocking a
    # legitimate subagent that cannot otherwise prove itself on this surface
    assert (code, out, err) == (0, "", "")


def test_copilot_subagent_less_call_is_allowed_even_with_a_drifter_definition(tmp_path):
    # Given a Copilot payload that names an agent definition with no
    # declared skills, but carries no --subagent flag to assert the call
    # actually came from that subagent
    root = project_with_agent(tmp_path, "drifter", WITHOUT_SKILLS)
    payload = {
        "toolName": "Edit",
        "toolArgs": {"filePath": "src/app.py"},
        "agent_type": "drifter",
    }

    # When
    code, out, err = run(payload, "copilot", cwd=root)

    # Then identity stays unknown, so Rule B never even looks up the
    # definition, and the call is allowed
    assert (code, out, err) == (0, "", "")


def test_notebook_path_key_is_understood():
    payload = {"tool_name": "NotebookEdit", "tool_input": {"notebook_path": "a.ipynb"}}

    code, out, _err = run(payload, "claude")

    assert code == 0
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.mark.parametrize("tool", ["WebFetch", "WebSearch"])
def test_main_thread_web_research_denies_on_the_claude_format(tool):
    # Given a main-thread call to a research tool, on the one format
    # (Claude Code) whose tool names for fetch and search are confirmed
    payload = {"tool_name": tool, "tool_input": {}}

    # When
    code, out, err = run(payload, "claude")

    # Then Rule C fires before Rule A ever inspects a target
    assert code == 0
    assert err == ""

    decision = json.loads(out)["hookSpecificOutput"]

    assert decision["permissionDecision"] == "deny"
    assert tool.lower() in decision["permissionDecisionReason"]


def test_subagent_web_research_is_allowed(tmp_path):
    # Given a specialist subagent calling the same research tool
    root = project_with_agent(tmp_path, "python-pro", WITH_SKILLS)
    payload = {
        "tool_name": "WebFetch",
        "tool_input": {},
        "agent_id": "sub-1",
        "agent_type": "python-pro",
    }

    # When
    code, out, err = run(payload, "claude", cwd=root)

    # Then Rule C never applies to a subagent call at all
    assert (code, out, err) == (0, "", "")


def test_web_research_is_not_denied_on_formats_without_a_confirmed_tool_name():
    # Given a main-thread WebFetch call on a format outside RESEARCH_FORMATS
    # (Codex has no confirmed tool name for this yet, see AGENTS.md)
    payload = {"tool_name": "WebFetch", "tool_input": {}}

    # When
    code, out, err = run(payload, "codex")

    # Then Rule C stays scoped to the formats it was verified for
    assert (code, out, err) == (0, "", "")


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
    ["cat src/app.py", "ls -la src/"],
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
    # A Read is never a write, so it allows regardless of the target's
    # extension; the exact output shape of a quiet allow is what this test
    # verifies, not any per-extension exemption (Rule A no longer has one).
    payload = {"tool_name": "Read", "tool_input": {"file_path": "README.md"}}

    code, out, err = run(payload, "plain")

    assert (code, out, err) == (0, "", "")


def test_claude_format_allow_path_is_silent():
    # Given a tool call that never reaches the deny branch
    payload = {"tool_name": "Read", "tool_input": {"file_path": "README.md"}}

    # When
    code, out, err = run(payload, "claude")

    # Then no wrapper is needed to swallow stderr noise: there is none
    assert (code, out, err) == (0, "", "")


def test_claude_format_deny_path_carries_no_stderr():
    # Given a main-thread edit of a source file
    payload = edit("src/app.py")

    # When
    code, out, err = run(payload, "claude")

    # Then the deny travels as JSON on stdout, exit 0, and stderr is empty
    assert code == 0
    assert err == ""

    decision = json.loads(out)["hookSpecificOutput"]

    assert decision["permissionDecision"] == "deny"


@pytest.mark.parametrize("extra_args", [["--format", "not-a-real-format"], []])
def test_bad_format_argument_fails_open_without_leaking_to_caller_stderr(extra_args):
    # Given a call that gives argparse a reason to exit: an invalid choice, or a
    # missing required flag
    result = subprocess.run(
        [sys.executable, str(PREFLIGHT_GATE), *extra_args],
        input=json.dumps(edit("src/app.py")),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO_ROOT),
    )

    # When/Then main() swallows the SystemExit argparse raises and fails open,
    # so the caller sees neither a crash nor argparse's usage text
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


class _FakeStdin:
    """Stands in for sys.stdin, exposing only the .buffer.read() path main() uses."""

    def __init__(self, data: bytes) -> None:
        self.buffer = io.BytesIO(data)


def _load_gate_module():
    """Import preflight_gate.py in-process.

    Needed only so a test can inspect whether sys.stderr survives a call to
    main() with its own identity intact; a subprocess cannot observe that.
    """
    spec = importlib.util.spec_from_file_location("preflight_gate_inprocess", PREFLIGHT_GATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


GATE = _load_gate_module()


@pytest.mark.parametrize(
    "payload",
    [edit("README.md"), edit("src/app.py")],
    ids=["allow", "deny"],
)
def test_main_restores_the_real_sys_stderr(monkeypatch, payload):
    # Given the real sys.stderr object identity before main() runs
    original_stderr = sys.stderr
    monkeypatch.setattr(sys, "stdin", _FakeStdin(json.dumps(payload).encode("utf-8")))

    # When
    GATE.main(["--format", "claude"])

    # Then main() must not leak its swapped-out sink past its own return
    assert sys.stderr is original_stderr


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
    # a main-thread write of documentation or a docs/ path, now denied like
    # any other file since Rule A's per-extension exemption was removed
    "echo hi > notes.md",
    "sed -i 's/a/b/' docs/guide.md",
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
    # git inspection and branch work
    "git status --short",
    "git diff -- src/app.py",
    "git log --oneline | head -20",
    "git checkout -b feature/gate",
    "git restore --staged src/app.py",
    "git apply --check /tmp/change.diff",
    # docker
    "docker compose up -d",
    'docker run --rm -v "$PWD:/app" node:20 npm test',
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


# Rule A protects the repository working tree, not the rest of the
# filesystem: see AGENTS.md "Required opening move" on this change. A target
# is out of Rule A's jurisdiction, and must allow, when it resolves outside
# the repository or is not a write at all (discarding output to the null
# device in any of the three shells' spellings, or a bare `git checkout`
# operand that names a branch rather than a file). A target that resolves
# inside the repository is exactly what Rule A exists to protect and must
# keep denying, even when it superficially resembles one of the cases above.
OUTSIDE_REPO_OR_NOT_A_WRITE = [
    "pytest -q 2>/dev/null",
    "pytest -q 2>/DEV/NULL",
    "curl -s http://example.com/data > /tmp/out.json",
    "sed 's/a/b/' src/app.py > /tmp/out.txt",
    "git diff HEAD > /tmp/change.diff",
    "git checkout master",
]


@pytest.mark.parametrize("command", OUTSIDE_REPO_OR_NOT_A_WRITE)
def test_targets_outside_the_repository_or_non_writes_are_allowed(command):
    assert decision(shell(command)) == "allow"


NULL_DEVICE_REDIRECTS = [
    ("echo x 2>/dev/null", "Bash"),
    ("Get-Content foo > $null", "PowerShell"),
    ("Get-Content foo > $NULL", "PowerShell"),
    ("dir > NUL", "PowerShell"),
    ("dir > nul", "PowerShell"),
]


@pytest.mark.parametrize("command,tool", NULL_DEVICE_REDIRECTS)
def test_null_device_redirection_is_never_a_write(command, tool):
    assert decision(shell(command, tool=tool)) == "allow"


# `rm -rf build node_modules` deletes directories inside the repository, so
# it stays denied under the same rule as everything below.
REPOSITORY_WRITES_STILL_DENY = [
    "rm -rf build node_modules",
    "git checkout -- src/thing.py",
    "git checkout README.md",
]


@pytest.mark.parametrize("command", REPOSITORY_WRITES_STILL_DENY)
def test_repository_writes_still_deny(command):
    assert decision(shell(command)) == "deny"


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


# Defect 1: with no --, git reads operand zero as a tree-ish and every
# operand after it as an unconditional pathspec once there are two or more
# operands, regardless of whether the file currently exists in the working
# tree. Only the single-operand form stays genuinely ambiguous.
TWO_OPERAND_GIT_CHECKOUT_FORMS = [
    "git checkout HEAD~1 tools/gen_subagents.py",
    "git checkout other-branch some/new/file.py",
]


@pytest.mark.parametrize("command", TWO_OPERAND_GIT_CHECKOUT_FORMS)
def test_two_operand_git_checkout_writes_are_denied(command):
    assert decision(shell(command)) == "deny"


# Defect 2: the repository boundary Rule A protects is anchored on the
# gate's own on-disk location as well as on the invocation cwd (see
# _roots()), not on the cwd alone. Every case below runs from a project root
# that is deliberately not the real repository, to prove the boundary still
# holds when the wiring's cd-to-project-root step has failed.
def test_edit_tool_writing_outside_the_repository_allows(tmp_path_factory):
    # Given a project root and a target that resolves under a wholly
    # separate directory, unrelated to either the invocation cwd or the
    # gate's own on-disk location
    project_root = tmp_path_factory.mktemp("project")
    outside = tmp_path_factory.mktemp("outside")
    target = str(outside / "file.py")

    # When
    code, out, err = run(edit(target), "claude", cwd=project_root)

    # Then
    assert (code, out, err) == (0, "", "")


def test_edit_tool_writing_an_absolute_path_inside_the_repository_denies(tmp_path_factory):
    # Given a project root that is not the real repository, and a target
    # that is an absolute path to a real file inside the actual repository
    project_root = tmp_path_factory.mktemp("project")
    target = str(REPO_ROOT / "README.md")

    # When
    code, out, err = run(edit(target), "claude", cwd=project_root)

    # Then the gate's own on-disk location still anchors the boundary, so
    # this denies even though the target is outside the invocation cwd
    assert code == 0
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_edit_tool_path_escaping_via_dotdot_denies():
    # Given a project root outside the repository but on the same drive (so
    # a relative .. path between the two is well defined on Windows), and a
    # target that climbs out of the project root and back down into the
    # real repository
    project_root = Path(tempfile.mkdtemp(dir=str(REPO_ROOT.parent)))

    try:
        climb = os.path.relpath(REPO_ROOT, start=project_root)
        target = str(Path(climb) / "README.md")

        # When
        code, out, err = run(edit(target), "claude", cwd=project_root)

        # Then
        assert code == 0
        assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"
    finally:
        shutil.rmtree(project_root, ignore_errors=True)


def test_edit_tool_symlinked_path_that_resolves_inside_denies(tmp_path_factory):
    # Given a symlink located entirely outside both roots, whose own link
    # target is a real file inside the repository
    outside = tmp_path_factory.mktemp("outside")
    project_root = tmp_path_factory.mktemp("project")
    link = outside / "escape.py"

    try:
        link.symlink_to(REPO_ROOT / "README.md")
    except OSError:
        pytest.skip("symlink creation is not permitted in this environment")

    # When
    code, out, err = run(edit(str(link)), "claude", cwd=project_root)

    # Then resolving the symlink lands inside the repository, so this denies
    # even though the link's own path is nowhere near either root
    assert code == 0
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_edit_tool_windows_drive_relative_path_denies():
    # Given a drive-relative path (a drive letter with no root separator):
    # Windows reads "D:app.py" as "app.py in the current directory of drive
    # D:", not as an absolute path
    target = REPO_ROOT.drive + "app.py"

    # When
    code, out, err = run(edit(target), "claude")

    # Then it joins onto the repository root exactly as a bare relative
    # path would, and denies
    assert code == 0
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_edit_tool_unc_path_allows():
    # Given a UNC path: always absolute on Windows, and never inside either
    # local root
    target = r"\\server\share\file.py"

    # When
    code, out, err = run(edit(target), "claude")

    # Then
    assert (code, out, err) == (0, "", "")


# Defect 3: apply_patch carries no path key at all, so its write target has
# to be read out of the patch body's own file headers instead.
def apply_patch_call(tool_input, tool="apply_patch"):
    return {"tool_name": tool, "tool_input": tool_input}


def test_apply_patch_update_file_header_is_denied():
    body = "*** Begin Patch\n*** Update File: src/app.py\n@@\n-old\n+new\n*** End Patch\n"

    code, out, err = run(apply_patch_call({"input": body}), "claude")

    assert code == 0
    assert err == ""

    output = json.loads(out)["hookSpecificOutput"]

    assert output["permissionDecision"] == "deny"
    assert "src/app.py" in output["permissionDecisionReason"]


def test_apply_patch_add_file_header_is_denied():
    body = "*** Begin Patch\n*** Add File: src/new_module.py\n+content\n*** End Patch\n"

    code, out, _err = run(apply_patch_call({"patch": body}), "claude")

    assert code == 0

    output = json.loads(out)["hookSpecificOutput"]

    assert output["permissionDecision"] == "deny"
    assert "src/new_module.py" in output["permissionDecisionReason"]


def test_apply_patch_unified_diff_header_is_denied():
    # Given the patch body carries no key the gate could special-case
    body = "--- a/src/app.py\n+++ b/src/app.py\n@@ -1 +1 @@\n-old\n+new\n"

    code, out, _err = run(apply_patch_call({"diff": body}), "claude")

    assert code == 0

    output = json.loads(out)["hookSpecificOutput"]

    assert output["permissionDecision"] == "deny"
    assert "src/app.py" in output["permissionDecisionReason"]


def test_apply_patch_touching_only_files_outside_the_repository_allows():
    body = "*** Begin Patch\n*** Update File: /tmp/outside/scratch.py\n*** End Patch\n"

    code, out, err = run(apply_patch_call({"input": body}), "claude")

    assert (code, out, err) == (0, "", "")


def test_apply_patch_with_no_readable_file_header_is_denied():
    # Given a body that carries no recognisable file header at all: the
    # gate cannot resolve a target, so it denies rather than trusts the call
    code, out, _err = run(apply_patch_call({"input": "not a patch"}), "claude")

    assert code == 0
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_apply_patch_with_no_tool_input_at_all_is_denied():
    code, out, _err = run(apply_patch_call({}), "claude")

    assert code == 0
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_a_subagent_may_still_call_apply_patch(tmp_path):
    # Given a specialist subagent
    root = project_with_agent(tmp_path, "python-pro", WITH_SKILLS)
    body = "*** Begin Patch\n*** Update File: src/app.py\n*** End Patch\n"
    payload = apply_patch_call({"input": body})
    payload["agent_id"] = "sub-1"
    payload["agent_type"] = "python-pro"

    # When
    code, out, err = run(payload, "claude", cwd=root)

    # Then
    assert (code, out, err) == (0, "", "")


# Defect 4: "nul" and "$null" are only the null device inside a PowerShell
# (or cmd) context. A POSIX shell treats either spelling as an ordinary
# filename, so gating them on the invoking tool is what stops a Bash write
# to a real repository file literally named nul or $null from being
# silently discarded.
NULL_DEVICE_TOKENS_ARE_POWERSHELL_ONLY = [
    "echo x > nul",
    "echo x > $null",
]


@pytest.mark.parametrize("command", NULL_DEVICE_TOKENS_ARE_POWERSHELL_ONLY)
def test_windows_null_device_spellings_are_literal_files_outside_powershell(command):
    assert decision(shell(command, tool="Bash")) == "deny"


def test_dev_null_stays_unconditional_even_under_powershell():
    # Given /dev/null redirected from a PowerShell-tagged call: the POSIX
    # spelling is never gated on which shell is running, unlike nul/$null
    assert decision(shell("Get-Content foo > /dev/null", tool="PowerShell")) == "allow"


# Rule C: only the codex format had coverage for "not in RESEARCH_FORMATS",
# so a regression that widened RESEARCH_FORMATS to include copilot or plain
# without also handling their caller-identity shape would go unnoticed.
def test_web_research_is_not_denied_on_the_copilot_format():
    payload = {"toolName": "WebFetch", "toolArgs": {}}

    code, out, err = run(payload, "copilot")

    assert (code, out, err) == (0, "", "")


def test_web_research_is_not_denied_on_the_plain_format():
    payload = {"tool_name": "WebFetch", "tool_input": {}}

    code, out, err = run(payload, "plain")

    assert (code, out, err) == (0, "", "")
