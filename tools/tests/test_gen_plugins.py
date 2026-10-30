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
    return gen_subagents.installed_skills(SOURCES.skills)


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


def test_all_installs_core_and_every_development_plugin_and_nothing_else(plugin_map):
    plugins = plugin_map.by_name()
    development = {p.name for p in plugin_map.plugins if p.category == gen.DEVELOPMENT_CATEGORY}

    assert gen.dependency_closure(gen.ALL, plugins) == development | {gen.CORE}


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


GOOD_MARKETPLACE = "marketplace: {name: m, owner: {name: o}, repository: 'https://github.com/o/r'}\n"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param(
            GOOD_MARKETPLACE + "plugins:\n  - {name: core, description: d, category: development, skils: [x]}\n",
            "unknown key",
            id="an unknown plugin key",
        ),
        pytest.param(
            GOOD_MARKETPLACE + "plugins:\n  - {name: core, description: d, category: development, defaultEnabled: 'false'}\n",
            "'defaultEnabled' must be true or false",
            id="a defaultEnabled that is not a boolean",
        ),
        pytest.param(
            "marketplace: {name: m, owner: {name: o}}\nplugins: []\n",
            "needs a 'repository'",
            id="a marketplace with no repository",
        ),
        pytest.param(
            "marketplace: {name: m, owner: {name: o}, repository: 'https://gitlab.com/o/r'}\nplugins: []\n",
            "needs a 'repository'",
            id="a repository that is not on GitHub",
        ),
    ],
)
def test_load_map_rejects_a_malformed_map(text, expected, tmp_path):
    bad = tmp_path / "plugins.yaml"
    bad.write_text(text)

    with pytest.raises(gen.PluginMapError, match=expected):
        gen.load_map(bad)


def test_render_refuses_an_output_directory_inside_the_repository(plugin_map):
    out = REPO_ROOT / "plugins-render-test"

    with pytest.raises(gen.PluginMapError, match="inside the repository"):
        gen.render(plugin_map, out, SOURCES)
    assert not out.exists()


def test_render_measures_inside_against_the_sources_root(plugin_map, tmp_path):
    with pytest.raises(gen.PluginMapError, match="inside the repository"):
        gen.render(plugin_map, tmp_path / "out", gen.Sources(tmp_path))


def test_a_failed_render_leaves_the_output_directory_as_it_was(plugin_map, tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    real = gen.render_plugin
    calls = []

    def fail_on_the_third(*args, **kwargs):
        calls.append(args[0].name)
        if len(calls) == 3:
            raise gen.PluginMapError("disk full")
        return real(*args, **kwargs)

    monkeypatch.setattr(gen, "render_plugin", fail_on_the_third)

    with pytest.raises(gen.PluginMapError, match="disk full"):
        gen.render(plugin_map, out, SOURCES)
    assert list(tmp_path.iterdir()) == [out]
    assert list(out.iterdir()) == []


def test_executable_skill_files_stay_executable(plugin_map, rendered):
    out, _ = rendered
    executables = 0

    for plugin in plugin_map.plugins:
        for skill in plugin.skills:
            for source in gen.skill_files(SOURCES.skills / skill):
                copy = out / "plugins" / plugin.name / "skills" / skill / source.relative_to(SOURCES.skills / skill)
                assert gen._is_executable(copy) is gen._is_executable(source), copy
                executables += gen._is_executable(source)

    assert executables > 0


def test_readme_names_a_development_domain_and_the_repository(plugin_map, rendered):
    out, _ = rendered
    domain = next(p.name for p in plugin_map.plugins if p.category == gen.DEVELOPMENT_CATEGORY and p.name != gen.CORE)
    text = (out / "README.md").read_text(encoding="utf-8")

    assert f"claude plugin install {domain}@{plugin_map.marketplace['name']}\n" in text
    assert "claude plugin marketplace add Lukk17/agent-standards#plugins\n" in text


def _replace(plugin_map: gen.PluginMap, target: str, /, **changes) -> gen.PluginMap:
    return dataclasses.replace(
        plugin_map,
        plugins=tuple(dataclasses.replace(p, **changes) if p.name == target else p for p in plugin_map.plugins),
    )


def _without(plugin_map: gen.PluginMap, name: str) -> gen.PluginMap:
    return dataclasses.replace(plugin_map, plugins=tuple(p for p in plugin_map.plugins if p.name != name))


def _plus(plugin_map: gen.PluginMap, plugin: gen.Plugin) -> gen.PluginMap:
    return dataclasses.replace(plugin_map, plugins=plugin_map.plugins + (plugin,))


def _get(plugin_map: gen.PluginMap, name: str) -> gen.Plugin:
    return plugin_map.by_name()[name]


def _add(plugin_map: gen.PluginMap, name: str, field: str, *items: str) -> gen.PluginMap:
    return _replace(plugin_map, name, **{field: getattr(_get(plugin_map, name), field) + items})


def _drop(plugin_map: gen.PluginMap, name: str, field: str, item: str) -> gen.PluginMap:
    return _replace(plugin_map, name, **{field: tuple(i for i in getattr(_get(plugin_map, name), field) if i != item)})


BROKEN_MAPS = [
    pytest.param(lambda m: _add(m, "jvm", "skills", "pytorch-patterns"), "sits in 2 plugins", id="a skill in two plugins"),
    pytest.param(lambda m: _replace(m, "python", skills=()), "'pytorch-patterns' sits in no plugin", id="a skill in no plugin"),
    pytest.param(lambda m: _add(m, "python", "skills", "no-such-skill"), "does not exist", id="an unknown skill"),
    pytest.param(lambda m: _replace(m, "python", agents=("python-pro",)), "'ml-engineer' sits in no plugin", id="a subagent in no plugin"),
    pytest.param(
        lambda m: _add(_replace(m, "python", agents=("python-pro",)), "jvm", "agents", "ml-engineer"),
        "preloads 'pytorch-patterns' from 'python'",
        id="a subagent away from its own skill",
    ),
    pytest.param(
        lambda m: _add(_replace(m, "python", skills=()), gen.CORE, "skills", "pytorch-patterns"),
        "fewer than two plugins",
        id="a single-use skill in core",
    ),
    pytest.param(
        lambda m: _add(_drop(m, gen.CORE, "skills", "bash"), "devops", "skills", "bash"),
        "belongs in 'core'",
        id="a shared skill outside core",
    ),
    pytest.param(lambda m: _replace(m, "python", dependencies=("core", "nope")), "unknown plugin 'nope'", id="an unknown dependency"),
    pytest.param(lambda m: _replace(m, "python", dependencies=("core", "python")), "'python' depends on itself", id="a self-dependency"),
    pytest.param(lambda m: _replace(m, gen.CORE, dependencies=("python",)), "dependency cycle", id="a dependency cycle"),
    pytest.param(lambda m: _replace(m, "python", dependencies=()), "does not depend on 'core'", id="a missing core dependency"),
    pytest.param(lambda m: _without(m, gen.CORE), "no 'core' plugin", id="a missing core plugin"),
    pytest.param(lambda m: _without(m, gen.ALL), "no 'all' plugin", id="a missing all plugin"),
    pytest.param(lambda m: _without(m, gen.MCP_ALL), "no 'mcp-all' plugin", id="a missing mcp-all plugin"),
    pytest.param(lambda m: _plus(m, _get(m, "game")), "duplicate plugin name 'game'", id="a duplicate plugin name"),
    pytest.param(lambda m: _replace(m, "game", name="Game"), "plugin name 'Game' is not kebab-case", id="a plugin name in capitals"),
    pytest.param(lambda m: _replace(m, "game", name="game\n"), "is not kebab-case", id="a plugin name ending in a newline"),
    pytest.param(lambda m: _replace(m, "game", name="game--dev"), "is not kebab-case", id="a plugin name with a double hyphen"),
    pytest.param(lambda m: _add(m, "python", "skills", "Bad_Skill"), "skill name 'Bad_Skill' in plugin 'python' is not kebab-case", id="a skill name not in kebab-case"),
    pytest.param(lambda m: _add(m, "python", "agents", "Python Pro"), "subagent name 'Python Pro' in plugin 'python' is not kebab-case", id="a subagent name not in kebab-case"),
    pytest.param(lambda m: _replace(m, "game", category="games"), "unknown category 'games'", id="an unknown category"),
    pytest.param(lambda m: _replace(m, "linux", default_enabled=True), "defaultEnabled: false", id="a host group switched on"),
    pytest.param(lambda m: _replace(m, "game", default_enabled=False), "'game' is not a host group, so it must stay on", id="a domain switched off"),
    pytest.param(lambda m: _replace(m, "mcp-redis", mcp="grafana"), "sits in 2 plugins", id="two plugins for one server"),
    pytest.param(lambda m: _replace(m, "mcp-redis", skills=("unity",)), "nothing else", id="a server plugin holding a skill"),
    pytest.param(lambda m: _replace(m, "mcp-redis", name="mcp-cache"), "must be named 'mcp-redis'", id="a server plugin named off its server"),
    pytest.param(lambda m: _replace(m, "mcp-redis", category="development"), "exactly when it names a server", id="a server plugin outside category mcp"),
    pytest.param(lambda m: _replace(m, "game", category="mcp"), "exactly when it names a server", id="category mcp with no server"),
    pytest.param(lambda m: _replace(m, gen.MCP_ALL, dependencies=()), "holds nothing and depends on nothing", id="an empty plugin"),
    pytest.param(lambda m: _replace(m, gen.MCP_ALL, category="development"), "its category must be 'bundle'", id="a bundle outside category bundle"),
    pytest.param(lambda m: _add(_drop(m, "game", "skills", "unity"), gen.MCP_ALL, "skills", "unity"), "must hold dependencies only", id="a bundle holding a skill"),
    pytest.param(lambda m: _replace(m, gen.CORE, dependencies=("game",)), "'core' must hold skills only", id="core with a dependency"),
    pytest.param(
        lambda m: _add(_replace(m, "game", agents=()), gen.CORE, "agents", "unity-game-dev"),
        "'core' must hold skills only",
        id="core with a subagent",
    ),
    pytest.param(lambda m: _drop(m, gen.MCP_ALL, "dependencies", "mcp-redis"), "every server plugin: missing mcp-redis", id="mcp-all missing a server"),
    pytest.param(lambda m: _add(m, gen.MCP_ALL, "dependencies", "game"), "every server plugin: must not include game", id="mcp-all pulling a domain"),
    pytest.param(lambda m: _drop(m, gen.ALL, "dependencies", "game"), "every development plugin: missing game", id="all missing a domain"),
    pytest.param(lambda m: _add(m, gen.ALL, "dependencies", "linux"), "must not include linux", id="all pulling a host group"),
    pytest.param(lambda m: _add(m, gen.ALL, "dependencies", gen.MCP_ALL), "must not include mcp-all", id="all pulling mcp-all"),
    pytest.param(lambda m: _add(m, "game", "dependencies", "mcp-redis"), "must not include mcp-redis", id="all reaching a server through a domain"),
]


@pytest.mark.parametrize(("breaks", "expected"), BROKEN_MAPS)
def test_check_map_catches_each_broken_rule(breaks, expected, plugin_map, skills, agents, servers):
    problems = gen.check_map(breaks(plugin_map), skills, agents, servers)

    assert any(expected in problem for problem in problems), problems


def test_check_map_catches_a_root_server_with_no_plugin(plugin_map, skills, agents, servers):
    problems = gen.check_map(plugin_map, skills, agents, [*servers, "new-server"])

    assert "server 'new-server' in the root .mcp.json has no plugin" in problems
