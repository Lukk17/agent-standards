"""Tests for the Copilot prompt hook at .agents/hooks/copilot/prompt_reminder.py.

Driven as a subprocess, because the hook contract is the process contract:
userPromptTransformed JSON on stdin, modifiedTransformedPrompt JSON on stdout,
exit 0 on every path.

The same file holds the one wording test for the preflight reminder, because
this hook is one of the copies that test holds to the canonical block in
AGENTS.md.
"""

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from tests.conftest import HOOKS_DIR, PROMPT_REMINDER_HOOK, REPO_ROOT
from tests.process_tree import run_bounded

COPILOT_WIRING = REPO_ROOT / ".github" / "hooks" / "preflight.json"


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


REMINDER = _load_module("prompt_reminder_inprocess", PROMPT_REMINDER_HOOK).REMINDER


def run(stdin: bytes) -> subprocess.CompletedProcess:
    return run_bounded(
        [sys.executable, "-S", "-E", str(PROMPT_REMINDER_HOOK)],
        input=stdin,
        capture_output=True,
        check=False,
    )


def payload(transformed_prompt: object) -> bytes:
    body = {
        "sessionId": "s-1",
        "timestamp": 1790000000000,
        "cwd": str(REPO_ROOT),
        "prompt": "fix the build",
        "transformedPrompt": transformed_prompt,
    }

    return json.dumps(body).encode("utf-8")


def test_reminder_is_appended_on_a_new_line():
    result = run(payload("fix the build"))

    assert result.returncode == 0
    assert json.loads(result.stdout) == {"modifiedTransformedPrompt": f"fix the build\n{REMINDER}"}


def test_non_ascii_prompt_survives_the_round_trip():
    result = run(payload("popraw błąd"))

    assert json.loads(result.stdout)["modifiedTransformedPrompt"] == f"popraw błąd\n{REMINDER}"


def test_prompt_already_carrying_the_reminder_is_left_unchanged():
    result = run(payload(f"fix the build\n{REMINDER}\n"))

    assert result.returncode == 0
    assert result.stdout == b""


@pytest.mark.parametrize(
    "stdin",
    [
        b"",
        b"not json",
        b"[]",
        json.dumps({"prompt": "no transformed field"}).encode("utf-8"),
        payload(None),
        payload(42),
        b"\xff\xfe",
    ],
)
def test_unusable_payload_prints_nothing_and_exits_zero(stdin):
    result = run(stdin)

    assert result.returncode == 0
    assert result.stdout == b""
    assert result.stderr == b""


def test_hook_sits_below_the_directory_the_tool_call_runner_discovers():
    assert PROMPT_REMINDER_HOOK.is_file()
    assert PROMPT_REMINDER_HOOK.parent.parent == HOOKS_DIR


@pytest.mark.parametrize("shell", ["bash", "powershell"])
def test_copilot_wiring_calls_the_hook_where_it_lives(shell):
    wiring = json.loads(COPILOT_WIRING.read_text(encoding="utf-8"))
    commands = [entry[shell] for entry in wiring["hooks"]["userPromptTransformed"]]
    relative = PROMPT_REMINDER_HOOK.relative_to(REPO_ROOT).as_posix()

    assert commands
    assert all(f"-S -E {relative} " in command for command in commands)


def canonical_reminder() -> str:
    """The fenced text block under Required opening move in AGENTS.md."""
    agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    section = agents.split("## Required opening move", 1)[1]
    match = re.search(r"```text\n(.*?)\n```", section, re.DOTALL)

    return match.group(1)


def canonical_subagent_reminder() -> str:
    """The fenced text block after "The subagent text:" under Required opening move in AGENTS.md."""
    agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    section = agents.split("## Required opening move", 1)[1].split("The subagent text:", 1)[1]
    match = re.search(r"```text\n(.*?)\n```", section, re.DOTALL)

    return match.group(1)


# Every wiring prints one single-quoted literal. sh, bash and PowerShell all
# print a single-quoted literal as written, so the literal is what the agent
# reads: plain text with real newlines, or JSON whose \n escapes decode to them.
PRINTED_LITERAL = re.compile(r"^(?:echo|printf '%s\\n') '(?P<literal>[^']*)'(?:; exit 0)?$")
SHELL_KEYS = ("command", "commandWindows", "bash", "powershell")
POWERSHELL_KEYS = ("commandWindows", "powershell")
MARKER = "PREFLIGHT: before code work"
SUBAGENT_MARKER = "PREFLIGHT for a subagent:"


def reminder_commands(node, key=None, marker=MARKER) -> list[tuple[str, str]]:
    """Every (key, command) pair in a parsed wiring whose command prints the text marker opens."""
    if isinstance(node, dict):
        return [pair for child_key, child in node.items() for pair in reminder_commands(child, child_key, marker)]
    if isinstance(node, list):
        return [pair for child in node for pair in reminder_commands(child, key, marker)]
    if key in SHELL_KEYS and isinstance(node, str) and marker in node:
        return [(key, node)]

    return []


def delivered_text(printed: str) -> str:
    """What the agent hands the model from a hook's stdout."""
    printed = printed.replace("\r\n", "\n").rstrip("\n")
    if not printed.startswith("{"):
        return printed

    payload = json.loads(printed)

    return payload.get("hookSpecificOutput", payload)["additionalContext"]


def printed_literal(command: str) -> str:
    match = PRINTED_LITERAL.match(command)
    assert match, command

    return match["literal"]


def json_blocks(markdown: str) -> list[object]:
    return [json.loads(block) for block in re.findall(r"```json\n(.*?)\n```", markdown, re.DOTALL)]


WIRINGS = {
    ".claude/settings.json": lambda text: [json.loads(text)],
    ".codex/config.toml": lambda text: [tomllib.loads(text)],
    ".github/hooks/preflight.json": lambda text: [json.loads(text)],
    "docs/GLOBAL_SETUP.md": json_blocks,
}

# How many commands in each file print the reminder.
WIRED_COPIES = {
    ".claude/settings.json": 2,
    ".codex/config.toml": 2,
    ".github/hooks/preflight.json": 2,
    "docs/GLOBAL_SETUP.md": 4,
}


# How many commands in each file print the subagent text.
SUBAGENT_WIRED_COPIES = {
    ".claude/settings.json": 1,
    ".codex/config.toml": 2,
    ".github/hooks/preflight.json": 2,
    "docs/GLOBAL_SETUP.md": 3,
}


def wiring_commands(relative: str, marker: str = MARKER) -> list[tuple[str, str]]:
    text = (REPO_ROOT / relative).read_text(encoding="utf-8")

    return [pair for document in WIRINGS[relative](text) for pair in reminder_commands(document, marker=marker)]


def wiring_reminder(relative: str, _tmp_path) -> list[str]:
    return [delivered_text(printed_literal(command)) for _key, command in wiring_commands(relative)]


def sandbox_reminder(_relative: str, _tmp_path) -> list[str]:
    script = (REPO_ROOT / "sandbox-agent" / "setup-global.sh").read_text(encoding="utf-8")

    return re.findall(r"^readonly PREFLIGHT_TEXT='([^']*)'$", script, re.MULTILINE)


def hook_module_reminder(_relative: str, _tmp_path) -> list[str]:
    return [REMINDER]


def plugin_reminder(_relative: str, tmp_path) -> list[str]:
    from tests.test_hook_runner import NODE, drive, user_message

    if NODE is None:
        pytest.skip("node is not installed")

    return [part["text"] for part in drive(tmp_path, [user_message()])[0]["parts"]]


COPIES = [
    *[(relative, wiring_reminder) for relative in WIRINGS],
    ("sandbox-agent/setup-global.sh", sandbox_reminder),
    (".agents/hooks/copilot/prompt_reminder.py", hook_module_reminder),
    (".agents/plugin/hooks.js", plugin_reminder),
]

STATUS_BLOCK_TEMPLATE = [
    "",
    "Running: `running task name` (or: nothing)",
    "",
    "~~DONE: older finished task~~",
    "~~DONE: most recent finished task~~",
    "",
    "**NOW: what is being done right now**",
    "",
    "Next: the next task",
    "Then: the task after that",
    "",
    "Waiting on: what you wait for (or: nothing)",
]

SEVERAL_RUNNING_TASKS = (
    "When several tasks run, list each name in backticks on the Running line, separated by commas."
)


def test_the_canonical_reminder_ends_with_the_status_block_template_line_for_line():
    lines = canonical_reminder().split("\n")

    assert lines[0].endswith(
        "End every reply to the user with this block, exactly as shown: no heading, no bullets, "
        "no numbered list, plain lines only, keeping every blank line:"
    )
    assert lines[1:] == [*STATUS_BLOCK_TEMPLATE, "", SEVERAL_RUNNING_TASKS]


def test_the_user_communication_skill_carries_the_same_template():
    reference = REPO_ROOT / ".agents" / "skills" / "user-communication" / "references" / "status-block.md"
    after_intro = reference.read_text(encoding="utf-8").split("Copy this template exactly as shown", 1)[1]
    template = re.search(r"```text\n(.*?)\n```", after_intro, re.DOTALL).group(1)

    assert template.split("\n") == STATUS_BLOCK_TEMPLATE[1:]


def test_the_canonical_reminder_survives_single_quoting():
    assert "'" not in canonical_reminder()


@pytest.mark.parametrize(("copy", "read"), COPIES, ids=[copy for copy, _ in COPIES])
def test_every_copy_of_the_reminder_matches_the_canonical_block(copy, read, tmp_path):
    # Given
    canonical = canonical_reminder()

    # When
    copies = read(copy, tmp_path)

    # Then every copy is present, as often as the file wires it, and line for line
    assert len(copies) == WIRED_COPIES.get(copy, 1)
    assert all(text == canonical for text in copies), copy


POSIX_SHELL = shutil.which("sh")
POWERSHELLS = [path for path in (shutil.which("pwsh"), shutil.which("powershell")) if path]


def shells_for(relative: str, key: str) -> list[str]:
    """Claude Code's one command field lands in sh, Git Bash, or PowerShell without Git Bash."""
    if key in POWERSHELL_KEYS:
        return POWERSHELLS
    if relative == ".claude/settings.json":
        return [shell for shell in (POSIX_SHELL, *POWERSHELLS) if shell]

    return [POSIX_SHELL] if POSIX_SHELL else []


def run_in(shell: str, command: str, cwd) -> subprocess.CompletedProcess:
    argv = [shell, "-c", command] if shell == POSIX_SHELL else [shell, "-NoProfile", "-Command", command]

    return run_bounded(argv, capture_output=True, text=True, encoding="utf-8", check=False, cwd=cwd, timeout=60)


PRINTED_COMMANDS = [
    pytest.param(key, command, shell, id=f"{relative}-{index}-{key}-{Path(shell).stem if shell else 'none'}")
    for relative in (".claude/settings.json", ".codex/config.toml", ".github/hooks/preflight.json")
    for index, (key, command) in enumerate(wiring_commands(relative))
    for shell in shells_for(relative, key) or [None]
]


@pytest.mark.parametrize(("key", "command", "shell"), PRINTED_COMMANDS)
def test_every_wired_command_prints_the_canonical_newlines(key, command, shell, tmp_path):
    if shell is None:
        pytest.skip(f"no shell that runs {key} is installed")

    # When the shell the agent would pick runs the wired command
    result = run_in(shell, command, tmp_path)

    # Then the model receives the reminder with every line break and blank line intact
    assert result.returncode == 0, result.stderr
    assert delivered_text(result.stdout) == canonical_reminder()


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is not installed")
def test_the_sandbox_install_renders_the_canonical_newlines():
    # Given the install script's definitions, without its entry point
    script = (REPO_ROOT / "sandbox-agent" / "setup-global.sh").read_text(encoding="utf-8")
    definitions = script.split('\nmain "$@"\n', 1)[0]

    # When it renders the Claude Code settings and the Codex hooks
    rendered = [
        run_bounded(
            [shutil.which("bash"), "-s"],
            input=f"{definitions}\n{function}\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
            timeout=60,
        ).stdout
        for function in ("claude_settings", "codex_hooks")
    ]

    # Then every reminder command in both files delivers the canonical text
    commands = [command for text in rendered for _key, command in reminder_commands(json.loads(text))]
    assert len(commands) == 4
    assert all(delivered_text(printed_literal(command)) == canonical_reminder() for command in commands)

    # And every subagent-start command delivers the canonical subagent text
    subagent = [command for text in rendered for _key, command in subagent_start_commands(json.loads(text))]
    assert len(subagent) == 3
    assert all(delivered_text(printed_literal(command)) == canonical_subagent_reminder() for command in subagent)


# The reminder tells its reader to delegate, so no wiring hands it to a subagent:
# a subagent told to delegate turns its own task away. Each gets the subagent
# text instead, held to its own canonical block the same way.
SUBAGENT_START_EVENTS = ("SubagentStart", "subagentStart")


def wiring_subagent_reminder(relative: str, _tmp_path) -> list[str]:
    return [delivered_text(printed_literal(command)) for _key, command in wiring_commands(relative, SUBAGENT_MARKER)]


def sandbox_subagent_reminder(_relative: str, _tmp_path) -> list[str]:
    script = (REPO_ROOT / "sandbox-agent" / "setup-global.sh").read_text(encoding="utf-8")

    return re.findall(r"^readonly SUBAGENT_TEXT='([^']*)'$", script, re.MULTILINE)


def plugin_subagent_reminder(_relative: str, tmp_path) -> list[str]:
    from tests.test_hook_runner import CHILD_SESSION, NODE, drive, user_message

    if NODE is None:
        pytest.skip("node is not installed")

    return [part["text"] for part in drive(tmp_path, [user_message(session=CHILD_SESSION)])[0]["parts"]]


SUBAGENT_COPIES = [
    *[(relative, wiring_subagent_reminder) for relative in WIRINGS],
    ("sandbox-agent/setup-global.sh", sandbox_subagent_reminder),
    (".agents/plugin/hooks.js", plugin_subagent_reminder),
]


def test_the_canonical_subagent_text_survives_quoting_as_one_line():
    text = canonical_subagent_reminder()

    assert text.startswith(SUBAGENT_MARKER)
    assert not set("'\"\\\n") & set(text)
    assert "Delegate investigation" not in text


@pytest.mark.parametrize(("copy", "read"), SUBAGENT_COPIES, ids=[copy for copy, _ in SUBAGENT_COPIES])
def test_every_copy_of_the_subagent_text_matches_the_canonical_block(copy, read, tmp_path):
    # Given
    canonical = canonical_subagent_reminder()

    # When
    copies = read(copy, tmp_path)

    # Then
    assert len(copies) == SUBAGENT_WIRED_COPIES.get(copy, 1)
    assert all(text == canonical for text in copies), copy


def subagent_start_commands(document) -> list[tuple[str, str]]:
    """Every (key, command) pair wired on a subagent-start event, whatever it prints."""
    hooks = document.get("hooks", {}) if isinstance(document, dict) else {}

    return [
        pair
        for event in SUBAGENT_START_EVENTS
        for pair in reminder_commands(hooks.get(event, []), marker="")
    ]


@pytest.mark.parametrize("relative", list(WIRINGS))
def test_a_subagent_start_carries_the_subagent_text_and_never_the_reminder(relative):
    # Given
    documents = WIRINGS[relative]((REPO_ROOT / relative).read_text(encoding="utf-8"))

    # When
    commands = [command for document in documents for _key, command in subagent_start_commands(document)]

    # Then
    assert commands
    assert all(SUBAGENT_MARKER in command and MARKER not in command for command in commands), relative


PRINTED_SUBAGENT_COMMANDS = [
    pytest.param(key, command, shell, id=f"{relative}-{index}-{key}-{Path(shell).stem if shell else 'none'}")
    for relative in (".claude/settings.json", ".codex/config.toml", ".github/hooks/preflight.json")
    for index, (key, command) in enumerate(wiring_commands(relative, SUBAGENT_MARKER))
    for shell in shells_for(relative, key) or [None]
]


@pytest.mark.parametrize(("key", "command", "shell"), PRINTED_SUBAGENT_COMMANDS)
def test_every_wired_subagent_command_prints_the_canonical_text(key, command, shell, tmp_path):
    if shell is None:
        pytest.skip(f"no shell that runs {key} is installed")

    # When the shell the agent would pick runs the wired command
    result = run_in(shell, command, tmp_path)

    # Then
    assert result.returncode == 0, result.stderr
    assert delivered_text(result.stdout) == canonical_subagent_reminder()
