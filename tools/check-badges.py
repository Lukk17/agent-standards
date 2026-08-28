#!/usr/bin/env python3
"""Badge-count lint for README.md.

Enforces that the three count badges in README.md (skills, subagents, MCP
servers) match what is actually in the repository tree:

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

Pass an explicit repository root as the sole argument to check a different
tree (used by the test suite); with no arguments the repository root is
resolved from this script's own location.

Exit codes:
  0  All three badges match the tree.
  1  At least one badge is missing or wrong; errors printed in GitHub
     Actions `::error file=path,line=n::message` format so they surface in
     PR checks and the Annotations tab.
"""

import json
import re
import sys
from pathlib import Path

CHECKS = ("skills", "subagents", "mcp_servers")


def badge_pattern(label: str) -> re.Pattern[str]:
    """Match a shields.io badge URL for `label`, capturing its numeric value."""
    return re.compile(rf"badge/{re.escape(label)}-(\d+)-[^)]*\)")


def find_badge(lines: list[str], label: str) -> tuple[int, int] | None:
    """Return `(value, line_no)` for the first badge carrying `label`, or None."""
    pattern = badge_pattern(label)

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


def check_badges(readme_path: Path, skills_dir: Path, subagents_dir: Path, mcp_json_path: Path) -> int:
    """Compare each badge in `readme_path` against the tree. Returns the violation count."""
    try:
        lines = readme_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        print(f"::error file={readme_path}::cannot read file: {exc}")
        return 1

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

    for label in CHECKS:
        if label not in actual_counts:
            continue

        found = find_badge(lines, label)

        if found is None:
            print(f"::error file={readme_path}::missing '{label}' badge in README.md")
            failures += 1
            continue

        badge_value, line_no = found
        actual = actual_counts[label]

        if badge_value != actual:
            print(
                f"::error file={readme_path},line={line_no}::"
                f"'{label}' badge says {badge_value}, actual count is {actual}"
            )
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

    failures = check_badges(readme_path, skills_dir, subagents_dir, mcp_json_path)

    print(f"\nChecked {len(CHECKS)} badges. Violations: {failures}.")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
