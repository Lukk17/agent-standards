"""Install plugins from this repository's marketplace with the real Claude Code CLI and check what lands.

Opt-in, because it needs the `claude` command line: set
AGENT_STANDARDS_INSTALL_TEST=1, and CLAUDE_BIN to pick a binary other than the
`claude` on PATH. The Plugins workflow runs it with the pinned Claude Code
release.

The tracked files of the working tree are committed into a scratch repository
and served over smart HTTP by tools/git_http.py, because Claude Code refuses a
file:// marketplace URL and loads a local-path marketplace in place instead of
copying each plugin into its cache. Each install runs against a fresh home and
configuration directory, so it sees only what that one install wrote, and
nothing reaches a model: the plugin commands never start a session.
"""

import json
import os
import pathlib
import shutil
import subprocess

import pytest

import check_versions
import git_http
from tests.conftest import REPO_ROOT

CLAUDE = os.environ.get("CLAUDE_BIN") or shutil.which("claude")
MARKETPLACE = json.loads((REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
ENTRIES = {entry["name"]: entry for entry in MARKETPLACE["plugins"]}
COMMAND_TIMEOUT_SECONDS = 180
# Markers Claude Code writes into a cached plugin folder, which are not plugin files.
CACHE_MARKERS = frozenset({".in_use", ".orphaned_at"})
CLEARED_VARIABLES = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_PLUGIN_ROOT", "CLAUDE_PROJECT_DIR")

pytestmark = [
    pytest.mark.skipif(os.environ.get("AGENT_STANDARDS_INSTALL_TEST") != "1", reason="set AGENT_STANDARDS_INSTALL_TEST=1 to run"),
    pytest.mark.skipif(CLAUDE is None, reason="the claude command line is not installed"),
]


@pytest.fixture(scope="module")
def market_url(tmp_path_factory):
    """The repository's tracked files, committed into a bare repository served over smart HTTP."""
    scratch = tmp_path_factory.mktemp("served")
    source, serve = scratch / "source", scratch / "serve"
    check_versions.copy_tracked(REPO_ROOT, source)
    identity = ("-c", "user.name=install test", "-c", "user.email=install@example.invalid")
    subprocess.run(["git", "init", "--quiet", "--initial-branch=master", str(source)], check=True)
    subprocess.run(["git", "-C", str(source), "add", "--all"], check=True)
    subprocess.run(["git", "-C", str(source), *identity, "commit", "--quiet", "-m", "served"], check=True)
    subprocess.run(["git", "clone", "--quiet", "--bare", str(source), str(serve / "marketplace.git")], check=True)
    with git_http.serving(serve) as base:
        yield f"{base}/marketplace.git"


class Home:
    """One fresh home and Claude Code configuration directory, with the marketplace added at user scope."""

    def __init__(self, root: pathlib.Path, market_url: str) -> None:
        self.root = root
        self.config = root / ".claude"
        self.config.mkdir(parents=True)
        self.claude("marketplace", "add", market_url)

    def environment(self) -> dict[str, str]:
        environment = {key: value for key, value in os.environ.items() if key not in CLEARED_VARIABLES}
        environment.update(
            HOME=str(self.root),
            CLAUDE_CONFIG_DIR=str(self.config),
            DISABLE_AUTOUPDATER="1",
            CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1",
            NO_PROXY="127.0.0.1,localhost",
            no_proxy="127.0.0.1,localhost",
        )
        return environment

    def claude(self, *args: str) -> str:
        result = subprocess.run(
            [CLAUDE, "plugin", *args, "--scope", "user"],
            cwd=self.root,
            env=self.environment(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
        assert result.returncode == 0, f"claude plugin {' '.join(args)}: {result.stdout}{result.stderr}"
        return result.stdout

    def install(self, plugin: str) -> str:
        return self.claude("install", f"{plugin}@{MARKETPLACE['name']}")

    def installed(self) -> set[str]:
        """Every plugin of this marketplace the configuration records as installed."""
        record = json.loads((self.config / "plugins" / "installed_plugins.json").read_text(encoding="utf-8"))
        suffix = f"@{MARKETPLACE['name']}"
        return {key.removesuffix(suffix) for key in record["plugins"] if key.endswith(suffix)}

    def folder(self, plugin: str) -> pathlib.Path:
        """The one cached version folder of a plugin."""
        versions = list((self.config / "plugins" / "cache" / MARKETPLACE["name"] / plugin).iterdir())
        assert [v.name for v in versions] == [ENTRIES[plugin]["version"]], versions
        return versions[0]


def files(folder: pathlib.Path) -> dict[str, bytes]:
    """Every plugin file under a folder by its relative path, links read through, cache markers left out."""
    return {
        path.relative_to(folder).as_posix(): path.read_bytes()
        for path in sorted(folder.rglob("*"))
        if path.is_file() and not CACHE_MARKERS & set(path.relative_to(folder).parts)
    }


def tracked(folder: str) -> dict[str, bytes]:
    """Every tracked file of one repository folder by its path relative to that folder, as the served copy holds it."""
    listed = subprocess.run(["git", "-C", str(REPO_ROOT), "ls-files", "-z", "--", folder], capture_output=True, text=True, check=True)
    names = [name for name in listed.stdout.split("\0") if name]
    return {pathlib.PurePosixPath(name).relative_to(folder).as_posix(): (REPO_ROOT / name).read_bytes() for name in names if (REPO_ROOT / name).is_file()}


def closure(plugin: str) -> set[str]:
    """The plugin and everything installing it pulls in, from the committed marketplace."""
    seen, stack = set(), [plugin]
    while stack:
        current = stack.pop()
        if current not in seen:
            seen.add(current)
            stack.extend(ENTRIES[current].get("dependencies", []))
    return seen


def test_a_skill_plugin_installs_only_that_skill(tmp_path, market_url):
    home = Home(tmp_path, market_url)

    home.install("python-patterns")

    assert home.installed() == {"python-patterns"}
    assert files(home.folder("python-patterns")) == tracked(".agents/skills/python-patterns")


def test_an_agent_plugin_installs_one_agent_file_and_the_skills_it_preloads(tmp_path, market_url):
    home = Home(tmp_path, market_url)
    preloads = set(ENTRIES["agent-python-pro"]["dependencies"])

    home.install("agent-python-pro")

    assert home.installed() == {"agent-python-pro"} | preloads
    assert files(home.folder("agent-python-pro")) == {"python-pro.md": (REPO_ROOT / ".claude" / "agents" / "python-pro" / "python-pro.md").read_bytes()}
    for skill in preloads:
        assert files(home.folder(skill)) == tracked(f".agents/skills/{skill}"), skill


def test_a_hook_plugin_installs_only_that_hook(tmp_path, market_url):
    home = Home(tmp_path, market_url)

    home.install("hook-preflight-gate")

    assert home.installed() == {"hook-preflight-gate"}
    assert files(home.folder("hook-preflight-gate")) == tracked(".agents/hooks/preflight-gate")


def test_a_bundle_installs_every_plugin_it_lists(tmp_path, market_url):
    home = Home(tmp_path, market_url)

    home.install("python")

    assert home.installed() == closure("python")
    assert {"core", "agent-python-pro", "agent-ml-engineer", "pytorch-patterns", "python-patterns"} <= home.installed()


def test_the_quality_loop_skill_carries_robert_c_martins_tools_into_the_cache(tmp_path, market_url):
    home = Home(tmp_path, market_url)

    home.install("quality-loop")

    folder = home.folder("quality-loop")
    assert (folder / "tools").is_dir() and not (folder / "tools").is_symlink()
    assert os.access(folder / "tools" / "run", os.X_OK)
    assert files(folder / "tools") == tracked(".metrics/tools")
