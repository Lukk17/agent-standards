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

import yaml

import gen_subagents
from plugin_map_rules import check_map, dependency_closure, dependency_graph, find_cycle, plugin_names, shared_skills
from plugin_model import (  # noqa: F401, the names tools/check_versions.py and the tests read from here
    AGENT_CATEGORY, AGENT_PREFIX, ALL, Agent, BUNDLE, BUNDLE_CATEGORIES, BUNDLE_KEYS, Bundle, CLAUDE_AGENTS_DIR,
    CLAUDE_WIRING, CORE, DEVELOPMENT, DOMAIN_CATEGORIES, ENTRY_ONLY_SOURCE, GITHUB_REPOSITORY, HOOKS_ALL,
    HOOKS_DIR, HOOK_CATEGORY, HOOK_FOLDER, HOOK_KEYS, HOOK_PREFIX, HOOK_SCRIPT, HOST, Hook, KEBAB, MAP_FILE,
    MARKETPLACE_FILE, MARKETPLACE_KEYS, MCP_ALL, MCP_CATEGORY, MCP_FILE, MCP_PREFIX, PLUGIN_ROOT_PATH, PluginMap,
    PluginMapError, SEMVER, SERVER_KEYS, SKILLS_DIR, SKILL_CATEGORY, SUBAGENTS_DIR, Server, Skill, Sources,
    load_map, parse_map, _version,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]

__all__ = [
    "check_map", "dependency_closure", "dependency_graph", "entries", "find_cycle", "load_sources",
    "marketplace", "owned_paths", "plugin_names", "render_text", "shared_skills",
]


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
