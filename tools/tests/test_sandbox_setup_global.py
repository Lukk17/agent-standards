"""Tests for sandbox-agent/setup-global.sh, the container's global install.

The script is loaded without its last two lines, which run the install, so one
function can be called on its own against this repository.
"""

import json
import shutil
import subprocess

import pytest

from tests.conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "sandbox-agent" / "setup-global.sh"
BASH = shutil.which("bash")


def loadable(tmp_path):
    lines = SCRIPT.read_text(encoding="utf-8").splitlines()
    assert lines[-2:] == ['main "$@"', 'exit "$EXIT_CODE"']
    path = tmp_path / "setup-global-loadable.sh"
    path.write_text("\n".join(lines[:-2]) + "\n", encoding="utf-8")
    return path


@pytest.mark.skipif(BASH is None, reason="bash is not installed")
def test_the_copilot_hooks_file_names_every_hook_by_its_installed_absolute_path(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    result = subprocess.run(
        [BASH, "-c", f"source '{loadable(tmp_path).as_posix()}'; SRC='{REPO_ROOT.as_posix()}'; copilot_hooks"],
        capture_output=True, text=True, env={"HOME": str(home), "PATH": "/usr/bin:/bin"},
    )

    assert result.returncode == 0, result.stderr
    assert ".agents/hooks/" not in result.stdout
    commands = [entry["bash"] for entries in json.loads(result.stdout)["hooks"].values() for entry in entries]
    scripts = [word for command in commands for word in command.split() if word.endswith('.py')]
    assert scripts and all(word.startswith(f"{home.as_posix()}/.config/agents/hooks/") for word in scripts), scripts
