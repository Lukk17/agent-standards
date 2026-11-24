"""Tests that every fixed setting the plugin map gives a server reaches every place that starts it.

A value in a server's env block that holds no substitution, such as
N8N_MCP_TELEMETRY_DISABLED set to "true", is a setting and not the default of
a variable a user may override. Each MCP file that declares the server, and
each `claude mcp add` line of the documents that adds it, carries it unchanged.
"""

import json
import shlex
import tomllib

import pytest

from plugin_model import MAP_FILE, load_map
from tests.conftest import REPO_ROOT

JSON_FILES = {
    ".mcp.json": ("mcpServers", "env"),
    ".github/mcp.json": ("mcpServers", "env"),
    ".vscode/mcp.json": ("servers", "env"),
    "opencode.json": ("mcp", "environment"),
}

MCP_ADD_PREFIX = ["claude", "mcp", "add", "--scope", "project"]
ENV_OPTIONS = frozenset({"-e", "--env"})


def fixed_settings() -> dict[str, dict[str, str]]:
    """Each server of the plugin map that has one, with the env values of its block that hold no substitution."""
    return {
        server.name: fixed
        for server in load_map(REPO_ROOT / MAP_FILE).servers
        if (fixed := {key: str(value) for key, value in dict(server.block.get("env", {})).items() if "$" not in str(value)})
    }


def shipped_env() -> dict[str, dict[str, dict[str, str]]]:
    """The env block of every server in each MCP file, by file, then by server."""
    found = {}
    for relative, (servers_key, env_key) in JSON_FILES.items():
        servers = json.loads((REPO_ROOT / relative).read_text(encoding="utf-8"))[servers_key]
        found[relative] = {name: block.get(env_key, {}) for name, block in servers.items()}
    codex = tomllib.loads((REPO_ROOT / ".codex" / "config.toml").read_text(encoding="utf-8"))["mcp_servers"]
    found[".codex/config.toml"] = {name: block.get("env", {}) for name, block in codex.items()}
    return found


def add_command_env(line: str) -> tuple[str, dict[str, str]] | None:
    """The server a `claude mcp add` line adds and the values its env options set, or None for any other line."""
    if not line.strip().startswith(" ".join(MCP_ADD_PREFIX) + " "):
        return None
    words = shlex.split(line)
    options = words[len(MCP_ADD_PREFIX) + 1 : words.index("--") if "--" in words else len(words)]
    values = [options[index + 1] for index, word in enumerate(options[:-1]) if word in ENV_OPTIONS]
    return words[len(MCP_ADD_PREFIX)], dict(value.split("=", 1) for value in values)


def documented_env() -> list[tuple[str, str, dict[str, str]]]:
    """Every `claude mcp add` line of README.md and docs/, as document, server and env values."""
    found = []
    for document in [REPO_ROOT / "README.md", *sorted((REPO_ROOT / "docs").glob("*.md"))]:
        for line in document.read_text(encoding="utf-8").splitlines():
            if added := add_command_env(line):
                found.append((document.name, *added))
    return found


@pytest.mark.parametrize(
    ("line", "added"),
    [
        pytest.param(
            "claude mcp add --scope project docs -e 'TOKEN=${TOKEN:-}' -e 'QUIET=true' -- npx docs-mcp@1.2.3 -e x",
            ("docs", {"TOKEN": "${TOKEN:-}", "QUIET": "true"}),
            id="env-options-before-the-command",
        ),
        pytest.param(
            "claude mcp add --scope project docs --env 'QUIET=a=b' -- npx docs-mcp@1.2.3",
            ("docs", {"QUIET": "a=b"}),
            id="long-option-and-an-equals-sign-in-the-value",
        ),
        pytest.param("claude mcp add --scope project docs -- npx docs-mcp@1.2.3", ("docs", {}), id="no-env"),
        pytest.param("claude mcp remove --scope project docs", None, id="another-claude-command"),
    ],
)
def test_a_documented_add_line_gives_its_server_and_env_values(line, added):
    assert add_command_env(line) == added


def test_the_plugin_map_turns_off_the_usage_data_of_n8n():
    assert fixed_settings()["n8n"] == {"N8N_MCP_TELEMETRY_DISABLED": "true"}


def test_every_mcp_file_that_declares_a_server_carries_its_fixed_settings():
    settings = fixed_settings()
    missing = {
        f"{file}: {server}": {key: value for key, value in fixed.items() if servers[server].get(key) != value}
        for file, servers in shipped_env().items()
        for server, fixed in settings.items()
        if server in servers and any(servers[server].get(key) != value for key, value in fixed.items())
    }

    assert all(any(server in servers for servers in shipped_env().values()) for server in settings)
    assert missing == {}


def test_every_documented_add_command_carries_the_fixed_settings_of_its_server():
    settings = fixed_settings()
    documented = documented_env()

    assert {server for _document, server, _env in documented} >= set(settings)
    for document, server, env in documented:
        for key, value in settings.get(server, {}).items():
            assert env.get(key) == value, f"{document}: {server} sets {key}={env.get(key)!r}"
