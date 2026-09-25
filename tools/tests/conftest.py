"""Shared filesystem paths for the hook and tooling test suite.

The hook scripts live in .agents/hooks/ at the repository root, two levels
above this package, and resolving that root once here keeps the location in a
single place. SUBPROCESS_TIMEOUT_SECONDS bounds every child a test starts, so
a hung hook fails its test instead of stalling the run. isolated_temp_directory
gives every test its own temp directory, so no hook state is read from or left
in the real one.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = REPO_ROOT / ".agents" / "hooks"
PREFLIGHT_GATE = HOOKS_DIR / "preflight_gate.py"
NO_AI_MARKERS_HOOK = HOOKS_DIR / "no_ai_markers_check.py"
TASK_LIST_SYNC_HOOK = HOOKS_DIR / "task_list_sync.py"
MARKDOWN_LINT_HOOK = HOOKS_DIR / "markdown_lint_check.py"
PROMPT_REMINDER_HOOK = HOOKS_DIR / "copilot" / "prompt_reminder.py"
PLUGIN = REPO_ROOT / ".agents" / "plugin" / "hooks.js"
RUNNER_DRIVER = Path(__file__).resolve().parent / "hook_runner_driver.mjs"
SUBPROCESS_TIMEOUT_SECONDS = 60

TEMP_DIRECTORY_VARIABLES = ("TMPDIR", "TEMP", "TMP")


@pytest.fixture(autouse=True)
def isolated_temp_directory(tmp_path_factory, monkeypatch):
    directory = tmp_path_factory.mktemp("temp")

    for name in TEMP_DIRECTORY_VARIABLES:
        monkeypatch.setenv(name, str(directory))

    return directory
