#!/usr/bin/env python3
"""Markdown lint for human-facing docs.

Enforces a subset of the `markdown-writer` skill rules:

- No em-dashes (U+2014) or en-dashes (U+2013) in body text.
- Section headings start at level 3; level 2 is never used (level 1 is
  reserved for the document title).
- A file inside `.agents/skills/<name>/` links only inside its own skill
  folder. A consumer keeps the skills it chose and deletes the rest, so a link
  into a sibling skill, or out of the skills tree, can be dead downstream.
  Another skill is named in backticks instead.

- No dated or "current version" baseline in an agent-facing file: a skill
  file under `.agents/skills/`, a `subagents/<name>.md` source, or a file in a
  generated agent tree. "Current as of", "as of <Month> <Year>", "as of
  <Year>", "verified <Month> <Year>" and "the current stable release is X" are
  stale the day after they are written, and an agent reads them as fact. State
  the major version the content is written for instead. Fenced code and inline
  code spans are exempt, so a specimen such as SQL `AS OF` stays legal.

There is no line-length rule. Prose is never hard-wrapped, so a paragraph is
one physical line however long it runs.

This module ships in `.agents/hooks/` so the markdown lint hook finds it in a
consumer checkout, which never receives `tools/`. The leading underscore keeps
the OpenCode and Kilo Code runner from running it as a hook. In this
repository `tools/check-markdown.py` is the command CI runs, and it only hands
over to this file.

It also validates the YAML front matter of the two manifest kinds an agent
loads by parsing it, `.agents/skills/<name>/SKILL.md` and `subagents/<name>.md`:
the block has to be present, parse under a strict YAML parser, carry a `name`
matching the folder name (skills) or the file stem (subagents), and carry a
non-empty string `description` of at most 1024 characters. A skill manifest may
carry no key beyond name, description, license, compatibility and metadata, per
the open Agent Skills specification. The description scalar is read raw as well
as parsed, so a plain scalar holding a colon-space, or opening with a character
YAML reads as an indicator, is reported as needing quotes rather than left for a
downstream agent to choke on. GitHub Copilot refused to load two skills over
exactly that, and the block parses as a nested mapping instead of a string.

Scope: README.md, AGENTS.md.example, docs/*.md, .agents/skills/**/*.md, the
global install's global/*.md and global/*.md.example, and the canonical
subagents/*.md source. The four generated subagent trees
(.claude/agents/, .agents/agents/, .codex/agents/, .github/agents/) get the
dated-baseline rule only, because a consumer receives them without the
canonical source; every other rule skips them, since they are rendered from
that source and would report the same violation five times. The .opencode/agents
and .kilo/agents symlinks into .agents/agents/ are never walked.

Pass explicit file paths as arguments to lint only those files; with no
arguments the default target set above is linted.

Exemptions inside checked files:

- Fenced code blocks. Handles both backtick (```) and tilde (~~~) fences,
  including nested fences via backtick-count matching plus an empty
  info-string requirement on the closer (CommonMark spec).
- Inline code spans, for the dash check only. A document that teaches the
  no-dash rule has to name the characters it bans, and `-` wrapped in
  backticks is a specimen rather than prose.
- Table rows (lines starting with `|`), except from the skill link check.
- HTML `<summary>` lines, except from the skill link check.
- Badge lines (`[![Name](url)](url)` style), except from the skill link check.

Exit codes:
  0  No violations.
  1  At least one violation found; errors printed in GitHub Actions
     `::error file=path,line=n::message` format so they surface in PR
     checks and the Annotations tab.

The markdown lint hook spawns this script as `python -S -E`, and `-S` leaves
site-packages off sys.path, so a plain `import yaml` would raise and take the
whole lint down with it. The site module is still importable under that flag,
just not run, so running it by hand restores the path. When even that fails,
the front matter check reports a warning and stands down while every other
check carries on, because a broken lint must never be the reason an edit goes
unchecked.
"""

import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    try:
        import site

        site.main()
        import yaml
    except (ModuleNotFoundError, AttributeError):
        yaml = None

EM_OR_EN_DASH = re.compile(r"[–—]")
HEADING = re.compile(r"^(#{1,6})\s")
FENCE_OPEN = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")
TABLE_ROW = re.compile(r"^\s*\|")
SUMMARY_TAG = re.compile(r"^\s*<summary[\s>]", re.IGNORECASE)
BADGE_LINE = re.compile(r"^\s*\[!\[")
INLINE_CODE = re.compile(r"``.*?``|`[^`]*`")
INLINE_LINK_TARGET = re.compile(r"\]\(\s*<?([^)\s>]+)")
REFERENCE_LINK_TARGET = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*<?([^\s>]+)")
URL_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
AGENTS_DIRECTORY = ".agents"

FRONT_MATTER_FENCE = "---"
SKILL_MANIFEST = "SKILL.md"
SKILLS_DIRECTORY = "skills"
SUBAGENTS_DIRECTORY = "subagents"
SKILL_ALLOWED_KEYS = ("name", "description", "license", "compatibility", "metadata")
MAX_DESCRIPTION = 1024
YAML_INDICATORS = "*&!%@`[{>|\"'"
QUOTES = "\"'"
KEY_LINE = re.compile(r"^([A-Za-z0-9_-]+):(.*)$")

GENERATED_AGENT_TREES = (
    (".claude", "agents"),
    (".agents", "agents"),
    (".codex", "agents"),
    (".github", "agents"),
    (".opencode", "agents"),
    (".kilo", "agents"),
)
GENERATED_AGENT_SUFFIXES = (".md", ".toml")

_MONTH = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?"
    r"|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?"
)
_YEAR = r"(?:19|20)\d{2}\b"
_DATE = (
    rf"(?:{_MONTH}\s+(?:\d{{1,2}},?\s+)?{_YEAR}"
    rf"|\d{{1,2}}\s+{_MONTH}\s+{_YEAR}"
    r"|(?:19|20)\d{2}-\d{2}(?:-\d{2})?\b)"
)
_RELEASE_NOUN = r"(?:(?:stable|lts|latest|supported)\s+)*(?:release|version|toolchain|lts)\b"
_CAPITALISED_NAME = r"(?-i:[A-Z])[\w.+#-]*"
_PERIOD = rf"(?:{_DATE}|{_YEAR}|q[1-4]\s+{_YEAR}|(?:early|mid|late)[\s-]+{_YEAR}|today\b)"
_NOW = r"(?:current|latest)"
# "v2 is the current version of the API" names the project's own API version, not a release of a tool.
_NOT_OWN_VERSION = r"(?!\s+of\s+(?:the|this|our|its|your)\b)"
DATED_BASELINES = (
    re.compile(r"\bcurrent\s+as\s+of\b", re.IGNORECASE),
    re.compile(rf"\bas\s+of\s+{_PERIOD}", re.IGNORECASE),
    re.compile(rf"\b(?:verified|checked|tested|confirmed)\s*:?\s+(?:on\s+|in\s+)?{_DATE}", re.IGNORECASE),
    re.compile(
        rf"\bthe\s+{_NOW}\s+(?:{_CAPITALISED_NAME}\s+)?{_RELEASE_NOUN}"
        rf"(?:\s+of\s+{_CAPITALISED_NAME}(?:\s+{_CAPITALISED_NAME})?)?"
        rf"\s+is\s+(?:v?\d|{_CAPITALISED_NAME}(?:\s+{_CAPITALISED_NAME})?\s+v?\d)",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\bv?\d+(?:\.\d+)*,?\s+(?:is\s+|as\s+)?the\s+{_NOW}\s+{_RELEASE_NOUN}{_NOT_OWN_VERSION}", re.IGNORECASE
    ),
)


# A skill tells a project to pin every action to a commit SHA and every image to
# a digest, but shows the pin as a placeholder such as `<commit-sha>` or
# `<digest>`: a real value in a skill is stale the day the upstream re-tags.
HASH_PINS = (
    re.compile(r"\buses:\s*['\"]?[^\s'\"#]+@[0-9a-fA-F]{40}(?![0-9a-zA-Z])"),
    re.compile(r"\bsha256:[0-9a-fA-F]{64}(?![0-9a-zA-Z])"),
)


def skill_folder(path: Path) -> Path | None:
    """The `.agents/skills/<name>` folder holding the file, None outside one."""
    parts = path.parts

    for index in range(len(parts) - 2, 0, -1):
        if parts[index] == SKILLS_DIRECTORY and parts[index - 1] == AGENTS_DIRECTORY:
            return Path(*parts[: index + 2])

    return None


def _link_targets(line: str) -> list[str]:
    """Every local link target on one line, inline code removed first."""
    text = INLINE_CODE.sub("", line)
    targets = INLINE_LINK_TARGET.findall(text)
    reference = REFERENCE_LINK_TARGET.match(text)

    if reference:
        targets.append(reference.group(1))

    return [target for target in targets if not URL_SCHEME.match(target) and not target.startswith("#")]


def _escapes_folder(target: str, path: Path, folder: Path) -> bool:
    location = target.split("#", 1)[0].split("?", 1)[0]

    if not location:
        return False

    resolved = os.path.normpath(os.path.join(path.parent, location))
    inside = os.path.normpath(folder)

    try:
        return os.path.commonpath([resolved, inside]) != inside
    except ValueError:
        return True


def _skill_link_violations(line: str, line_no: int, path: Path, folder: Path | None) -> int:
    if folder is None:
        return 0

    failures = 0

    for target in _link_targets(line):
        if _escapes_folder(target, path, folder):
            failures += _violation(
                path,
                line_no,
                f"links outside its own skill folder to {target}; a consumer may not have that path, "
                "so name another skill in backticks instead of linking it",
            )

    return failures


def _outside_fences(lines: list[str], first_index: int = 0):
    """Yield (line number, line) for every line outside a fenced code block.

    Lines before `first_index` are skipped. Fences follow CommonMark: a closer
    uses the opener's character, is at least as long, and has no info string.
    """
    in_fence = False
    fence_char = ""
    fence_marker_len = 0

    for line_no, line in enumerate(lines, start=1):
        if line_no - 1 < first_index:
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

        yield line_no, line


def check_lines(lines: list[str], path: Path) -> int:
    """Pure linter. Returns the violation count for one file's lines.

    Separated from file I/O so unit tests can pass synthetic `lines`
    without touching the filesystem.
    """
    failures = 0
    folder = skill_folder(path)

    # Skip a leading YAML frontmatter block; it is metadata, not prose.
    fm_end = -1
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                fm_end = i
                break

    for line_no, line in _outside_fences(lines, fm_end + 1):
        failures += _skill_link_violations(line, line_no, path, folder)

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

        if EM_OR_EN_DASH.search(INLINE_CODE.sub("", line)):
            preview = line[:80].rstrip()
            print(
                f"::error file={path},line={line_no}::"
                f"em-dash or en-dash found: {preview}"
            )
            failures += 1

    return failures


def generated_agent_file(path: Path) -> bool:
    """True for a file inside one of the generated subagent trees."""
    parts = path.parts

    return len(parts) >= 3 and tuple(parts[-3:-1]) in GENERATED_AGENT_TREES and path.suffix in GENERATED_AGENT_SUFFIXES


def dated_baseline_scope(path: Path) -> bool:
    """True for an agent-facing file: a skill file, a subagent source, or a generated agent."""
    return skill_folder(path) is not None or front_matter_target(path) is not None or generated_agent_file(path)


def check_hash_pins(lines: list[str], path: Path) -> int:
    """Report every real commit SHA in a `uses:` line and every real sha256 digest. Returns the count.

    Code fences are checked too, because that is where a workflow or a Compose
    file shows its pins. A placeholder such as `<commit-sha>` or `<digest>` passes.
    """
    if not dated_baseline_scope(path):
        return 0

    failures = 0

    for line_no, line in enumerate(lines, start=1):
        for pattern in HASH_PINS:
            match = pattern.search(line)

            if match:
                failures += _violation(
                    path,
                    line_no,
                    f'real hash pin "{match.group(0)}"; show the pin as a placeholder such as '
                    "`@<commit-sha> # v5` or `@sha256:<digest>`, with the command that resolves it",
                )
                break

    return failures


def check_dated_baselines(lines: list[str], path: Path) -> int:
    """Report every dated or "current version" baseline outside code. Returns the count.

    The front matter is checked too, because the description is what an agent
    reads first.
    """
    if not dated_baseline_scope(path):
        return 0

    failures = 0

    for line_no, line in _outside_fences(lines):
        prose = INLINE_CODE.sub("", line)

        for pattern in DATED_BASELINES:
            match = pattern.search(prose)

            if match:
                failures += _violation(
                    path,
                    line_no,
                    f'dated or "current version" baseline "{match.group(0)}"; it goes stale unseen, '
                    "so state only the major version or versions the content is written for",
                )
                break

    return failures


def front_matter_target(path: Path) -> tuple[str, str] | None:
    """Classify a path as a skill manifest or a subagent source.

    Returns the kind and the name the front matter has to declare, or None for
    every other markdown file in the lint scope, which carries no front matter
    contract at all.
    """
    parts = path.parts

    if path.name == SKILL_MANIFEST and len(parts) >= 3 and parts[-3] == SKILLS_DIRECTORY:
        return "skill", parts[-2]

    if path.suffix == ".md" and len(parts) >= 2 and parts[-2] == SUBAGENTS_DIRECTORY:
        return "subagent", path.stem

    return None


def _violation(path: Path, line_no: int, message: str) -> int:
    """Print one violation in the GitHub Actions format and count it as 1."""
    print(f"::error file={path},line={line_no}::{message}")

    return 1


def _front_matter_end(lines: list[str]) -> int:
    for index in range(1, len(lines)):
        if lines[index].strip() == FRONT_MATTER_FENCE:
            return index

    return -1


def _key_line_numbers(block: list[str], offset: int) -> dict[str, int]:
    """Map each top-level front matter key to the file line it is written on."""
    numbers: dict[str, int] = {}

    for index, line in enumerate(block):
        match = KEY_LINE.match(line)

        if match and match.group(1) not in numbers:
            numbers[match.group(1)] = offset + index

    return numbers


def _raw_description(block: list[str]) -> str | None:
    for line in block:
        match = KEY_LINE.match(line)

        if match and match.group(1) == "description":
            return match.group(2).strip()

    return None


def _description_quoting_problem(raw: str) -> str:
    """The reason a raw description scalar needs quotes, empty when it does not."""
    if not raw:
        return ""

    if len(raw) >= 2 and raw[0] in QUOTES and raw[-1] == raw[0]:
        return ""

    if raw[0] in YAML_INDICATORS:
        return (
            f"description opens with the YAML indicator {raw[0]!r} and is not quoted; "
            "wrap the whole value in double quotes"
        )

    if ": " in raw or raw.endswith(":"):
        return (
            "description holds an unquoted colon, which YAML reads as a nested mapping; "
            "wrap the whole value in double quotes and escape any inner double quote"
        )

    return ""


def check_front_matter(lines: list[str], path: Path) -> int:
    """Validate the front matter of a skill manifest or a subagent source.

    Returns the violation count, and 0 for any path outside those two kinds.
    """
    target = front_matter_target(path)

    if target is None:
        return 0

    kind, expected_name = target

    if not lines or lines[0].strip() != FRONT_MATTER_FENCE:
        return _violation(path, 1, f"{kind} front matter missing; the file has to open with a --- block")

    end = _front_matter_end(lines)

    if end < 0:
        return _violation(path, 1, f"{kind} front matter is never closed by a second ---")

    block = lines[1:end]
    key_lines = _key_line_numbers(block, 2)
    failures = 0

    raw_description = _raw_description(block)

    if raw_description is not None:
        problem = _description_quoting_problem(raw_description)

        if problem:
            failures += _violation(path, key_lines.get("description", 1), problem)

    if yaml is None:
        print(f"::warning file={path}::pyyaml is not importable, front matter left unparsed")

        return failures

    try:
        data = yaml.safe_load("\n".join(block))
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        detail = getattr(exc, "problem", None) or str(exc).splitlines()[0]

        return failures + _violation(
            path,
            mark.line + 2 if mark is not None else 1,
            f"front matter is not valid YAML: {detail}",
        )

    if not isinstance(data, dict):
        return failures + _violation(path, 1, "front matter has to be a YAML mapping of keys to values")

    name = data.get("name")

    if name != expected_name:
        source = "folder name" if kind == "skill" else "file stem"
        failures += _violation(
            path,
            key_lines.get("name", 1),
            f"name is {name!r} but the {source} is {expected_name!r}; they have to match",
        )

    description = data.get("description")
    description_line = key_lines.get("description", 1)

    if description is None:
        failures += _violation(path, 1, "description is missing")
    elif not isinstance(description, str):
        failures += _violation(
            path,
            description_line,
            f"description has to be a string, found {type(description).__name__}",
        )
    elif not description.strip():
        failures += _violation(path, description_line, "description is empty")
    elif len(description) > MAX_DESCRIPTION:
        failures += _violation(
            path,
            description_line,
            f"description is {len(description)} characters, over the {MAX_DESCRIPTION} character cap",
        )

    if kind == "skill":
        allowed = ", ".join(SKILL_ALLOWED_KEYS)

        for key in sorted(set(data) - set(SKILL_ALLOWED_KEYS), key=str):
            failures += _violation(
                path,
                key_lines.get(str(key), 1),
                f"key {key!r} is not in the Agent Skills specification; allowed keys are {allowed}",
            )

    return failures


def check_file(path: Path) -> int:
    """Read one file, lint it and validate its front matter. Returns the violation count.

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

    pins = check_hash_pins(lines, path)

    if generated_agent_file(path):
        return check_dated_baselines(lines, path) + pins

    return check_lines(lines, path) + check_front_matter(lines, path) + check_dated_baselines(lines, path) + pins


def default_targets(repo_root: Path) -> list[Path]:
    targets = [
        repo_root / "README.md",
        repo_root / "AGENTS.md.example",
    ]
    targets.extend(sorted((repo_root / "docs").glob("*.md")))
    targets.extend(sorted((repo_root / ".agents" / "skills").glob("**/*.md")))
    targets.extend(sorted((repo_root / "global").glob("*.md")))
    targets.extend(sorted((repo_root / "global").glob("*.md.example")))
    targets.extend(sorted((repo_root / "subagents").glob("*.md")))
    targets.extend(generated_agent_targets(repo_root))

    return targets


def generated_agent_targets(repo_root: Path) -> list[Path]:
    """Every file of the four generated subagent trees, symlinked trees excluded."""
    targets: list[Path] = []

    for tree in (".claude", ".agents", ".codex", ".github"):
        directory = repo_root / tree / "agents"
        targets.extend(sorted(p for p in directory.glob("*") if p.suffix in GENERATED_AGENT_SUFFIXES))

    return targets


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]

    if len(sys.argv) > 1:
        targets = [Path(arg) for arg in sys.argv[1:]]
    else:
        targets = default_targets(repo_root)

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
