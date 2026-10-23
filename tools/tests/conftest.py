"""Shared filesystem paths for the hook and tooling test suite.

The hook scripts live in .agents/hooks/ at the repository root, two levels
above this package, and resolving that root once here keeps the location in a
single place. SUBPROCESS_TIMEOUT_SECONDS bounds every child a test starts, so
a hung hook fails its test instead of stalling the run. isolated_temp_directory
gives every test its own temp directory, so no hook state is read from or left
in the real one. isolated_home_directory does the same for the home
directory: HOME and USERPROFILE name a fresh folder, and every variable that
moves an agent's home or an XDG base directory elsewhere is removed, so a path
the code builds from the environment always lands under that folder and never
in the user's real ~/.config/codex, ~/.claude or ~/.local/state.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = REPO_ROOT / ".agents" / "hooks"
PREFLIGHT_GATE = HOOKS_DIR / "preflight_gate.py"
NO_AI_MARKERS_HOOK = HOOKS_DIR / "no_ai_markers_check.py"
TASK_LIST_SYNC_HOOK = HOOKS_DIR / "task_list_sync.py"
MARKDOWN_LINT_HOOK = HOOKS_DIR / "markdown_lint_check.py"
MARKDOWN_LINT_RULES = HOOKS_DIR / "_check_markdown.py"
PROMPT_REMINDER_HOOK = HOOKS_DIR / "copilot" / "prompt_reminder.py"
SYNC_SKILL_LINKS_HOOK = HOOKS_DIR / "claude" / "sync_skill_links.py"
PLUGIN = REPO_ROOT / ".agents" / "plugin" / "hooks.js"
RUNNER_DRIVER = Path(__file__).resolve().parent / "hook_runner_driver.mjs"
SUBPROCESS_TIMEOUT_SECONDS = 60

TEMP_DIRECTORY_VARIABLES = ("TMPDIR", "TEMP", "TMP")
HOME_VARIABLES = ("HOME", "USERPROFILE")
RELOCATING_VARIABLES = (
    "CODEX_HOME",
    "CLAUDE_CONFIG_DIR",
    "COPILOT_HOME",
    "XDG_CONFIG_HOME",
    "XDG_STATE_HOME",
    "XDG_DATA_HOME",
    "XDG_CACHE_HOME",
)


@pytest.fixture(autouse=True)
def isolated_temp_directory(tmp_path_factory, monkeypatch):
    directory = tmp_path_factory.mktemp("temp")

    for name in TEMP_DIRECTORY_VARIABLES:
        monkeypatch.setenv(name, str(directory))

    return directory


@pytest.fixture(autouse=True)
def isolated_home_directory(tmp_path_factory, monkeypatch):
    home = tmp_path_factory.mktemp("home")

    for name in HOME_VARIABLES:
        monkeypatch.setenv(name, str(home))

    for name in RELOCATING_VARIABLES:
        monkeypatch.delenv(name, raising=False)

    return home
