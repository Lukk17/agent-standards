#!/usr/bin/env python3
"""Render the Claude Code plugin marketplace from tools/plugins.yaml and the items' own files.

Source of truth:  tools/plugins.yaml               hooks, servers and bundles, each with its version
                  .agents/skills/<name>/SKILL.md    one skill plugin each, version in metadata.version
                  subagents/<name>.md               one agent-<name> plugin each, version in version
                  .claude/settings.json             the Claude Code wiring each hook plugin copies
                  .mcp.json                         the server block each mcp-<name> plugin carries
Generated:        .claude-plugin/marketplace.json   committed, checked by --check in CI

Every plugin points at files that already sit in the repository, so no plugin
file is ever copied into it:

- a skill plugin is the skill folder itself, `./.agents/skills/<skill>`, with
  SKILL.md at the plugin root, which installs that one skill;
- an agent plugin is the agent's own folder of the generated Claude Code tree,
  `./.claude/agents/<name>`, with `strict: false` and an `agents` list naming
  the file, and the skills it preloads as its dependencies;
- a hook plugin is the hook's folder, `./.agents/hooks/<hook>`, with the hook
  commands of the project wiring inline, each running the script from
  `${CLAUDE_PLUGIN_ROOT}` instead;
- a server plugin and a bundle point at `./.claude-plugin` and carry nothing
  but their entry: the server block inline, or the plugin names a bundle
  installs as dependencies.

A marketplace entry with no plugin.json "is the manifest regardless of
`strict`" (https://code.claude.com/docs/en/plugins/marketplace-reference,
"How an entry combines with plugin.json"), so no plugin.json is ever written
and each version is stated once, in its entry. Claude Code keeps a user on the
cached copy until that string changes
(https://code.claude.com/docs/en/plugins/loading, "How Claude Code computes the
version"), which is why tools/check_versions.py makes every change raise it.

Usage:
  python tools/gen_plugins.py            write .claude-plugin/marketplace.json
  python tools/gen_plugins.py --check    exit 1 when the committed file is stale
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass

import yaml

import gen_subagents

ROOT = pathlib.Path(__file__).resolve().parents[1]
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
HOOK_SCRIPT = re.compile(r"\.agents/hooks/((?:[a-z0-9-]+/)*[a-z0-9-]+)/([A-Za-z0-9_]+\.py)")
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
            folder=str(item.get("folder") or item["name"]),
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


def front_matter(path: pathlib.Path) -> dict:
    """The YAML front matter of a manifest, as a mapping."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PluginMapError(f"cannot read {path}: {exc}") from exc
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        raise PluginMapError(f"{path} has no front matter")
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise PluginMapError(f"{path} front matter is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise PluginMapError(f"{path} front matter is not a mapping")
    return data


def load_skills(root: pathlib.Path) -> dict[str, Skill]:
    """Every skill folder, with the version and description its SKILL.md declares."""
    skills: dict[str, Skill] = {}
    for manifest in sorted((root / SKILLS_DIR).glob("*/SKILL.md")):
        data = front_matter(manifest)
        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        version = _version(metadata.get("version"), f"{manifest} metadata.version")
        skills[manifest.parent.name] = Skill(manifest.parent.name, version, str(data.get("description", "")).strip())
    return skills


def load_agents(root: pathlib.Path, skills: set[str]) -> dict[str, Agent]:
    """Every canonical subagent, parsed and validated the way gen_subagents does."""
    agents: dict[str, Agent] = {}
    for path in sorted((root / SUBAGENTS_DIR).glob("*.md")):
        data, _body = gen_subagents.parse(path, skills)
        version = _version(data.get("version"), f"{path} version")
        agents[data["name"]] = Agent(data["name"], version, data["description"].strip(), tuple(data.get("skills") or ()))
    return agents


def load_servers(root: pathlib.Path) -> dict[str, dict[str, object]]:
    try:
        return json.loads((root / MCP_FILE).read_text(encoding="utf-8"))["mcpServers"]
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        raise PluginMapError(f"cannot read mcpServers from {root / MCP_FILE}: {exc}") from exc


def plugin_command(command: str) -> str:
    """A project hook command rewritten to run the script from the plugin's own folder."""
    return HOOK_SCRIPT.sub(lambda match: PLUGIN_ROOT_PATH + match.group(2), command)


def _group_key(group: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in group.items() if key != "hooks"}


def wired_hooks(root: pathlib.Path) -> dict[str, dict[str, list[dict[str, object]]]]:
    """The Claude Code wiring of each hook folder, as plugin hooks: folder, then event, then matcher groups.

    Each command that runs a script under .agents/hooks/ moves to the plugin of
    that script's folder with its matcher, its timeout and its arguments, and
    runs the script from ${CLAUDE_PLUGIN_ROOT} instead. A command that runs no
    script, such as a reminder printed with echo, stays with the project wiring.
    """
    try:
        settings = json.loads((root / CLAUDE_WIRING).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PluginMapError(f"cannot read {root / CLAUDE_WIRING}: {exc}") from exc
    folders: dict[str, dict[str, list[dict[str, object]]]] = {}
    for event, groups in (settings.get("hooks") or {}).items():
        for group in groups:
            for hook in group.get("hooks", []):
                match = HOOK_SCRIPT.search(str(hook.get("command", "")))
                if not match:
                    continue
                event_groups = folders.setdefault(match.group(1), {}).setdefault(event, [])
                copied = {**hook, "command": plugin_command(hook["command"])}
                same = next((g for g in event_groups if _group_key(g) == _group_key(group)), None)
                if same is None:
                    event_groups.append({**_group_key(group), "hooks": [copied]})
                else:
                    same["hooks"].append(copied)
    return folders


def load_sources(root: pathlib.Path = ROOT, map_path: pathlib.Path | None = None) -> Sources:
    """Read every input of the marketplace from one repository root."""
    plugin_map = load_map(map_path or root / MAP_FILE)
    skills = load_skills(root)
    return Sources(
        root=root,
        plugin_map=plugin_map,
        skills=skills,
        agents=load_agents(root, set(skills)),
        servers=load_servers(root),
        wired_hooks=wired_hooks(root),
    )


def _domain_homes(bundles: Iterable[Bundle], attribute: str) -> dict[str, list[str]]:
    homes: dict[str, list[str]] = {}
    for bundle in bundles:
        if bundle.category in DOMAIN_CATEGORIES:
            for item in getattr(bundle, attribute):
                homes.setdefault(item, []).append(bundle.name)
    return homes


def plugin_names(sources: Sources) -> list[str]:
    """Every plugin name the marketplace lists, duplicates included so check_map can report them."""
    plugin_map = sources.plugin_map
    return [
        *(bundle.name for bundle in plugin_map.bundles),
        *(AGENT_PREFIX + name for name in sources.agents),
        *sources.skills,
        *(hook.plugin for hook in plugin_map.hooks),
        *(server.plugin for server in plugin_map.servers),
    ]


def dependency_graph(sources: Sources) -> dict[str, tuple[str, ...]]:
    """What each plugin depends on: a bundle its members, an agent the skills it preloads."""
    graph: dict[str, tuple[str, ...]] = {AGENT_PREFIX + agent.name: agent.skills for agent in sources.agents.values()}
    graph.update({bundle.name: bundle.members for bundle in sources.plugin_map.bundles})
    return graph


def dependency_closure(name: str, graph: dict[str, tuple[str, ...]]) -> set[str]:
    """Every plugin installing `name` pulls in, not counting `name` itself."""
    seen: set[str] = set()
    stack = list(graph.get(name, ()))
    while stack:
        current = stack.pop()
        if current not in seen:
            seen.add(current)
            stack.extend(graph.get(current, ()))
    return seen


def find_cycle(graph: dict[str, tuple[str, ...]]) -> list[str] | None:
    """One dependency cycle as a path of names, or None."""
    state: dict[str, int] = {}
    path: list[str] = []

    def visit(name: str) -> list[str] | None:
        state[name] = 1
        path.append(name)
        for dependency in graph.get(name, ()):
            if state.get(dependency) == 1:
                return path[path.index(dependency):] + [dependency]
            if dependency not in state and (cycle := visit(dependency)):
                return cycle
        path.pop()
        state[name] = 2
        return None

    for name in graph:
        if name not in state and (cycle := visit(name)):
            return cycle
    return None


def _set_problems(what: str, actual: set[str], expected: set[str]) -> list[str]:
    problems = []
    if missing := sorted(expected - actual):
        problems.append(f"{what}: missing {', '.join(missing)}")
    if extra := sorted(actual - expected):
        problems.append(f"{what}: must not include {', '.join(extra)}")
    return problems


def _name_problems(sources: Sources) -> list[str]:
    names = plugin_names(sources)
    problems = [f"plugin name {n!r} is used by {names.count(n)} plugins" for n in sorted(set(names)) if names.count(n) > 1]
    problems += [f"plugin name {n!r} is not kebab-case" for n in sorted(set(names)) if not KEBAB.fullmatch(n)]
    problems += [f"no {r!r} bundle" for r in (CORE, ALL, MCP_ALL, HOOKS_ALL) if sources.plugin_map.bundle(r) is None]
    return problems


def _membership_problems(sources: Sources) -> list[str]:
    problems: list[str] = []
    bundles = sources.plugin_map.bundles
    for kind, homes, known in (
        ("skill", _domain_homes(bundles, "skills"), set(sources.skills)),
        ("subagent", _domain_homes(bundles, "agents"), set(sources.agents)),
    ):
        problems += [f"{kind} {k!r} sits in {len(v)} bundles: {', '.join(v)}" for k, v in sorted(homes.items()) if len(v) > 1]
        problems += [f"{kind} {k!r} in bundle {v[0]!r} does not exist" for k, v in sorted(homes.items()) if k not in known]
        problems += [f"{kind} {k!r} sits in no development or host bundle" for k in sorted(known - set(homes))]
    for bundle in bundles:
        if bundle.category not in BUNDLE_CATEGORIES:
            problems.append(f"bundle {bundle.name!r} has unknown category {bundle.category!r}, use one of {', '.join(sorted(BUNDLE_CATEGORIES))}")
        elif bundle.category == BUNDLE and (bundle.agents or bundle.skills):
            problems.append(f"bundle {bundle.name!r} has category {BUNDLE!r}, so it lists other plugins as dependencies only")
        if not bundle.members:
            problems.append(f"bundle {bundle.name!r} installs nothing")
    return problems


def _wiring_problems(sources: Sources) -> list[str]:
    plugin_map = sources.plugin_map
    folders = [hook.folder for hook in plugin_map.hooks]
    problems = [f"hook folder {f!r} has {folders.count(f)} hook entries" for f in sorted(set(folders)) if folders.count(f) > 1]
    problems += [f"hook {h.name!r} must be named for its folder {h.folder!r}" for h in plugin_map.hooks if h.folder.rsplit("/", 1)[-1] != h.name]
    problems += [f"hook {h.name!r} has no folder {HOOKS_DIR / h.folder}" for h in plugin_map.hooks if not (sources.root / HOOKS_DIR / h.folder).is_dir()]
    problems += [f"hook {h.name!r} is not run by {CLAUDE_WIRING}, so its plugin would do nothing" for h in plugin_map.hooks if h.folder not in sources.wired_hooks]
    problems += [f"{CLAUDE_WIRING} runs a script in {HOOKS_DIR / f} that no hook entry covers" for f in sorted(set(sources.wired_hooks) - set(folders))]
    served = [server.name for server in plugin_map.servers]
    problems += [f"server {s!r} has {served.count(s)} server entries" for s in sorted(set(served)) if served.count(s) > 1]
    problems += [f"server {s!r} is not in the root {MCP_FILE}" for s in sorted(set(served) - set(sources.servers))]
    problems += [f"server {s!r} in the root {MCP_FILE} has no server entry" for s in sorted(set(sources.servers) - set(served))]
    return problems


def _graph_problems(sources: Sources) -> list[str]:
    plugin_map = sources.plugin_map
    known = set(plugin_names(sources))
    problems = [
        f"bundle {bundle.name!r} depends on unknown plugin {member!r}"
        for bundle in plugin_map.bundles
        for member in bundle.members
        if member not in known
    ]
    if cycle := find_cycle(dependency_graph(sources)):
        problems.append(f"dependency cycle: {' -> '.join(cycle)}")
    if (core := plugin_map.bundle(CORE)) and (core.agents or core.dependencies):
        problems.append(f"{CORE!r} must hold skills only, with no subagents and no dependencies")
    if mcp_all := plugin_map.bundle(MCP_ALL):
        problems += _set_problems(f"{MCP_ALL!r} depends on every server plugin", set(mcp_all.members), {s.plugin for s in plugin_map.servers})
    if hooks_all := plugin_map.bundle(HOOKS_ALL):
        problems += _set_problems(f"{HOOKS_ALL!r} depends on every hook plugin", set(hooks_all.members), {h.plugin for h in plugin_map.hooks})
    if everything := plugin_map.bundle(ALL):
        development = {b.name for b in plugin_map.bundles if b.category == DEVELOPMENT}
        problems += _set_problems(f"{ALL!r} installs core and every development bundle", set(everything.members), development)
    return problems


def shared_skills(sources: Sources) -> set[str]:
    """Skills preloaded by subagents that sit in two or more different bundles."""
    users: dict[str, set[str]] = {}
    for bundle in sources.plugin_map.bundles:
        for agent_name in bundle.agents:
            for skill in sources.agents[agent_name].skills:
                users.setdefault(skill, set()).add(bundle.name)
    return {skill for skill, owners in users.items() if len(owners) >= 2}


def _core_problems(sources: Sources) -> list[str]:
    plugin_map = sources.plugin_map
    home = {skill: bundles[0] for skill, bundles in _domain_homes(plugin_map.bundles, "skills").items()}
    problems: list[str] = []
    for bundle in plugin_map.bundles:
        for agent_name in bundle.agents:
            for skill in sources.agents[agent_name].skills:
                if home[skill] not in (bundle.name, CORE):
                    problems.append(
                        f"subagent {agent_name!r} in {bundle.name!r} preloads {skill!r} from {home[skill]!r}. "
                        f"Move the subagent to {home[skill]!r}, or the skill to {CORE!r} if two bundles now use it"
                    )
                elif home[skill] == CORE and CORE not in bundle.dependencies:
                    problems.append(f"bundle {bundle.name!r} preloads {CORE!r} skill {skill!r} but does not depend on {CORE!r}")
    core = plugin_map.bundle(CORE)
    core_skills = set(core.skills) if core else set()
    shared = shared_skills(sources)
    problems += [f"skill {s!r} is in {CORE!r} but subagents in fewer than two bundles preload it" for s in sorted(core_skills - shared)]
    problems += [f"skill {s!r} is preloaded by subagents in two or more bundles, so it belongs in {CORE!r}" for s in sorted(shared - core_skills)]
    return problems


def check_map(sources: Sources) -> list[str]:
    """Every rule the map has to meet, as a list of problems. Empty means renderable."""
    problems = _name_problems(sources) + _membership_problems(sources) + _wiring_problems(sources) + _graph_problems(sources)
    return problems or _core_problems(sources)


def _source(path: pathlib.PurePosixPath) -> str:
    return f"./{path}"


def bundle_entry(bundle: Bundle) -> dict[str, object]:
    return {
        "name": bundle.name,
        "source": ENTRY_ONLY_SOURCE,
        "version": bundle.version,
        "description": bundle.description,
        "category": bundle.category,
        "dependencies": list(bundle.members),
    }


def agent_entry(agent: Agent) -> dict[str, object]:
    entry: dict[str, object] = {
        "name": AGENT_PREFIX + agent.name,
        "source": _source(CLAUDE_AGENTS_DIR / agent.name),
        "strict": False,
        "version": agent.version,
        "description": agent.description,
        "category": AGENT_CATEGORY,
        "agents": [f"./{agent.name}.md"],
    }
    if agent.skills:
        entry["dependencies"] = list(agent.skills)
    return entry


def skill_entry(skill: Skill) -> dict[str, object]:
    return {
        "name": skill.name,
        "source": _source(SKILLS_DIR / skill.name),
        "version": skill.version,
        "description": skill.description,
        "category": SKILL_CATEGORY,
    }


def hook_entry(hook: Hook, wiring: dict[str, list[dict[str, object]]]) -> dict[str, object]:
    return {
        "name": hook.plugin,
        "source": _source(HOOKS_DIR / hook.folder),
        "version": hook.version,
        "description": hook.description,
        "category": HOOK_CATEGORY,
        "hooks": wiring,
    }


def server_entry(server: Server, block: dict[str, object]) -> dict[str, object]:
    return {
        "name": server.plugin,
        "source": ENTRY_ONLY_SOURCE,
        "version": server.version,
        "description": server.description,
        "category": MCP_CATEGORY,
        "mcpServers": {server.name: block},
    }


def entries(sources: Sources) -> list[dict[str, object]]:
    """Every marketplace entry: bundles, then agents, skills, hooks and servers, each in a stable order."""
    plugin_map = sources.plugin_map
    return [
        *(bundle_entry(bundle) for bundle in plugin_map.bundles),
        *(agent_entry(agent) for agent in sources.agents.values()),
        *(skill_entry(skill) for skill in sources.skills.values()),
        *(hook_entry(hook, sources.wired_hooks[hook.folder]) for hook in plugin_map.hooks),
        *(server_entry(server, sources.servers[server.name]) for server in plugin_map.servers),
    ]


def marketplace(sources: Sources) -> dict[str, object]:
    """The whole marketplace document, after checking the map.

    Raises:
        PluginMapError: the map breaks one of its rules.
    """
    if problems := check_map(sources):
        raise PluginMapError("the plugin map breaks its rules:\n  " + "\n  ".join(problems))
    market = sources.plugin_map.marketplace
    document: dict[str, object] = {"name": market["name"], "owner": market["owner"]}
    if "description" in market:
        document["description"] = market["description"]
    document["plugins"] = entries(sources)
    return document


def owned_paths(entry: dict[str, object]) -> list[pathlib.PurePosixPath]:
    """The repository paths whose content an entry ships, besides the entry itself.

    A skill, an agent and a hook ship their source folder, and an agent also
    the canonical file its folder is generated from. A server and a bundle
    point at the marketplace folder and ship nothing but their entry.
    """
    source = str(entry["source"])
    if source == ENTRY_ONLY_SOURCE:
        return []
    paths = [pathlib.PurePosixPath(source.removeprefix("./"))]
    if entry.get("category") == AGENT_CATEGORY:
        paths.append(SUBAGENTS_DIR / (str(entry["name"]).removeprefix(AGENT_PREFIX) + ".md"))
    return paths


def render_text(document: dict[str, object]) -> str:
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    check = "--check" in args
    target = ROOT / MARKETPLACE_FILE
    try:
        document = marketplace(load_sources(ROOT))
    except PluginMapError as exc:
        sys.exit(f"ERROR {exc}")
    text = render_text(document)
    count = len(document["plugins"])
    current = target.read_text(encoding="utf-8") if target.is_file() else None
    if check:
        if current != text:
            sys.exit(f"STALE: {MARKETPLACE_FILE} does not match its sources. Run `python tools/gen_plugins.py` and commit")
        print(f"ok: {MARKETPLACE_FILE} lists {count} plugins and is up to date")
        return
    if current != text:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    print(f"done: {count} plugins -> {MARKETPLACE_FILE}")


if __name__ == "__main__":
    main()
