"""Tests for tools/gen_plugins.py, the plugin map in tools/plugins.yaml, and the committed marketplace.

The first group holds the committed .claude-plugin/marketplace.json to its
sources: one entry per skill, subagent, Claude Code hook and MCP server, each
pointing at files that already sit in the repository. The second group holds
the real map to its rules. The third feeds check_map a small fixture
repository broken one rule at a time, so each rule is seen to fail on the
input it exists to catch.
"""

import json
import pathlib
import shutil

import pytest
import yaml

import gen_plugins as gen
from tests.conftest import REPO_ROOT


@pytest.fixture(scope="module")
def sources() -> gen.Sources:
    return gen.load_sources(REPO_ROOT)


@pytest.fixture(scope="module")
def committed() -> dict:
    return json.loads((REPO_ROOT / gen.MARKETPLACE_FILE).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def by_name(committed) -> dict[str, dict]:
    return {entry["name"]: entry for entry in committed["plugins"]}


LISTING_KEYS = ("author", "homepage", "repository", "license", "keywords", "tags")


def _category(by_name: dict[str, dict], category: str) -> dict[str, dict]:
    return {name: entry for name, entry in by_name.items() if entry["category"] == category}


# The committed marketplace


def test_the_committed_marketplace_matches_its_sources(sources):
    assert (REPO_ROOT / gen.MARKETPLACE_FILE).read_text(encoding="utf-8") == gen.render_text(gen.marketplace(sources))


def test_every_skill_is_its_own_plugin_at_its_own_folder(by_name):
    skills = {path.parent.name for path in (REPO_ROOT / gen.SKILLS_DIR).glob("*/SKILL.md")}

    assert set(_category(by_name, gen.SKILL_CATEGORY)) == skills
    for skill in skills:
        entry = by_name[skill]
        metadata = gen.front_matter(REPO_ROOT / gen.SKILLS_DIR / skill / "SKILL.md")["metadata"]
        assert entry["source"] == f"./.agents/skills/{skill}"
        assert entry["version"] == metadata["version"]
        assert set(entry) == {"name", "source", "version", "description", "category", *LISTING_KEYS}


def test_every_subagent_is_its_own_plugin_holding_one_agent_file_and_its_preloads(by_name):
    canonical = {path.stem: gen.front_matter(path) for path in (REPO_ROOT / gen.SUBAGENTS_DIR).glob("*.md")}

    assert set(_category(by_name, gen.AGENT_CATEGORY)) == {f"agent-{name}" for name in canonical}
    for name, data in canonical.items():
        entry = by_name[f"agent-{name}"]
        folder = REPO_ROOT / ".claude" / "agents" / name
        assert entry["source"] == f"./.claude/agents/{name}"
        assert entry["strict"] is False
        assert entry["agents"] == [f"./{name}.md"]
        assert sorted(p.name for p in folder.iterdir()) == [f"{name}.md"]
        assert entry["version"] == data["version"]
        assert entry.get("dependencies", []) == list(data.get("skills") or [])


def test_every_hook_plugin_carries_the_wiring_of_its_map_entry_inline(by_name):
    wiring = {hook["name"]: hook["wiring"] for hook in yaml.safe_load((REPO_ROOT / gen.MAP_FILE).read_text(encoding="utf-8"))["hooks"]}
    plugins = _category(by_name, gen.HOOK_CATEGORY)

    assert set(plugins) == {f"hook-{name}" for name in wiring}
    for name, events in wiring.items():
        assert plugins[f"hook-{name}"]["hooks"] == events
        assert events


def test_every_hook_plugin_command_starts_in_the_project_and_runs_a_script_of_its_own_folder(by_name):
    prefix = 'cd "${CLAUDE_PROJECT_DIR}" && PY=$(command -v python3 || command -v python) && "$PY" -S -E "${CLAUDE_PLUGIN_ROOT}"/'
    commands = [
        (REPO_ROOT / entry["source"], handler["command"])
        for entry in _category(by_name, gen.HOOK_CATEGORY).values()
        for groups in entry["hooks"].values()
        for group in groups
        for handler in group["hooks"]
    ]

    assert commands
    for folder, command in commands:
        assert command.startswith(prefix) and command.endswith(" ; exit 0"), command
        assert (folder / command.removeprefix(prefix).split()[0]).is_file(), command
        assert ".agents/hooks/" not in command, command


def test_every_server_plugin_carries_the_block_of_its_map_entry_inline(by_name):
    servers = {server["name"]: server["block"] for server in yaml.safe_load((REPO_ROOT / gen.MAP_FILE).read_text(encoding="utf-8"))["servers"]}
    plugins = _category(by_name, gen.MCP_CATEGORY)

    assert set(plugins) == {f"mcp-{name}" for name in servers}
    for name, block in servers.items():
        assert plugins[f"mcp-{name}"]["mcpServers"] == {name: block}
        assert plugins[f"mcp-{name}"]["source"] == gen.ENTRY_ONLY_SOURCE


def test_the_root_mcp_file_starts_context7_alone_with_the_block_of_its_plugin(by_name):
    root = json.loads((REPO_ROOT / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]

    assert list(root) == ["context7"]
    assert by_name["mcp-context7"]["mcpServers"] == root


def test_every_entry_carries_the_listing_fields_of_the_map(committed):
    market = yaml.safe_load((REPO_ROOT / gen.MAP_FILE).read_text(encoding="utf-8"))["marketplace"]

    for entry in committed["plugins"]:
        assert entry["author"] == market["owner"], entry["name"]
        assert entry["homepage"] == market["homepage"], entry["name"]
        assert entry["repository"] == market["repository"], entry["name"]
        assert entry["license"] == market["license"], entry["name"]
        assert entry["keywords"] == entry["tags"], entry["name"]
        assert len(entry["keywords"]) >= 2 and len(set(entry["keywords"])) == len(entry["keywords"]), entry["name"]
        assert all(gen.KEBAB.fullmatch(word) for word in entry["keywords"]), entry["name"]


def test_keywords_name_the_kind_the_bundle_and_the_item(by_name):
    assert by_name["pytorch-patterns"]["keywords"] == ["skill", "python", "pytorch-patterns"]
    assert by_name["coding-standards"]["keywords"] == ["skill", "core", "coding-standards"]
    assert by_name["agent-python-pro"]["keywords"] == ["agent", "python", "python-pro"]
    assert by_name["hook-preflight-gate"]["keywords"] == ["hook", "preflight-gate"]
    assert by_name["mcp-context7"]["keywords"] == ["mcp", "context7"]
    assert by_name["python"]["keywords"] == ["bundle", "development", "python"]
    assert by_name["homelab"]["keywords"] == ["bundle", "host", "homelab"]
    assert by_name["mcp-all"]["keywords"] == ["bundle", "mcp-all"]


def test_bundles_hold_only_plugin_names_and_no_files(committed, by_name):
    bundles = [entry for entry in committed["plugins"] if entry["category"] in gen.BUNDLE_CATEGORIES]

    assert {entry["name"] for entry in bundles} >= {"core", "python", "jvm", "backend", "all", "mcp-all", "hooks-all"}
    for entry in bundles:
        assert entry["source"] == gen.ENTRY_ONLY_SOURCE
        assert set(entry) == {"name", "source", "version", "description", "category", "dependencies", *LISTING_KEYS}
        assert all(dependency in by_name for dependency in entry["dependencies"]), entry["name"]


def test_no_dependency_carries_a_version_range(committed):
    # Claude Code ignores a range on an entry dependency, so every dependency is a bare plugin name
    for entry in committed["plugins"]:
        assert all(isinstance(dependency, str) for dependency in entry.get("dependencies", [])), entry["name"]


def test_every_plugin_carries_a_semantic_version_and_a_unique_name(committed):
    names = [entry["name"] for entry in committed["plugins"]]

    assert len(names) == len(set(names))
    assert all(gen.SEMVER.fullmatch(entry["version"]) for entry in committed["plugins"])


def test_no_plugin_json_is_committed_anywhere():
    # The entry is the manifest, so a version is never written twice
    assert not [p for p in REPO_ROOT.rglob("plugin.json") if not {".git", "node_modules"} & set(p.parts)]


def test_every_entry_source_exists_inside_the_repository(committed):
    for entry in committed["plugins"]:
        source = (REPO_ROOT / entry["source"]).resolve()
        assert source.is_dir() and source.is_relative_to(REPO_ROOT.resolve()), entry["name"]


def test_the_quality_loop_skill_carries_robert_c_martins_tools_through_a_link():
    link = REPO_ROOT / ".agents" / "skills" / "quality-loop" / "tools"

    assert link.is_symlink()
    assert link.readlink().as_posix() == "../../../.metrics/tools"
    assert link.resolve() == (REPO_ROOT / ".metrics" / "tools").resolve()
    assert (link / "run").is_file() and (link / "crapper").is_dir()


def test_owned_paths_name_the_folder_and_the_canonical_agent(by_name):
    assert gen.owned_paths(by_name["agent-python-pro"]) == [
        pathlib.PurePosixPath(".claude/agents/python-pro"),
        pathlib.PurePosixPath("subagents/python-pro.md"),
    ]
    assert gen.owned_paths(by_name["python-patterns"]) == [pathlib.PurePosixPath(".agents/skills/python-patterns")]
    assert gen.owned_paths(by_name["hook-preflight-gate"]) == [pathlib.PurePosixPath(".agents/hooks/preflight-gate")]
    assert gen.owned_paths(by_name["mcp-context7"]) == []
    assert gen.owned_paths(by_name["core"]) == []


# The real map


def test_the_real_map_breaks_no_rule(sources):
    assert gen.check_map(sources) == []


def test_core_holds_exactly_the_skills_two_bundles_share(sources):
    assert set(sources.plugin_map.bundle(gen.CORE).skills) == gen.shared_skills(sources)


def test_installing_all_pulls_every_development_bundle_and_no_host_group(sources):
    closure = gen.dependency_closure(gen.ALL, gen.dependency_graph(sources))
    bundles = {bundle.name: bundle for bundle in sources.plugin_map.bundles}

    assert {name for name in closure if name in bundles} == {n for n, b in bundles.items() if b.category == gen.DEVELOPMENT}


SERVER_PAIRINGS = {
    "homelab": ("mcp-home-assistant",),
    "data": ("mcp-mongodb", "mcp-redis"),
    "web-frontend": ("mcp-playwright", "mcp-chrome-devtools"),
    "testing": ("mcp-playwright", "mcp-chrome-devtools"),
    "devops": ("mcp-grafana",),
    "review-and-security": ("mcp-sonarqube",),
}


@pytest.mark.parametrize(("bundle", "servers"), SERVER_PAIRINGS.items(), ids=SERVER_PAIRINGS)
def test_a_themed_bundle_names_the_server_plugins_that_go_with_it(by_name, bundle, servers):
    assert by_name[bundle]["category"] in gen.DOMAIN_CATEGORIES
    for server in servers:
        assert by_name[server]["category"] == gen.MCP_CATEGORY
        assert server in by_name[bundle]["description"], by_name[bundle]["description"]


def test_no_plugin_but_mcp_all_depends_on_a_server_plugin(committed, by_name):
    for entry in committed["plugins"]:
        if entry["name"] != gen.MCP_ALL:
            assert [d for d in entry.get("dependencies", []) if by_name[d]["category"] == gen.MCP_CATEGORY] == [], entry["name"]


def test_the_map_comment_names_the_rules_this_file_tests():
    header = (REPO_ROOT / gen.MAP_FILE).read_text(encoding="utf-8").split("\nmarketplace:")[0]

    for phrase in ("core holds exactly", "mcp-all depends on", "hooks-all on every hook plugin", "metadata.version"):
        assert phrase in header


def test_the_map_lists_as_many_hooks_servers_and_bundles_as_the_marketplace(committed):
    raw = yaml.safe_load((REPO_ROOT / gen.MAP_FILE).read_text(encoding="utf-8"))
    categories = [entry["category"] for entry in committed["plugins"]]

    assert categories.count(gen.HOOK_CATEGORY) == len(raw["hooks"])
    assert categories.count(gen.MCP_CATEGORY) == len(raw["servers"])
    assert sum(categories.count(c) for c in gen.BUNDLE_CATEGORIES) == len(raw["bundles"])


# check_map against a fixture repository, one broken rule at a time


MAP = """
marketplace:
  name: lab
  owner: {name: Lab, url: "https://github.com/lab"}
  repository: https://github.com/lab/agents
  homepage: "https://github.com/lab/agents#readme"
  license: MIT
hooks:
  - {name: gate, version: 1.0.0, description: The gate., wiring: {PreToolUse: [{matcher: "^(Edit)$", hooks: [{type: command, timeout: 10, command: 'cd "${CLAUDE_PROJECT_DIR}" && python3 "${CLAUDE_PLUGIN_ROOT}"/gate.py --format claude ; exit 0'}]}]}}
servers:
  - {name: docs, version: 1.0.0, description: Docs server., block: {type: http, url: "https://docs.example"}}
bundles:
  - {name: core, version: 1.0.0, category: development, description: Shared., skills: [shared]}
  - {name: py, version: 1.0.0, category: development, description: Python., dependencies: [core], agents: [pro], skills: [own]}
  - {name: web, version: 1.0.0, category: development, description: Web., dependencies: [core], agents: [front], skills: [solo]}
  - {name: all, version: 1.0.0, category: bundle, description: All., dependencies: [core, py, web]}
  - {name: mcp-all, version: 1.0.0, category: bundle, description: Servers., dependencies: [mcp-docs]}
  - {name: hooks-all, version: 1.0.0, category: bundle, description: Hooks., dependencies: [hook-gate]}
"""

DOCS_ENTRY = '  - {name: docs, version: 1.0.0, description: Docs server., block: {type: http, url: "https://docs.example"}}\n'

GATE_HANDLER = "command: 'cd \"${CLAUDE_PROJECT_DIR}\" && python3 \"${CLAUDE_PLUGIN_ROOT}\"/gate.py --format claude ; exit 0'"


def write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def skill(root: pathlib.Path, name: str) -> None:
    write(root / ".agents" / "skills" / name / "SKILL.md", f'---\nname: {name}\ndescription: The {name} skill.\nmetadata:\n  version: "1.0.0"\n---\nBody.\n')


def agent(root: pathlib.Path, name: str, skills: list[str]) -> None:
    listed = "".join(f"  - {s}\n" for s in skills)
    write(root / "subagents" / f"{name}.md", f"---\nname: {name}\nversion: 1.0.0\nlevel: 3\ndescription: Use when {name}.\nskills:\n{listed}---\nBody.\n")


def build_lab(root: pathlib.Path) -> pathlib.Path:
    """A small repository the map in MAP renders cleanly from, also used by tests/test_check_versions.py."""
    for name in ("shared", "own", "solo"):
        skill(root, name)
    agent(root, "pro", ["shared", "own"])
    agent(root, "front", ["shared", "solo"])
    write(root / ".agents" / "hooks" / "gate" / "gate.py", "print()\n")
    write(root / ".mcp.json", json.dumps({"mcpServers": {"docs": {"type": "http", "url": "https://docs.example"}}}))
    write(root / "tools" / "plugins.yaml", MAP)
    return root


@pytest.fixture
def lab(tmp_path) -> pathlib.Path:
    return build_lab(tmp_path)


def problems(root: pathlib.Path) -> list[str]:
    return gen.check_map(gen.load_sources(root))


def edit_map(root: pathlib.Path, old: str, new: str) -> None:
    path = root / "tools" / "plugins.yaml"
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")


def test_the_fixture_repository_renders_with_the_wiring_of_its_hook_entry(lab):
    document = gen.marketplace(gen.load_sources(lab))
    names = [entry["name"] for entry in document["plugins"]]

    assert names == ["core", "py", "web", "all", "mcp-all", "hooks-all", "agent-front", "agent-pro", "own", "shared", "solo", "hook-gate", "mcp-docs"]
    assert document["plugins"][-1]["mcpServers"] == {"docs": {"type": "http", "url": "https://docs.example"}}
    hook = next(entry for entry in document["plugins"] if entry["name"] == "hook-gate")
    assert hook["hooks"] == {
        "PreToolUse": [
            {
                "matcher": "^(Edit)$",
                "hooks": [{"type": "command", "timeout": 10, "command": 'cd "${CLAUDE_PROJECT_DIR}" && python3 "${CLAUDE_PLUGIN_ROOT}"/gate.py --format claude ; exit 0'}],
            }
        ]
    }


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        pytest.param("skills: [own]", "skills: [own, solo]", "skill 'solo' sits in 2 bundles: py, web", id="skill-in-two-bundles"),
        pytest.param("skills: [solo]", "skills: []", "skill 'solo' sits in no development or host bundle", id="skill-in-no-bundle"),
        pytest.param("agents: [front]", "agents: [front, ghost]", "subagent 'ghost' in bundle 'web' does not exist", id="unknown-agent"),
        pytest.param("dependencies: [core], agents: [front]", "agents: [front]", "bundle 'web' preloads 'core' skill 'shared' but does not depend on 'core'", id="no-core-dependency"),
        pytest.param("dependencies: [core, py, web]", "dependencies: [core, py]", "'all' installs core and every development bundle: missing web", id="all-misses-a-domain"),
        pytest.param("dependencies: [mcp-docs]", "dependencies: [core]", "'mcp-all' depends on every server plugin", id="mcp-all-wrong"),
        pytest.param("dependencies: [hook-gate]", "dependencies: [core]", "'hooks-all' depends on every hook plugin", id="hooks-all-wrong"),
        pytest.param("category: bundle, description: All.", "category: misc, description: All.", "unknown category 'misc'", id="unknown-category"),
        pytest.param("{name: py, version", "{name: own, version", "plugin name 'own' is used by 2 plugins", id="name-collision"),
        pytest.param("{name: web, version", "{name: Web, version", "plugin name 'Web' is not kebab-case", id="not-kebab"),
        pytest.param("dependencies: [core, py, web]", "dependencies: [core, py, web, nowhere]", "depends on unknown plugin 'nowhere'", id="unknown-dependency"),
        pytest.param("description: Shared., skills: [shared]}", "description: Shared., skills: [shared], dependencies: [py]}", "'core' must hold skills only", id="core-with-dependency"),
        pytest.param(GATE_HANDLER, GATE_HANDLER.replace('cd "${CLAUDE_PROJECT_DIR}" && ', ""), "hook 'gate' on PreToolUse must start with 'cd \"${CLAUDE_PROJECT_DIR}\" &&'", id="hook-outside-the-project"),
        pytest.param('"${CLAUDE_PLUGIN_ROOT}"/gate.py', ".agents/hooks/gate/gate.py", "hook 'gate' on PreToolUse names a script by its project path", id="hook-by-project-path"),
        pytest.param('"${CLAUDE_PLUGIN_ROOT}"/gate.py', "gate.py", "hook 'gate' on PreToolUse must run exactly one script from", id="hook-without-plugin-root"),
        pytest.param('"${CLAUDE_PLUGIN_ROOT}"/gate.py', '"${CLAUDE_PLUGIN_ROOT}"/other.py', "hook 'gate' on PreToolUse runs other.py, which .agents/hooks/gate does not hold", id="hook-script-missing"),
        pytest.param(DOCS_ENTRY, "", "server 'docs' in the root .mcp.json has no server entry", id="server-without-entry"),
        pytest.param('url: "https://docs.example"}', 'url: "https://docs.example/v2"}', "server 'docs' in the root .mcp.json differs from the block of its server entry", id="root-block-differs"),
    ],
)
def test_a_broken_map_names_the_rule_it_breaks(lab, old, new, expected):
    edit_map(lab, old, new)

    assert any(expected in problem for problem in problems(lab)), problems(lab)


def test_the_fixture_repository_gives_every_entry_the_listing_fields(lab):
    by_name = {entry["name"]: entry for entry in gen.marketplace(gen.load_sources(lab))["plugins"]}

    for entry in by_name.values():
        assert entry["author"] == {"name": "Lab", "url": "https://github.com/lab"}
        assert entry["homepage"] == "https://github.com/lab/agents#readme"
        assert entry["repository"] == "https://github.com/lab/agents"
        assert entry["license"] == "MIT"
        assert entry["tags"] == entry["keywords"]
    assert by_name["own"]["keywords"] == ["skill", "py", "own"]
    assert by_name["shared"]["keywords"] == ["skill", "core", "shared"]
    assert by_name["agent-pro"]["keywords"] == ["agent", "py", "pro"]
    assert by_name["hook-gate"]["keywords"] == ["hook", "gate"]
    assert by_name["mcp-docs"]["keywords"] == ["mcp", "docs"]
    assert by_name["py"]["keywords"] == ["bundle", "development", "py"]
    assert by_name["all"]["keywords"] == ["bundle", "all"]


def test_a_server_entry_the_root_file_leaves_out_still_renders_from_its_own_block(lab):
    edit_map(lab, DOCS_ENTRY, DOCS_ENTRY + "  - {name: cache, version: 1.0.0, description: Cache server., block: {type: stdio, command: uvx, args: [\"cache-mcp==1.2.3\"]}}\n")
    edit_map(lab, "dependencies: [mcp-docs]", "dependencies: [mcp-docs, mcp-cache]")

    document = gen.marketplace(gen.load_sources(lab))

    cache = next(entry for entry in document["plugins"] if entry["name"] == "mcp-cache")
    assert cache["mcpServers"] == {"cache": {"type": "stdio", "command": "uvx", "args": ["cache-mcp==1.2.3"]}}


@pytest.mark.parametrize(
    ("block", "reason"),
    [
        pytest.param('{type: stdio, command: npx, args: ["-y", "cache-mcp@latest"]}', "names no exact version", id="npm-latest"),
        pytest.param("{type: stdio, command: uvx, args: [cache-mcp]}", "names no exact version", id="no-version"),
        pytest.param("{type: stdio, command: docker, args: [run, -i, lab/cache]}", "names no tag and no digest", id="untagged-image"),
        pytest.param('{type: stdio, command: docker, args: [run, "--pull=always", -i, "lab/cache:1.2.3"]}', "pulls the image on every start", id="pull-always"),
    ],
)
def test_a_server_block_that_floats_is_refused(lab, block, reason):
    edit_map(lab, DOCS_ENTRY, DOCS_ENTRY + f"  - {{name: cache, version: 1.0.0, description: Cache server., block: {block}}}\n")
    edit_map(lab, "dependencies: [mcp-docs]", "dependencies: [mcp-docs, mcp-cache]")

    assert any(p.startswith("server 'cache' floats: ") and reason in p for p in problems(lab)), problems(lab)


@pytest.mark.parametrize(
    ("wiring", "expected"),
    [
        pytest.param("", "hook 'idle' needs a 'wiring'", id="no-wiring"),
        pytest.param(", wiring: {}", "hook 'idle' needs a 'wiring'", id="empty-wiring"),
        pytest.param(", wiring: {Stop: []}", "hook 'idle' 'wiring' on Stop needs a list of matcher groups", id="no-group"),
        pytest.param(", wiring: {Stop: [{matcher: Edit}]}", "hook 'idle' 'wiring' on Stop needs a 'hooks' list in every matcher group", id="no-handler"),
        pytest.param(", wiring: {Stop: [{hooks: [{type: prompt, prompt: Check.}]}]}", "takes handlers of type 'command' with a 'command' only", id="not-a-command"),
    ],
)
def test_a_hook_entry_that_wires_nothing_is_refused(lab, wiring, expected):
    write(lab / ".agents" / "hooks" / "idle" / "idle.py", "print()\n")
    edit_map(lab, "  - {name: gate,", f"  - {{name: idle, version: 1.0.0, description: Idle.{wiring}}}\n  - {{name: gate,")

    with pytest.raises(gen.PluginMapError, match=expected):
        gen.load_sources(lab)


def test_a_skill_two_bundles_preload_outside_core_is_refused(lab):
    agent(lab, "front", ["shared", "solo", "own"])

    assert any("preloads 'own' from 'py'" in p for p in problems(lab))


def test_a_dependency_cycle_is_refused(lab):
    edit_map(lab, "dependencies: [core], agents: [pro]", "dependencies: [core, all], agents: [pro]")

    assert any(p.startswith("dependency cycle:") for p in problems(lab))


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        pytest.param("{name: gate, version: 1.0.0,", "{name: gate, version: 1.0,", "MAJOR.MINOR.PATCH", id="two-part-version"),
        pytest.param("{name: docs, version: 1.0.0,", "{name: docs, version: v1.0.0,", "MAJOR.MINOR.PATCH", id="v-prefix"),
        pytest.param("{name: docs, version: 1.0.0,", "{name: docs, version: \"1.0.1\u0661\",", "MAJOR.MINOR.PATCH", id="non-ascii-digit"),
        pytest.param("{name: core, version: 1.0.0,", "{name: core, version: 1.0.0, defaultEnabled: false,", "unknown key", id="unknown-key"),
        pytest.param("{name: gate, version: 1.0.0,", "{name: gate, folder: ../gate, version: 1.0.0,", "folder", id="hook-folder-escapes"),
        pytest.param("{name: gate, version: 1.0.0,", "{name: gate, folder: /tmp/gate, version: 1.0.0,", "folder", id="hook-folder-absolute"),
        pytest.param("{name: gate, version: 1.0.0,", "{name: gate, folder: Gate, version: 1.0.0,", "folder", id="hook-folder-not-kebab"),
        pytest.param(', block: {type: http, url: "https://docs.example"}}', "}", "needs a 'block'", id="server-without-block"),
        pytest.param('block: {type: http, url: "https://docs.example"}', "block: npx docs", "needs a 'block'", id="server-block-not-a-mapping"),
        pytest.param("  license: MIT\n", "", "'license'", id="no-license"),
        pytest.param('  homepage: "https://github.com/lab/agents#readme"\n', "", "'homepage'", id="no-homepage"),
        pytest.param('homepage: "https://github.com/lab/agents#readme"', "homepage: the readme", "'homepage'", id="homepage-not-a-url"),
    ],
)
def test_a_malformed_map_is_refused_before_any_rule(lab, old, new, message):
    edit_map(lab, old, new)

    with pytest.raises(gen.PluginMapError, match=message):
        gen.load_sources(lab)


def test_a_skill_without_a_version_is_refused(lab):
    shutil.rmtree(lab / ".agents" / "skills" / "solo")
    write(lab / ".agents" / "skills" / "solo" / "SKILL.md", "---\nname: solo\ndescription: No version.\n---\nBody.\n")

    with pytest.raises(gen.PluginMapError, match="metadata.version"):
        gen.load_sources(lab)


def test_a_subagent_without_a_version_is_refused(lab):
    write(lab / "subagents" / "front.md", "---\nname: front\nlevel: 3\ndescription: Use when front.\nskills:\n  - shared\n---\nBody.\n")

    with pytest.raises(gen.PluginMapError, match="front.md version"):
        gen.load_sources(lab)


def test_the_check_mode_fails_on_a_stale_marketplace_and_passes_once_written(lab, monkeypatch, capsys):
    monkeypatch.setattr(gen, "ROOT", lab)

    with pytest.raises(SystemExit, match="STALE"):
        gen.main(["--check"])

    gen.main([])
    gen.main(["--check"])
    assert "is up to date" in capsys.readouterr().out
    assert json.loads((lab / gen.MARKETPLACE_FILE).read_text(encoding="utf-8"))["name"] == "lab"
