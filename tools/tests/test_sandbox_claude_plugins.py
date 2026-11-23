"""Tests for sandbox-agent/lib-claude-plugins.sh and the Claude Code step of sandbox-agent/setup-project.sh.

The sandbox gives Claude Code the plugin route docs/AGENT_TOOLING.md step 1
tells a consumer to take: no .claude tree by checkout but the workflows, the
marketplace added and the bundles installed at project scope. The library is
driven here with a real smart HTTP server over a small repository and a
`claude` that only records what it was asked, so nothing is installed and no
session starts.
"""

import json
import re
import shlex
import shutil
import socket
import subprocess
from pathlib import Path

import pytest

from tests.conftest import REPO_ROOT, SUBPROCESS_TIMEOUT_SECONDS

SANDBOX = REPO_ROOT / "sandbox-agent"
LIBRARY = SANDBOX / "lib-claude-plugins.sh"
SETUP = SANDBOX / "setup-project.sh"
CONSUMER_DOCUMENT = REPO_ROOT / "docs" / "AGENT_TOOLING.md"
BASH = shutil.which("bash")
GIT = shutil.which("git")
FAKE_CLAUDE = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$CLAUDE_RECORD"
if [[ "$2" == "marketplace" ]]; then
  mkdir -p .claude
  printf '{"extraKnownMarketplaces": {"lab": {"source": {"source": "git", "url": "%s"}}}}\\n' "$4" > .claude/settings.json
fi
"""

needs_bash = pytest.mark.skipif(BASH is None or GIT is None, reason="bash and git are not installed")


def step_one() -> str:
    """The first import of the consumer document, from its checkout to the end of the setup."""
    text = CONSUMER_DOCUMENT.read_text(encoding="utf-8")

    return text[text.index("git checkout agent-standards/master -- ") : text.index("That is the whole setup.")]


def array(script: Path, name: str) -> list[str]:
    declared = re.search(rf"^readonly {name}=\(([^)]*)\)$", script.read_text(encoding="utf-8"), re.MULTILINE)
    assert declared, name

    return shlex.split(declared.group(1))


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_the_project_setup_checks_out_no_claude_tree_but_the_workflows():
    paths = array(SETUP, "IMPORT_PATHS")

    assert [path for path in paths if path.startswith(".claude")] == [".claude/workflows"]
    assert not [link for link in array(SETUP, "SYMLINKS") if link.startswith(".claude")]


def test_the_project_setup_checks_out_only_paths_the_consumer_document_names():
    pathspec = set(step_one().splitlines()[0].removeprefix("git checkout agent-standards/master -- ").split())

    assert set(array(SETUP, "IMPORT_PATHS")) <= pathspec


def test_the_project_setup_installs_the_bundles_the_consumer_document_installs():
    documented = re.findall(r"^claude plugin install ([\w-]+)@agent-standards --scope project$", step_one(), re.MULTILINE)

    assert documented
    assert array(LIBRARY, "CLAUDE_PROJECT_PLUGINS") == documented
    assert "claude plugin marketplace add Lukk17/agent-standards --scope project" in step_one()


@needs_bash
def test_the_library_serves_the_import_branch_and_installs_every_bundle_at_project_scope(tmp_path):
    # Given a repository with one commit on master and the real smart HTTP server among its tools
    upstream, project, tools, record = tmp_path / "upstream", tmp_path / "project", tmp_path / "bin", tmp_path / "record"
    (upstream / "tools").mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / "tools" / "git_http.py", upstream / "tools" / "git_http.py")
    identity = ["-c", "user.name=lab", "-c", "user.email=lab@example.invalid"]
    subprocess.run([GIT, "init", "--quiet", "--initial-branch=master", str(upstream)], check=True)
    subprocess.run([GIT, "-C", str(upstream), "add", "--all"], check=True)
    subprocess.run([GIT, "-C", str(upstream), *identity, "commit", "--quiet", "-m", "served"], check=True)
    project.mkdir()
    tools.mkdir()
    (tools / "claude").write_text(FAKE_CLAUDE, encoding="utf-8")
    (tools / "claude").chmod(0o755)
    port = free_port()
    script = (
        f"source '{LIBRARY.as_posix()}'; trap claude_market_stop EXIT; "
        f"claude_market_start '{upstream.as_posix()}' && git ls-remote \"$CLAUDE_MARKET_URL\" && "
        f"claude_plugins_install '{project.as_posix()}' && claude_market_stop && "
        f"if (exec 3<>/dev/tcp/127.0.0.1/{port}) 2>/dev/null; then echo still-serving; else echo stopped; fi"
    )

    # When the library serves it, installs into a project and stops
    result = subprocess.run(
        [BASH, "-c", script],
        capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_SECONDS,
        env={"PATH": f"{tools}:{Path(BASH).parent}:{Path(GIT).parent}:{Path(shutil.which('python3')).parent}:/usr/bin:/bin",
             "HOME": str(tmp_path), "SANDBOX_CLAUDE_MARKET_PORT": str(port), "CLAUDE_RECORD": str(record), "TMPDIR": str(tmp_path)},
    )

    # Then the branch was readable over HTTP, the three commands ran in order at project scope, and the port is closed again
    assert result.returncode == 0, result.stderr
    url = f"http://127.0.0.1:{port}/marketplace.git"
    assert "refs/heads/master" in result.stdout and result.stdout.splitlines()[-1] == "stopped"
    assert record.read_text(encoding="utf-8").splitlines() == [
        f"plugin marketplace add {url} --scope project",
        "plugin install all@lab --scope project",
        "plugin install hooks-all@lab --scope project",
    ]
    assert json.loads((project / ".claude" / "settings.json").read_text(encoding="utf-8"))["extraKnownMarketplaces"]["lab"]["source"]["url"] == url


@needs_bash
def test_the_library_refuses_a_repository_with_no_import_branch(tmp_path):
    upstream = tmp_path / "upstream"
    subprocess.run([GIT, "init", "--quiet", "--initial-branch=feature", str(upstream)], check=True)

    result = subprocess.run(
        [BASH, "-c", f"source '{LIBRARY.as_posix()}'; claude_market_start '{upstream.as_posix()}'; echo \"status=$? pid=${{CLAUDE_MARKET_PID:-none}}\""],
        capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )

    assert result.stdout.strip() == "status=1 pid=none"
