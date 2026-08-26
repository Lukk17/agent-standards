"""Shared filesystem paths for the hook and tooling test suite.

Every test in this package drives a real hook script as a subprocess, and those
scripts live in .agents/hooks/ at the repository root, two levels above this
package. Resolving that root once here keeps the location in a single place.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = REPO_ROOT / ".agents" / "hooks"
PREFLIGHT_GATE = HOOKS_DIR / "preflight_gate.py"
NO_AI_MARKERS_HOOK = HOOKS_DIR / "no_ai_markers_check.py"
PLUGIN = REPO_ROOT / ".agents" / "plugin" / "hooks.js"
RUNNER_DRIVER = Path(__file__).resolve().parent / "hook_runner_driver.mjs"
