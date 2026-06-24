#!/usr/bin/env python3
"""Markdown lint for human-facing docs.

Enforces a subset of the `markdown-writer` skill rules:

- No em-dashes (U+2014) or en-dashes (U+2013) in body text.
- Prose lines kept under 120 chars.
- Section headings start at level 3; level 2 is never used (level 1 is
  reserved for the document title).

Scope: README.md, AGENTS.md.example, docs/*.md, and .agents/skills/**/*.md.
The generated subagent dirs (.claude/agents/, .opencode/agents/) and the
canonical subagents/ source are NOT checked.

Pass explicit file paths as arguments to lint only those files; with no
arguments the default target set above is linted.

Exemptions inside checked files:

- Fenced code blocks. Handles both backtick (```) and tilde (~~~) fences,
  including nested fences via backtick-count matching plus an empty
  info-string requirement on the closer (CommonMark spec).
- Table rows (lines starting with `|`).
- HTML `<summary>` lines (cannot wrap inside a `<details>` block).
- Badge lines (`[![Name](url)](url)` style).

Exit codes:
  0  No violations.
  1  At least one violation found; errors printed in GitHub Actions
     `::error file=path,line=n::message` format so they surface in PR
     checks and the Annotations tab.
"""

import re
import sys
from pathlib import Path

EM_OR_EN_DASH = re.compile(r"[–—]")
HEADING = re.compile(r"^(#{1,6})\s")
FENCE_OPEN = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")
TABLE_ROW = re.compile(r"^\s*\|")
SUMMARY_TAG = re.compile(r"^\s*<summary[\s>]", re.IGNORECASE)
BADGE_LINE = re.compile(r"^\s*\[!\[")
ATOMIC = re.compile(r"!?\[[^\]]*\]\([^)]*\)|`[^`]+`")
MAX_LINE = 120


def _unsplittable(line: str) -> bool:
    """True when no wrapping can bring the line under MAX_LINE.

    A markdown link or inline-code span has no internal break point, so a
    single such token longer than the limit (plus its indent) is exempt;
    genuinely long prose with breakable words is not.
    """
    indent = len(line) - len(line.lstrip(" "))
    s = line.strip()
    i = 0
    longest = 0
    cur = ""
    while i < len(s):
        if s[i] in " \t":
            longest = max(longest, len(cur))
            cur = ""
            i += 1
            continue
        m = ATOMIC.match(s, i)
        if m:
            cur += m.group(0)
            i = m.end()
            continue
        cur += s[i]
        i += 1
    longest = max(longest, len(cur))

    return indent + longest > MAX_LINE


def check_lines(lines: list[str], path: Path) -> int:
    """Pure linter. Returns the violation count for one file's lines.

    Separated from file I/O so unit tests can pass synthetic `lines`
    without touching the filesystem.
    """
    in_fence = False
    fence_char = ""
    fence_marker_len = 0
    failures = 0

    # Skip a leading YAML frontmatter block; it is metadata, not prose.
    fm_end = -1
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                fm_end = i
                break

    for line_no, line in enumerate(lines, start=1):
        if line_no - 1 <= fm_end:
            continue

        m = FENCE_OPEN.match(line)

        if m:
            marker = m.group(2)
            this_char = marker[0]
            this_len = len(marker)
            info_string = m.group(3).strip()

            if not in_fence:
                in_fence = True
                fence_char = this_char
                fence_marker_len = this_len
                continue

            is_closer = (
                this_char == fence_char
                and this_len >= fence_marker_len
                and info_string == ""
            )

            if is_closer:
                in_fence = False
                fence_char = ""
                fence_marker_len = 0

            continue

        if in_fence:
            continue

        if TABLE_ROW.match(line):
            continue

        if SUMMARY_TAG.match(line):
            continue

        if BADGE_LINE.match(line):
            continue

        heading = HEADING.match(line)
        if heading and len(heading.group(1)) == 2:
            preview = line[:80].rstrip()
            print(
                f"::error file={path},line={line_no}::"
                f"level-2 heading; sections start at level 3, level 1 is the title only: {preview}"
            )
            failures += 1

        if EM_OR_EN_DASH.search(line):
            preview = line[:80].rstrip()
            print(
                f"::error file={path},line={line_no}::"
                f"em-dash or en-dash found: {preview}"
            )
            failures += 1

        if len(line) > MAX_LINE and not _unsplittable(line):
            print(
                f"::error file={path},line={line_no}::"
                f"prose line over {MAX_LINE} chars ({len(line)} chars)"
            )
            failures += 1

    return failures


def check_file(path: Path) -> int:
    """Read one file and lint it. Returns the violation count.

    Reads in universal-newlines mode and uses `splitlines()` so CRLF
    files don't count trailing CR in line length, and so a trailing
    newline doesn't produce a spurious empty final line.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"::error file={path}::cannot read file: {exc}")
        return 1

    lines = text.splitlines()

    return check_lines(lines, path)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent

    if len(sys.argv) > 1:
        targets = [Path(arg) for arg in sys.argv[1:]]
    else:
        targets = [
            repo_root / "README.md",
            repo_root / "AGENTS.md.example",
        ]
        targets.extend(sorted((repo_root / "docs").glob("*.md")))
        targets.extend(sorted((repo_root / ".agents" / "skills").glob("**/*.md")))

    total = 0
    checked = 0

    for path in targets:
        if not path.exists():
            print(f"::warning::skipping missing file: {path}")
            continue

        checked += 1
        total += check_file(path)

    print(f"\nChecked {checked} files. Violations: {total}.")

    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
