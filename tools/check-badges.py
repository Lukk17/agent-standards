#!/usr/bin/env python3
"""Count lint for the README badges and the social card.

Enforces that the three count badges in README.md (skills, subagents, MCP
servers), and the same three counts drawn on docs/assets/social-card.svg,
match what is actually in the repository tree:

- skills: number of directories directly under `.agents/skills/`
- subagents: number of `*.md` files under `subagents/`, the canonical
  source, never a generated tree
- MCP servers: number of entries under the top-level `mcpServers` key in
  `.mcp.json`

Badges are shields.io URLs of the form
`https://img.shields.io/badge/<label>-<value>-<color>`. The label segment
(`skills`, `subagents`, `mcp_servers`) is the stable identifier this script
keys on, so a badge colour change or a change to the markdown alt text
(`[![Skills]`) never breaks the check. Matching is anchored to that
`badge/<label>-` prefix, so an unrelated number elsewhere in the README is
never mistaken for a badge.

On the card each count is the whole content of one SVG `<text>` element,
`>N skills<`, `>N subagents<` and `>N MCP servers<`, so matching is
anchored to the closing `>` of the tag and the opening `<` of the next one.

Pass an explicit repository root as the sole argument to check a different
tree (used by the test suite); with no arguments the repository root is
resolved from this script's own location.

Exit codes:
  0  All three badges and all three card counts match the tree.
  1  At least one badge or card count is missing or wrong; errors printed in
     GitHub Actions `::error file=path,line=n::message` format so they surface
     in PR checks and the Annotations tab.
"""

import json
import re
import sys
from collections.abc import Callable
from pathlib import Path

CHECKS = ("skills", "subagents", "mcp_servers")

CARD_WORDS = {"skills": "skills", "subagents": "subagents", "mcp_servers": "MCP servers"}

CountFinder = Callable[[list[str], str], tuple[int, int] | None]


def badge_pattern(label: str) -> re.Pattern[str]:
    """Match a shields.io badge URL for `label`, capturing its numeric value."""
    return re.compile(rf"badge/{re.escape(label)}-(\d+)-[^)]*\)")


def card_pattern(label: str) -> re.Pattern[str]:
    """Match the SVG text content `>N <words><` for `label`, capturing N."""
    return re.compile(rf">\s*(\d+)\s+{re.escape(CARD_WORDS[label])}\s*<")


def find_badge(lines: list[str], label: str) -> tuple[int, int] | None:
    """Return `(value, line_no)` for the first badge carrying `label`, or None."""
    return find_first(lines, badge_pattern(label))


def find_card_count(lines: list[str], label: str) -> tuple[int, int] | None:
    """Return `(value, line_no)` for the first card count carrying `label`, or None."""
    return find_first(lines, card_pattern(label))


def find_first(lines: list[str], pattern: re.Pattern[str]) -> tuple[int, int] | None:
    for line_no, line in enumerate(lines, start=1):
        match = pattern.search(line)
        if match:
            return int(match.group(1)), line_no

    return None


def count_skills(skills_dir: Path) -> int:
    return sum(1 for entry in skills_dir.iterdir() if entry.is_dir())


def count_subagents(subagents_dir: Path) -> int:
    if not subagents_dir.is_dir():
        raise FileNotFoundError(f"no such directory: {subagents_dir}")

    return sum(1 for _ in subagents_dir.glob("*.md"))


def count_mcp_servers(mcp_json_path: Path) -> int:
    data = json.loads(mcp_json_path.read_text(encoding="utf-8"))
    return len(data.get("mcpServers", {}))


def check_badges(
    readme_path: Path, skills_dir: Path, subagents_dir: Path, mcp_json_path: Path, card_path: Path
) -> int:
    """Compare the README badges and the card counts against the tree. Returns the violation count."""
    failures = 0
    actual_counts: dict[str, int] = {}

    try:
        actual_counts["skills"] = count_skills(skills_dir)
    except OSError as exc:
        print(f"::error file={skills_dir}::cannot read skills directory: {exc}")
        failures += 1

    try:
        actual_counts["subagents"] = count_subagents(subagents_dir)
    except OSError as exc:
        print(f"::error file={subagents_dir}::cannot read subagents directory: {exc}")
        failures += 1

    try:
        actual_counts["mcp_servers"] = count_mcp_servers(mcp_json_path)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"::error file={mcp_json_path}::cannot read MCP server config: {exc}")
        failures += 1

    failures += check_document(readme_path, find_badge, "badge", actual_counts)
    failures += check_document(card_path, find_card_count, "card count", actual_counts)

    return failures


def check_document(path: Path, find: CountFinder, kind: str, actual_counts: dict[str, int]) -> int:
    """Compare every count `find` locates in `path` against `actual_counts`. Returns the violation count."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        print(f"::error file={path}::cannot read file: {exc}")
        return 1

    failures = 0

    for label in CHECKS:
        if label not in actual_counts:
            continue

        found = find(lines, label)

        if found is None:
            print(f"::error file={path}::missing '{label}' {kind} in {path.name}")
            failures += 1
            continue

        value, line_no = found
        actual = actual_counts[label]

        if value != actual:
            print(f"::error file={path},line={line_no}::'{label}' {kind} says {value}, actual count is {actual}")
            failures += 1

    return failures


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    if argv:
        repo_root = Path(argv[0])
    else:
        repo_root = Path(__file__).resolve().parent.parent

    readme_path = repo_root / "README.md"
    skills_dir = repo_root / ".agents" / "skills"
    subagents_dir = repo_root / "subagents"
    mcp_json_path = repo_root / ".mcp.json"
    card_path = repo_root / "docs" / "assets" / "social-card.svg"

    failures = check_badges(readme_path, skills_dir, subagents_dir, mcp_json_path, card_path)

    print(f"\nChecked {len(CHECKS)} badges and {len(CHECKS)} card counts. Violations: {failures}.")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
