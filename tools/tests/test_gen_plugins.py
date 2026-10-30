"""Tests for tools/gen_plugins.py and the plugin map in tools/plugins.yaml.

The map is data, so the first group holds the real map to its rules: one home
per skill and per subagent, a core that holds exactly the skills two or more
plugins share, dependencies that exist and never loop. The second group
renders the real map once into a temp directory and checks the output against
its sources byte for byte. The third group feeds check_map broken maps, so
each rule is seen to fail on the input it exists to catch.
"""

import dataclasses
import json
import os
import pathlib
from collections import Counter

import pytest

import gen_plugins as gen
import gen_subagents
from tests.conftest import REPO_ROOT

SOURCES = gen.Sources(REPO_ROOT)
NEVER_SHIP_PARTS = {"tools", "subagents", "e2e", "sandbox-agent", "docs", "openspec", "global"}
NEVER_SHIP_NAMES = {"main-thread-allowlist.txt", "AGENTS.md", "AGENTS.md.example", "CLAUDE.md", "CONTRIBUTING.md"}
PLUGIN_ENTRIES = {gen.MANIFEST_DIR, "skills", "agents", gen.MCP_FILE}


@pytest.fixture(scope="module")
def plugin_map() -> gen.PluginMap:
    return gen.load_map()


@pytest.fixture(scope="module")
def skills() -> set[str]:
    return gen.installed_skills(SOURCES)


@pytest.fixture(scope="module")
def agents(skills) -> dict[str, gen.Agent]:
    return gen.load_agents(SOURCES, skills)


@pytest.fixture(scope="module")
def servers() -> dict[str, dict[str, object]]:
    return gen.load_servers(SOURCES)


@pytest.fixture(scope="module")
def rendered(plugin_map, tmp_path_factory) -> tuple[pathlib.Path, dict[str, str]]:
    out = tmp_path_factory.mktemp("marketplace") / "out"
    versions = gen.render(plugin_map, out, SOURCES)
    return out, versions


def _manifest(out: pathlib.Path, name: str) -> dict:
    return json.loads((out / "plugins" / name / gen.MANIFEST_DIR / gen.PLUGIN_MANIFEST).read_text(encoding="utf-8"))


def _files(directory: pathlib.Path) -> dict[str, bytes]:
    return {
        p.relative_to(directory).as_posix(): p.read_bytes()
        for p in directory.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    }


# The real map


def test_real_map_breaks_no_rule(plugin_map, skills, agents, servers):
    assert gen.check_map(plugin_map, skills, agents, servers) == []


def test_every_skill_sits_in_exactly_one_plugin(plugin_map, skills):
    homes = Counter(skill for plugin in plugin_map.plugins for skill in plugin.skills)

    assert set(homes) == skills
    assert {skill: count for skill, count in homes.items() if count > 1} == {}


def test_every_subagent_sits_in_exactly_one_plugin(plugin_map, agents):
    homes = Counter(agent for plugin in plugin_map.plugins for agent in plugin.agents)

    assert set(homes) == set(agents)
    assert {agent: count for agent, count in homes.items() if count > 1} == {}


def test_every_dependency_exists_and_none_loops(plugin_map):
    plugins = plugin_map.by_name()

    assert {d for p in plugin_map.plugins for d in p.dependencies} <= set(plugins)
    assert gen.find_cycle(plugins) is None


def test_core_holds_exactly_the_skills_two_plugins_share(plugin_map, agents):
    core = plugin_map.by_name()[gen.CORE]

    assert set(core.skills) == gen.shared_skills(plugin_map, agents)
    assert core.agents == () and core.dependencies == ()


def test_every_preloaded_skill_is_in_core_or_the_subagents_own_plugin(plugin_map, agents):
    home = {skill: p.name for p in plugin_map.plugins for skill in p.skills}
    plugins = plugin_map.by_name()

    for plugin in plugin_map.plugins:
        for agent in plugin.agents:
            for skill in agents[agent].skills:
                assert home[skill] in (plugin.name, gen.CORE), f"{agent} preloads {skill} from {home[skill]}"
                if home[skill] == gen.CORE:
                    assert gen.CORE in gen.dependency_closure(plugin.name, plugins)


def test_host_groups_are_off_and_everything_else_is_on(plugin_map):
    for plugin in plugin_map.plugins:
        assert plugin.default_enabled is (plugin.category != gen.HOST_CATEGORY), plugin.name


def test_one_plugin_per_root_server_and_mcp_all_depends_on_each(plugin_map, servers):
    served = {p.mcp: p.name for p in plugin_map.plugins if p.mcp}

    assert set(served) == set(servers)
    assert set(plugin_map.by_name()["mcp-all"].dependencies) == set(served.values())


def test_all_pulls_in_every_other_plugin(plugin_map):
    plugins = plugin_map.by_name()

    assert gen.dependency_closure("all", plugins) == set(plugins) - {"all"}


def test_bundles_hold_nothing_but_dependencies(plugin_map):
    plugins = plugin_map.by_name()

    assert plugins["all"].is_bundle and plugins["mcp-all"].is_bundle


# The rendered output


def test_skill_copies_are_byte_identical_to_their_sources(plugin_map, rendered):
    out, _ = rendered

    for plugin in plugin_map.plugins:
        for skill in plugin.skills:
            copy = out / "plugins" / plugin.name / "skills" / skill
            assert _files(copy) == _files(SOURCES.skills / skill), skill


def test_agent_copies_equal_the_claude_render_and_the_generated_tree(plugin_map, rendered, skills):
    out, _ = rendered

    for plugin in plugin_map.plugins:
        for agent in plugin.agents:
            copy = (out / "plugins" / plugin.name / "agents" / f"{agent}.md").read_bytes()
            front_matter, body = gen_subagents.parse(SOURCES.subagents / f"{agent}.md", skills)
            assert copy == gen_subagents.emit_claude(front_matter, body).encode("utf-8"), agent
            assert copy == (REPO_ROOT / ".claude" / "agents" / f"{agent}.md").read_bytes(), agent


def test_each_server_plugin_mcp_file_equals_its_root_block(plugin_map, rendered, servers):
    out, _ = rendered

    for plugin in plugin_map.plugins:
        mcp_file = out / "plugins" / plugin.name / gen.MCP_FILE
        if plugin.mcp:
            assert json.loads(mcp_file.read_text(encoding="utf-8")) == {"mcpServers": {plugin.mcp: servers[plugin.mcp]}}
        else:
            assert not mcp_file.exists(), plugin.name


def test_output_holds_no_symlink(rendered):
    out, _ = rendered

    assert [p for p in out.rglob("*") if p.is_symlink()] == []


def test_output_holds_no_never_ship_file(rendered):
    out, _ = rendered

    assert {p.name for p in out.iterdir()} == {gen.MANIFEST_DIR, "plugins", "LICENSE", "README.md"}
    assert (out / "README.md").read_bytes() != (REPO_ROOT / "README.md").read_bytes()
    for plugin_dir in (out / "plugins").iterdir():
        assert {p.name for p in plugin_dir.iterdir()} <= PLUGIN_ENTRIES, plugin_dir.name
        for path in plugin_dir.rglob("*"):
            relative = path.relative_to(plugin_dir)
            assert path.name not in NEVER_SHIP_NAMES, relative
            if relative.parts[0] != "skills":
                assert not NEVER_SHIP_PARTS & set(relative.parts), relative


def test_version_equals_the_content_hash(plugin_map, rendered):
    out, versions = rendered

    for plugin in plugin_map.plugins:
        version = _manifest(out, plugin.name)["version"]
        assert version == versions[plugin.name] == gen.content_hash(out / "plugins" / plugin.name)
        assert len(version) == gen.VERSION_LENGTH


def test_rendering_twice_gives_the_same_bytes(plugin_map, rendered, tmp_path):
    out, versions = rendered

    again = gen.render(plugin_map, tmp_path / "again", SOURCES)

    assert again == versions
    assert _files(tmp_path / "again") == _files(out)


def test_marketplace_entries_match_the_plugin_manifests(plugin_map, rendered):
    out, _ = rendered
    market = json.loads((out / gen.MANIFEST_DIR / gen.MARKETPLACE_MANIFEST).read_text(encoding="utf-8"))

    assert market["name"] == plugin_map.marketplace["name"]
    assert [e["name"] for e in market["plugins"]] == [p.name for p in plugin_map.plugins]
    for entry, plugin in zip(market["plugins"], plugin_map.plugins):
        manifest = _manifest(out, plugin.name)
        assert entry["source"] == f"./plugins/{plugin.name}"
        assert "version" not in entry
        assert entry.get("defaultEnabled", True) is plugin.default_enabled
        assert manifest.get("defaultEnabled", True) is plugin.default_enabled
        assert manifest.get("dependencies", []) == list(plugin.dependencies)
        assert manifest["name"] == plugin.name and manifest["description"] == entry["description"]


# The hash, the guards and the command line


def test_content_hash_ignores_the_version_and_follows_every_byte(tmp_path):
    plugin = tmp_path / "p"
    (plugin / gen.MANIFEST_DIR).mkdir(parents=True)
    (plugin / "skills" / "s").mkdir(parents=True)
    manifest = plugin / gen.MANIFEST_DIR / gen.PLUGIN_MANIFEST
    skill = plugin / "skills" / "s" / "SKILL.md"
    manifest.write_text('{"name": "p", "version": "one"}')
    skill.write_text("body")
    first = gen.content_hash(plugin)

    manifest.write_text('{"name": "p", "version": "two"}')
    unchanged = gen.content_hash(plugin)
    skill.write_text("body!")
    changed = gen.content_hash(plugin)

    assert unchanged == first
    assert changed != first


def test_render_refuses_a_directory_that_is_not_empty(plugin_map, tmp_path):
    (tmp_path / "keep.txt").write_text("mine")

    with pytest.raises(gen.PluginMapError, match="not an empty directory"):
        gen.render(plugin_map, tmp_path, SOURCES)
    assert (tmp_path / "keep.txt").read_text() == "mine"


def test_a_symlink_inside_a_skill_is_refused(tmp_path):
    skill = tmp_path / "s"
    skill.mkdir()
    (skill / "SKILL.md").write_text("body")
    (tmp_path / "outside.md").write_text("secret")
    try:
        os.symlink(tmp_path / "outside.md", skill / "linked.md")
    except OSError:
        pytest.skip("this platform cannot create a symlink")

    with pytest.raises(gen.PluginMapError, match="symlink"):
        list(gen.skill_files(skill))


def test_main_exits_with_an_error_on_a_non_empty_directory(tmp_path):
    (tmp_path / "keep.txt").write_text("mine")

    with pytest.raises(SystemExit) as exc:
        gen.main([str(tmp_path)])

    assert str(exc.value.code).startswith("ERROR")


def test_load_map_rejects_an_unknown_plugin_key(tmp_path):
    bad = tmp_path / "plugins.yaml"
    bad.write_text(
        "marketplace: {name: m, owner: {name: o}}\n"
        "plugins:\n  - {name: core, description: d, category: c, skils: [x]}\n"
    )

    with pytest.raises(gen.PluginMapError, match="unknown key"):
        gen.load_map(bad)


def _replace(plugin_map: gen.PluginMap, name: str, **changes) -> gen.PluginMap:
    return dataclasses.replace(
        plugin_map,
        plugins=tuple(dataclasses.replace(p, **changes) if p.name == name else p for p in plugin_map.plugins),
    )


def _broken_maps(plugin_map: gen.PluginMap) -> list[tuple[str, gen.PluginMap, str]]:
    plugins = plugin_map.by_name()
    python = plugins["python"]
    jvm = plugins["jvm"]
    core = plugins[gen.CORE]
    return [
        ("a skill in two plugins", _replace(plugin_map, "jvm", skills=jvm.skills + ("pytorch-patterns",)), "sits in 2 plugins"),
        ("a skill in no plugin", _replace(plugin_map, "python", skills=()), "'pytorch-patterns' sits in no plugin"),
        ("an unknown skill", _replace(plugin_map, "python", skills=python.skills + ("no-such-skill",)), "does not exist"),
        ("a subagent in no plugin", _replace(plugin_map, "python", agents=("python-pro",)), "'ml-engineer' sits in no plugin"),
        (
            "a subagent away from its own skill",
            _replace(_replace(plugin_map, "python", agents=("python-pro",)), "jvm", agents=jvm.agents + ("ml-engineer",)),
            "preloads 'pytorch-patterns' from 'python'",
        ),
        ("a single-use skill in core", _replace(_replace(plugin_map, "python", skills=()), gen.CORE, skills=core.skills + ("pytorch-patterns",)), "fewer than two plugins"),
        ("a shared skill outside core", _replace(_replace(plugin_map, gen.CORE, skills=tuple(s for s in core.skills if s != "bash")), "devops", skills=plugins["devops"].skills + ("bash",)), "belongs in 'core'"),
        ("an unknown dependency", _replace(plugin_map, "python", dependencies=("core", "nope")), "unknown plugin 'nope'"),
        ("a dependency cycle", _replace(plugin_map, gen.CORE, dependencies=("python",)), "dependency cycle"),
        ("a missing core dependency", _replace(plugin_map, "python", dependencies=()), "does not depend on 'core'"),
        ("a host group switched on", _replace(plugin_map, "linux", default_enabled=True), "defaultEnabled: false"),
        ("a server plugin under another name", _replace(plugin_map, "mcp-redis", mcp="grafana"), "sits in 2 plugins"),
        ("a server plugin holding a skill", _replace(plugin_map, "mcp-redis", skills=("unity",)), "nothing else"),
        ("an empty plugin", _replace(plugin_map, "mcp-all", dependencies=()), "holds nothing and depends on nothing"),
    ]


@pytest.mark.parametrize("case", range(14))
def test_check_map_catches_each_broken_rule(case, plugin_map, skills, agents, servers):
    label, broken, expected = _broken_maps(plugin_map)[case]

    problems = gen.check_map(broken, skills, agents, servers)

    assert any(expected in problem for problem in problems), f"{label}: {problems}"


def test_check_map_catches_a_root_server_with_no_plugin(plugin_map, skills, agents, servers):
    problems = gen.check_map(plugin_map, skills, agents, [*servers, "new-server"])

    assert "server 'new-server' in the root .mcp.json has no plugin" in problems
