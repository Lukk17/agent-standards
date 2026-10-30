"""Tests for tools/gen_subagents.py.

The generator is installed as a top-level module (`py-modules` in
tools/pyproject.toml), so it imports normally rather than through the
importlib dance the hyphenated scripts need.

Validation failures are `sys.exit(message)` calls, so they surface as a
`SystemExit` whose `code` is the message string. The emitters are pure
functions over a frontmatter dict, so each one is exercised directly on a
fixture rather than through the filesystem.
"""

import re
import tomllib

import pytest
import yaml

import gen_subagents as gen

SKILLS = {"coding-standards", "python-patterns", "markdown-writer"}

BODY = "You do one thing.\n\n### Done when\n\nIt is done.\n"

WRITER = {
    "name": "fixture-writer",
    "description": "Use when a fixture needs writing.",
    "tools": ["read", "write", "edit", "grep", "glob", "bash"],
    "skills": ["coding-standards", "python-patterns"],
}

TRICKY = {
    "name": "fixture-tricky",
    "description": 'Use when auditing a "live" system. Read-only: produces a report, applies no fix.',
    "tools": ["read", "grep", "glob"],
    "skills": ["markdown-writer"],
}

FRONT_MATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)

READER = {
    "name": "fixture-reader",
    "description": "Use when a fixture needs reading only.",
    "tools": ["read", "grep", "glob"],
    "skills": ["markdown-writer"],
}


def front_matter(rendered):
    """The parsed front matter of a rendered markdown agent file."""
    match = FRONT_MATTER.match(rendered)

    assert match, f"no front matter block in:\n{rendered}"

    return yaml.safe_load(match.group(1))


def write_agent(directory, name, frontmatter, body=BODY):
    path = directory / f"{name}.md"
    path.write_text(f"---\n{frontmatter}\n---\n\n{body}", encoding="utf-8")

    return path


def test_parse_accepts_a_skill_that_has_a_folder(tmp_path):
    path = write_agent(
        tmp_path,
        "ok",
        "name: ok\ndescription: Use when fine.\nskills:\n  - coding-standards",
    )

    frontmatter, body = gen.parse(path, SKILLS)

    assert frontmatter["skills"] == ["coding-standards"]
    assert body.startswith("You do one thing.")


def test_parse_rejects_a_skill_with_no_folder(tmp_path):
    path = write_agent(
        tmp_path,
        "dangling",
        "name: dangling\ndescription: Use when broken.\n"
        "skills:\n  - coding-standards\n  - flutter-accessibility\n  - nextjs-best-practices",
    )

    with pytest.raises(SystemExit) as exc:
        gen.parse(path, SKILLS)

    message = str(exc.value)
    assert "dangling.md" in message
    assert "flutter-accessibility" in message
    assert "nextjs-best-practices" in message
    assert "coding-standards" not in message


def test_parse_rejects_a_scalar_skills_value(tmp_path):
    # Given a skills key written as one name rather than a list, which would
    # otherwise iterate as characters and report every letter as dangling
    path = write_agent(
        tmp_path,
        "scalar",
        "name: scalar\ndescription: Use when broken.\nskills: coding-standards",
    )

    # When
    with pytest.raises(SystemExit) as exc:
        gen.parse(path, SKILLS)

    # Then the message names the file and the shape it wanted
    message = str(exc.value)

    assert "scalar.md" in message
    assert "must be a list" in message


def test_parse_accepts_a_missing_skills_key(tmp_path):
    path = write_agent(tmp_path, "none", "name: none\ndescription: Use when fine.")

    frontmatter, _body = gen.parse(path, SKILLS)

    assert "skills" not in frontmatter


def test_parse_rejects_an_unknown_tool(tmp_path):
    path = write_agent(
        tmp_path, "bad-tool", "name: bad-tool\ndescription: Use when broken.\ntools: [read, telepathy]"
    )

    with pytest.raises(SystemExit) as exc:
        gen.parse(path, SKILLS)

    assert "telepathy" in str(exc.value)


@pytest.mark.parametrize("model", ["inherit", "opus", "sonnet", "gpt-9"])
def test_parse_rejects_any_model_key(tmp_path, model):
    # Given a canonical agent that pins a model, even the one that means the session model
    path = write_agent(tmp_path, "pinned", f"name: pinned\ndescription: Use when pinned.\nmodel: {model}")

    # When
    with pytest.raises(SystemExit) as exc:
        gen.parse(path, SKILLS)

    # Then the message names the file and says why no model is allowed
    message = str(exc.value)

    assert "pinned.md" in message
    assert "remove the 'model' key" in message
    assert "session model" in message


def test_parse_accepts_websearch_as_a_tool(tmp_path):
    path = write_agent(
        tmp_path, "searcher", "name: searcher\ndescription: Use when researching.\ntools: [read, webfetch, websearch]"
    )

    frontmatter, _ = gen.parse(path, SKILLS)

    assert gen.CLAUDE_TOOLS["websearch"] == "WebSearch"
    assert gen.emit_claude(frontmatter, BODY).splitlines()[3] == "tools: Read, WebFetch, WebSearch"


def test_generating_two_agents_with_the_same_name_fails(tmp_path, monkeypatch):
    src = tmp_path / "subagents"
    src.mkdir()
    skills = tmp_path / "skills"
    (skills / "coding-standards").mkdir(parents=True)
    write_agent(src, "first", "name: clash\ndescription: Use when first.")
    write_agent(src, "second", "name: clash\ndescription: Use when second.")

    monkeypatch.setattr(gen, "SRC", src)
    monkeypatch.setattr(gen, "SKILLS", skills)
    monkeypatch.setattr(gen, "SYMLINKS", {})
    monkeypatch.setattr(gen, "TARGETS", {"claude": (tmp_path / "out", ".md")})
    monkeypatch.setattr(gen.sys, "argv", ["gen_subagents.py"])

    with pytest.raises(SystemExit) as exc:
        gen.main()

    assert "duplicate agent name: clash" in str(exc.value)


def test_claude_emits_name_tools_and_skills():
    rendered = gen.emit_claude(WRITER, BODY)
    head = rendered.split("---\n")[1].splitlines()

    assert head[0] == "name: fixture-writer"
    assert head[1] == 'description: "Use when a fixture needs writing."'
    assert head[2] == "tools: Read, Write, Edit, Grep, Glob, Bash"
    assert head[3:] == ["skills:", "  - coding-standards", "  - python-patterns"]
    assert "permissionMode" not in rendered


def test_opencode_emits_no_model_and_a_tool_map():
    rendered = gen.emit_opencode(WRITER, BODY)
    head = rendered.split("---\n")[1].splitlines()

    assert head[0] == 'description: "Use when a fixture needs writing."'
    assert head[1] == "mode: subagent"
    assert head[2] == "tools:"
    assert head[3:] == [f"  {tool}: true" for tool in WRITER["tools"]]


def test_opencode_no_longer_emits_a_permissions_block():
    rendered = gen.emit_opencode({**WRITER, "permissions": {"edit": "deny"}}, BODY)

    assert "permissions" not in rendered
    assert "deny" not in rendered


def test_codex_emits_a_toml_document_with_the_body_inline():
    parsed = tomllib.loads(gen.emit_codex(WRITER, BODY))

    assert parsed["name"] == "fixture-writer"
    assert parsed["description"] == "Use when a fixture needs writing."
    assert parsed["developer_instructions"].startswith("You do one thing.")
    assert "- `coding-standards`" in parsed["developer_instructions"]


def test_copilot_emits_its_own_tool_names():
    rendered = gen.emit_copilot(WRITER, BODY)
    head = rendered.split("---\n")[1].splitlines()

    assert head[0] == "name: fixture-writer"
    assert head[1] == 'description: "Use when a fixture needs writing."'
    assert head[2] == 'tools: ["read", "create", "apply_patch", "edit", "search", "bash", "powershell"]'


def test_a_copilot_writing_agent_can_write_on_a_model_that_edits_with_apply_patch():
    """Copilot hands a GPT model apply_patch as its only file tool, and neither create nor edit grants it.

    In live run 36168529868 the docs-architect subagent, declared with create and edit, reached
    gpt-6-luna with only view and bash, under a system prompt telling it not to write files.
    """
    generated = (gen.TARGETS["copilot"][0] / "docs-architect.agent.md").read_text(encoding="utf-8")

    assert "apply_patch" in front_matter(generated)["tools"]


def test_copilot_drops_a_tool_it_has_no_mapping_for():
    assert gen.copilot_tools(["read", "task"]) == ["read"]


def test_copilot_maps_webfetch_and_websearch_onto_its_single_web_tool():
    """Copilot documents one `web` alias covering both WebSearch and WebFetch."""
    assert gen.copilot_tools(["read", "webfetch", "websearch"]) == ["read", "web"]


def test_a_copilot_research_agent_renders_with_the_web_tool():
    researcher = dict(WRITER, tools=["read", "grep", "webfetch", "websearch"])

    assert front_matter(gen.emit_copilot(researcher, BODY))["tools"] == ["read", "search", "web"]


def test_the_generated_copilot_research_agent_carries_the_web_tool():
    generated = (gen.TARGETS["copilot"][0] / "agent-engineer.agent.md").read_text(encoding="utf-8")

    assert "web" in front_matter(generated)["tools"]


def test_claude_renders_task_as_the_agent_spawning_tool():
    """Claude Code renamed Task to Agent and keeps Task only as an alias."""
    orchestrator = dict(WRITER, tools=["read", "task"])

    assert front_matter(gen.emit_claude(orchestrator, BODY))["tools"] == "Read, Agent"


def test_copilot_emits_an_empty_list_when_every_tool_maps_to_nothing():
    """No key at all is how Copilot is told to grant everything.

    An agent whose whole canonical list has no Copilot name would otherwise be
    handed the full tool set, which is the opposite of what it declared.
    """
    researcher = dict(WRITER, tools=["task"])

    front_matter = gen.emit_copilot(researcher, BODY).split("---\n")[1]

    assert "tools: []" in front_matter


def test_copilot_omits_the_tool_key_when_the_agent_declares_none():
    inheritor = {key: value for key, value in WRITER.items() if key != "tools"}

    front_matter = gen.emit_copilot(inheritor, BODY).split("---\n")[1]

    assert "tools:" not in front_matter


@pytest.mark.parametrize(
    "emitter",
    [gen.emit_claude, gen.emit_opencode, gen.emit_copilot],
    ids=["claude", "opencode", "copilot"],
)
def test_a_description_holding_a_colon_and_a_quote_stays_valid_yaml(emitter):
    """A colon followed by a space ends the key unless the value is quoted.

    GitHub Copilot skips an agent whose front matter a strict parser rejects,
    so every markdown emitter writes the description as a quoted scalar.
    """
    parsed = front_matter(emitter(TRICKY, BODY))

    assert parsed["description"] == TRICKY["description"]


@pytest.mark.parametrize(
    ("tool", "extension"),
    [("claude", ".md"), ("agents", ".md"), ("copilot", ".agent.md")],
)
def test_every_generated_markdown_agent_parses_and_keeps_its_description(tool, extension):
    outdir = gen.TARGETS[tool][0]
    sources = sorted(gen.SRC.glob("*.md"))

    assert sources, f"no canonical agents under {gen.SRC}"

    for source in sources:
        canonical = front_matter(source.read_text(encoding="utf-8"))
        generated = outdir / f"{canonical['name']}{extension}"

        assert generated.is_file(), f"{generated} was never generated"

        parsed = front_matter(generated.read_text(encoding="utf-8"))

        assert parsed["description"] == canonical["description"].strip()


@pytest.mark.parametrize(
    ("emitter", "forbidden"),
    [
        (gen.emit_claude, ("Write", "Edit", "Bash")),
        (gen.emit_opencode, ("write: true", "edit: true", "bash: true")),
        (gen.emit_copilot, ("create", "apply_patch", "edit", "bash", "powershell")),
    ],
    ids=["claude", "opencode", "copilot"],
)
def test_a_read_only_agent_gets_no_write_tool(emitter, forbidden):
    front_matter = emitter(READER, BODY).split("---\n")[1]

    for name in forbidden:
        assert name not in front_matter


def test_a_read_only_agent_is_denied_edit_and_bash_on_opencode():
    """OpenCode and Kilo Code treat `tools` as overrides, so only a permission denial makes it read-only."""
    parsed = front_matter(gen.emit_opencode(READER, BODY))

    assert parsed["permission"] == {"edit": "deny", "bash": "deny"}
    assert parsed["tools"] == {"read": True, "grep": True, "glob": True}


def test_an_agent_with_bash_but_no_file_tool_is_denied_only_edit_on_opencode():
    runner = dict(READER, tools=["read", "grep", "glob", "bash"])

    assert front_matter(gen.emit_opencode(runner, BODY))["permission"] == {"edit": "deny"}


def test_an_agent_with_write_alone_keeps_edit_on_opencode():
    drafter = dict(READER, tools=["read", "write", "grep", "glob"])

    assert front_matter(gen.emit_opencode(drafter, BODY))["permission"] == {"bash": "deny"}


def test_a_writing_agent_gets_no_permission_block_on_opencode():
    assert "permission" not in front_matter(gen.emit_opencode(WRITER, BODY))


def test_an_agent_declaring_no_tools_gets_no_permission_block_on_opencode():
    inheritor = {key: value for key, value in WRITER.items() if key != "tools"}

    assert "permission" not in front_matter(gen.emit_opencode(inheritor, BODY))


def test_every_generated_read_only_opencode_agent_denies_edit():
    for source in sorted(gen.SRC.glob("*.md")):
        canonical = front_matter(source.read_text(encoding="utf-8"))

        if set(canonical.get("tools") or []) != gen.READ_ONLY_TOOLS:
            continue

        generated = front_matter((gen.TARGETS["agents"][0] / f"{canonical['name']}.md").read_text(encoding="utf-8"))

        assert generated["permission"]["edit"] == "deny", canonical["name"]
        assert generated["permission"]["bash"] == "deny", canonical["name"]


def test_read_only_agent_gets_plan_permission_mode_on_claude():
    assert "permissionMode: plan" in gen.emit_claude(READER, BODY)
    assert gen.CLAUDE_READ_ONLY_PERMISSION_MODE == "plan"


def test_a_writing_agent_gets_no_permission_mode_on_claude():
    assert "permissionMode" not in gen.emit_claude(WRITER, BODY)


def test_codex_grants_no_tools_at_all():
    parsed = tomllib.loads(gen.emit_codex(READER, BODY))

    assert set(parsed) == {"name", "description", "developer_instructions"}


def test_the_generator_keeps_no_model_table():
    assert not hasattr(gen, "OPENCODE_MODELS")
    assert not hasattr(gen, "MODEL")
    assert not hasattr(gen, "CLAUDE_MODEL_LINE")


@pytest.mark.parametrize("fixture", [WRITER, READER, TRICKY], ids=["writer", "reader", "tricky"])
def test_claude_emits_no_model_line(fixture):
    """An explicit `model: inherit` would outrank the user's CLAUDE_CODE_SUBAGENT_MODEL default."""
    assert "model" not in front_matter(gen.emit_claude(fixture, BODY))


@pytest.mark.parametrize("tool", ["claude", "agents", "codex", "copilot"])
def test_every_target_emits_no_model(tmp_path, tool):
    # Given a parsed canonical agent with no model key
    path = write_agent(tmp_path, "plain", "name: plain\ndescription: Use when plain.\ntools: [read]")
    frontmatter, body = gen.parse(path, SKILLS)

    # When
    rendered = gen.render(tool, frontmatter, body)

    # Then the target falls back on the user's subagent default or the session model
    header = tomllib.loads(rendered) if tool == "codex" else front_matter(rendered)

    assert "model" not in header


def test_every_generated_agent_runs_on_the_session_model():
    sources = sorted(gen.SRC.glob("*.md"))

    assert sources, f"no canonical agents under {gen.SRC}"

    for source in sources:
        canonical = front_matter(source.read_text(encoding="utf-8"))
        name = canonical["name"]

        assert "model" not in canonical, f"{source.name} pins a model"

        for tool, (outdir, extension) in gen.TARGETS.items():
            rendered = (outdir / f"{name}{extension}").read_text(encoding="utf-8")
            header = tomllib.loads(rendered) if tool == "codex" else front_matter(rendered)

            assert "model" not in header, f"{tool}: {name}"


REVIEWER = {
    "name": "fixture-reviewer",
    "description": "Use when the user says review this diff.",
    "tools": ["read", "grep", "glob", "bash"],
    "readonly": True,
    "readonly-commands": ["gh pr diff*", "gh pr view*"],
    "skills": ["markdown-writer"],
}

REVIEWER_COMMANDS = ["git diff*", "git log*", "git show*", "git status*", "gh pr diff*", "gh pr view*"]


def read_only_section(text):
    """The backticked items under the read-only heading, in order."""
    section = text.split(f"### {gen.READ_ONLY_HEADING}\n", 1)[1].split("\n### ", 1)[0]

    return re.findall(r"^- `([^`]+)`$", section, re.M)


@pytest.mark.parametrize(
    ("frontmatter", "message"),
    [
        ("readonly: yes-please\ntools: [read, bash]", "must be true or false"),
        ("readonly-commands: [\"gh pr view*\"]\ntools: [read, bash]", "needs 'readonly: true'"),
        ("readonly: true\nreadonly-commands: gh pr view\ntools: [read, bash]", "must be a list"),
        ("readonly: true\ntools: [read, edit, bash]", "may not list edit"),
        ("readonly: true\ntools: [read, task, bash]", "may not list task"),
        ("readonly: true\ntools: [read, grep]", "list bash"),
    ],
)
def test_parse_rejects_a_read_only_marker_it_cannot_honour(tmp_path, frontmatter, message):
    path = write_agent(tmp_path, "marked", f"name: marked\ndescription: Use when marked.\n{frontmatter}")

    with pytest.raises(SystemExit) as exc:
        gen.parse(path, SKILLS)

    assert "marked.md" in str(exc.value)
    assert message in str(exc.value)


def test_parse_accepts_a_read_only_marker_with_extra_commands(tmp_path):
    path = write_agent(
        tmp_path,
        "marked",
        'name: marked\ndescription: Use when marked.\ntools: [read, bash]\nreadonly: true\nreadonly-commands: ["gh pr view*"]',
    )

    frontmatter, _ = gen.parse(path, SKILLS)

    assert gen.read_only_commands(frontmatter) == ["git diff*", "git log*", "git show*", "git status*", "gh pr view*"]


def test_claude_keeps_bash_and_plan_mode_for_a_read_only_agent():
    rendered = gen.emit_claude(REVIEWER, BODY)
    head = front_matter(rendered)

    assert head["tools"] == "Read, Grep, Glob, Bash"
    assert head["permissionMode"] == "plan"
    assert read_only_section(rendered) == REVIEWER_COMMANDS


def test_opencode_denies_edit_and_every_command_but_the_list_for_a_read_only_agent():
    rendered = gen.emit_opencode(REVIEWER, BODY)
    permission = front_matter(rendered)["permission"]

    assert permission["edit"] == "deny"
    assert list(permission["bash"]) == ["*", *REVIEWER_COMMANDS]
    assert permission["bash"]["*"] == "deny"
    assert all(permission["bash"][command] == "allow" for command in REVIEWER_COMMANDS)
    assert read_only_section(rendered) == REVIEWER_COMMANDS


def test_codex_carries_the_read_only_list_in_its_instructions():
    instructions = tomllib.loads(gen.emit_codex(REVIEWER, BODY))["developer_instructions"]

    assert read_only_section(instructions) == REVIEWER_COMMANDS


def test_copilot_drops_the_shell_for_a_read_only_agent():
    rendered = gen.emit_copilot(REVIEWER, BODY)

    assert front_matter(rendered)["tools"] == ["read", "search"]
    assert "gets no shell on this agent" in rendered
    assert read_only_section(rendered) == REVIEWER_COMMANDS


def test_an_agent_without_the_marker_gets_no_read_only_section():
    for tool in gen.TARGETS:
        assert gen.READ_ONLY_HEADING not in gen.render(tool, WRITER, BODY)


@pytest.mark.parametrize("agent", ["code-reviewer", "code-archaeologist"])
def test_the_shipped_reviewers_are_read_only_with_bash(agent):
    canonical = front_matter((gen.SRC / f"{agent}.md").read_text(encoding="utf-8"))
    opencode = front_matter((gen.TARGETS["agents"][0] / f"{agent}.md").read_text(encoding="utf-8"))

    assert canonical["readonly"] is True
    assert "bash" in canonical["tools"]
    assert opencode["permission"]["edit"] == "deny"
    assert opencode["permission"]["bash"]["*"] == "deny"


def test_the_skills_block_names_no_project_only_path():
    block = gen.skills_block(["markdown-writer"])

    assert "Load a skill by name" in block
    assert "`.agents/skills/` in a project, the global skills folder otherwise" in block
    assert "from `.agents/skills/` before acting" not in block


def test_no_canonical_body_hard_codes_a_skill_path():
    for source in sorted(gen.SRC.glob("*.md")):
        assert ".agents/skills/" not in source.read_text(encoding="utf-8"), source.name


DESCRIPTION_LIMITS = (300, 400)


@pytest.mark.parametrize("source", sorted(gen.SRC.glob("*.md")), ids=lambda path: path.stem)
def test_every_subagent_description_follows_the_contributing_rule(source):
    """CONTRIBUTING.md, "Adding a new subagent": third person, 300 to 400 characters, one "Not for" pointer."""
    description = front_matter(source.read_text(encoding="utf-8"))["description"]

    assert description.startswith("Use when the user "), description
    assert DESCRIPTION_LIMITS[0] <= len(description) <= DESCRIPTION_LIMITS[1], len(description)
    assert description.count("Not for ") == 1, description
    pointer = re.search(r"Not for [^.]+, use `([a-z0-9-]+)`\.$", description)

    assert pointer, description
    assert pointer.group(1) != source.stem, "the pointer names the agent itself"
    assert (gen.SRC / f"{pointer.group(1)}.md").is_file(), pointer.group(1)
