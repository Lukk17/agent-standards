"""Tests for tools/mcp_pins.py and for the pin of every MCP server command this repository ships.

The first group feeds the helper one command at a time, so each floating form
is seen to fail and each exact form to pass. The second group reads the five
MCP files and the plugin map and holds every local server in them to an exact
version, the same one in every file. The third does the same for every
command a document shows that adds a server: a `claude mcp add` line, and a
`python -c` line that ends with the server name and its start command.
"""

import json
import re
import shlex
import tomllib

import pytest

import mcp_pins
from plugin_model import MAP_FILE, load_map
from tests.conftest import REPO_ROOT

DIGEST = "sha256:" + "0123456789abcdef" * 4


# One command at a time


@pytest.mark.parametrize(
    ("command", "package"),
    [
        pytest.param(["npx", "-y", "docs-mcp@1.2.3", "--readOnly"], "docs-mcp@1.2.3", id="npx"),
        pytest.param(["npx", "@scope/docs-mcp@0.0.85"], "@scope/docs-mcp@0.0.85", id="npx-scoped"),
        pytest.param(["uvx", "docs-mcp==2.2.0"], "docs-mcp==2.2.0", id="uvx"),
        pytest.param(["uvx", "--from", "docs-mcp==0.5.1", "docs", "--url", "redis://localhost"], "docs-mcp==0.5.1", id="uvx-from"),
        pytest.param(["uvx", "--env-file", "/home/me/lab.env", "docs-mcp==8.7.0"], "docs-mcp==8.7.0", id="uvx-env-file"),
        pytest.param(["docker", "run", "--init", "-i", "--rm", "-e", "TOKEN", f"lab/docs:1.2.3@{DIGEST}"], f"lab/docs:1.2.3@{DIGEST}", id="docker-tag-and-digest"),
        pytest.param(["docker", "run", "--rm", f"registry.lab:5000/docs:1.2.3@{DIGEST}"], f"registry.lab:5000/docs:1.2.3@{DIGEST}", id="docker-tag-and-digest-with-port"),
    ],
)
def test_a_command_that_names_an_exact_version_is_pinned(command, package):
    assert mcp_pins.package(command) == package
    assert mcp_pins.floating(command) is None


@pytest.mark.parametrize(
    ("command", "reason"),
    [
        pytest.param(["npx", "-y", "docs-mcp@latest"], "names no exact version", id="npx-latest"),
        pytest.param(["npx", "docs-mcp"], "names no exact version", id="npx-no-version"),
        pytest.param(["npx", "docs-mcp@^1.2.3"], "names no exact version", id="npx-range"),
        pytest.param(["npx", "@scope/docs-mcp"], "names no exact version", id="npx-scoped-no-version"),
        pytest.param(["uvx", "docs-mcp"], "names no exact version", id="uvx-no-version"),
        pytest.param(["uvx", "--from", "docs-mcp@latest", "docs"], "names no exact version", id="uvx-latest"),
        pytest.param(["uvx", "docs-mcp>=2"], "names no exact version", id="uvx-range"),
        pytest.param(["docker", "run", "-i", "--rm", "lab/docs"], "names no tag and no digest", id="docker-untagged"),
        pytest.param(["docker", "run", "-i", "--rm", "registry.lab:5000/docs"], "names no tag and no digest", id="docker-untagged-with-port"),
        pytest.param(["docker", "run", "-i", "--rm", f"lab/docs:{mcp_pins.FLOATING_TAG}"], "floats on the tag latest", id="docker-floating-tag"),
        pytest.param(["docker", "run", "-i", "--rm", f"lab/docs:{mcp_pins.FLOATING_TAG}@{DIGEST}"], "names the moving tag latest", id="docker-floating-tag-with-digest"),
        pytest.param(["docker", "run", "--init", "-i", "--rm", "-e", "TOKEN", "lab/docs:1.2.3"], "names the tag '1.2.3' but no digest", id="docker-tag-without-digest"),
        pytest.param(["docker", "run", "--rm", "registry.lab:5000/docs:1.2.3"], "names the tag '1.2.3' but no digest", id="docker-tag-without-digest-with-port"),
        pytest.param(["docker", "run", "-i", "--rm", f"lab/docs@{DIGEST}"], "names a digest but no version tag", id="docker-digest-without-tag"),
        pytest.param(["docker", "run", "-i", "--rm", "lab/docs:1.2.3@sha256:1234"], "names the tag '1.2.3' but no digest", id="docker-short-digest"),
        pytest.param(["docker", "run", "--pull=always", "-i", "lab/docs:1.2.3"], "pulls the image on every start", id="docker-pull-always"),
        pytest.param(["docker", "run", "--pull", "always", "-i", "lab/docs:1.2.3"], "pulls the image on every start", id="docker-pull-always-two-words"),
        pytest.param(["docker", "run", "--pull=always", "-i", f"lab/docs@{DIGEST}"], "pulls the image on every start", id="docker-pull-always-with-digest"),
        pytest.param(["docker", "run", "-i", "--rm"], "names no package", id="docker-no-image"),
        pytest.param(["npx", "-y"], "names no package", id="npx-no-package"),
        pytest.param(["bunx", "docs-mcp@1.2.3"], "unknown launcher 'bunx'", id="unknown-launcher"),
        pytest.param([], "empty command", id="empty"),
    ],
)
def test_a_command_that_floats_names_why(command, reason):
    assert reason in mcp_pins.floating(command)


# The five MCP files and the plugin map


def _json_commands(path, key):
    servers = json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))[key]
    return {name: [block["command"], *block.get("args", [])] for name, block in servers.items() if "command" in block}


def _opencode_commands():
    servers = json.loads((REPO_ROOT / "opencode.json").read_text(encoding="utf-8"))["mcp"]
    return {name: list(block["command"]) for name, block in servers.items() if "command" in block}


def _codex_commands():
    servers = tomllib.loads((REPO_ROOT / ".codex" / "config.toml").read_text(encoding="utf-8"))["mcp_servers"]
    return {name: [block["command"], *block.get("args", [])] for name, block in servers.items() if "command" in block}


def _map_commands():
    servers = load_map(REPO_ROOT / MAP_FILE).servers
    return {server.name: [server.block["command"], *server.block.get("args", [])] for server in servers if "command" in server.block}


def shipped_commands() -> dict[str, dict[str, list[str]]]:
    """Every local server command this repository ships, by file, then by server."""
    return {
        str(MAP_FILE): _map_commands(),
        ".mcp.json": _json_commands(".mcp.json", "mcpServers"),
        ".github/mcp.json": _json_commands(".github/mcp.json", "mcpServers"),
        ".vscode/mcp.json": _json_commands(".vscode/mcp.json", "servers"),
        "opencode.json": _opencode_commands(),
        ".codex/config.toml": _codex_commands(),
    }


def test_every_shipped_server_command_names_an_exact_version():
    floats = {
        f"{file}: {server}": reason
        for file, commands in shipped_commands().items()
        for server, command in commands.items()
        if (reason := mcp_pins.floating(command))
    }

    assert floats == {}


def test_every_file_names_the_package_the_plugin_map_names():
    commands = shipped_commands()
    mapped = {server: mcp_pins.package(command) for server, command in commands[str(MAP_FILE)].items()}

    assert len(mapped) >= 8
    for file, servers in commands.items():
        for server, command in servers.items():
            if server in mapped:
                assert mcp_pins.package(command) == mapped[server], f"{file}: {server}"


def test_every_file_but_the_root_one_declares_local_servers():
    commands = shipped_commands()

    assert commands[".mcp.json"] == {}
    assert all(len(servers) >= 7 for file, servers in commands.items() if file != ".mcp.json"), {f: len(s) for f, s in commands.items()}


# The commands the documents show


MCP_ADD = re.compile(r"^claude mcp add --scope project (?P<name>[a-z0-9-]+) (?:.*? )?-- (?P<command>.+)$")
SCRIPTED_ADD = re.compile(r"^python3? -c '.+' (?P<name>[a-z0-9-]+) (?P<command>(?:docker|npx|uvx) .+)$")


def add_command(line: str) -> tuple[str, list[str]] | None:
    """The server a documented line adds and the command that starts it, or None for any other line."""
    for pattern in (MCP_ADD, SCRIPTED_ADD):
        if match := pattern.match(line.strip()):
            return match["name"], shlex.split(match["command"])
    return None


def documented_commands() -> list[tuple[str, str, list[str]]]:
    """Every line of README.md and docs/ that adds a server, as document, server and command."""
    found = []
    for document in [REPO_ROOT / "README.md", *sorted((REPO_ROOT / "docs").glob("*.md"))]:
        for line in document.read_text(encoding="utf-8").splitlines():
            if added := add_command(line):
                found.append((document.name, *added))
    return found


@pytest.mark.parametrize(
    ("line", "added"),
    [
        pytest.param(
            "claude mcp add --scope project docs -e 'TOKEN=${TOKEN:-}' -- uvx docs-mcp==1.2.3",
            ("docs", ["uvx", "docs-mcp==1.2.3"]),
            id="claude-mcp-add",
        ),
        pytest.param(
            "python3 -c 'import sys;print(sys.argv)' docs uvx --env-file \"<env file>\" docs-mcp==1.2.3",
            ("docs", ["uvx", "--env-file", "<env file>", "docs-mcp==1.2.3"]),
            id="scripted-python3",
        ),
        pytest.param(
            "python -c 'import sys;print(sys.argv)' docs uvx --from docs-mcp==1.2.3 --with 'mcp<2' docs-mcp",
            ("docs", ["uvx", "--from", "docs-mcp==1.2.3", "--with", "mcp<2", "docs-mcp"]),
            id="scripted-python-with-a-quoted-argument",
        ),
        pytest.param(
            "python3 -c 'import sys;print(sys.argv)' docs docker run -i --rm lab/docs:1.2.3",
            ("docs", ["docker", "run", "-i", "--rm", "lab/docs:1.2.3"]),
            id="scripted-docker",
        ),
        pytest.param("python3 -c 'import sys;print(sys.argv)' docs", None, id="scripted-without-a-command"),
        pytest.param("claude mcp get docs", None, id="another-claude-command"),
        pytest.param("uvx docs-mcp==1.2.3", None, id="a-bare-start-command"),
    ],
)
def test_a_documented_line_that_adds_a_server_gives_its_name_and_command(line, added):
    assert add_command(line) == added


def test_the_documents_show_scripted_add_commands_for_a_shipped_server():
    scripted = {
        server
        for document in [REPO_ROOT / "README.md", *sorted((REPO_ROOT / "docs").glob("*.md"))]
        for line in document.read_text(encoding="utf-8").splitlines()
        if (match := SCRIPTED_ADD.match(line.strip())) and (server := match["name"])
    }

    assert scripted & set(_map_commands())


def test_every_documented_add_command_names_an_exact_version():
    documented = documented_commands()

    assert {server for _document, server, _command in documented} >= set(_map_commands())
    for document, server, command in documented:
        assert mcp_pins.floating(command) is None, f"{document}: {server}"


def test_every_documented_add_command_names_the_package_the_plugin_map_names():
    mapped = {server: mcp_pins.package(command) for server, command in _map_commands().items()}

    for document, server, command in documented_commands():
        if server in mapped:
            assert mcp_pins.package(command) == mapped[server], f"{document}: {server}"
