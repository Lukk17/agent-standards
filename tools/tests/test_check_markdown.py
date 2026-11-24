"""Tests for the markdown rules in .agents/hooks/markdown-lint-check/_check_markdown.py.

The rules ship inside the hooks directory so a consumer checkout has them, and
tools/check-markdown.py is only the command CI runs over this repository. The
module lives in a dotted directory, so it is loaded in-process via importlib
rather than a normal `import` statement, the same technique
tests/test_check_badges.py uses for its own hyphenated sibling.

Every case drives a real file under a throwaway repo root, because the check
reads the skill folder name and the subagent file stem out of the path itself.
The check also runs over the real repository, every file of every skill and
every subagent source, so a manifest that stops parsing or a skill that leaves
the lean layout can never reach a green suite.
"""

import importlib.util
import sys

import pytest

from tests.conftest import MARKDOWN_LINT_RULES, REPO_ROOT
from tests.process_tree import run_bounded

CHECK_MARKDOWN = MARKDOWN_LINT_RULES

CI_COMMAND = REPO_ROOT / "tools" / "check-markdown.py"


def _load_check_markdown_module():
    spec = importlib.util.spec_from_file_location("check_markdown", CHECK_MARKDOWN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


MARKDOWN = _load_check_markdown_module()

SKILLS_ROOT = REPO_ROOT / ".agents" / "skills"

CLEAN_SKILL_FRONT_MATTER = """---
name: demo-skill
description: Demo skill for the lint tests. Use when you say "run the lint tests".
metadata:
  version: "1.0.0"
---
"""

CLEAN_SUBAGENT_FRONT_MATTER = """---
name: demo-agent
description: Demo subagent for the lint tests.
version: 1.0.0
tools: Read, Grep, Glob
skills: [coding-standards]
---
"""

BODY = """
# Demo

Body prose that breaks none of the other rules.
"""


def _with_version(front_matter, line):
    """The front matter with a version line before its closing fence, unless it already names one."""
    if "version" in front_matter or not front_matter.startswith("---\n") or front_matter.startswith("---\n- ") or "\n---\n" not in front_matter[3:]:
        return front_matter
    head, _, tail = front_matter.rpartition("---\n")

    return f"{head}{line}---\n{tail}"


def _write_skill(tmp_path, front_matter, name="demo-skill"):
    front_matter = _with_version(front_matter, 'metadata:\n  version: "1.0.0"\n')
    directory = tmp_path / ".agents" / "skills" / name
    directory.mkdir(parents=True)
    path = directory / "SKILL.md"
    path.write_text(front_matter + BODY, encoding="utf-8")

    return path


def _write_subagent(tmp_path, front_matter, name="demo-agent"):
    front_matter = _with_version(front_matter, "version: 1.0.0\n")
    directory = tmp_path / "subagents"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.md"
    path.write_text(front_matter + BODY, encoding="utf-8")

    return path


def _write_manifest(tmp_path, body, name="demo-skill"):
    directory = tmp_path / ".agents" / "skills" / name
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "SKILL.md"
    path.write_text(CLEAN_SKILL_FRONT_MATTER + "\n# Demo\n\n" + body, encoding="utf-8")

    return path


def _write_reference(tmp_path, relative, body, name="demo-skill"):
    path = tmp_path / ".agents" / "skills" / name / "references" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")

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
  version: "2.1.0"
  owner: demo
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


DESCRIPTION_CAPS = {"skill": MARKDOWN.MAX_SKILL_DESCRIPTION_CHARACTERS, "subagent": MARKDOWN.MAX_DESCRIPTION}

OVER_THE_CAP_MESSAGES = {
    "skill": 'description is 221 characters, over the 220 character limit for a skill. Keep what the skill covers, the phrases a user says and one "Not for X, use `skill`" pointer',
    "subagent": "description is 1025 characters, over the 1024 character cap",
}


def _with_description(tmp_path, kind, length):
    name, write = ("demo-skill", _write_skill) if kind == "skill" else ("demo-agent", _write_subagent)
    front_matter = f"""---
name: {name}
description: {"d" * length}
---
"""

    return write(tmp_path, front_matter)


@pytest.mark.parametrize("kind", sorted(DESCRIPTION_CAPS))
def test_description_over_the_cap_is_reported(tmp_path, capsys, kind):
    # Given a description one character past the cap of its kind
    path = _with_description(tmp_path, kind, DESCRIPTION_CAPS[kind] + 1)

    # When
    failures = MARKDOWN.check_file(path)

    # Then the description line is reported once, with the size, the cap and, for a skill, what a description keeps
    out = capsys.readouterr().out
    assert failures == 1
    assert "line=3::" in out
    assert OVER_THE_CAP_MESSAGES[kind] in out


@pytest.mark.parametrize("kind", sorted(DESCRIPTION_CAPS))
def test_description_exactly_at_the_cap_passes(tmp_path, capsys, kind):
    # Given a description of exactly the cap of its kind
    path = _with_description(tmp_path, kind, DESCRIPTION_CAPS[kind])

    # When
    failures = MARKDOWN.check_file(path)

    # Then the cap is inclusive
    assert failures == 0
    assert capsys.readouterr().out == ""


def test_a_skill_description_over_the_subagent_cap_is_reported_once(tmp_path, capsys):
    # Given a skill description past the cap of a subagent too
    path = _with_description(tmp_path, "skill", MARKDOWN.MAX_DESCRIPTION + 1)

    # When
    failures = MARKDOWN.check_file(path)

    # Then one violation names the skill limit, and the subagent cap stays silent
    out = capsys.readouterr().out
    assert failures == 1
    assert out.count("::error") == 1
    assert "description is 1025 characters, over the 220 character limit for a skill" in out


def test_subagent_description_is_not_held_to_the_skill_limit(tmp_path, capsys):
    # Given a subagent description of the length its own rule asks for, past the skill limit
    front_matter = f"""---
name: demo-agent
description: {"d" * 400}
---
"""
    path = _write_subagent(tmp_path, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 0
    assert capsys.readouterr().out == ""


def _pad_to(path, size):
    text = path.read_text(encoding="utf-8")
    path.write_text(text + "x" * (size - len(text) - 1) + "\n", encoding="utf-8")


def test_skill_manifest_over_the_size_limit_is_reported(tmp_path, capsys):
    # Given a clean skill manifest one character past the limit, front matter included
    path = _write_skill(tmp_path, CLEAN_SKILL_FRONT_MATTER)
    _pad_to(path, MARKDOWN.MAX_SKILL_MANIFEST_CHARACTERS + 1)

    # When
    failures = MARKDOWN.check_file(path)

    # Then the message names the size, the limit and where the depth goes
    out = capsys.readouterr().out
    assert failures == 1
    assert "skill manifest is 4501 characters, over the 4500 character limit" in out
    assert "references/" in out


def test_skill_manifest_exactly_at_the_size_limit_passes(tmp_path, capsys):
    # Given a clean skill manifest of exactly the limit
    path = _write_skill(tmp_path, CLEAN_SKILL_FRONT_MATTER)
    _pad_to(path, MARKDOWN.MAX_SKILL_MANIFEST_CHARACTERS)

    # When
    failures = MARKDOWN.check_file(path)

    # Then the limit is inclusive
    assert failures == 0
    assert capsys.readouterr().out == ""


def test_reference_file_over_the_size_limit_is_not_reported(tmp_path, capsys):
    # Given a reference file past the manifest limit, which loads only on demand
    directory = tmp_path / ".agents" / "skills" / "demo-skill" / "references"
    directory.mkdir(parents=True)
    path = directory / "depth.md"
    path.write_text(BODY, encoding="utf-8")
    _pad_to(path, MARKDOWN.MAX_SKILL_MANIFEST_CHARACTERS * 2)

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 0
    assert capsys.readouterr().out == ""


TRIGGERS_ADVICE = "The description already carries the triggers, so delete the section"
NEIGHBOUR_ADVICE = 'Name a neighbouring skill in the description or under "When not to activate"'
CHECKLIST_ADVICE = "Move it to references/checklist.md and link that file from the routing table"


@pytest.mark.parametrize(
    ("heading", "title", "advice"),
    [
        ("### When to activate", "When to activate", TRIGGERS_ADVICE),
        ("### When to Activate", "When to Activate", TRIGGERS_ADVICE),
        ("### __When to activate__", "When to activate", TRIGGERS_ADVICE),
        ("### Related skills", "Related skills", NEIGHBOUR_ADVICE),
        ("### Related Skills", "Related Skills", NEIGHBOUR_ADVICE),
        ("### *Related skills*", "Related skills", NEIGHBOUR_ADVICE),
        ("### Checklist", "Checklist", CHECKLIST_ADVICE),
        ("#### Checklist:", "Checklist", CHECKLIST_ADVICE),
        ("### Checklists", "Checklists", CHECKLIST_ADVICE),
        ("### **Checklist**", "Checklist", CHECKLIST_ADVICE),
        ("### **Checklists:**", "Checklists", CHECKLIST_ADVICE),
    ],
)
def test_a_section_that_left_the_manifest_is_reported(tmp_path, capsys, heading, title, advice):
    # Given a manifest still carrying a section the lean layout moved out, in any case, plural or emphasis
    path = _write_manifest(tmp_path, f"Purpose line.\n\n{heading}\n\n- An item.\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then the heading line is reported once, with where its content goes
    out = capsys.readouterr().out
    assert failures == 1
    assert "line=12::" in out
    assert f'section "{title}" is not allowed in a skill manifest. {advice}' in out


@pytest.mark.parametrize("heading", ["### Checklist of the release", "### Related work", "### When to activate the alarm"])
def test_a_heading_that_only_starts_like_a_section_that_left_passes(tmp_path, capsys, heading):
    # Given a manifest heading that holds more than one of the three names
    path = _write_manifest(tmp_path, f"Purpose line.\n\n{heading}\n\n- An item.\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 0, capsys.readouterr().out


def test_a_section_that_left_the_manifest_may_stay_in_a_reference(tmp_path, capsys):
    # Given a reference file with the same headings, linked from its manifest
    _write_manifest(tmp_path, "Open [topic](references/topic.md) for the depth.\n")
    path = _write_reference(tmp_path, "topic.md", "# Topic\n\n### Related skills\n\n- `bash` owns scripts.\n\n### Checklist\n\n- [ ] Done.\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 0, capsys.readouterr().out


def test_a_forbidden_heading_inside_a_code_fence_is_a_specimen(tmp_path, capsys):
    # Given a manifest showing the heading inside a fenced example
    path = _write_manifest(tmp_path, "Purpose line.\n\n```markdown\n### Related skills\n```\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 0, capsys.readouterr().out


WHEN_NOT = "### When not to activate\n\n"

NOT_A_ONE_LINE_ITEM = 'line under "When not to activate" is not a one-line list item. Write each item on one line and keep nothing else in the section'


def test_three_one_line_items_each_naming_a_skill_pass(tmp_path, capsys):
    # Given the longest "When not to activate" section the lean layout allows, a numbered item included
    body = WHEN_NOT + "- Shell scripts, use `bash`.\n- Tests, use `tdd-workflow`.\n1. A full audit, use the `security-auditor` agent.\n\n---\n\n### Rules\n\n1. A rule.\n"
    path = _write_manifest(tmp_path, body)

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 0, capsys.readouterr().out


def test_a_fourth_when_not_to_activate_item_is_reported(tmp_path, capsys):
    # Given one item more than the limit
    items = "".join(f"- Job {number}, use `skill-{number}`.\n" for number in range(MARKDOWN.MAX_WHEN_NOT_TO_ACTIVATE_ITEMS + 1))
    path = _write_manifest(tmp_path, WHEN_NOT + items)

    # When
    failures = MARKDOWN.check_file(path)

    # Then the heading line is reported once, naming the count and the limit
    out = capsys.readouterr().out
    assert failures == 1
    assert "line=10::" in out
    assert '"When not to activate" holds 4 items, over the limit of 3. Keep the nearest neighbouring jobs only' in out


def test_a_when_not_to_activate_heading_in_emphasis_marks_is_still_held_to_the_limit(tmp_path, capsys):
    # Given the section under a heading wrapped in emphasis marks, one item over the limit
    items = "".join(f"- Job {number}, use `skill-{number}`.\n" for number in range(MARKDOWN.MAX_WHEN_NOT_TO_ACTIVATE_ITEMS + 1))
    path = _write_manifest(tmp_path, "### **When Not To Activate:**\n\n" + items)

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    out = capsys.readouterr().out
    assert failures == 1
    assert '"When not to activate" holds 4 items, over the limit of 3' in out


def test_a_when_not_to_activate_item_wrapped_onto_a_second_line_is_reported(tmp_path, capsys):
    # Given an item that continues on an indented second line
    path = _write_manifest(tmp_path, WHEN_NOT + "- Shell scripts, use `bash`,\n  and everything around them.\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then the continuation line is reported
    out = capsys.readouterr().out
    assert failures == 1
    assert "line=13::" in out
    assert NOT_A_ONE_LINE_ITEM in out


def test_a_prose_line_under_when_not_to_activate_is_reported(tmp_path, capsys):
    # Given a sentence above the items
    path = _write_manifest(tmp_path, WHEN_NOT + "Hand these jobs over.\n\n- Shell scripts, use `bash`.\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 1
    assert NOT_A_ONE_LINE_ITEM in capsys.readouterr().out


@pytest.mark.parametrize("fence", ["```", "~~~", "```text"])
def test_a_fenced_block_under_when_not_to_activate_is_reported_once(tmp_path, capsys, fence):
    # Given a fenced block under the items, holding lines that look like items and like a heading
    block = f"{fence}\n- Job 1, use `skill-1`.\n- Job 2, use `skill-2`.\n\n### Rules\n{fence[:3]}\n"
    path = _write_manifest(tmp_path, WHEN_NOT + "- Shell scripts, use `bash`.\n\n" + block + "\n- Tests, use `tdd-workflow`.\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then the line that opens the block is reported, and nothing inside it counts as an item or a heading
    out = capsys.readouterr().out
    assert failures == 1
    assert "line=14::" in out
    assert NOT_A_ONE_LINE_ITEM in out


def test_a_deeper_heading_under_when_not_to_activate_is_reported_and_does_not_end_the_section(tmp_path, capsys):
    # Given a deeper heading under the section with a line of prose below it
    path = _write_manifest(tmp_path, WHEN_NOT + "- Shell scripts, use `bash`.\n\n#### More\n\nHand these jobs over.\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then the heading and the prose are both content the section may not hold
    out = capsys.readouterr().out
    assert failures == 2
    assert "line=14::" in out
    assert "line=16::" in out
    assert out.count(NOT_A_ONE_LINE_ITEM) == 2


def test_the_next_section_of_the_same_level_ends_when_not_to_activate(tmp_path, capsys):
    # Given prose and a fenced block under the section that follows
    body = WHEN_NOT + "- Shell scripts, use `bash`.\n\n### Rules\n\nProse of the next section.\n\n```bash\nls\n```\n"
    path = _write_manifest(tmp_path, body)

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 0, capsys.readouterr().out


def test_a_when_not_to_activate_item_naming_no_skill_or_agent_is_reported(tmp_path, capsys):
    # Given an item that names no owner in backticks
    path = _write_manifest(tmp_path, WHEN_NOT + "- Shell scripts, use `bash`.\n- The answer is already in the repository.\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then that item is reported
    out = capsys.readouterr().out
    assert failures == 1
    assert "line=13::" in out
    assert '"When not to activate" item names no skill or agent. Name the skill or the agent that owns the job in backticks, as in use `bash`' in out


def test_a_reference_not_linked_from_its_manifest_is_reported(tmp_path, capsys):
    # Given a manifest linking one reference and a second reference it never names
    _write_manifest(tmp_path, "Open [topic](references/topic.md) for the depth.\n")
    path = _write_reference(tmp_path, "orphan.md", "# Orphan\n\nPlain reference prose.\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    out = capsys.readouterr().out
    assert failures == 1
    assert "references/orphan.md is not linked from SKILL.md. Add it to the routing table with a cue saying when to open it, or delete the file" in out


@pytest.mark.parametrize(
    "link",
    ["[topic](references/topic.md)", "[part](references/topic.md#part)", "| Cue | [topic](./references/topic.md) |"],
    ids=["plain", "with-anchor", "table-row-with-dot-prefix"],
)
def test_a_reference_linked_from_its_manifest_passes(tmp_path, capsys, link):
    # Given a manifest that links the reference in one of the forms a routing table uses
    _write_manifest(tmp_path, link + "\n")
    path = _write_reference(tmp_path, "topic.md", "# Topic\n\n### Part\n\nPlain reference prose.\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 0, capsys.readouterr().out


@pytest.mark.parametrize(
    "body",
    ["Named as `[topic](references/topic.md)` only.\n", "```markdown\n[topic](references/topic.md)\n```\n", "Named as references/topic.md only.\n"],
    ids=["inline-code", "code-fence", "bare-path"],
)
def test_a_reference_named_but_not_linked_is_reported(tmp_path, capsys, body):
    # Given a manifest that shows the path without linking it
    _write_manifest(tmp_path, body)
    path = _write_reference(tmp_path, "topic.md", "# Topic\n\nPlain reference prose.\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 1
    assert "is not linked from SKILL.md" in capsys.readouterr().out


def test_a_reference_linked_only_from_another_reference_is_reported(tmp_path, capsys):
    # Given a chain: the manifest links one reference, and only that reference links the second
    _write_manifest(tmp_path, "Open [topic](references/topic.md) for the depth.\n")
    _write_reference(tmp_path, "topic.md", "# Topic\n\nSee [deeper](deeper.md).\n")
    path = _write_reference(tmp_path, "deeper.md", "# Deeper\n\nPlain reference prose.\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then the second file is one hop too far from the manifest
    assert failures == 1
    assert "is not linked from SKILL.md" in capsys.readouterr().out


def test_a_reference_in_a_subfolder_of_references_is_reported(tmp_path, capsys):
    # Given a reference one folder deeper than references/, linked from the manifest
    _write_manifest(tmp_path, "Open [topic](references/deep/topic.md) for the depth.\n")
    path = _write_reference(tmp_path, "deep/topic.md", "# Topic\n\nPlain reference prose.\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    out = capsys.readouterr().out
    assert failures == 1
    assert "references/deep/topic.md sits deeper than one level under references/. Move it directly into that folder" in out


@pytest.mark.parametrize("manifest", [None, b"\xff\xfe\x00"], ids=["missing", "not-utf-8"])
def test_a_reference_whose_manifest_cannot_be_read_is_not_reported_as_unlinked(tmp_path, capsys, manifest):
    # Given a reference in a folder whose SKILL.md is missing or cannot be decoded
    path = _write_reference(tmp_path, "topic.md", "# Topic\n\nPlain reference prose.\n")
    if manifest is not None:
        (path.parent.parent / "SKILL.md").write_bytes(manifest)

    # When
    failures = MARKDOWN.check_file(path)

    # Then the folder is no skill the link rule can speak for
    assert failures == 0
    assert capsys.readouterr().out == ""


def test_a_reference_in_a_subfolder_is_reported_even_when_its_manifest_is_missing(tmp_path, capsys):
    # Given a reference one folder too deep in a folder with no SKILL.md
    path = _write_reference(tmp_path, "deep/topic.md", "# Topic\n\nPlain reference prose.\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then the place is reported and the link is not
    out = capsys.readouterr().out
    assert failures == 1
    assert "sits deeper than one level under references/" in out
    assert "is not linked from" not in out


def test_a_markdown_file_directly_in_the_skills_folder_is_held_to_no_layout_rule(tmp_path, capsys):
    # Given a file beside the skill folders, in no skill of its own, longer than a reference may be without Contents
    path = tmp_path / ".agents" / "skills" / "README.md"
    path.parent.mkdir(parents=True)
    path.write_text("# Skills\n\n### Checklist\n\n" + "Plain prose.\n" * 120, encoding="utf-8")

    # When
    failures = MARKDOWN.check_file(path)

    # Then the check returns instead of raising
    assert failures == 0
    assert capsys.readouterr().out == ""


def test_a_manifest_link_to_a_missing_file_is_reported(tmp_path, capsys):
    # Given a manifest linking a reference that was never written
    path = _write_manifest(tmp_path, "Open [topic](references/missing.md#part) for the depth.\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then the line is reported with the target as written
    out = capsys.readouterr().out
    assert failures == 1
    assert "line=10::" in out
    assert "links to references/missing.md#part, which does not exist. Fix the path or remove the link" in out


def test_a_reference_link_to_a_missing_sibling_is_reported(tmp_path, capsys):
    # Given a linked reference pointing at a sibling that does not exist
    _write_manifest(tmp_path, "Open [topic](references/topic.md) for the depth.\n")
    path = _write_reference(tmp_path, "topic.md", "# Topic\n\nSee [gone](gone.md) and [the manifest](../SKILL.md).\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then only the missing target is reported, resolved from the reference's own folder
    out = capsys.readouterr().out
    assert failures == 1
    assert "links to gone.md, which does not exist" in out


def test_a_reference_style_link_to_a_missing_file_is_reported(tmp_path, capsys):
    # Given a linked reference whose link definition names a sibling that does not exist
    _write_manifest(tmp_path, "Open [topic](references/topic.md) for the depth.\n")
    path = _write_reference(tmp_path, "topic.md", "# Topic\n\nSee [the sibling][gone].\n\n[gone]: gone.md\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    out = capsys.readouterr().out
    assert failures == 1
    assert "line=5::" in out
    assert "links to gone.md, which does not exist" in out


def test_a_percent_encoded_manifest_link_to_a_file_that_exists_passes(tmp_path, capsys):
    # Given a manifest linking a reference whose name holds a space, written as %20
    path = _write_manifest(tmp_path, "Open [topic](references/my%20file.md#part) for the depth.\n")
    _write_reference(tmp_path, "my file.md", "# Topic\n\n### Part\n\nPlain reference prose.\n")

    # When the manifest is checked
    failures = MARKDOWN.check_file(path)

    # Then the decoded path is found
    assert failures == 0, capsys.readouterr().out


def test_a_reference_linked_with_percent_encoding_counts_as_linked(tmp_path, capsys):
    # Given a reference with a space in its name, linked from its manifest as %20
    _write_manifest(tmp_path, "Open [topic](references/my%20file.md) for the depth.\n")
    path = _write_reference(tmp_path, "my file.md", "# Topic\n\nSee [the manifest](../SKILL.md).\n")

    # When the reference is checked
    failures = MARKDOWN.check_file(path)

    # Then it is neither unlinked nor broken
    assert failures == 0, capsys.readouterr().out


def test_a_percent_encoded_link_to_a_missing_file_is_still_reported(tmp_path, capsys):
    # Given a manifest linking a %20 name that no file carries
    path = _write_manifest(tmp_path, "Open [topic](references/no%20such.md) for the depth.\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then the link is reported as written
    out = capsys.readouterr().out
    assert failures == 1
    assert "links to references/no%20such.md, which does not exist" in out


@pytest.mark.parametrize(
    "definition",
    ["[^1]: Measured on one host.", "[^note]: ../other-skill/SKILL.md says the same.", "   [^1]: gone.md"],
    ids=["prose", "path-leaving-the-folder", "indented-file-name"],
)
def test_a_footnote_is_not_a_link(tmp_path, capsys, definition):
    # Given a linked reference with a footnote, whose first word is no link target
    _write_manifest(tmp_path, "Open [topic](references/topic.md) for the depth.\n")
    path = _write_reference(tmp_path, "topic.md", f"# Topic\n\nA claim.[^1]\n\n{definition}\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then neither link rule speaks
    assert failures == 0
    assert capsys.readouterr().out == ""


def test_a_link_leaving_the_skill_folder_is_reported_once(tmp_path, capsys):
    # Given a manifest linking a sibling skill that does not exist on disk
    path = _write_manifest(tmp_path, "See [sibling](../other-skill/SKILL.md).\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then the folder rule speaks and the missing-file rule stays silent
    out = capsys.readouterr().out
    assert failures == 1
    assert "links outside its own skill folder" in out
    assert "does not exist" not in out


def _long_reference(opening, lines=101, sections=("### First section",)):
    filler = [f"Line {number}." for number in range(lines)]
    text = opening + "\n\n" + "\n\n".join(sections) + "\n\n"
    padding = lines - len(text.splitlines())

    return text + "\n".join(filler[:padding]) + "\n"


CONTENTS_OPENINGS = {
    "contents-line": "# Topic\n\nContents:\n\n- [First section](#first-section)",
    "contents-heading": "# Topic\n\nWhat the file holds.\n\n---\n\n### Contents\n\n- [First section](#first-section)",
    "numbered-list": "# Topic\n\nContents:\n\n1. [First section](#first-section)",
    "no-title": "### Contents\n\n- [First section](#first-section)",
    "nested-items": "# Topic\n\nContents:\n\n- [First section](#first-section)\n  - [A part of it](#a-part-of-it)\n\n#### A part of it",
    "code-in-the-link-text": "# Topic\n\nContents:\n\n- [`first` section](#first-section)",
}


@pytest.mark.parametrize("opening", list(CONTENTS_OPENINGS.values()), ids=list(CONTENTS_OPENINGS))
def test_a_long_reference_opening_with_a_contents_list_passes(tmp_path, capsys, opening):
    # Given a linked reference over the line limit that opens with a Contents list
    _write_manifest(tmp_path, "Open [topic](references/topic.md) for the depth.\n")
    path = _write_reference(tmp_path, "topic.md", _long_reference(opening))

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert len(path.read_text(encoding="utf-8").splitlines()) == 101
    assert failures == 0, capsys.readouterr().out


MISSING_CONTENTS_OPENINGS = {
    "no-contents": "# Topic\n\nWhat the file holds.",
    "contents-with-no-list": "# Topic\n\nContents:\n\nThe sections follow.",
    "contents-after-the-first-section": "# Topic\n\n### Early section\n\nProse.\n\n### Contents\n\n- First section",
}


@pytest.mark.parametrize("opening", list(MISSING_CONTENTS_OPENINGS.values()), ids=list(MISSING_CONTENTS_OPENINGS))
def test_a_long_reference_without_an_opening_contents_list_is_reported(tmp_path, capsys, opening):
    # Given a linked reference over the line limit with no Contents list before its first section
    _write_manifest(tmp_path, "Open [topic](references/topic.md) for the depth.\n")
    path = _write_reference(tmp_path, "topic.md", _long_reference(opening))

    # When
    failures = MARKDOWN.check_file(path)

    # Then the message names the length and the limit
    out = capsys.readouterr().out
    assert failures == 1
    assert "line=1::" in out
    assert 'reference is 101 lines, over 100, and has no Contents list before its first section. Open it with "Contents:" and a list that links its sections' in out


UNLINKED_CONTENTS_OPENINGS = {
    "no-item-linked": ("# Topic\n\nContents:\n\n- First section\n- Second section", 5, "2 of 2"),
    "one-item-not-linked": ("# Topic\n\nContents:\n\n- [First section](#first-section)\n- Second section\n- [Third](#third)\n\n### Third", 6, "1 of 3"),
    "link-to-another-file": ("# Topic\n\nContents:\n\n- [First section](#first-section)\n- [Topic](topic.md)", 6, "1 of 2"),
    "link-shown-as-code": ("# Topic\n\nContents:\n\n- `[First section](#first-section)`", 5, "1 of 1"),
    "nested-item-not-linked": ("# Topic\n\nContents:\n\n- [First section](#first-section)\n  - A part of it", 6, "1 of 2"),
}


@pytest.mark.parametrize(("opening", "line", "share"), list(UNLINKED_CONTENTS_OPENINGS.values()), ids=list(UNLINKED_CONTENTS_OPENINGS))
def test_a_contents_list_item_that_links_no_section_is_reported(tmp_path, capsys, opening, line, share):
    # Given a linked reference over the line limit whose Contents list holds an item with no link to a section
    _write_manifest(tmp_path, "Open [topic](references/topic.md) for the depth.\n")
    path = _write_reference(tmp_path, "topic.md", _long_reference(opening))

    # When
    failures = MARKDOWN.check_file(path)

    # Then the first such item is reported once, with how many items lack the link
    out = capsys.readouterr().out
    assert failures == 1
    assert f"line={line}::" in out
    assert f"Contents list items without a link to a section: {share}, the first on this line. Write each item as a link to its section, as in [Setup](#setup)" in out


MATCHING_CONTENTS_ANCHORS = {
    "punctuation-removed": (("### Step 1: set up the venv",), "#step-1-set-up-the-venv"),
    "inline-code-kept-as-text": (("### Install `uv` and pip",), "#install-uv-and-pip"),
    "underscore-inside-a-word-kept": (("### The snake_case rule",), "#the-snake_case-rule"),
    "emphasis-removed": (("### **Bold** and _italic_ words",), "#bold-and-italic-words"),
    "link-text-kept": (("### Read [the docs](https://example.com) first",), "#read-the-docs-first"),
    "symbol-between-spaces": (("### Pins & digests",), "#pins--digests"),
    "dots-and-brackets-removed": (("### Version 1.2 (old)",), "#version-12-old"),
    "closing-hashes-dropped": (("### Closed heading ###",), "#closed-heading"),
    "repeated-heading-numbered": (("### Setup", "### Setup"), "#setup-1"),
    "backslash-escape-kept": (("### Exclude \\_id",), "#exclude-_id"),
    "letters-beyond-ascii": (("### Größe der Straße",), "#größe-der-straße"),
    "percent-encoded-anchor": (("### Größe der Straße",), "#gr%C3%B6%C3%9Fe-der-stra%C3%9Fe"),
    "emoji-variation-selector-kept": (("### \u26a0\ufe0f Policy",), "#%EF%B8%8F-policy"),
    "the-title-itself": (("### Body",), "#topic"),
}


@pytest.mark.parametrize(("sections", "anchor"), list(MATCHING_CONTENTS_ANCHORS.values()), ids=list(MATCHING_CONTENTS_ANCHORS))
def test_a_contents_link_to_the_anchor_github_gives_a_heading_passes(tmp_path, capsys, sections, anchor):
    # Given a long reference whose Contents list links the anchor GitHub makes from one of its headings
    _write_manifest(tmp_path, "Open [topic](references/topic.md) for the depth.\n")
    opening = f"# Topic\n\nContents:\n\n- [The section]({anchor})"
    path = _write_reference(tmp_path, "topic.md", _long_reference(opening, sections=sections))

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 0, capsys.readouterr().out


BROKEN_CONTENTS_ANCHORS = {
    "misspelt": (("### First section",), "#first-sectoin"),
    "heading-text-cut-short": (("### Step 1: set up the venv",), "#step-1-set-up"),
    "punctuation-left-in": (("### Version 1.2",), "#version-1.2"),
    "first-of-a-repeated-heading-numbered": (("### Setup",), "#setup-1"),
    "heading-inside-a-fence": (("```text\n### Hidden\n```",), "#hidden"),
    "emoji-variation-selector-dropped": (("### \u26a0\ufe0f Policy",), "#-policy"),
}


@pytest.mark.parametrize(("sections", "anchor"), list(BROKEN_CONTENTS_ANCHORS.values()), ids=list(BROKEN_CONTENTS_ANCHORS))
def test_a_contents_link_that_matches_no_heading_is_reported(tmp_path, capsys, sections, anchor):
    # Given a long reference whose Contents list links an anchor no heading of the file produces
    _write_manifest(tmp_path, "Open [topic](references/topic.md) for the depth.\n")
    opening = f"# Topic\n\nContents:\n\n- [The section]({anchor})"
    path = _write_reference(tmp_path, "topic.md", _long_reference(opening, sections=sections))

    # When
    failures = MARKDOWN.check_file(path)

    # Then the item is reported on its own line, naming the anchor
    out = capsys.readouterr().out
    assert failures == 1, out
    assert "line=5::" in out
    assert f"Contents link {anchor} matches no heading in this file. Use the anchor GitHub makes from the heading, as in [Setup steps](#setup-steps)" in out


def test_every_contents_link_that_matches_no_heading_is_reported(tmp_path, capsys):
    # Given a long reference whose Contents list holds two items linking no heading of the file
    _write_manifest(tmp_path, "Open [topic](references/topic.md) for the depth.\n")
    opening = "# Topic\n\nContents:\n\n- [Gone](#gone)\n- [First section](#first-section)\n  - [Also gone](#also-gone)"
    path = _write_reference(tmp_path, "topic.md", _long_reference(opening))

    # When
    failures = MARKDOWN.check_file(path)

    # Then each broken link is reported on its own line
    out = capsys.readouterr().out
    assert failures == 2, out
    assert "line=5::Contents link #gone matches no heading" in out
    assert "line=7::Contents link #also-gone matches no heading" in out


def test_a_short_reference_may_link_a_missing_heading_from_its_contents_list(tmp_path, capsys):
    # Given a linked reference of exactly the line limit whose Contents list links an anchor no heading produces
    _write_manifest(tmp_path, "Open [topic](references/topic.md) for the depth.\n")
    path = _write_reference(tmp_path, "topic.md", _long_reference("# Topic\n\nContents:\n\n- [Gone](#gone)", lines=100))

    # When
    failures = MARKDOWN.check_file(path)

    # Then the Contents rule starts past the limit
    assert failures == 0, capsys.readouterr().out


def test_a_short_reference_may_keep_a_contents_list_without_links(tmp_path, capsys):
    # Given a linked reference of exactly the line limit whose Contents list links nothing
    _write_manifest(tmp_path, "Open [topic](references/topic.md) for the depth.\n")
    path = _write_reference(tmp_path, "topic.md", _long_reference("# Topic\n\nContents:\n\n- First section", lines=100))

    # When
    failures = MARKDOWN.check_file(path)

    # Then the Contents rule starts past the limit
    assert failures == 0, capsys.readouterr().out


def test_a_reference_at_the_line_limit_needs_no_contents_list(tmp_path, capsys):
    # Given a linked reference of exactly the line limit with no Contents list
    _write_manifest(tmp_path, "Open [topic](references/topic.md) for the depth.\n")
    path = _write_reference(tmp_path, "topic.md", _long_reference("# Topic\n\nWhat the file holds.", lines=100))

    # When
    failures = MARKDOWN.check_file(path)

    # Then the limit is inclusive
    assert len(path.read_text(encoding="utf-8").splitlines()) == 100
    assert failures == 0, capsys.readouterr().out


def test_the_layout_rules_leave_a_document_outside_the_skills_tree_alone(tmp_path, capsys):
    # Given a shipped document with a forbidden heading, a dead link and more than the line limit
    body = "# Guide\n\n### Related skills\n\nSee [gone](gone.md).\n" + "Line.\n" * 120
    path = tmp_path / "docs" / "GUIDE.md"
    path.parent.mkdir(parents=True)
    path.write_text(body, encoding="utf-8")

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 0, capsys.readouterr().out


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
    assert "key 'tools' is not in the Agent Skills specification. Allowed keys are name, description, license, compatibility, metadata" in out


def test_every_key_outside_the_specification_is_reported(tmp_path, capsys):
    # Given two keys outside the specification at once
    front_matter = """---
name: demo-skill
description: Demo skill for the lint tests.
tools: Read
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
    assert "key 'tools'" in out


def test_model_key_in_skill_front_matter_is_reported_once(tmp_path, capsys):
    # Given a manifest that pins a model in its front matter
    front_matter = """---
name: demo-skill
description: Demo skill for the lint tests.
model: sonnet
---
"""
    path = _write_skill(tmp_path, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then one violation on the model line says to remove the key and why
    out = capsys.readouterr().out
    assert failures == 1
    assert "line=4::" in out
    assert "key 'model' is not allowed. Remove it, because skills never pin a model" in out
    assert "and run on the user's default model" in out


def test_model_key_is_reported_even_when_the_allowed_keys_widen(tmp_path, capsys, monkeypatch):
    # Given an allowed-key list that someday admits model, and a manifest using it
    monkeypatch.setattr(MARKDOWN, "SKILL_ALLOWED_KEYS", (*MARKDOWN.SKILL_ALLOWED_KEYS, "model"))
    front_matter = """---
name: demo-skill
description: Demo skill for the lint tests.
model: sonnet
---
"""
    path = _write_skill(tmp_path, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then the model rule still holds on its own
    assert failures == 1
    assert "key 'model' is not allowed. Remove it" in capsys.readouterr().out


def test_model_key_in_a_skill_body_is_not_front_matter(tmp_path, capsys):
    # Given a clean manifest whose body holds a model assignment and a model line
    path = _write_skill(tmp_path, CLEAN_SKILL_FRONT_MATTER)
    path.write_text(path.read_text(encoding="utf-8") + "\nmodel = MyModel()\n\nmodel: sonnet\n", encoding="utf-8")

    # When
    failures = MARKDOWN.check_file(path)

    # Then the body is not read as front matter
    assert failures == 0
    assert capsys.readouterr().out == ""


def test_model_key_in_a_skill_reference_is_not_front_matter(tmp_path, capsys):
    # Given a reference file holding a fenced model assignment and a prose model line
    path = _write_skill_reference(tmp_path, "```python\nmodel = MyModel()\n```\n\nmodel: sonnet")

    # When
    failures = MARKDOWN.check_file(path)

    # Then a reference file carries no front matter contract
    assert failures == 0
    assert capsys.readouterr().out == ""


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
        _with_version(front_matter, 'metadata:\n  version: "1.0.0"\n') + "\n# Demo\n\nProse with an em-dash \u2014 in it.\n",
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


def test_every_subagent_source_and_every_skill_file_passes_every_rule(capsys):
    # Given every file of every skill and every subagent source in the actual repository
    targets = sorted(SKILLS_ROOT.glob("*/**/*.md"))
    targets.extend(sorted((REPO_ROOT / "subagents").glob("*.md")))

    # When
    failures = sum(MARKDOWN.check_file(path) for path in targets)

    # Then every file an agent loads is valid by the time the suite is green
    assert failures == 0, capsys.readouterr().out


def _write_document(tmp_path, body):
    path = tmp_path / "docs" / "GUIDE.md"
    path.parent.mkdir(parents=True)
    path.write_text(body, encoding="utf-8")

    return path


def test_a_long_prose_line_is_not_reported(tmp_path, capsys):
    # Given a paragraph written as one physical line, because prose is never hard-wrapped
    path = _write_document(tmp_path, "### Heading\n\n" + " ".join(["word"] * 60) + "\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 0
    assert capsys.readouterr().out == ""


def test_a_level_two_heading_is_still_reported(tmp_path, capsys):
    # Given a document using a level-2 section heading
    path = _write_document(tmp_path, "# Title\n\n## Section\n\nProse.\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 1
    assert "level-2 heading" in capsys.readouterr().out


@pytest.mark.parametrize(
    "link",
    [
        "[sibling](../other-skill/SKILL.md)",
        "[sibling reference](../other-skill/references/topic.md)",
        "[repository doc](../../../docs/GUIDE.md)",
        "[rooted path](/docs/GUIDE.md)",
    ],
    ids=["sibling-manifest", "sibling-reference", "outside-the-skills-tree", "rooted-path"],
)
def test_a_skill_link_leaving_its_own_folder_is_reported(tmp_path, capsys, link):
    # Given a skill manifest linking to a path a consumer may not have
    path = _write_skill(tmp_path, CLEAN_SKILL_FRONT_MATTER)
    path.write_text(CLEAN_SKILL_FRONT_MATTER + "\n# Demo\n\nSee " + link + ".\n", encoding="utf-8")

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 1
    assert "links outside its own skill folder" in capsys.readouterr().out


def test_a_rooted_link_in_a_skill_given_as_a_relative_path_is_reported(tmp_path, capsys, monkeypatch):
    # Given a skill passed on the command line as a relative path, holding a link rooted at the drive
    path = _write_skill(tmp_path, CLEAN_SKILL_FRONT_MATTER)
    path.write_text(CLEAN_SKILL_FRONT_MATTER + "\n# Demo\n\nSee [rooted](/docs/GUIDE.md).\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    # When
    failures = MARKDOWN.check_file(path.relative_to(tmp_path))

    # Then the mixed absolute and relative comparison is reported rather than raised
    assert failures == 1
    assert "links outside its own skill folder" in capsys.readouterr().out


def test_a_skill_reference_file_linking_to_a_sibling_skill_is_reported(tmp_path, capsys):
    # Given a reference file one level down linking two levels up into another skill
    _write_manifest(tmp_path, "Open [topic](references/topic.md) for the depth.\n")
    path = _write_reference(tmp_path, "topic.md", "### Topic\n\nPer [node](../../node-backend-patterns/SKILL.md).\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 1
    assert "links outside its own skill folder" in capsys.readouterr().out


@pytest.mark.parametrize(
    "link",
    [
        "[reference](references/topic.md)",
        "[anchor](#demo)",
        "[vendor](https://example.com/docs)",
        "`[not a link](../other-skill/SKILL.md)`",
    ],
    ids=["own-reference", "anchor", "absolute-url", "inside-inline-code"],
)
def test_a_skill_link_staying_inside_its_folder_passes(tmp_path, capsys, link):
    # Given a skill manifest linking only within itself or to the web, and the reference it names
    path = _write_manifest(tmp_path, "Open [topic](references/topic.md) for the depth. See " + link + ".\n")
    _write_reference(tmp_path, "topic.md", "### Topic\n\nPlain reference prose.\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 0
    assert capsys.readouterr().out == ""


def test_a_document_outside_the_skills_tree_may_link_anywhere(tmp_path, capsys):
    # Given a shipped document linking into the skills tree
    path = _write_document(tmp_path, "### Guide\n\nSee [bash](../.agents/skills/bash/SKILL.md).\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 0
    assert capsys.readouterr().out == ""


def test_no_real_skill_links_outside_its_own_folder(capsys):
    # Given every markdown file of every skill this repository ships
    targets = sorted(SKILLS_ROOT.glob("**/*.md"))

    # When
    failures = sum(MARKDOWN.check_lines(path.read_text(encoding="utf-8").splitlines(), path) for path in targets)

    # Then a consumer that removed any one skill still has no dead link in the others
    assert failures == 0, capsys.readouterr().out


def test_the_ci_command_runs_the_shipped_rules(tmp_path):
    # Given a file breaking a shipped rule
    path = tmp_path / "GUIDE.md"
    path.write_text("### Heading\n\nProse with an em-dash \u2014 in it.\n", encoding="utf-8")

    # When the command CI and CONTRIBUTING.md name is run on it
    result = run_bounded(
        [sys.executable, str(CI_COMMAND), str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    # Then it delegates to the one copy of the rules
    assert result.returncode == 1
    assert "em-dash or en-dash found" in result.stdout


@pytest.mark.parametrize("name", ["AGENTS.md.example", "MACHINE.md.example", "bootstrap-machine.prompt.md"])
def test_a_violation_in_a_global_template_is_caught_by_default(tmp_path, capsys, name):
    # Given a global install document carrying an em dash, under a throwaway repo root
    path = tmp_path / "global" / name
    path.parent.mkdir(parents=True)
    path.write_text("### Heading\n\nProse \u2014 with a dash.\n", encoding="utf-8")

    # When the default target set is linted
    targets = MARKDOWN.default_targets(tmp_path)
    failures = sum(MARKDOWN.check_file(target) for target in targets if target.exists())

    # Then the file is in scope and its violation is reported
    assert path in targets
    assert failures == 1
    assert name in capsys.readouterr().out


DATED_BASELINE_HITS = [
    "Current as of 2026-10-30.",
    "Supported as of March 2026.",
    "Behaves this way as of Oct. 2025, per the changelog.",
    "As of 2026, the default changed.",
    "Shipped as of 14 March 2026.",
    "Measured as of 2026-03-14.",
    "Verified October 2026 against the vendor page.",
    "VERIFIED on 2026-10-23 against the running box.",
    "Last checked in Sep 2025.",
    "The current stable release is 3.14.",
    "The current LTS is Java 25.",
    "The current release of Spring Boot is 4.0.",
    "Python 3.13 or newer, with 3.14 the current release.",
    "JDK 25 is the current LTS.",
    "Go 1.25, the current stable toolchain.",
    "Last verified: October 2026.",
    "Verified: 2026-10-23 on the build host.",
    "The default changed as of Q3 2026.",
    "Supported as of mid-2026.",
    "This is the recommended flag as of today.",
    "The latest stable release is 3.14.",
    "The current Python release is 3.14.",
]

DATED_BASELINE_NON_HITS = [
    "Written for Spring Boot 4 and Java 25.",
    "The current release notes are attached to the tag.",
    "The current version is read from package.json.",
    "The current state is 3 rows.",
    "Correct as of now, and as of this commit.",
    "Zoneless is the default as of v21.",
    "Bash 5 (verified locally).",
    "Tested in staging before release.",
    "Released in 2024 and still supported.",
    "Timeout as of 200 ms is too short.",
    "v2 is the current version of the API.",
    "The latest release notes list every change.",
    "Checked: the flag is on.",
]


def _write_skill_reference(tmp_path, body):
    directory = tmp_path / ".agents" / "skills" / "demo-skill" / "references"
    directory.mkdir(parents=True)
    path = directory / "guide.md"
    path.write_text(f"# Guide\n\n{body}\n", encoding="utf-8")

    return path


@pytest.mark.parametrize("sentence", DATED_BASELINE_HITS)
def test_a_dated_or_current_version_baseline_in_a_skill_is_reported(tmp_path, capsys, sentence):
    # Given a skill reference file stating a dated or "current" version baseline
    path = _write_skill_reference(tmp_path, sentence)

    # When
    failures = MARKDOWN.check_file(path)

    # Then the line is reported once, naming the phrase
    assert failures == 1
    assert "dated or \"current version\" baseline" in capsys.readouterr().out


@pytest.mark.parametrize("sentence", DATED_BASELINE_NON_HITS)
def test_ordinary_prose_about_versions_and_time_is_not_a_dated_baseline(tmp_path, capsys, sentence):
    # Given a skill reference file with prose that names a version or a time but claims no dated baseline
    path = _write_skill_reference(tmp_path, sentence)

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 0, capsys.readouterr().out


def test_a_dated_baseline_inside_code_is_a_specimen_not_a_claim(tmp_path, capsys):
    # Given SQL temporal syntax in a fence and a quoted phrase in an inline code span
    body = "Quote the banned phrase as `current as of 2026` when teaching the rule.\n\n```sql\nSELECT * FROM t FOR SYSTEM_TIME AS OF '2024-01-01';\n```"
    path = _write_skill_reference(tmp_path, body)

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 0, capsys.readouterr().out


def test_a_dated_baseline_in_a_subagent_description_is_reported(tmp_path, capsys):
    # Given a subagent source whose front matter description carries the date
    front_matter = '---\nname: demo-agent\ndescription: "Use when building Java, current as of 2026."\n---\n'
    path = _write_subagent(tmp_path, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then the description line is reported
    assert failures == 1
    assert "line=3" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("tree", "name"),
    [(".claude", "demo/demo.md"), (".agents", "demo.md"), (".codex", "demo.toml"), (".github", "demo.agent.md")],
)
def test_a_generated_agent_file_gets_the_dated_baseline_rule_and_no_other(tmp_path, capsys, tree, name):
    # Given a generated agent file carrying a dated baseline and an em dash
    path = tmp_path / tree / "agents" / name
    path.parent.mkdir(parents=True)
    path.write_text("## Heading\n\nWritten \u2014 verified October 2026.\n", encoding="utf-8")

    # When
    failures = MARKDOWN.check_file(path)

    # Then only the baseline is reported, since the other rules run on the canonical source
    output = capsys.readouterr().out
    assert failures == 1
    assert "baseline" in output
    assert "em-dash" not in output


def test_a_shipped_document_may_carry_a_dated_statement(tmp_path, capsys):
    # Given a human-facing document outside the agent-facing scope
    path = _write_document(tmp_path, "### Notes\n\nMeasured as of March 2026.\n")

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 0, capsys.readouterr().out


def test_the_generated_agent_trees_are_in_the_default_targets(tmp_path):
    # Given one file in each generated tree and one behind a symlinked tree
    for tree, name in [(".claude", "a.md"), (".agents", "a.md"), (".codex", "a.toml"), (".github", "a.agent.md")]:
        path = tmp_path / tree / "agents" / name
        path.parent.mkdir(parents=True)
        path.write_text("Body.\n", encoding="utf-8")

    # When
    targets = MARKDOWN.default_targets(tmp_path)

    # Then all four are linted and nothing is read twice through a symlink
    assert tmp_path / ".codex" / "agents" / "a.toml" in targets
    assert tmp_path / ".github" / "agents" / "a.agent.md" in targets
    assert len([t for t in targets if t.parent.name == "agents"]) == 4


def test_the_quality_tools_readme_is_linted_and_the_vendored_tools_are_not(tmp_path):
    # Given the agent-standards readme beside Robert C. Martin's three vendored tools, each with its own readme
    readme = tmp_path / ".metrics" / "tools" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text("### Heading\n\nProse.\n", encoding="utf-8")
    for tool in ("crapper", "dryer", "mutator"):
        vendored = tmp_path / ".metrics" / "tools" / tool / "README.md"
        vendored.parent.mkdir(parents=True)
        vendored.write_text("## His heading\n\nHis prose \u2014 in his style.\n", encoding="utf-8")

    # When
    targets = MARKDOWN.default_targets(tmp_path)

    # Then our readme is linted and nothing of his is
    assert readme in targets
    assert [t for t in targets if t.parent.parent.name == "tools" and t.parent.name in {"crapper", "dryer", "mutator"}] == []


def test_the_generated_targets_hold_every_agent_of_every_tree():
    targets = MARKDOWN.generated_agent_targets(REPO_ROOT)
    agents = {p.stem for p in (REPO_ROOT / "subagents").glob("*.md")}

    assert {p.parent.name for p in targets if p.parts[-4:-2] == (".claude", "agents")} == agents
    assert len(targets) == 4 * len(agents)


def test_no_subagent_source_or_generated_agent_states_a_dated_baseline(capsys):
    # Given every canonical subagent and every generated agent this repository ships
    targets = sorted((REPO_ROOT / "subagents").glob("*.md"))
    targets.extend(MARKDOWN.generated_agent_targets(REPO_ROOT))

    # When
    failures = sum(MARKDOWN.check_dated_baselines(path.read_text(encoding="utf-8").splitlines(), path) for path in targets)

    # Then
    assert failures == 0, capsys.readouterr().out


REAL_SHA = "0123456789abcdef0123456789abcdef01234567"
REAL_DIGEST = "sha256:" + "ab" * 32

HASH_PIN_HITS = [
    f"      - uses: actions/checkout@{REAL_SHA} # v5",
    f"  uses: codecov/codecov-action@{REAL_SHA}",
    f"- uses: 'docker/login-action@{REAL_SHA}'",
    f"    image: postgres:18-alpine@{REAL_DIGEST}",
    f"FROM node:26-alpine@{REAL_DIGEST} AS build",
    f"cosign verify myregistry/app@{REAL_DIGEST}",
]

HASH_PIN_NON_HITS = [
    "      - uses: actions/checkout@<commit-sha> # v5",
    "    image: postgres:18-alpine@sha256:<digest>",
    "FROM node:26-alpine AS build",
    f"Commit {REAL_SHA} fixed the race.",
    "      - uses: actions/checkout@v5",
    "The image digest is printed by `docker buildx imagetools inspect <image>:<tag>`.",
    f"      - uses: actions/checkout@{REAL_SHA}0 # not a 40-character SHA",
]


def _write_fenced_skill_reference(tmp_path, line):
    return _write_skill_reference(tmp_path, f"Example:\n\n```yaml\n{line}\n```")


@pytest.mark.parametrize("line", HASH_PIN_HITS)
def test_a_real_hash_pin_in_a_skill_is_reported_even_inside_a_fence(tmp_path, capsys, line):
    # Given a skill reference whose example shows a real commit SHA or digest
    path = _write_fenced_skill_reference(tmp_path, line)

    # When
    failures = MARKDOWN.check_file(path)

    # Then the pin is reported once, with the placeholder form to use instead
    assert failures == 1
    assert "real hash pin" in capsys.readouterr().out


@pytest.mark.parametrize("line", HASH_PIN_NON_HITS)
def test_a_placeholder_pin_or_a_prose_sha_is_not_a_hash_pin(tmp_path, capsys, line):
    # Given a skill reference with a placeholder pin or a commit named in prose
    path = _write_fenced_skill_reference(tmp_path, line)

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 0, capsys.readouterr().out


def test_a_real_hash_pin_outside_agent_files_is_not_reported(tmp_path, capsys):
    # Given a human-facing document under docs/, outside the skill and subagent scope
    path = tmp_path / "docs" / "CI.md"
    path.parent.mkdir(parents=True)
    path.write_text(f"# CI\n\n```yaml\n      - uses: actions/checkout@{REAL_SHA} # v5\n```\n", encoding="utf-8")

    # When
    failures = MARKDOWN.check_file(path)

    # Then the repository's own pinned workflows can be documented as they are
    assert failures == 0, capsys.readouterr().out


def test_a_real_digest_in_a_subagent_source_is_reported(tmp_path, capsys):
    # Given a clean subagent source whose body shows a real image digest
    path = _write_subagent(tmp_path, CLEAN_SUBAGENT_FRONT_MATTER)
    path.write_text(path.read_text(encoding="utf-8") + f"\nRun `app@{REAL_DIGEST}`.\n", encoding="utf-8")

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 1
    assert "real hash pin" in capsys.readouterr().out


SKILL_WITHOUT_VERSION = '---\nname: demo-skill\ndescription: Demo skill.\n'
AGENT_WITHOUT_VERSION = '---\nname: demo-agent\ndescription: Demo subagent.\n'


def _write_raw(tmp_path, relative, text):
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + BODY, encoding="utf-8")

    return path


@pytest.mark.parametrize(
    ("relative", "front_matter", "message"),
    [
        pytest.param(".agents/skills/demo-skill/SKILL.md", SKILL_WITHOUT_VERSION + "---\n", "metadata.version is missing", id="skill-missing"),
        pytest.param(".agents/skills/demo-skill/SKILL.md", SKILL_WITHOUT_VERSION + "metadata:\n  version: 1\n---\n", "metadata.version is 1", id="skill-integer"),
        pytest.param(".agents/skills/demo-skill/SKILL.md", SKILL_WITHOUT_VERSION + 'metadata:\n  version: "1.0"\n---\n', "metadata.version is '1.0'", id="skill-two-parts"),
        pytest.param(".agents/skills/demo-skill/SKILL.md", SKILL_WITHOUT_VERSION + "metadata: 1.0.0\n---\n", "metadata.version is missing", id="skill-metadata-not-a-mapping"),
        pytest.param("subagents/demo-agent.md", AGENT_WITHOUT_VERSION + "---\n", "version is missing", id="agent-missing"),
        pytest.param("subagents/demo-agent.md", AGENT_WITHOUT_VERSION + "version: 1.0.0-beta\n---\n", "version is '1.0.0-beta'", id="agent-pre-release"),
        pytest.param("subagents/demo-agent.md", AGENT_WITHOUT_VERSION + "version: 01.0.0\n---\n", "version is '01.0.0'", id="agent-leading-zero"),
        pytest.param("subagents/demo-agent.md", AGENT_WITHOUT_VERSION + 'version: "1.0.1\u0661"\n---\n', "not a MAJOR.MINOR.PATCH", id="agent-non-ascii-digit"),
    ],
)
def test_a_manifest_without_a_plain_semantic_version_is_reported(tmp_path, capsys, relative, front_matter, message):
    # Given a skill or a subagent whose version is missing or not MAJOR.MINOR.PATCH
    path = _write_raw(tmp_path, relative, front_matter)

    # When
    failures = MARKDOWN.check_file(path)

    # Then
    assert failures == 1
    assert message in capsys.readouterr().out


@pytest.mark.parametrize(
    ("relative", "front_matter"),
    [
        pytest.param(".agents/skills/demo-skill/SKILL.md", SKILL_WITHOUT_VERSION + 'metadata:\n  version: "10.2.33"\n---\n', id="skill"),
        pytest.param("subagents/demo-agent.md", AGENT_WITHOUT_VERSION + "version: 0.1.0\n---\n", id="agent"),
    ],
)
def test_a_manifest_with_a_plain_semantic_version_passes(tmp_path, capsys, relative, front_matter):
    assert MARKDOWN.check_file(_write_raw(tmp_path, relative, front_matter)) == 0, capsys.readouterr().out


def test_every_shipped_skill_and_subagent_carries_a_version():
    # Given the repository's own manifests
    manifests = sorted((REPO_ROOT / ".agents" / "skills").glob("*/SKILL.md")) + sorted((REPO_ROOT / "subagents").glob("*.md"))

    # When / Then
    for path in manifests:
        assert MARKDOWN.check_front_matter(path.read_text(encoding="utf-8").splitlines(), path) == 0, path
