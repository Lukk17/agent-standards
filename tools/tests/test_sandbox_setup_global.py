"""Tests for sandbox-agent/setup-global.sh, the container's global install.

The script is loaded without its last two lines, which run the install, so one
function can be called on its own against this repository. The Claude Code
install is driven with a real smart HTTP server over a small repository and a
`claude` that only records what it was asked, so nothing is installed and no
session starts.
"""

import json
import shutil
import socket
import subprocess
from pathlib import Path

import pytest

from tests.conftest import REPO_ROOT, SUBPROCESS_TIMEOUT_SECONDS

SCRIPT = REPO_ROOT / "sandbox-agent" / "setup-global.sh"
LIBRARY = REPO_ROOT / "sandbox-agent" / "lib-claude-plugins.sh"
BASH = shutil.which("bash")
GIT = shutil.which("git")
SYSTEM_PATH = "/usr/bin:/bin"
FAKE_CLAUDE = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$CLAUDE_RECORD"
if [[ "$2" == "marketplace" ]]; then
  mkdir -p "$HOME/.claude"
  printf '{"extraKnownMarketplaces": {"lab": {"source": {"source": "git", "url": "%s"}}}}\\n' "$4" > "$HOME/.claude/settings.json"
fi
"""


def loadable(tmp_path):
    lines = SCRIPT.read_text(encoding="utf-8").splitlines()
    assert lines[-2:] == ['main "$@"', 'exit "$EXIT_CODE"']
    path = tmp_path / "setup-global-loadable.sh"
    path.write_text("\n".join(lines[:-2]) + "\n", encoding="utf-8")
    shutil.copyfile(LIBRARY, tmp_path / LIBRARY.name)
    return path


def served_upstream(root: Path) -> Path:
    """A repository with one commit on master that holds the smart HTTP server the library starts."""
    upstream = root / "upstream"
    (upstream / "tools").mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / "tools" / "git_http.py", upstream / "tools" / "git_http.py")
    identity = ["-c", "user.name=lab", "-c", "user.email=lab@example.invalid"]
    subprocess.run([GIT, "init", "--quiet", "--initial-branch=master", str(upstream)], check=True)
    subprocess.run([GIT, "-C", str(upstream), "add", "--all"], check=True)
    subprocess.run([GIT, "-C", str(upstream), *identity, "commit", "--quiet", "-m", "served"], check=True)
    return upstream


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


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


@pytest.mark.skipif(BASH is None or GIT is None, reason="bash and git are not installed")
def test_the_claude_code_install_writes_the_import_and_installs_plugins_and_nothing_else_under_its_directory(tmp_path):
    # Given a home with no Claude Code directory, a served repository and a claude that records its calls
    home, tools, start, record = tmp_path / "home", tmp_path / "bin", tmp_path / "start", tmp_path / "record"
    upstream = served_upstream(tmp_path)
    for folder in (home, tools, start):
        folder.mkdir()
    (tools / "claude").write_text(FAKE_CLAUDE, encoding="utf-8")
    (tools / "claude").chmod(0o755)
    port = free_port()
    script = (
        f"source '{loadable(tmp_path).as_posix()}'; CLONE_PARENT='{start.as_posix()}'; install_claude && "
        f"if (exec 3<>/dev/tcp/127.0.0.1/{port}) 2>/dev/null; then echo still-serving; else echo stopped; fi"
    )

    # When the sandbox installs for Claude Code
    result = subprocess.run(
        [BASH, "-c", script],
        capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_SECONDS,
        env={"PATH": f"{tools}:{Path(BASH).parent}:{Path(GIT).parent}:{Path(shutil.which('python3')).parent}:/usr/bin:/bin",
             "HOME": str(home), "AGENT_STANDARDS_REPO": str(upstream), "SANDBOX_CLAUDE_MARKET_PORT": str(port),
             "CLAUDE_RECORD": str(record), "TMPDIR": str(tmp_path)},
    )

    # Then the one shared file is imported, every command carried the user scope, and the marketplace is stopped again
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[-1] == "stopped"
    assert (home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8") == "@~/.config/agents/AGENTS.md\n"
    calls = record.read_text(encoding="utf-8").splitlines()
    assert calls[0] == f"plugin marketplace add http://127.0.0.1:{port}/marketplace.git --scope user"
    assert len(calls) > 1 and all(call.startswith("plugin install ") and call.endswith("@lab --scope user") for call in calls[1:])
    assert sorted(path.name for path in (home / ".claude").iterdir()) == ["CLAUDE.md", "settings.json"]
    assert "hooks" not in json.loads((home / ".claude" / "settings.json").read_text(encoding="utf-8"))


@pytest.mark.skipif(BASH is None, reason="bash is not installed")
@pytest.mark.skipif(shutil.which("claude", path=SYSTEM_PATH) is not None, reason="a claude command sits on the system path")
def test_the_claude_code_install_fails_when_there_is_no_claude_command(tmp_path):
    home = tmp_path / "home"
    home.mkdir()

    result = subprocess.run(
        [BASH, "-c", f"source '{loadable(tmp_path).as_posix()}'; install_claude"],
        capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_SECONDS, env={"HOME": str(home), "PATH": SYSTEM_PATH},
    )

    assert result.returncode != 0
    assert "no claude command on PATH" in result.stderr
    assert not (home / ".claude" / "skills").exists() and not (home / ".claude" / "agents").exists()
