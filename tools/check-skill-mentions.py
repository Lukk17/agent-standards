#!/usr/bin/env python3
"""Guard that every skill a skill file names has a folder under .agents/skills.

A skill names another skill in three places, and only there is a backticked
name read as a skill name, because elsewhere a backticked name is as often a
command or a package:

1. After "use" in the front matter description or in a bullet under a "When not
   to activate" heading, as in "use `bash` or `powershell`".
2. At the start of a bullet under a "Related skills" heading, as in
   "- `arch-linux`, `cachyos` own ...". A name followed by "agent" is a subagent.
3. Anywhere as "`name` skill".

A bullet and its indented continuation lines are read as one line, so a list
broken across two lines is still read whole. Every SKILL.md and every file
under its references/ is checked.

Exit codes: 0 every named skill has a folder, 1 a named skill has none and the
output names the file, the line and the skill, 2 a file could not be read.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterator
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIRECTORY = Path(".agents") / "skills"
SKILL_FILE_NAME = "SKILL.md"

NAME = r"`([a-z0-9]+(?:-[a-z0-9]+)*)`"
NAME_LIST = r"(?:`[a-z0-9]+(?:-[a-z0-9]+)*`(?:,\s*|,?\s+or\s+|,?\s+and\s+)?)+"
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*$")
BULLET = re.compile(r"^\s*-\s+")
AFTER_USE = re.compile(r"\b[Uu]se\s+(" + NAME_LIST + ")")
LEADING_NAMES = re.compile(r"^\s*-\s+(" + NAME_LIST + r")(?!\s+(?:sub)?agent\b)")
NAMED_AS_SKILL = re.compile(NAME + r"\s+skill\b")

RELATED_SKILLS = "related skills"
WHEN_NOT_TO_ACTIVATE = "when not to activate"
DESCRIPTION_KEY = "description:"


def skill_names(skills_root: Path) -> set[str]:
    return {entry.name for entry in skills_root.iterdir() if (entry / SKILL_FILE_NAME).is_file()}


def checked_files(skills_root: Path) -> list[Path]:
    manifests = skills_root.glob(f"*/{SKILL_FILE_NAME}")
    references = skills_root.glob("*/references/**/*.md")
    return sorted([*manifests, *references])


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        print(f"could not read {path}: {error}", file=sys.stderr)
        raise SystemExit(2)


def logical_lines(text: str) -> Iterator[tuple[int, str, str]]:
    """Yield line number, lower-case section heading and the line with its continuation lines joined."""
    section = ""
    pending: tuple[int, str] | None = None
    for number, line in enumerate(text.splitlines(), 1):
        heading = HEADING.match(line)
        is_continuation = pending is not None and line[:1].isspace() and bool(line.strip()) and not BULLET.match(line)
        if is_continuation:
            pending = (pending[0], f"{pending[1]} {line.strip()}")
            continue
        if pending is not None:
            yield pending[0], section, pending[1]
            pending = None
        if heading:
            section = heading.group(1).casefold()
            continue
        pending = (number, line)
    if pending is not None:
        yield pending[0], section, pending[1]


def named_skills(section: str, line: str) -> set[str]:
    names: set[str] = set(NAMED_AS_SKILL.findall(line))
    is_bullet = BULLET.match(line) is not None
    if line.startswith(DESCRIPTION_KEY) or (is_bullet and section == WHEN_NOT_TO_ACTIVATE):
        for match in AFTER_USE.finditer(line):
            names.update(re.findall(NAME, match.group(1)))
    if is_bullet and section == RELATED_SKILLS:
        leading = LEADING_NAMES.match(line)
        if leading:
            names.update(re.findall(NAME, leading.group(1)))
    return names


def find_missing(root: Path) -> list[str]:
    skills_root = root / SKILLS_DIRECTORY
    known = skill_names(skills_root)
    findings = []
    for path in checked_files(skills_root):
        for number, section, line in logical_lines(read_text(path)):
            for name in sorted(named_skills(section, line) - known):
                findings.append(
                    f"{path.relative_to(root).as_posix()}:{number} names the skill `{name}`, which has no folder "
                    f"under {SKILLS_DIRECTORY.as_posix()}. Remove the mention or name a skill that exists."
                )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    root: Path = args.root

    if not (root / SKILLS_DIRECTORY).is_dir():
        print(f"{root / SKILLS_DIRECTORY} is not a directory", file=sys.stderr)
        return 2

    findings = find_missing(root)
    for finding in findings:
        print(finding, file=sys.stderr)

    if findings:
        return 1

    print(f"Every skill named in {SKILLS_DIRECTORY.as_posix()} has a folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
