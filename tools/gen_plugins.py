#!/usr/bin/env python3
"""Render the Claude Code plugin marketplace from tools/plugins.yaml.

Source of truth:  tools/plugins.yaml              which plugin holds which skills, subagents and MCP server
                  .agents/skills/<name>/          copied byte for byte
                  subagents/<name>.md             rendered with gen_subagents.emit_claude
                  .mcp.json                       one server block per MCP plugin
Generated:        <out>/.claude-plugin/marketplace.json
                  <out>/plugins/<plugin>/.claude-plugin/plugin.json
                  <out>/plugins/<plugin>/skills/, agents/, .mcp.json
                  <out>/LICENSE, <out>/README.md

The output is never committed on master. CI renders it on every push to master
and commits it to the `plugins` branch, which users add as a marketplace with
`claude plugin marketplace add Lukk17/agent-standards#plugins`.

Every file is a real copy. Claude Code's validator does not follow symlinks
(https://code.claude.com/docs/en/plugins/cli-reference, "plugin validate"), and
a plugin cannot reach files outside its own directory
(https://code.claude.com/docs/en/plugins/loading).

Each plugin's `version` is a hash of its own rendered content. Claude Code keeps
users on a cached copy until the version string changes
(https://code.claude.com/docs/en/plugins/host-marketplace, "Bump `version` on
each release"), so a plugin re-versions only when something inside it changed.

The output directory has to sit outside the repository, so a render can never
land in the working tree, and the tree is rendered into a sibling temporary
directory first and moved into place only once every plugin is written, so a
failed render leaves nothing behind.

Usage:
  python tools/gen_plugins.py <out-dir>                 render into an empty or missing directory
  python tools/gen_plugins.py <out-dir> --map <file>    render from another plugin map
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import shutil
import stat
import sys
import tempfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

import yaml

import gen_subagents

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_MAP = ROOT / "tools" / "plugins.yaml"

CORE = "core"
ALL = "all"
MCP_ALL = "mcp-all"
MCP_PREFIX = "mcp-"
DEVELOPMENT_CATEGORY = "development"
HOST_CATEGORY = "host"
MCP_CATEGORY = "mcp"
BUNDLE_CATEGORY = "bundle"
CATEGORIES = frozenset({DEVELOPMENT_CATEGORY, HOST_CATEGORY, MCP_CATEGORY, BUNDLE_CATEGORY})
VERSION_LENGTH = 12
# Kebab-case, matched whole with fullmatch: lowercase words joined by single hyphens.
PLUGIN_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
GITHUB_REPOSITORY = re.compile(r"https://github\.com/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+/?")
PLUGIN_KEYS = frozenset(
    {"name", "description", "category", "dependencies", "agents", "skills", "mcp", "defaultEnabled"}
)
MARKETPLACE_KEYS = frozenset({"name", "description", "owner", "repository", "license"})

# Local build leftovers that are never part of a skill, even when they sit in
# the working tree. A clean CI checkout has none of them.
IGNORED_NAMES = frozenset({"__pycache__", ".DS_Store"})
IGNORED_SUFFIXES = (".pyc",)

MANIFEST_DIR = ".claude-plugin"
PLUGIN_MANIFEST = "plugin.json"
MARKETPLACE_MANIFEST = "marketplace.json"
MCP_FILE = ".mcp.json"


class PluginMapError(Exception):
    """The plugin map or a source it names cannot be rendered."""


@dataclass(frozen=True, slots=True)
class Sources:
    """Where the generator reads from, so a test can point it at a fixture tree."""

    root: pathlib.Path = ROOT

    @property
    def skills(self) -> pathlib.Path:
        return self.root / ".agents" / "skills"

    @property
    def subagents(self) -> pathlib.Path:
        return self.root / "subagents"

    @property
    def mcp(self) -> pathlib.Path:
        return self.root / ".mcp.json"

    @property
    def license(self) -> pathlib.Path:
        return self.root / "LICENSE"


@dataclass(frozen=True, slots=True)
class Plugin:
    name: str
    description: str
    category: str
    dependencies: tuple[str, ...] = ()
    agents: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    mcp: str | None = None
    default_enabled: bool = True

    @property
    def is_bundle(self) -> bool:
        return not (self.agents or self.skills or self.mcp)


@dataclass(frozen=True, slots=True)
class PluginMap:
    marketplace: dict[str, object]
    plugins: tuple[Plugin, ...]

    def by_name(self) -> dict[str, Plugin]:
        return {plugin.name: plugin for plugin in self.plugins}


@dataclass(frozen=True, slots=True)
class Agent:
    name: str
    skills: tuple[str, ...]
    rendered: str


def _string_list(raw: object, where: str) -> tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list) or not all(isinstance(item, str) and item for item in raw):
        raise PluginMapError(f"{where} must be a list of names")
    return tuple(raw)


def parse_plugin(raw: object, index: int) -> Plugin:
    """One plugin entry of the map, with every key and type checked."""
    if not isinstance(raw, dict):
        raise PluginMapError(f"plugins[{index}] must be a mapping")
    unknown = sorted(set(raw) - PLUGIN_KEYS)
    name = raw.get("name")
    where = f"plugin {name!r}" if isinstance(name, str) else f"plugins[{index}]"
    if unknown:
        raise PluginMapError(f"{where} has unknown key(s) {', '.join(unknown)}")
    for key in ("name", "description", "category"):
        if not isinstance(raw.get(key), str) or not raw[key].strip():
            raise PluginMapError(f"{where} needs a non-empty string '{key}'")
    mcp = raw.get("mcp")
    if mcp is not None and not (isinstance(mcp, str) and mcp):
        raise PluginMapError(f"{where} 'mcp' must be one server name")
    default_enabled = raw.get("defaultEnabled", True)
    if not isinstance(default_enabled, bool):
        raise PluginMapError(f"{where} 'defaultEnabled' must be true or false")
    return Plugin(
        name=raw["name"],
        description=raw["description"].strip(),
        category=raw["category"],
        dependencies=_string_list(raw.get("dependencies"), f"{where} 'dependencies'"),
        agents=_string_list(raw.get("agents"), f"{where} 'agents'"),
        skills=_string_list(raw.get("skills"), f"{where} 'skills'"),
        mcp=mcp,
        default_enabled=default_enabled,
    )


def load_map(path: pathlib.Path = DEFAULT_MAP) -> PluginMap:
    """Read and type-check the plugin map. Cross-references are checked by check_map."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise PluginMapError(f"cannot read the plugin map {path}: {exc}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("plugins"), list):
        raise PluginMapError(f"{path} needs a 'marketplace' mapping and a 'plugins' list")
    marketplace = raw.get("marketplace")
    if not isinstance(marketplace, dict) or set(marketplace) - MARKETPLACE_KEYS:
        raise PluginMapError(f"{path} 'marketplace' takes only {', '.join(sorted(MARKETPLACE_KEYS))}")
    owner = marketplace.get("owner")
    if not isinstance(marketplace.get("name"), str) or not isinstance(owner, dict) or "name" not in owner:
        raise PluginMapError(f"{path} 'marketplace' needs a 'name' and an 'owner' with a 'name'")
    repository = marketplace.get("repository")
    if not isinstance(repository, str) or not GITHUB_REPOSITORY.fullmatch(repository):
        raise PluginMapError(
            f"{path} 'marketplace' needs a 'repository' of the form https://github.com/<owner>/<repo>, "
            "because the branch README names the marketplace by it"
        )
    return PluginMap(marketplace, tuple(parse_plugin(item, i) for i, item in enumerate(raw["plugins"])))


def load_agents(sources: Sources, skills: set[str]) -> dict[str, Agent]:
    """Every canonical subagent, rendered exactly as gen_subagents writes .claude/agents/."""
    agents: dict[str, Agent] = {}
    for path in sorted(sources.subagents.glob("*.md")):
        front_matter, body = gen_subagents.parse(path, skills)
        name = front_matter["name"]
        agents[name] = Agent(
            name=name,
            skills=tuple(front_matter.get("skills") or ()),
            rendered=gen_subagents.emit_claude(front_matter, body),
        )
    return agents


def load_servers(sources: Sources) -> dict[str, dict[str, object]]:
    try:
        servers = json.loads(sources.mcp.read_text(encoding="utf-8"))["mcpServers"]
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        raise PluginMapError(f"cannot read mcpServers from {sources.mcp}: {exc}") from exc
    return servers


def dependency_closure(name: str, plugins: dict[str, Plugin]) -> set[str]:
    """Every plugin that installing `name` pulls in, not counting `name` itself."""
    seen: set[str] = set()
    stack = list(plugins[name].dependencies)
    while stack:
        current = stack.pop()
        if current in seen or current not in plugins:
            continue
        seen.add(current)
        stack.extend(plugins[current].dependencies)
    return seen


def find_cycle(plugins: dict[str, Plugin]) -> list[str] | None:
    """One dependency cycle as a path of names, or None."""
    state: dict[str, int] = {}
    path: list[str] = []

    def visit(name: str) -> list[str] | None:
        state[name] = 1
        path.append(name)
        for dependency in plugins[name].dependencies:
            if dependency not in plugins:
                continue
            if state.get(dependency) == 1:
                return path[path.index(dependency):] + [dependency]
            if dependency not in state and (cycle := visit(dependency)):
                return cycle
        path.pop()
        state[name] = 2
        return None

    for name in plugins:
        if name not in state and (cycle := visit(name)):
            return cycle
    return None


def _homes(plugins: Iterable[Plugin], attribute: str) -> dict[str, list[str]]:
    homes: dict[str, list[str]] = {}
    for plugin in plugins:
        for item in getattr(plugin, attribute):
            homes.setdefault(item, []).append(plugin.name)
    return homes


def shared_skills(plugin_map: PluginMap, agents: dict[str, Agent]) -> set[str]:
    """Skills preloaded by subagents that sit in two or more different plugins."""
    users: dict[str, set[str]] = {}
    for plugin in plugin_map.plugins:
        for agent_name in plugin.agents:
            agent = agents.get(agent_name)
            for skill in agent.skills if agent else ():
                users.setdefault(skill, set()).add(plugin.name)
    return {skill for skill, owners in users.items() if len(owners) >= 2}


def _plugin_problems(plugin: Plugin, plugins: dict[str, Plugin], servers: set[str]) -> list[str]:
    """The rules one plugin entry has to meet on its own."""
    problems: list[str] = []
    for dependency in plugin.dependencies:
        if dependency == plugin.name:
            problems.append(f"plugin {plugin.name!r} depends on itself")
        elif dependency not in plugins:
            problems.append(f"plugin {plugin.name!r} depends on unknown plugin {dependency!r}")
    if plugin.category not in CATEGORIES:
        problems.append(
            f"plugin {plugin.name!r} has unknown category {plugin.category!r}, use one of {', '.join(sorted(CATEGORIES))}"
        )
    if plugin.category == HOST_CATEGORY and plugin.default_enabled:
        problems.append(f"host group {plugin.name!r} must set defaultEnabled: false")
    if plugin.category != HOST_CATEGORY and not plugin.default_enabled:
        problems.append(f"plugin {plugin.name!r} is not a host group, so it must stay on: drop defaultEnabled: false")
    if plugin.is_bundle != (plugin.category == BUNDLE_CATEGORY):
        problems.append(
            f"plugin {plugin.name!r} holds only dependencies, so its category must be {BUNDLE_CATEGORY!r}"
            if plugin.is_bundle
            else f"bundle {plugin.name!r} must hold dependencies only, with no skill, subagent or server"
        )
    if (plugin.mcp is not None) != (plugin.category == MCP_CATEGORY):
        problems.append(f"plugin {plugin.name!r} must carry category {MCP_CATEGORY!r} exactly when it names a server")
    if plugin.mcp is not None:
        if plugin.agents or plugin.skills or plugin.dependencies:
            problems.append(f"MCP plugin {plugin.name!r} must hold its server and nothing else")
        if plugin.name != MCP_PREFIX + plugin.mcp:
            problems.append(f"MCP plugin {plugin.name!r} must be named {MCP_PREFIX + plugin.mcp!r}")
        if plugin.mcp not in servers:
            problems.append(f"MCP plugin {plugin.name!r} names server {plugin.mcp!r}, not in the root .mcp.json")
    if plugin.is_bundle and not plugin.dependencies:
        problems.append(f"plugin {plugin.name!r} holds nothing and depends on nothing")
    return problems


def _set_problems(what: str, actual: set[str], expected: set[str]) -> list[str]:
    """Name what a plugin set is missing and what it holds that it should not."""
    problems = []
    if missing := sorted(expected - actual):
        problems.append(f"{what}: missing {', '.join(missing)}")
    if extra := sorted(actual - expected):
        problems.append(f"{what}: must not include {', '.join(extra)}")
    return problems


def check_map(
    plugin_map: PluginMap,
    skills: set[str],
    agents: dict[str, Agent],
    servers: Iterable[str],
) -> list[str]:
    """Every rule the map has to meet, as a list of problems. Empty means renderable."""
    problems: list[str] = []
    plugins = plugin_map.by_name()
    servers = set(servers)

    names = [plugin.name for plugin in plugin_map.plugins]
    problems += [f"duplicate plugin name {n!r}" for n in sorted({n for n in names if names.count(n) > 1})]
    problems += [f"plugin name {n!r} is not kebab-case" for n in names if not PLUGIN_NAME.fullmatch(n)]
    for required in (CORE, ALL, MCP_ALL):
        if required not in plugins:
            problems.append(f"no {required!r} plugin")

    for kind, homes, known in (
        ("skill", _homes(plugin_map.plugins, "skills"), skills),
        ("subagent", _homes(plugin_map.plugins, "agents"), set(agents)),
    ):
        problems += [f"{kind} name {k!r} in plugin {v[0]!r} is not kebab-case" for k, v in sorted(homes.items()) if not PLUGIN_NAME.fullmatch(k)]
        problems += [f"{kind} {k!r} sits in {len(v)} plugins: {', '.join(v)}" for k, v in sorted(homes.items()) if len(v) > 1]
        problems += [f"{kind} {k!r} in plugin {v[0]!r} does not exist" for k, v in sorted(homes.items()) if k not in known]
        problems += [f"{kind} {k!r} sits in no plugin" for k in sorted(known - set(homes))]

    for plugin in plugin_map.plugins:
        problems += _plugin_problems(plugin, plugins, servers)

    cycle = find_cycle(plugins)
    if cycle:
        problems.append(f"dependency cycle: {' -> '.join(cycle)}")

    served = [plugin.mcp for plugin in plugin_map.plugins if plugin.mcp]
    problems += [f"server {s!r} sits in {served.count(s)} plugins" for s in sorted(set(served)) if served.count(s) > 1]
    problems += [f"server {s!r} in the root .mcp.json has no plugin" for s in sorted(servers - set(served))]

    if CORE in plugins and (plugins[CORE].agents or plugins[CORE].dependencies):
        problems.append(f"{CORE!r} must hold skills only, with no subagents and no dependencies")
    if MCP_ALL in plugins:
        server_plugins = {plugin.name for plugin in plugin_map.plugins if plugin.mcp}
        problems += _set_problems(f"{MCP_ALL!r} depends on every server plugin", set(plugins[MCP_ALL].dependencies), server_plugins)
    if ALL in plugins:
        development = {plugin.name for plugin in plugin_map.plugins if plugin.category == DEVELOPMENT_CATEGORY}
        problems += _set_problems(f"{ALL!r} installs core and every development plugin", dependency_closure(ALL, plugins), development)

    if problems:
        return problems

    skill_home = {skill: home[0] for skill, home in _homes(plugin_map.plugins, "skills").items()}
    for plugin in plugin_map.plugins:
        closure = dependency_closure(plugin.name, plugins)
        for agent_name in plugin.agents:
            for skill in agents[agent_name].skills:
                home = skill_home[skill]
                if home not in (plugin.name, CORE):
                    problems.append(
                        f"subagent {agent_name!r} in {plugin.name!r} preloads {skill!r} from {home!r}. "
                        f"Move the subagent to {home!r}, or the skill to {CORE!r} if two plugins now use it"
                    )
                elif home == CORE and CORE not in closure:
                    problems.append(f"plugin {plugin.name!r} preloads {CORE!r} skill {skill!r} but does not depend on {CORE!r}")

    core_skills = set(plugins[CORE].skills)
    shared = shared_skills(plugin_map, agents)
    problems += [f"skill {s!r} is in {CORE!r} but subagents in fewer than two plugins preload it" for s in sorted(core_skills - shared)]
    problems += [f"skill {s!r} is preloaded by subagents in two or more plugins, so it belongs in {CORE!r}" for s in sorted(shared - core_skills)]
    return problems


def _is_ignored(path: pathlib.Path) -> bool:
    return path.name in IGNORED_NAMES or path.suffix in IGNORED_SUFFIXES


def skill_files(skill_dir: pathlib.Path) -> Iterator[pathlib.Path]:
    """Every file of one skill, sorted, refusing a symlink so nothing outside the skill is copied."""
    for path in sorted(skill_dir.rglob("*")):
        if any(_is_ignored(part) for part in [path, *path.relative_to(skill_dir).parents]):
            continue
        if path.is_symlink():
            raise PluginMapError(f"{path} is a symlink, and a plugin ships real files only")
        if path.is_file():
            yield path


def _is_executable(path: pathlib.Path) -> bool:
    return bool(path.stat().st_mode & stat.S_IXUSR)


def _write(path: pathlib.Path, content: bytes, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    path.chmod(0o755 if executable else 0o644)


def _json(document: object) -> bytes:
    return (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def content_hash(plugin_dir: pathlib.Path) -> str:
    """A short hash of everything in a plugin directory, with the manifest's own `version` left out."""
    digest = hashlib.sha256()
    for path in sorted(p for p in plugin_dir.rglob("*") if p.is_file()):
        relative = path.relative_to(plugin_dir).as_posix()
        content = path.read_bytes()
        if relative == f"{MANIFEST_DIR}/{PLUGIN_MANIFEST}":
            manifest = json.loads(content)
            manifest.pop("version", None)
            content = json.dumps(manifest, sort_keys=True).encode("utf-8")
        for part in (relative.encode("utf-8"), b"x" if _is_executable(path) else b"-", content):
            digest.update(len(part).to_bytes(8, "big"))
            digest.update(part)
    return digest.hexdigest()[:VERSION_LENGTH]


def plugin_manifest(plugin: Plugin, marketplace: dict[str, object], version: str | None) -> dict[str, object]:
    manifest: dict[str, object] = {"name": plugin.name}
    if version is not None:
        manifest["version"] = version
    manifest["description"] = plugin.description
    manifest["author"] = marketplace["owner"]
    for key in ("repository", "license"):
        if key in marketplace:
            manifest[key] = marketplace[key]
    if not plugin.default_enabled:
        manifest["defaultEnabled"] = False
    if plugin.dependencies:
        manifest["dependencies"] = list(plugin.dependencies)
    return manifest


def render_plugin(
    plugin: Plugin,
    plugin_dir: pathlib.Path,
    marketplace: dict[str, object],
    sources: Sources,
    agents: dict[str, Agent],
    servers: dict[str, dict[str, object]],
) -> str:
    """Write one plugin directory and return the version it was stamped with."""
    for skill in plugin.skills:
        source = sources.skills / skill
        for path in skill_files(source):
            target = plugin_dir / "skills" / skill / path.relative_to(source)
            _write(target, path.read_bytes(), _is_executable(path))
    for agent_name in plugin.agents:
        _write(plugin_dir / "agents" / f"{agent_name}.md", agents[agent_name].rendered.encode("utf-8"))
    if plugin.mcp:
        _write(plugin_dir / MCP_FILE, _json({"mcpServers": {plugin.mcp: servers[plugin.mcp]}}))
    manifest_path = plugin_dir / MANIFEST_DIR / PLUGIN_MANIFEST
    _write(manifest_path, _json(plugin_manifest(plugin, marketplace, None)))
    version = content_hash(plugin_dir)
    _write(manifest_path, _json(plugin_manifest(plugin, marketplace, version)))
    return version


def marketplace_manifest(plugin_map: PluginMap) -> dict[str, object]:
    market = plugin_map.marketplace
    entries = []
    for plugin in plugin_map.plugins:
        entry: dict[str, object] = {
            "name": plugin.name,
            "source": f"./plugins/{plugin.name}",
            "description": plugin.description,
            "category": plugin.category,
        }
        if not plugin.default_enabled:
            entry["defaultEnabled"] = False
        entries.append(entry)
    document: dict[str, object] = {"name": market["name"], "owner": market["owner"]}
    if "description" in market:
        document["description"] = market["description"]
    document["plugins"] = entries
    return document


def readme(plugin_map: PluginMap, versions: dict[str, str]) -> str:
    """The landing page of the generated branch, so a visitor learns where it comes from."""
    market = plugin_map.marketplace
    name = market["name"]
    repository = str(market["repository"]).removesuffix("/")
    example = next(
        (p.name for p in plugin_map.plugins if p.category == DEVELOPMENT_CATEGORY and p.name != CORE),
        plugin_map.plugins[0].name,
    )
    rows = "\n".join(
        f"| `{p.name}` | {p.category} | {'on' if p.default_enabled else 'off'} | `{versions[p.name]}` | {p.description} |"
        for p in plugin_map.plugins
    )
    return (
        f"# {name} plugins\n\n"
        f"Generated by `tools/gen_plugins.py` from `tools/plugins.yaml` on the default branch of {repository}. "
        "Every push there rebuilds this branch, so never edit it by hand.\n\n"
        "Add the marketplace from this branch:\n\n"
        "```bash\n"
        f"claude plugin marketplace add {repository.removeprefix('https://github.com/')}#plugins\n"
        "```\n\n"
        "Install one plugin, which also installs the plugins it depends on:\n\n"
        "```bash\n"
        f"claude plugin install {example}@{name}\n"
        "```\n\n"
        "| Plugin | Category | Default | Version | What it holds |\n"
        "| --- | --- | --- | --- | --- |\n"
        f"{rows}\n"
    )


def _write_marketplace(
    plugin_map: PluginMap,
    out_dir: pathlib.Path,
    sources: Sources,
    agents: dict[str, Agent],
    servers: dict[str, dict[str, object]],
) -> dict[str, str]:
    versions = {
        plugin.name: render_plugin(plugin, out_dir / "plugins" / plugin.name, plugin_map.marketplace, sources, agents, servers)
        for plugin in plugin_map.plugins
    }
    _write(out_dir / MANIFEST_DIR / MARKETPLACE_MANIFEST, _json(marketplace_manifest(plugin_map)))
    _write(out_dir / "LICENSE", sources.license.read_bytes())
    _write(out_dir / "README.md", readme(plugin_map, versions).encode("utf-8"))
    return versions


def render(plugin_map: PluginMap, out_dir: pathlib.Path, sources: Sources = Sources()) -> dict[str, str]:
    """Check the map, then write the whole marketplace into out_dir. Returns each plugin's version.

    The tree is written into a temporary sibling of out_dir and renamed into
    place only when every file is written, so a failure leaves out_dir as it was.

    Raises:
        PluginMapError: out_dir sits inside sources.root or is not an empty
            directory, the map breaks a rule, or a source cannot be read.
    """
    if out_dir.resolve().is_relative_to(sources.root.resolve()):
        raise PluginMapError(f"{out_dir} is inside the repository {sources.root}. Render outside it, such as ../plugins-out")
    if out_dir.exists() and (not out_dir.is_dir() or any(out_dir.iterdir())):
        raise PluginMapError(f"{out_dir} is not an empty directory. Render into a fresh one")
    skills = gen_subagents.installed_skills(sources.skills)
    agents = load_agents(sources, skills)
    servers = load_servers(sources)
    problems = check_map(plugin_map, skills, agents, servers)
    if problems:
        raise PluginMapError("the plugin map breaks its rules:\n  " + "\n  ".join(problems))

    out_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = pathlib.Path(tempfile.mkdtemp(prefix=f".{out_dir.name}.", dir=out_dir.parent))
    try:
        staging.chmod(0o755)
        versions = _write_marketplace(plugin_map, staging, sources, agents, servers)
        if out_dir.exists():
            out_dir.rmdir()
        staging.rename(out_dir)
    except OSError as exc:
        shutil.rmtree(staging, ignore_errors=True)
        raise PluginMapError(f"cannot write the marketplace into {out_dir}: {exc}") from exc
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return versions


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Render the Claude Code plugin marketplace.")
    parser.add_argument("out_dir", type=pathlib.Path, help="empty or missing directory to write into")
    parser.add_argument("--map", type=pathlib.Path, default=DEFAULT_MAP, help="plugin map, default tools/plugins.yaml")
    args = parser.parse_args(argv)
    try:
        plugin_map = load_map(args.map)
        versions = render(plugin_map, args.out_dir)
    except PluginMapError as exc:
        sys.exit(f"ERROR {exc}")
    print(f"done: {len(versions)} plugins -> {args.out_dir}")


if __name__ == "__main__":
    main()
