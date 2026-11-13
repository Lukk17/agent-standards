"""The plugin map of tools/plugins.yaml: its names, its types and how it is read.

tools/gen_plugins.py reads the map with parse_map and the items' own files
into Sources, tools/plugin_map_rules.py checks the result, and
tools/check_versions.py and the tests share the names below.
"""
from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass

import yaml

MAP_FILE = pathlib.PurePosixPath("tools/plugins.yaml")
MARKETPLACE_FILE = pathlib.PurePosixPath(".claude-plugin/marketplace.json")
SKILLS_DIR = pathlib.PurePosixPath(".agents/skills")
HOOKS_DIR = pathlib.PurePosixPath(".agents/hooks")
SUBAGENTS_DIR = pathlib.PurePosixPath("subagents")
CLAUDE_AGENTS_DIR = pathlib.PurePosixPath(".claude/agents")
CLAUDE_WIRING = pathlib.PurePosixPath(".claude/settings.json")
MCP_FILE = pathlib.PurePosixPath(".mcp.json")

ENTRY_ONLY_SOURCE = "./.claude-plugin"
AGENT_PREFIX = "agent-"
HOOK_PREFIX = "hook-"
MCP_PREFIX = "mcp-"
CORE = "core"
ALL = "all"
MCP_ALL = "mcp-all"
HOOKS_ALL = "hooks-all"
DEVELOPMENT = "development"
HOST = "host"
BUNDLE = "bundle"
BUNDLE_CATEGORIES = frozenset({DEVELOPMENT, HOST, BUNDLE})
DOMAIN_CATEGORIES = frozenset({DEVELOPMENT, HOST})
AGENT_CATEGORY = "agent"
SKILL_CATEGORY = "skill"
HOOK_CATEGORY = "hook"
MCP_CATEGORY = "mcp"

# Kebab-case, matched whole: lowercase words joined by single hyphens.
KEBAB = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
# MAJOR.MINOR.PATCH, each part without a leading zero, the form a release tag carries.
SEMVER = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")
GITHUB_REPOSITORY = re.compile(r"https://github\.com/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+/?")
# A hook command of the project wiring names its script as .agents/hooks/<folder>/<script>.py.
HOOK_FOLDER = r"(?:[a-z0-9-]+/)*[a-z0-9-]+"
HOOK_SCRIPT = re.compile(rf"\.agents/hooks/({HOOK_FOLDER})/([A-Za-z0-9_]+\.py)")
PLUGIN_ROOT_PATH = '"${CLAUDE_PLUGIN_ROOT}"/'

MARKETPLACE_KEYS = frozenset({"name", "description", "owner", "repository", "license"})
HOOK_KEYS = frozenset({"name", "version", "description", "folder"})
SERVER_KEYS = frozenset({"name", "version", "description"})
BUNDLE_KEYS = frozenset({"name", "version", "category", "description", "dependencies", "agents", "skills"})


class PluginMapError(Exception):
    """The plugin map or a file it reads cannot be rendered."""


@dataclass(frozen=True, slots=True)
class Hook:
    name: str
    version: str
    description: str
    folder: str

    @property
    def plugin(self) -> str:
        return HOOK_PREFIX + self.name


@dataclass(frozen=True, slots=True)
class Server:
    name: str
    version: str
    description: str

    @property
    def plugin(self) -> str:
        return MCP_PREFIX + self.name


@dataclass(frozen=True, slots=True)
class Bundle:
    name: str
    version: str
    category: str
    description: str
    dependencies: tuple[str, ...] = ()
    agents: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()

    @property
    def members(self) -> tuple[str, ...]:
        """Every plugin this bundle installs, in entry order: listed plugins first, then agents, then skills."""
        return (*self.dependencies, *(AGENT_PREFIX + agent for agent in self.agents), *self.skills)


@dataclass(frozen=True, slots=True)
class PluginMap:
    marketplace: dict[str, object]
    hooks: tuple[Hook, ...]
    servers: tuple[Server, ...]
    bundles: tuple[Bundle, ...]

    def bundle(self, name: str) -> Bundle | None:
        return next((bundle for bundle in self.bundles if bundle.name == name), None)


@dataclass(frozen=True, slots=True)
class Skill:
    name: str
    version: str
    description: str


@dataclass(frozen=True, slots=True)
class Agent:
    name: str
    version: str
    description: str
    skills: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Sources:
    """Everything the marketplace is rendered from, read once from one repository root."""

    root: pathlib.Path
    plugin_map: PluginMap
    skills: dict[str, Skill]
    agents: dict[str, Agent]
    servers: dict[str, dict[str, object]]
    wired_hooks: dict[str, dict[str, list[dict[str, object]]]]

def _string(raw: dict, key: str, where: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PluginMapError(f"{where} needs a non-empty string '{key}'")
    return value.strip()


def _names(raw: object, where: str) -> tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list) or not all(isinstance(item, str) and item for item in raw):
        raise PluginMapError(f"{where} must be a list of names")
    return tuple(raw)


def _version(value: object, where: str) -> str:
    if not isinstance(value, str) or not SEMVER.fullmatch(value):
        raise PluginMapError(f"{where} needs a version of the form MAJOR.MINOR.PATCH, got {value!r}")
    return value


def _hook_folder(value: object, where: str) -> str:
    """A hook folder relative to .agents/hooks/: kebab-case names joined by slashes, never leaving it."""
    if not isinstance(value, str) or not re.fullmatch(HOOK_FOLDER, value):
        raise PluginMapError(f"{where} needs a 'folder' of kebab-case names joined by '/', got {value!r}")
    return value


def _entries(raw: object, key: str, allowed: frozenset[str], path: pathlib.Path) -> list[tuple[dict, str]]:
    """The mappings under one top-level list, each with the name it is reported by."""
    if not isinstance(raw, dict) or key not in raw:
        raise PluginMapError(f"{path} needs a '{key}' list")
    items = raw[key] or []
    if not isinstance(items, list):
        raise PluginMapError(f"{path} '{key}' must be a list")
    found = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise PluginMapError(f"{key}[{index}] in {path} must be a mapping")
        name = item.get("name")
        where = f"{key[:-1]} {name!r}" if isinstance(name, str) else f"{key}[{index}]"
        if unknown := sorted(set(item) - allowed):
            raise PluginMapError(f"{where} has unknown key(s) {', '.join(unknown)}")
        found.append((item, where))
    return found


def _marketplace(raw: object, path: pathlib.Path) -> dict[str, object]:
    market = raw.get("marketplace") if isinstance(raw, dict) else None
    if not isinstance(market, dict) or set(market) - MARKETPLACE_KEYS:
        raise PluginMapError(f"{path} 'marketplace' takes only {', '.join(sorted(MARKETPLACE_KEYS))}")
    owner = market.get("owner")
    if not isinstance(market.get("name"), str) or not isinstance(owner, dict) or "name" not in owner:
        raise PluginMapError(f"{path} 'marketplace' needs a 'name' and an 'owner' with a 'name'")
    if not GITHUB_REPOSITORY.fullmatch(str(market.get("repository", ""))):
        raise PluginMapError(f"{path} 'marketplace' needs a 'repository' of the form https://github.com/<owner>/<repo>")
    return market


def parse_map(raw: object, path: pathlib.Path) -> PluginMap:
    """Type-check the plugin map. Cross-references are left to check_map."""
    market = _marketplace(raw, path)
    hooks = tuple(
        Hook(
            name=_string(item, "name", where),
            version=_version(item.get("version"), where),
            description=_string(item, "description", where),
            folder=_hook_folder(item.get("folder") or item["name"], where),
        )
        for item, where in _entries(raw, "hooks", HOOK_KEYS, path)
    )
    servers = tuple(
        Server(_string(item, "name", where), _version(item.get("version"), where), _string(item, "description", where))
        for item, where in _entries(raw, "servers", SERVER_KEYS, path)
    )
    bundles = tuple(
        Bundle(
            name=_string(item, "name", where),
            version=_version(item.get("version"), where),
            category=_string(item, "category", where),
            description=_string(item, "description", where),
            dependencies=_names(item.get("dependencies"), f"{where} 'dependencies'"),
            agents=_names(item.get("agents"), f"{where} 'agents'"),
            skills=_names(item.get("skills"), f"{where} 'skills'"),
        )
        for item, where in _entries(raw, "bundles", BUNDLE_KEYS, path)
    )
    return PluginMap(market, hooks, servers, bundles)


def load_map(path: pathlib.Path) -> PluginMap:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise PluginMapError(f"cannot read the plugin map {path}: {exc}") from exc
    return parse_map(raw, path)
