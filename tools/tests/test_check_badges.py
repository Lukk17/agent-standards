"""Tests for tools/check-badges.py.

The script's filename carries a hyphen, so it is loaded in-process via
importlib rather than a normal `import` statement, the same technique
tests/test_preflight_gate.py uses for its own hyphenated sibling. The pure
counting and parsing functions are exercised directly; the CLI entry point
is exercised through `main()` with an explicit repo-root argument, which
is the same `argv` injection pattern the preflight gate's own `main()`
supports for in-process testing.
"""

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

from tests.conftest import REPO_ROOT

CHECK_BADGES = REPO_ROOT / "tools" / "check-badges.py"


def _load_check_badges_module():
    spec = importlib.util.spec_from_file_location("check_badges", CHECK_BADGES)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


BADGES = _load_check_badges_module()

CARD_TEXT_LINE = '    <text x="205" y="401" fill="#ffffff" text-anchor="middle">{text}</text>'


def _write_card(root: Path, *, skills: int | None, subagents: int | None, mcp_servers: int | None) -> Path:
    """Write a social card shaped like docs/assets/social-card.svg, leaving out any count passed as None."""
    card_path = root / "docs" / "assets" / "social-card.svg"
    card_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="640">',
        '  <text x="80" y="240" font-size="36">One git checkout drops a shared AI coding setup</text>',
        '  <g font-size="30" font-weight="600">',
    ]
    for value, words in ((skills, "skills"), (subagents, "subagents"), (mcp_servers, "MCP servers")):
        if value is not None:
            lines.append(CARD_TEXT_LINE.format(text=f"{value} {words}"))
    lines.extend(["  </g>", "</svg>"])
    card_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return card_path


def _build_repo(
    tmp_path: Path,
    *,
    skills_count: int,
    subagents_count: int,
    mcp_count: int,
    skills_badge: int | None,
    subagents_badge: int | None,
    mcp_badge: int | None,
) -> Path:
    """Build a throwaway repo root holding the five pieces check-badges.py reads."""
    skills_dir = tmp_path / ".agents" / "skills"
    skills_dir.mkdir(parents=True)
    for i in range(skills_count):
        (skills_dir / f"skill-{i}").mkdir()
    # A file directly under .agents/skills/ must never count as a skill.
    (skills_dir / "NOTES.md").write_text("not a skill directory", encoding="utf-8")

    subagents_dir = tmp_path / "subagents"
    subagents_dir.mkdir()
    for i in range(subagents_count):
        (subagents_dir / f"agent-{i}.md").write_text("agent", encoding="utf-8")
    # A non-.md file under subagents/ must never count as a subagent.
    (subagents_dir / "notes.txt").write_text("ignore me", encoding="utf-8")

    mcp_json = {"mcpServers": {f"server-{i}": {"type": "stdio"} for i in range(mcp_count)}}
    (tmp_path / ".mcp.json").write_text(json.dumps(mcp_json), encoding="utf-8")

    lines = ["# Title", ""]
    if skills_badge is not None:
        lines.append(f"[![Skills](https://img.shields.io/badge/skills-{skills_badge}-blueviolet)](.agents/skills/)")
    if subagents_badge is not None:
        lines.append(
            f"[![Subagents](https://img.shields.io/badge/subagents-{subagents_badge}-blueviolet)](subagents/)"
        )
    if mcp_badge is not None:
        lines.append(
            f"[![MCP](https://img.shields.io/badge/mcp_servers-{mcp_badge}-blueviolet)](docs/MCP_SETUP.md)"
        )
    lines.append("Unrelated prose mentioning the number 84 in passing.")
    (tmp_path / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    _write_card(tmp_path, skills=skills_count, subagents=subagents_count, mcp_servers=mcp_count)

    return tmp_path


def _all_correct_repo(tmp_path: Path) -> Path:
    return _build_repo(
        tmp_path,
        skills_count=2,
        subagents_count=3,
        mcp_count=4,
        skills_badge=2,
        subagents_badge=3,
        mcp_badge=4,
    )


def test_all_three_counts_correct_passes(tmp_path, capsys):
    # Given a repo where every badge matches the real tree
    root = _all_correct_repo(tmp_path)

    # When
    exit_code = BADGES.main([str(root)])

    # Then
    assert exit_code == 0
    assert "Violations: 0" in capsys.readouterr().out


def test_wrong_skills_badge_fails_with_useful_message(tmp_path, capsys):
    # Given every count correct except the skills badge, which is stale
    root = _build_repo(
        tmp_path,
        skills_count=2,
        subagents_count=3,
        mcp_count=4,
        skills_badge=1,
        subagents_badge=3,
        mcp_badge=4,
    )

    # When
    exit_code = BADGES.main([str(root)])

    # Then
    assert exit_code == 1

    out = capsys.readouterr().out
    assert "::error" in out
    assert "'skills' badge says 1, actual count is 2" in out


def test_wrong_subagents_badge_fails_with_useful_message(tmp_path, capsys):
    # Given every count correct except the subagents badge, which is stale
    root = _build_repo(
        tmp_path,
        skills_count=2,
        subagents_count=3,
        mcp_count=4,
        skills_badge=2,
        subagents_badge=99,
        mcp_badge=4,
    )

    # When
    exit_code = BADGES.main([str(root)])

    # Then
    assert exit_code == 1

    out = capsys.readouterr().out
    assert "'subagents' badge says 99, actual count is 3" in out


def test_wrong_mcp_badge_fails_with_useful_message(tmp_path, capsys):
    # Given every count correct except the MCP servers badge, which is stale
    root = _build_repo(
        tmp_path,
        skills_count=2,
        subagents_count=3,
        mcp_count=4,
        skills_badge=2,
        subagents_badge=3,
        mcp_badge=8,
    )

    # When
    exit_code = BADGES.main([str(root)])

    # Then
    assert exit_code == 1

    out = capsys.readouterr().out
    assert "'mcp_servers' badge says 8, actual count is 4" in out


BADGE_KWARG_BY_LABEL = {
    "skills": "skills_badge",
    "subagents": "subagents_badge",
    "mcp_servers": "mcp_badge",
}


@pytest.mark.parametrize("missing_label", ["skills", "subagents", "mcp_servers"])
def test_missing_badge_is_reported_not_silently_passed(tmp_path, capsys, missing_label):
    # Given a README that never mentions one of the three badges at all
    kwargs = {
        "skills_count": 2,
        "subagents_count": 3,
        "mcp_count": 4,
        "skills_badge": 2,
        "subagents_badge": 3,
        "mcp_badge": 4,
    }
    kwargs[BADGE_KWARG_BY_LABEL[missing_label]] = None
    root = _build_repo(tmp_path, **kwargs)

    # When
    exit_code = BADGES.main([str(root)])

    # Then
    assert exit_code == 1

    out = capsys.readouterr().out
    assert f"missing '{missing_label}' badge" in out


def test_multiple_wrong_badges_are_all_reported(tmp_path, capsys):
    # Given two stale badges at once
    root = _build_repo(
        tmp_path,
        skills_count=2,
        subagents_count=3,
        mcp_count=4,
        skills_badge=1,
        subagents_badge=3,
        mcp_badge=1,
    )

    # When
    exit_code = BADGES.main([str(root)])

    # Then every violation is reported, not just the first
    assert exit_code == 1

    out = capsys.readouterr().out
    assert "'skills' badge says 1, actual count is 2" in out
    assert "'mcp_servers' badge says 1, actual count is 4" in out
    assert "Violations: 2" in out


def test_badge_colour_change_does_not_break_matching(tmp_path, capsys):
    # Given a badge whose colour differs from the repo's current blueviolet
    root = _build_repo(
        tmp_path,
        skills_count=2,
        subagents_count=3,
        mcp_count=4,
        skills_badge=2,
        subagents_badge=3,
        mcp_badge=4,
    )
    readme = root / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            "badge/skills-2-blueviolet", "badge/skills-2-success"
        ),
        encoding="utf-8",
    )

    # When
    exit_code = BADGES.main([str(root)])

    # Then the colour change alone must not be flagged as a violation
    assert exit_code == 0


def test_unrelated_number_in_prose_is_not_mistaken_for_a_badge(tmp_path):
    # Given a README whose prose happens to contain a number matching the
    # stale skills count, alongside a correct skills badge
    root = _all_correct_repo(tmp_path)
    readme = root / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8") + "\nWe once had skills-1-blueviolet as a typo, not a badge.\n",
        encoding="utf-8",
    )

    # When
    exit_code = BADGES.main([str(root)])

    # Then the real badge still matches and the check stays clean
    assert exit_code == 0


def test_count_skills_ignores_files(tmp_path):
    # Given a skills directory with two subdirectories and one stray file
    skills_dir = tmp_path / ".agents" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "a").mkdir()
    (skills_dir / "b").mkdir()
    (skills_dir / "README.md").write_text("not a skill", encoding="utf-8")

    # When
    count = BADGES.count_skills(skills_dir)

    # Then
    assert count == 2


def test_count_subagents_only_counts_markdown_files(tmp_path):
    # Given a subagents directory with two markdown files and a stray text file
    subagents_dir = tmp_path / "subagents"
    subagents_dir.mkdir()
    (subagents_dir / "a.md").write_text("agent", encoding="utf-8")
    (subagents_dir / "b.md").write_text("agent", encoding="utf-8")
    (subagents_dir / "notes.txt").write_text("ignore", encoding="utf-8")

    # When
    count = BADGES.count_subagents(subagents_dir)

    # Then
    assert count == 2


def test_count_mcp_servers_reads_top_level_key(tmp_path):
    # Given an .mcp.json with three servers under mcpServers
    mcp_json = tmp_path / ".mcp.json"
    mcp_json.write_text(
        json.dumps({"mcpServers": {"a": {}, "b": {}, "c": {}}}),
        encoding="utf-8",
    )

    # When
    count = BADGES.count_mcp_servers(mcp_json)

    # Then
    assert count == 3


def test_find_badge_returns_none_when_label_absent():
    # Given a README with no badge for the requested label
    lines = ["# Title", "no badges here"]

    # When
    found = BADGES.find_badge(lines, "skills")

    # Then
    assert found is None


def test_check_badges_reports_unreadable_readme(tmp_path, capsys):
    # Given a repo root whose README.md does not exist
    root = _all_correct_repo(tmp_path)
    readme_path = root / "README.md"
    readme_path.unlink()

    # When
    exit_code = BADGES.main([str(root)])

    # Then the failure is reported rather than raising, the exit code is 1,
    # and the message names the file that could not be read
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "::error" in out
    assert str(readme_path) in out


def test_check_badges_reports_missing_skills_directory(tmp_path, capsys):
    # Given a repo root whose .agents/skills/ directory does not exist
    root = _all_correct_repo(tmp_path)
    skills_dir = root / ".agents" / "skills"
    shutil.rmtree(skills_dir)

    # When
    exit_code = BADGES.main([str(root)])

    # Then the failure is reported rather than raising, the exit code is 1,
    # and the message names the directory that could not be read
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "::error" in out
    assert str(skills_dir) in out


def test_check_badges_reports_missing_subagents_directory(tmp_path, capsys):
    # Given a repo root whose subagents/ directory does not exist
    root = _all_correct_repo(tmp_path)
    subagents_dir = root / "subagents"
    shutil.rmtree(subagents_dir)

    # When
    exit_code = BADGES.main([str(root)])

    # Then the failure is reported rather than raising, the exit code is 1,
    # and the message names the directory that could not be read
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "::error" in out
    assert str(subagents_dir) in out


def test_check_badges_reports_malformed_mcp_json(tmp_path, capsys):
    # Given a repo root whose .mcp.json is not valid JSON
    root = _all_correct_repo(tmp_path)
    mcp_json_path = root / ".mcp.json"
    mcp_json_path.write_text("{not valid json", encoding="utf-8")

    # When
    exit_code = BADGES.main([str(root)])

    # Then the failure is reported rather than raising, the exit code is 1,
    # and the message names the file that could not be read
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "::error" in out
    assert str(mcp_json_path) in out


def test_count_subagents_raises_file_not_found_for_missing_directory(tmp_path):
    # Given a subagents directory that does not exist
    subagents_dir = tmp_path / "subagents"

    # When / Then
    with pytest.raises(FileNotFoundError):
        BADGES.count_subagents(subagents_dir)


def test_stale_card_counts_fail_with_useful_message(tmp_path, capsys):
    # Given correct README badges and a card still showing older counts
    root = _all_correct_repo(tmp_path)
    _write_card(root, skills=84, subagents=30, mcp_servers=4)

    # When
    exit_code = BADGES.main([str(root)])

    # Then every stale card count is reported, and the correct one is not
    assert exit_code == 1

    out = capsys.readouterr().out
    assert "'skills' card count says 84, actual count is 2" in out
    assert "'subagents' card count says 30, actual count is 3" in out
    assert "mcp_servers' card count" not in out
    assert "Violations: 2" in out


@pytest.mark.parametrize("missing_label", ["skills", "subagents", "mcp_servers"])
def test_missing_card_count_is_reported_not_silently_passed(tmp_path, capsys, missing_label):
    # Given a card that no longer draws one of the three counts
    root = _all_correct_repo(tmp_path)
    counts = {"skills": 2, "subagents": 3, "mcp_servers": 4}
    counts[missing_label] = None
    _write_card(root, **counts)

    # When
    exit_code = BADGES.main([str(root)])

    # Then
    assert exit_code == 1

    out = capsys.readouterr().out
    assert f"missing '{missing_label}' card count in social-card.svg" in out


def test_missing_card_file_is_reported(tmp_path, capsys):
    # Given a repo root whose social card does not exist
    root = _all_correct_repo(tmp_path)
    card_path = root / "docs" / "assets" / "social-card.svg"
    card_path.unlink()

    # When
    exit_code = BADGES.main([str(root)])

    # Then the failure names the card rather than raising
    assert exit_code == 1

    out = capsys.readouterr().out
    assert "::error" in out
    assert str(card_path) in out


def test_card_subagents_count_is_not_read_as_the_skills_count():
    # Given a card line for subagents only
    lines = [CARD_TEXT_LINE.format(text="35 subagents")]

    # When
    found = BADGES.find_card_count(lines, "skills")

    # Then
    assert found is None


def test_real_repo_readme_and_card_match_the_real_tree():
    # Given the actual repository this test suite lives in
    # When
    exit_code = BADGES.main([str(REPO_ROOT)])

    # Then the README badges and the social card counts must already be
    # correct by the time the test suite is green
    assert exit_code == 0
