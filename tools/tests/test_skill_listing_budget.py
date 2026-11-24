"""Tests that every plugin group's descriptions fit what Claude Code lists of them.

Claude Code puts a listing of the enabled skills into every turn, and "The
budget scales at 1% of the model's context window. When the listing overflows,
Claude Code drops descriptions starting with the skills you invoke least"
(https://code.claude.com/docs/en/skills, "Skill descriptions are cut short",
read 2026-11-24). The budget is a character count, "1% of the context window,
with a fallback of 8,000 characters" (https://code.claude.com/docs/en/env-vars,
SLASH_COMMAND_TOOL_CHAR_BUDGET). The docs give no rate from tokens to
characters. The Claude Code 2.1.314 binary multiplies the window by 4
characters a token for the Claude 3 models and Claude 4 up to 4.6, and by 3 for
every other model, so these tests use 3, the smaller budget.

The same binary counts the listing as one line per skill, "- <name>:
<description>", joined by newlines, with each description cut at 1,536
characters. A skill from a plugin is named <plugin>:<skill>, and every skill
plugin here is named for its skill. That count matched the listing a sandbox
session sent to the model, character for character.

Subagent descriptions are not in that listing. Claude Code warns "When the
combined descriptions of your subagents, except the built-in ones, exceed 15,000
tokens" (https://code.claude.com/docs/en/sub-agents, read 2026-11-24). A token
holds at least one byte, so a group whose descriptions take at most 15,000
bytes in UTF-8 stays under that limit.
"""

import dataclasses

import pytest

import gen_plugins as gen
from plugin_model import AGENT_PREFIX, ALL, CORE, DOMAIN_CATEGORIES
from tests.conftest import REPO_ROOT

BUDGET_FRACTION = 0.01
CHARACTERS_PER_TOKEN = 3
SMALL_WINDOW = 200_000
LARGE_WINDOW = 1_000_000
DESCRIPTION_CAP = 1536
AGENT_DESCRIPTION_TOKENS = 15_000
OVERSIZED = "x" * (DESCRIPTION_CAP * 3)

SOURCES = gen.load_sources(REPO_ROOT)


def budget(window: int) -> int:
    """The listing budget in characters for a context window of `window` tokens."""
    return int(window * CHARACTERS_PER_TOKEN * BUDGET_FRACTION)


def installed(sources: gen.Sources, *bundles: str) -> set[str]:
    """Every plugin the named bundles install, the bundles included."""
    graph = gen.dependency_graph(sources)

    return {plugin for bundle in bundles for plugin in {bundle, *gen.dependency_closure(bundle, graph)}}


def listing_size(sources: gen.Sources, plugins: set[str]) -> int:
    """The characters of the skill listing those plugins add, counted the way Claude Code counts it."""
    skills = sorted(name for name in plugins if name in sources.skills)
    lines = [len(f"- {name}:{name}: ") + min(len(sources.skills[name].description), DESCRIPTION_CAP) for name in skills]

    return sum(lines) + max(0, len(lines) - 1)


def agent_bytes(sources: gen.Sources, plugins: set[str]) -> int:
    """The UTF-8 bytes of the descriptions of every subagent those plugins install."""
    agents = [agent for agent in sources.agents.values() if AGENT_PREFIX + agent.name in plugins]

    return sum(len(agent.description.encode("utf-8")) for agent in agents)


def groups(sources: gen.Sources) -> dict[str, tuple[set[str], int]]:
    """Each group a user installs, with what it installs and the budget it has to fit."""
    domains = [bundle.name for bundle in sources.plugin_map.bundles if bundle.category in DOMAIN_CATEGORIES and bundle.name != CORE]
    found = {CORE: (installed(sources, CORE), budget(SMALL_WINDOW))}
    found.update({f"{CORE} and {name}": (installed(sources, CORE, name), budget(SMALL_WINDOW)) for name in domains})
    found[ALL] = (installed(sources, ALL), budget(LARGE_WINDOW))

    return found


def over_budget(sources: gen.Sources) -> list[str]:
    """Every group whose skill listing is larger than its budget."""
    return [name for name, (plugins, limit) in groups(sources).items() if listing_size(sources, plugins) > limit]


def over_warning(sources: gen.Sources) -> list[str]:
    """Every group whose subagent descriptions can pass the warning limit."""
    return [name for name, (plugins, _limit) in groups(sources).items() if agent_bytes(sources, plugins) > AGENT_DESCRIPTION_TOKENS]


GROUPS = groups(SOURCES)


def test_the_budgets_are_the_characters_claude_code_gives_a_200k_and_a_1m_window():
    assert (budget(SMALL_WINDOW), budget(LARGE_WINDOW)) == (6_000, 30_000)


def test_core_alone_each_domain_with_core_and_all_are_checked():
    domains = {bundle.name for bundle in SOURCES.plugin_map.bundles if bundle.category in DOMAIN_CATEGORIES} - {CORE}

    assert set(GROUPS) == {CORE, ALL} | {f"{CORE} and {name}" for name in domains}
    assert all(listing_size(SOURCES, plugins) > 0 for plugins, _limit in GROUPS.values())


@pytest.mark.parametrize("name", GROUPS)
def test_the_skill_listing_of_each_group_fits_its_budget(name):
    plugins, limit = GROUPS[name]

    assert listing_size(SOURCES, plugins) <= limit


@pytest.mark.parametrize("name", GROUPS)
def test_the_subagent_descriptions_of_each_group_stay_under_the_warning(name):
    plugins, _limit = GROUPS[name]

    assert agent_bytes(SOURCES, plugins) <= AGENT_DESCRIPTION_TOKENS


def test_a_line_is_the_skill_s_plugin_name_and_its_description_and_lines_are_joined_by_newlines():
    skill = SOURCES.skills["bash"]

    assert listing_size(SOURCES, {"bash"}) == len(f"- bash:bash: {skill.description}")
    assert listing_size(SOURCES, {"bash", "powershell"}) == listing_size(SOURCES, {"bash"}) + listing_size(SOURCES, {"powershell"}) + 1


def test_a_description_counts_only_up_to_the_cap():
    sources = dataclasses.replace(SOURCES, skills={**SOURCES.skills, "bash": dataclasses.replace(SOURCES.skills["bash"], description=OVERSIZED)})

    assert listing_size(sources, {"bash"}) == len("- bash:bash: ") + DESCRIPTION_CAP


def test_oversized_skill_descriptions_put_every_group_over_its_budget():
    skills = {name: dataclasses.replace(skill, description=OVERSIZED) for name, skill in SOURCES.skills.items()}

    assert over_budget(dataclasses.replace(SOURCES, skills=skills)) == list(GROUPS)


def test_oversized_subagent_descriptions_put_all_over_the_warning():
    agents = {name: dataclasses.replace(agent, description=OVERSIZED) for name, agent in SOURCES.agents.items()}

    assert ALL in over_warning(dataclasses.replace(SOURCES, agents=agents))
