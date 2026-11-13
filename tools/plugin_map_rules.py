"""Every rule the plugin map has to meet, checked by check_map.

tools/tests/test_gen_plugins.py holds one failing map for each rule. The map's
own comment in tools/plugins.yaml and "Placing an item in the plugin
marketplace" in CONTRIBUTING.md state them in prose.
"""
from __future__ import annotations

from collections.abc import Iterable

from plugin_model import (
    AGENT_PREFIX,
    ALL,
    BUNDLE,
    BUNDLE_CATEGORIES,
    CLAUDE_WIRING,
    CORE,
    DEVELOPMENT,
    DOMAIN_CATEGORIES,
    HOOKS_ALL,
    HOOKS_DIR,
    KEBAB,
    MCP_ALL,
    MCP_FILE,
    Bundle,
    Sources,
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
