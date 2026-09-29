"""Shared helpers for the per-agent reminder test modules."""

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

RECORDED_SUBAGENT_TEXT = (
    "PREFLIGHT for a subagent: you are a subagent, and the main thread delegated this task to you. Do the work "
    "yourself with your own tools and load the skills your definition names. The rules that the main thread must "
    "delegate and may not write files apply to the main thread only, so do not hand this task on and do not refuse "
    "it for that reason. The preflight gate still checks every tool call you make. Report back what you changed "
    "and how you verified it."
)

RECORDED_SUBAGENT_TASK = (
    "Create `live-probe/subagent-note.md` in the repository with exactly one line of content: `written by "
    "subagent`. Do not add any other content. You own the write and should make it yourself. Report once the file "
    "is created."
)

SUBAGENT_GUARDS = (
    r"grep -F '\"agent_id\"' >/dev/null \|\| ",
    r'if \(-not \[Console\]::In\.ReadToEnd\(\)\.Contains\("`"agent_id`""\)\) \{ ',
)

PRINTED_LITERAL = re.compile(
    rf"^(?:{'|'.join(SUBAGENT_GUARDS)})?(?:echo|printf '%s\\n') '(?P<literal>[^']*)'(?: \}})?(?:; exit 0)?$"
)

SHELL_KEYS = ("command", "commandWindows", "bash", "powershell")

POWERSHELL_KEYS = ("commandWindows", "powershell")

MARKER = "Before code work, name the skills"

CLAUDE_MARKER = "PREFLIGHT: before code work"

SUBAGENT_MARKER = "PREFLIGHT for a subagent:"

WIRED_COPIES = {
    ".claude/settings.json": 2,
    ".codex/config.toml": 2,
    ".github/hooks/preflight.json": 2,
    "docs/GLOBAL_SETUP.md": 6,
}

SUBAGENT_WIRED_COPIES = {
    ".claude/settings.json": 1,
    ".codex/config.toml": 2,
    ".github/hooks/preflight.json": 2,
    "docs/GLOBAL_SETUP.md": 5,
}

def posix_shell() -> str | None:
    import os

    candidates: list[str | None] = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
    ]
    for base in (os.environ.get("PROGRAMFILES"), os.environ.get("LOCALAPPDATA")):
        if base:
            candidates.append(f"{base}\\Git\\bin\\bash.exe")
            candidates.append(f"{base}\\Git\\usr\\bin\\bash.exe")
    candidates.append(shutil.which("sh"))
    candidates.append(shutil.which("bash"))
    for candidate in candidates:
        if not candidate:
            continue
        try:
            probed = run_bounded([candidate, "-c", "exit 0"], capture_output=True, check=False, timeout=30)
        except Exception:
            continue
        if probed.returncode == 0:
            return candidate
    return None


POSIX_SHELL = posix_shell()

POWERSHELLS = [path for path in (shutil.which("pwsh"), shutil.which("powershell")) if path]

SUBAGENT_START_EVENTS = ("SubagentStart", "subagentStart")

def sandbox_subagent_reminder(_relative: str, _tmp_path) -> list[str]:
    script = (REPO_ROOT / "sandbox-agent" / "setup-global.sh").read_text(encoding="utf-8")

    return re.findall(r"^readonly SUBAGENT_TEXT='([^']*)'$", script, re.MULTILINE)

def recorded_subagent_prompt() -> bytes:
    prompt = f"{RECORDED_SUBAGENT_TEXT}\n\n{RECORDED_SUBAGENT_TEXT}\n\n{RECORDED_SUBAGENT_TASK}"
    body = {
        "sessionId": "1112aa66-72ed-419e-81db-17efb6c06726",
        "prompt": prompt,
        "transformedPrompt": f"<current_datetime>2026-09-25T19:02:08.746+00:00</current_datetime>\n\n{prompt}",
        "timestamp": 1790362928747,
        "cwd": "/home/runner/work/_temp/live-copilot/project",
    }

    return json.dumps(body).encode("utf-8")

def hook_module_reminder(_relative: str, _tmp_path) -> list[str]:
    return [REMINDER]

def plugin_reminder(_relative: str, tmp_path) -> list[str]:
    from tests.test_hook_runner import NODE, drive, user_message

    if NODE is None:
        pytest.skip("node is not installed")

    return [part["text"] for part in drive(tmp_path, [user_message()])[0]["parts"]]

def run(stdin: bytes) -> subprocess.CompletedProcess:
    return run_bounded(
        [sys.executable, "-S", "-E", str(PROMPT_REMINDER_HOOK)],
        input=stdin,
        capture_output=True,
        check=False,
    )

def wiring_subagent_reminder(relative: str, _tmp_path) -> list[str]:
    return [delivered_text(printed_literal(command)) for _key, command in wiring_commands(relative, SUBAGENT_MARKER)]

def wiring_reminder(relative: str, _tmp_path) -> list[str]:
    return [delivered_text(printed_literal(command)) for _key, command in wiring_commands(relative)]

def delivered_text(printed: str) -> str:
    """What the agent hands the model from a hook's stdout."""
    printed = printed.replace("\r\n", "\n").rstrip("\n")
    if not printed.startswith("{"):
        return printed

    payload = json.loads(printed)

    return payload.get("hookSpecificOutput", payload)["additionalContext"]

def sandbox_reminder(_relative: str, _tmp_path) -> list[str]:
    script = (REPO_ROOT / "sandbox-agent" / "setup-global.sh").read_text(encoding="utf-8")

    return re.findall(r"^readonly PREFLIGHT_TEXT='([^']*)'$", script, re.MULTILINE)

def subagent_start_commands(document) -> list[tuple[str, str]]:
    """Every (key, command) pair wired on a subagent-start event, whatever it prints."""
    hooks = document.get("hooks", {}) if isinstance(document, dict) else {}

    return [
        pair
        for event in SUBAGENT_START_EVENTS
        for pair in reminder_commands(hooks.get(event, []), marker="")
    ]

def wiring_commands(relative: str, marker: str = MARKER) -> list[tuple[str, str]]:
    text = (REPO_ROOT / relative).read_text(encoding="utf-8")
    if marker == MARKER and relative in (".claude/settings.json", "docs/GLOBAL_SETUP.md"):
        short = [pair for document in WIRINGS[relative](text) for pair in reminder_commands(document, marker=marker)]
        long = [pair for document in WIRINGS[relative](text) for pair in reminder_commands(document, marker=CLAUDE_MARKER)]
        # The long Claude text never contains the short marker, the short never the long one.
        return short + [pair for pair in long if pair not in short]

    return [pair for document in WIRINGS[relative](text) for pair in reminder_commands(document, marker=marker)]

def reminder_commands(node, key=None, marker=MARKER) -> list[tuple[str, str]]:
    """Every (key, command) pair in a parsed wiring whose command prints the text marker opens."""
    if isinstance(node, dict):
        return [pair for child_key, child in node.items() for pair in reminder_commands(child, child_key, marker)]
    if isinstance(node, list):
        return [pair for child in node for pair in reminder_commands(child, key, marker)]
    if key in SHELL_KEYS and isinstance(node, str) and marker in node:
        return [(key, node)]

    return []

def printed_literal(command: str) -> str:
    match = PRINTED_LITERAL.match(command)
    assert match, command

    return match["literal"]

def run_in(shell: str, command: str, cwd) -> subprocess.CompletedProcess:
    argv = [shell, "-NoProfile", "-Command", command] if shell in POWERSHELLS else [shell, "-c", command]

    return run_bounded(argv, capture_output=True, text=True, encoding="utf-8", check=False, cwd=cwd, timeout=60)

def payload(transformed_prompt: object) -> bytes:
    body = {
        "sessionId": "s-1",
        "timestamp": 1790000000000,
        "cwd": str(REPO_ROOT),
        "prompt": "fix the build",
        "transformedPrompt": transformed_prompt,
    }

    return json.dumps(body).encode("utf-8")

def shells_for(relative: str, key: str) -> list[str]:
    """Claude Code's one command field lands in sh, Git Bash, or PowerShell without Git Bash."""
    if key in POWERSHELL_KEYS:
        return POWERSHELLS
    shell = posix_shell()
    if relative == ".claude/settings.json":
        return [s for s in (shell, *POWERSHELLS) if s]

    return [shell] if shell else []

def plugin_subagent_reminder(_relative: str, tmp_path) -> list[str]:
    from tests.test_hook_runner import CHILD_SESSION, NODE, drive, user_message

    if NODE is None:
        pytest.skip("node is not installed")

    return [part["text"] for part in drive(tmp_path, [user_message(session=CHILD_SESSION)])[0]["parts"]]

def canonical_subagent_reminder() -> str:
    """The SubagentStart echo in .claude/settings.json."""
    import json as _json

    settings = _json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    for entry in settings["hooks"]["SubagentStart"]:
        for hook in entry["hooks"]:
            cmd = hook.get("command", "")
            if "PREFLIGHT for a subagent:" in cmd:
                return _json.loads(delivered_text(printed_literal(cmd)))["hookSpecificOutput"]["additionalContext"] if delivered_text(printed_literal(cmd)).startswith("{") else delivered_text(printed_literal(cmd))
    raise AssertionError("no subagent text")

def canonical_reminder() -> str:
    """The short opening line: the REMINDER constant of the Copilot hook."""
    hook = _load_module("prompt_reminder_canonical", PROMPT_REMINDER_HOOK)

    return hook.REMINDER

def json_blocks(markdown: str) -> list[object]:
    return [json.loads(block) for block in re.findall(r"```json\n(.*?)\n```", markdown, re.DOTALL)]

def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module

def expected_reminder_for_command(command: str) -> str:
    """The Claude wiring carries the long text, every other wiring the short one."""
    text = delivered_text(printed_literal(command))
    if text == CLAUDE_REMINDER:
        return CLAUDE_REMINDER
    return SHORT_REMINDER

WIRINGS = {
    ".claude/settings.json": lambda text: [json.loads(text)],
    ".codex/config.toml": lambda text: [tomllib.loads(text)],
    ".github/hooks/preflight.json": lambda text: [json.loads(text)],
    "docs/GLOBAL_SETUP.md": json_blocks,
}

COPIES = [
    *[(relative, wiring_reminder) for relative in WIRINGS],
    ("sandbox-agent/setup-global.sh", sandbox_reminder),
    (".agents/hooks/copilot/prompt_reminder.py", hook_module_reminder),
]

STATUS_BLOCK_TEMPLATE = """---------------------

Status

```text
Running: name of each running task, with progress like 3 of 10 todos done
```

```text
Done: older finished task
Done: most recent finished task
```

```text
NOW: what is being done right now, one line
```

```text
Next: the next task
Then: the task after that
```

```text
Waiting on: what the agent waits for
```

```text
State: WAITING FOR YOU
```"""

SEVERAL_RUNNING_TASKS = (
    "When several tasks run, list each name on the Running line separated by commas."
)

SUBAGENT_COPIES = [
    *[(relative, wiring_subagent_reminder) for relative in WIRINGS],
    ("sandbox-agent/setup-global.sh", sandbox_subagent_reminder),
]

REMINDER = _load_module("prompt_reminder_inprocess", PROMPT_REMINDER_HOOK).REMINDER

SHORT_REMINDER = REMINDER

CLAUDE_REMINDER = (
    "PREFLIGHT: before code work, name the skills and subagents that own this task and invoke them, "
    "or say none apply and why. Delegate investigation, review and bounded implementation by default. "
    "Follow the user-communication skill when writing to the user. If the prompt asks anything, answer "
    "every question first, then start the work. End every reply to the user with this block, exactly as "
    "shown: no heading, no bullets, no numbered list, plain lines only, keeping every blank line:\n"
    "\n"
    "Running: `running task name` (or: nothing)\n"
    "\n"
    "~~DONE: older finished task~~\n"
    "~~DONE: most recent finished task~~\n"
    "\n"
    "**NOW: what is being done right now**\n"
    "\n"
    "Next: the next task\n"
    "Then: the task after that\n"
    "\n"
    "Waiting on: what you wait for (or: nothing)\n"
    "\n"
    "When several tasks run, list each name in backticks on the Running line, separated by commas."
)

EXPECTED_REMINDERS = {
    ".claude/settings.json": [CLAUDE_REMINDER, CLAUDE_REMINDER],
    ".codex/config.toml": [SHORT_REMINDER, SHORT_REMINDER],
    ".github/hooks/preflight.json": [SHORT_REMINDER, SHORT_REMINDER],
    "sandbox-agent/setup-global.sh": [SHORT_REMINDER],
    ".agents/hooks/copilot/prompt_reminder.py": [SHORT_REMINDER],
    "docs/GLOBAL_SETUP.md": [
        CLAUDE_REMINDER,
        CLAUDE_REMINDER,
        SHORT_REMINDER,
        SHORT_REMINDER,
        SHORT_REMINDER,
        SHORT_REMINDER,
    ],
}
