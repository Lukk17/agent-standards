"""Tests for the front matter checks in tools/check-markdown.py.

The script's filename carries a hyphen, so it is loaded in-process via
importlib rather than a normal `import` statement, the same technique
tests/test_check_badges.py uses for its own hyphenated sibling.

Every case drives a real file under a throwaway repo root, because the check
reads the skill folder name and the subagent file stem out of the path itself.
The last test runs the check over the real repository, so a manifest that stops
parsing can never reach a green suite.
"""

import importlib.util

import pytest

from tests.conftest import REPO_ROOT

CHECK_MARKDOWN = REPO_ROOT / "tools" / "check-markdown.py"


def _load_check_markdown_module():
    spec = importlib.util.spec_from_file_location("check_markdown", CHECK_MARKDOWN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


MARKDOWN = _load_check_markdown_module()

CLEAN_SKILL_FRONT_MATTER = """---
name: demo-skill
description: Demo skill for the lint tests. Use when you say "run the lint tests".
---
"""

CLEAN_SUBAGENT_FRONT_MATTER = """---
name: demo-agent
description: Demo subagent for the lint tests.
tools: Read, Grep, Glob
model: inherit
skills: [coding-standards]
---
"""

BODY = """
# Demo

Body prose that breaks none of the other rules.
"""


def _write_skill(tmp_path, front_matter, name="demo-skill"):
    directory = tmp_path / ".agents" / "skills" / name
    directory.mkdir(parents=True)
    path = directory / "SKILL.md"
    path.write_text(front_matter + BODY, encoding="utf-8")

    return path


def _write_subagent(tmp_path, front_matter, name="demo-agent"):
    directory = tmp_path / "subagents"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.md"
    path.write_text(front_matter + BODY, encoding="utf-8")

    return path


def test_clean_skill_manifest_reports_nothing(tmp_path, capsys):
    # Given a skill manifest whose front matter satisfies every rule
    path = _write_skill(tmp_path, CLEAN_SKILL_FRONT_MATTER)

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 0
    assert capsys.readouterr().out == ""


def test_clean_subagent_source_reports_nothing(tmp_path, capsys):
    # Given a subagent source carrying the keys the generator needs
    path = _write_subagent(tmp_path, CLEAN_SUBAGENT_FRONT_MATTER)

    # When
    failures = MARKDOWN.check_file(path)

    # Then the subagent-only keys are not treated as a specification violation
    assert failures == 0
    assert capsys.readouterr().out == ""


def test_skill_carrying_the_optional_specification_keys_passes(tmp_path, capsys):
    # Given a manifest using every key the Agent Skills specification allows
    front_matter = """---
name: demo-skill
description: Demo skill for the lint tests.
license: Apache-2.0
compatibility: Works anywhere.
metadata:
  version: 1
---
"""
    path = _write_skill(tmp_path, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 0
    assert capsys.readouterr().out == ""


def test_missing_front_matter_block_is_reported(tmp_path, capsys):
    # Given a manifest that opens straight into prose
    path = _write_skill(tmp_path, "# Demo skill\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 1

    out = capsys.readouterr().out
    assert "::error" in out
    assert "front matter missing" in out


def test_unterminated_front_matter_block_is_reported(tmp_path, capsys):
    # Given a front matter block whose closing fence was never written
    front_matter = """---
name: demo-skill
description: Demo skill for the lint tests.
"""
    path = _write_skill(tmp_path, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 1
    assert "never closed by a second ---" in capsys.readouterr().out


def test_unquoted_colon_in_description_is_reported_as_both_defects(tmp_path, capsys):
    # Given the exact shape GitHub Copilot refused to load: a plain scalar
    # holding a colon and a space, which YAML reads as a nested mapping
    front_matter = """---
name: demo-skill
description: Regression testing for AI-assisted development: bug-driven selection.
---
"""
    path = _write_skill(tmp_path, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then the actionable quoting message lands alongside the parser's own
    assert failures == 2

    out = capsys.readouterr().out
    assert "description holds an unquoted colon" in out
    assert "front matter is not valid YAML" in out


def test_quoted_colon_in_description_passes(tmp_path, capsys):
    # Given the same description with the whole scalar wrapped in double quotes
    front_matter = """---
name: demo-skill
description: "Regression testing for AI-assisted development: bug-driven selection."
---
"""
    path = _write_skill(tmp_path, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 0
    assert capsys.readouterr().out == ""


def test_quoted_description_may_hold_escaped_double_quotes(tmp_path, capsys):
    # Given a quoted description quoting a user phrase inside itself
    front_matter = """---
name: demo-skill
description: "Optimisation help: \\"why is this query slow?\\", and index advice."
---
"""
    path = _write_skill(tmp_path, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 0
    assert capsys.readouterr().out == ""


INDICATOR_DESCRIPTIONS = {
    "folded-block-scalar": ">-\n  Folded description text.",
    "literal-block-scalar": "|\n  Literal description text.",
    "alias": "*anchor-name",
    "anchor": "&anchor-name text",
    "tag": "!!str text",
    "directive": "%YAML text",
    "reserved-at": "@text",
    "backtick": "`text`",
    "flow-sequence": "[text]",
    "flow-mapping": "{text}",
    "stray-double-quote": '"text unbalanced',
    "stray-single-quote": "'text unbalanced",
}


@pytest.mark.parametrize(
    ("case", "scalar"),
    sorted(INDICATOR_DESCRIPTIONS.items()),
    ids=sorted(INDICATOR_DESCRIPTIONS),
)
def test_description_opening_with_a_yaml_indicator_is_reported(tmp_path, capsys, case, scalar):
    # Given a description scalar starting with a character YAML reads as an indicator
    front_matter = f"""---
name: demo-skill
description: {scalar}
---
"""
    path = _write_skill(tmp_path, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then the quoting advice is reported whether or not YAML also rejects it
    assert failures >= 1
    assert "and is not quoted" in capsys.readouterr().out


def test_missing_name_is_reported(tmp_path, capsys):
    # Given front matter with no name key at all
    front_matter = """---
description: Demo skill for the lint tests.
---
"""
    path = _write_skill(tmp_path, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 1
    assert "name is None but the folder name is 'demo-skill'" in capsys.readouterr().out


def test_skill_name_not_matching_the_folder_is_reported(tmp_path, capsys):
    # Given a manifest declaring a name other than its own folder
    front_matter = """---
name: renamed-skill
description: Demo skill for the lint tests.
---
"""
    path = _write_skill(tmp_path, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 1
    assert "name is 'renamed-skill' but the folder name is 'demo-skill'" in capsys.readouterr().out


def test_subagent_name_not_matching_the_file_stem_is_reported(tmp_path, capsys):
    # Given a subagent source declaring a name other than its own file stem
    front_matter = """---
name: renamed-agent
description: Demo subagent for the lint tests.
---
"""
    path = _write_subagent(tmp_path, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 1
    assert "name is 'renamed-agent' but the file stem is 'demo-agent'" in capsys.readouterr().out


def test_missing_description_is_reported(tmp_path, capsys):
    # Given front matter carrying only a name
    front_matter = """---
name: demo-skill
---
"""
    path = _write_skill(tmp_path, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 1
    assert "description is missing" in capsys.readouterr().out


def test_empty_description_is_reported(tmp_path, capsys):
    # Given a description key with nothing but whitespace after it
    front_matter = """---
name: demo-skill
description: "   "
---
"""
    path = _write_skill(tmp_path, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 1
    assert "description is empty" in capsys.readouterr().out


def test_non_string_description_is_reported(tmp_path, capsys):
    # Given a description YAML resolves to a number rather than text
    front_matter = """---
name: demo-skill
description: 42
---
"""
    path = _write_skill(tmp_path, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 1
    assert "description has to be a string, found int" in capsys.readouterr().out


def test_description_over_the_cap_is_reported(tmp_path, capsys):
    # Given a description one character past the 1024 cap
    front_matter = f"""---
name: demo-skill
description: {"d" * (MARKDOWN.MAX_DESCRIPTION + 1)}
---
"""
    path = _write_skill(tmp_path, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 1
    assert f"description is 1025 characters, over the {MARKDOWN.MAX_DESCRIPTION} character cap" in capsys.readouterr().out


def test_description_exactly_at_the_cap_passes(tmp_path, capsys):
    # Given a description of exactly 1024 characters
    front_matter = f"""---
name: demo-skill
description: {"d" * MARKDOWN.MAX_DESCRIPTION}
---
"""
    path = _write_skill(tmp_path, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then the cap is inclusive
    assert failures == 0
    assert capsys.readouterr().out == ""


def test_skill_key_outside_the_specification_is_reported(tmp_path, capsys):
    # Given a manifest carrying a key the Agent Skills specification does not define
    front_matter = """---
name: demo-skill
description: Demo skill for the lint tests.
tools: Read, Grep
---
"""
    path = _write_skill(tmp_path, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 1

    out = capsys.readouterr().out
    assert "key 'tools' is not in the Agent Skills specification" in out
    assert "allowed keys are name, description, license, compatibility, metadata" in out


def test_every_key_outside_the_specification_is_reported(tmp_path, capsys):
    # Given two keys outside the specification at once
    front_matter = """---
name: demo-skill
description: Demo skill for the lint tests.
model: inherit
allowed-tools: Read
---
"""
    path = _write_skill(tmp_path, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then neither is swallowed by the first
    assert failures == 2

    out = capsys.readouterr().out
    assert "key 'allowed-tools'" in out
    assert "key 'model'" in out


def test_front_matter_that_is_not_a_mapping_is_reported(tmp_path, capsys):
    # Given a front matter block holding a YAML sequence
    front_matter = """---
- demo-skill
- a description
---
"""
    path = _write_skill(tmp_path, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 1
    assert "front matter has to be a YAML mapping" in capsys.readouterr().out


def test_reference_file_beside_a_manifest_carries_no_front_matter_contract(tmp_path, capsys):
    # Given a reference file inside a skill folder, which ships no front matter
    directory = tmp_path / ".agents" / "skills" / "demo-skill" / "references"
    directory.mkdir(parents=True)
    path = directory / "typing.md"
    path.write_text("# Typing\n\nPlain reference prose.\n", encoding="utf-8")

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 0
    assert capsys.readouterr().out == ""


def test_shipped_document_carries_no_front_matter_contract(tmp_path, capsys):
    # Given a document under docs/, which is prose rather than a manifest
    directory = tmp_path / "docs"
    directory.mkdir()
    path = directory / "MCP_SETUP.md"
    path.write_text("# MCP setup\n\nPlain prose.\n", encoding="utf-8")

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 0
    assert capsys.readouterr().out == ""


def test_existing_prose_checks_still_run_on_a_manifest(tmp_path, capsys):
    # Given a manifest with both a broken front matter and an em-dash in the body
    front_matter = """---
name: renamed-skill
description: Demo skill for the lint tests.
---
"""
    path = _write_skill(tmp_path, front_matter)
    path.write_text(
        front_matter + "\n# Demo\n\nProse with an em-dash — in it.\n",
        encoding="utf-8",
    )

    # When
    failures = MARKDOWN.check_file(path)

    # Then the front matter check adds to the prose checks rather than replacing them
    assert failures == 2

    out = capsys.readouterr().out
    assert "em-dash or en-dash found" in out
    assert "name is 'renamed-skill'" in out


def test_front_matter_check_stands_down_when_pyyaml_is_unavailable(tmp_path, capsys, monkeypatch):
    # Given an interpreter with no yaml module, which is what `python -S -E`
    # produces when the site path was not recovered
    monkeypatch.setattr(MARKDOWN, "yaml", None)
    front_matter = """---
name: renamed-skill
description: Demo skill for the lint tests.
---
"""
    path = _write_skill(tmp_path, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then the parsed checks are skipped with a warning instead of an exception
    assert failures == 0

    out = capsys.readouterr().out
    assert "::warning" in out
    assert "pyyaml is not importable" in out


def test_raw_description_check_still_runs_without_pyyaml(tmp_path, capsys, monkeypatch):
    # Given no yaml module and a description needing quotes
    monkeypatch.setattr(MARKDOWN, "yaml", None)
    front_matter = """---
name: demo-skill
description: Regression testing for AI-assisted development: bug-driven selection.
---
"""
    path = _write_skill(tmp_path, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then the defect that broke GitHub Copilot is still caught
    assert failures == 1
    assert "description holds an unquoted colon" in capsys.readouterr().out


def test_front_matter_target_classifies_the_two_manifest_kinds():
    # Given one path of each kind and one of neither
    skill = REPO_ROOT / ".agents" / "skills" / "python-patterns" / "SKILL.md"
    subagent = REPO_ROOT / "subagents" / "python-pro.md"
    document = REPO_ROOT / "docs" / "MCP_SETUP.md"

    # When / Then
    assert MARKDOWN.front_matter_target(skill) == ("skill", "python-patterns")
    assert MARKDOWN.front_matter_target(subagent) == ("subagent", "python-pro")
    assert MARKDOWN.front_matter_target(document) is None


def test_generated_subagent_trees_are_out_of_front_matter_scope():
    # Given a generated OpenCode-format agent, which is rendered rather than authored
    generated = REPO_ROOT / ".agents" / "agents" / "python-pro.md"

    # When / Then the check never fires there, so a violation is reported once
    assert MARKDOWN.front_matter_target(generated) is None


def test_every_real_manifest_and_subagent_source_parses():
    # Given the actual repository this test suite lives in
    targets = sorted((REPO_ROOT / ".agents" / "skills").glob("*/SKILL.md"))
    targets.extend(sorted((REPO_ROOT / "subagents").glob("*.md")))

    # When
    failures = sum(MARKDOWN.check_file(path) for path in targets)

    # Then every manifest an agent loads is valid by the time the suite is green
    assert failures == 0
