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
    "model": "sonnet",
    "skills": ["coding-standards", "python-patterns"],
}

TRICKY = {
    "name": "fixture-tricky",
    "description": 'Use when auditing a "live" system. Read-only: produces a report, applies no fix.',
    "tools": ["read", "grep", "glob"],
    "model": "sonnet",
    "skills": ["markdown-writer"],
}

FRONT_MATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)

READER = {
    "name": "fixture-reader",
    "description": "Use when a fixture needs reading only.",
    "tools": ["read", "grep", "glob"],
    "model": "opus",
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


def test_parse_rejects_an_unknown_model(tmp_path):
    path = write_agent(tmp_path, "bad-model", "name: bad-model\ndescription: Use when broken.\nmodel: gpt-9")

    with pytest.raises(SystemExit) as exc:
        gen.parse(path, SKILLS)

    assert "gpt-9" in str(exc.value)


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


def test_claude_emits_name_tools_model_and_skills():
    rendered = gen.emit_claude(WRITER, BODY)
    head = rendered.split("---\n")[1].splitlines()

    assert head[0] == "name: fixture-writer"
    assert head[1] == 'description: "Use when a fixture needs writing."'
    assert head[2] == "tools: Read, Write, Edit, Grep, Glob, Bash"
    assert head[3] == "model: sonnet"
    assert head[4:] == ["skills:", "  - coding-standards", "  - python-patterns"]
    assert "permissionMode" not in rendered


def test_opencode_emits_a_pinned_model_and_a_tool_map():
    rendered = gen.emit_opencode(WRITER, BODY)
    head = rendered.split("---\n")[1].splitlines()

    assert head[0] == 'description: "Use when a fixture needs writing."'
    assert head[1] == "mode: subagent"
    assert head[2] == "model: anthropic/claude-sonnet-4-6"
    assert head[3] == "tools:"
    assert head[4:] == [f"  {tool}: true" for tool in WRITER["tools"]]


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
    assert head[2] == 'tools: ["read", "create", "edit", "search", "bash", "powershell"]'


def test_copilot_drops_a_tool_it_has_no_confirmed_name_for():
    assert gen.copilot_tools(["read", "webfetch", "websearch", "task"]) == ["read"]


def test_copilot_emits_an_empty_list_when_every_tool_maps_to_nothing():
    """No key at all is how Copilot is told to grant everything.

    An agent whose whole canonical list has no Copilot name would otherwise be
    handed the full tool set, which is the opposite of what it declared.
    """
    researcher = dict(WRITER, tools=["webfetch", "websearch", "task"])

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
        (gen.emit_copilot, ("create", "edit", "bash", "powershell")),
    ],
    ids=["claude", "opencode", "copilot"],
)
def test_a_read_only_agent_gets_no_write_tool(emitter, forbidden):
    front_matter = emitter(READER, BODY).split("---\n")[1]

    for name in forbidden:
        assert name not in front_matter


def test_read_only_agent_gets_plan_permission_mode_on_claude():
    assert "permissionMode: plan" in gen.emit_claude(READER, BODY)
    assert gen.CLAUDE_READ_ONLY_PERMISSION_MODE == "plan"


def test_a_writing_agent_gets_no_permission_mode_on_claude():
    assert "permissionMode" not in gen.emit_claude(WRITER, BODY)


def test_codex_grants_no_tools_at_all():
    parsed = tomllib.loads(gen.emit_codex(READER, BODY))

    assert set(parsed) == {"name", "description", "developer_instructions"}


def test_the_opencode_model_ids_are_pinned_in_one_constant():
    assert gen.OPENCODE_MODELS == {
        "opus": "anthropic/claude-opus-4-7",
        "sonnet": "anthropic/claude-sonnet-4-6",
        "haiku": "anthropic/claude-haiku-4-5",
        "inherit": None,
    }
    assert gen.MODEL["opencode"] is gen.OPENCODE_MODELS
    assert set(gen.OPENCODE_MODELS) == set(gen.MODEL["claude"])


def test_inherit_is_passed_through_on_claude():
    assert "model: inherit" in gen.emit_claude({**WRITER, "model": "inherit"}, BODY)


def test_inherit_omits_the_model_line_on_opencode():
    rendered = gen.emit_opencode({**WRITER, "model": "inherit"}, BODY)

    assert "model:" not in rendered.split("---\n")[1]


def test_inherit_survives_a_round_trip_through_parse(tmp_path):
    path = write_agent(
        tmp_path, "inheritor", "name: inheritor\ndescription: Use when inheriting.\nmodel: inherit\ntools: [read]"
    )

    frontmatter, body = gen.parse(path, SKILLS)

    assert gen.render("claude", frontmatter, body).count("model: inherit") == 1
    assert "model:" not in gen.render("agents", frontmatter, body).split("---\n")[1]
