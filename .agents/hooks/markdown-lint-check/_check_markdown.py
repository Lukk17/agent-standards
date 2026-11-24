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

- A skill manifest, `.agents/skills/<name>/SKILL.md`, stays at or under
  4,500 characters, front matter included. The manifest loads in full whenever
  the skill activates, and a subagent preloads it on every run, while a file
  under `references/` loads only on demand, so depth past the limit moves
  there.

- A skill description stays at or under 220 characters, because every skill
  description in a project shares one listing budget.

- A skill manifest carries no "When to activate", "Related skills" or
  "Checklist" section. The description carries the triggers, a neighbouring
  skill is named in the description or under "When not to activate", and the
  checklist lives in `references/checklist.md`. A heading is compared without
  case, emphasis marks, a trailing colon or a plural "s".

- "When not to activate" in a skill manifest holds at most three items, each
  one line, each naming in backticks the skill or the agent that owns the job,
  and nothing else: no prose, no fenced block and no deeper heading.

- A file inside `.agents/skills/<name>/` links only to files that exist. A
  file under `references/` sits directly in that folder, is linked from its
  `SKILL.md`, and opens with a Contents list that links its sections once it
  runs past 100 lines. Each of those links matches the anchor GitHub makes
  from a heading of the same file.

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
non-empty string `description` of at most 1024 characters in a subagent and 220
in a skill. A skill manifest may
carry no key beyond name, description, license, compatibility and metadata, per
the open Agent Skills specification, and has to carry its plugin version as
`metadata.version`, while a subagent source carries it as `version`, each
MAJOR.MINOR.PATCH. A `model` key gets its own message and
stays rejected even if that list widens, because skills never pin a model and
run on the user's default model. The description scalar is read raw as well
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
import unicodedata
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import unquote

try:
    import yaml
except ModuleNotFoundError:
    try:
        import site

        site.main()
        import yaml
    except (ModuleNotFoundError, AttributeError):
        yaml = None

EM_OR_EN_DASH = re.compile(r"[\u2013\u2014]")
HEADING = re.compile(r"^(#{1,6})\s")
FENCE_OPEN = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")
TABLE_ROW = re.compile(r"^\s*\|")
SUMMARY_TAG = re.compile(r"^\s*<summary[\s>]", re.IGNORECASE)
BADGE_LINE = re.compile(r"^\s*\[!\[")
INLINE_CODE = re.compile(r"``.*?``|`[^`]*`")
INLINE_LINK_TARGET = re.compile(r"\]\(\s*<?([^)\s>]+)")
REFERENCE_LINK_TARGET = re.compile(r"^\s{0,3}\[(?!\^)[^\]]+\]:\s*<?([^\s>]+)")
URL_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
AGENTS_DIRECTORY = ".agents"

FRONT_MATTER_FENCE = "---"
SKILL_MANIFEST = "SKILL.md"
SKILLS_DIRECTORY = "skills"
SUBAGENTS_DIRECTORY = "subagents"
SKILL_ALLOWED_KEYS = ("name", "description", "license", "compatibility", "metadata")
MODEL_KEY = "model"
VERSION_KEY = "version"
SKILL_VERSION_KEY = "metadata"
# MAJOR.MINOR.PATCH and nothing else, each part without a leading zero, the
# version a marketplace entry and a release tag carry.
SEMANTIC_VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", re.ASCII)
MAX_DESCRIPTION = 1024
MAX_SKILL_DESCRIPTION_CHARACTERS = 220
MAX_SKILL_MANIFEST_CHARACTERS = 4500
MAX_WHEN_NOT_TO_ACTIVATE_ITEMS = 3
MAX_REFERENCE_LINES_WITHOUT_CONTENTS = 100
REFERENCES_DIRECTORY = "references"
DESCRIPTION_LIMITS = {
    "skill": (
        MAX_SKILL_DESCRIPTION_CHARACTERS,
        "character limit for a skill. Keep what the skill covers, the phrases a user says "
        'and one "Not for X, use `skill`" pointer',
    ),
    "subagent": (MAX_DESCRIPTION, "character cap"),
}
WHEN_NOT_TO_ACTIVATE = "when not to activate"
FORBIDDEN_MANIFEST_SECTIONS = {
    "when to activate": "The description already carries the triggers, so delete the section",
    "related skill": 'Name a neighbouring skill in the description or under "When not to activate"',
    "checklist": "Move it to references/checklist.md and link that file from the routing table",
}
HEADING_TEXT = re.compile(r"^(#{1,6})\s+(.*?)[\s#]*$")
EMPHASIS_MARKS = re.compile(r"[*_]")
HORIZONTAL_RULE = re.compile(r"^\s{0,3}([-*_])(?:\s*\1){2,}\s*$")
LIST_ITEM = re.compile(r"^(?:[-*+]|\d+[.)])\s+\S")
BACKTICKED_NAME = re.compile(r"`[a-z0-9]+(?:-[a-z0-9]+)*`")
CONTENTS_MARKER = re.compile(r"^(?:#{1,6}\s+)?contents:?$", re.IGNORECASE)
SECTION_ANCHOR = "#"
HEADING_CODE_SPAN = re.compile(r"(`+)(.+?)\1")
HEADING_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
HTML_TAG = re.compile(r"<[^>]+>")
ESCAPE_OR_EMPHASIS_UNDERSCORE = re.compile(r"\\([!-/:-@\[-`{-~])|(?<![^\W_])_+|_+(?![^\W_])")
SLUG_REMOVED = frozenset({"No", "Pe", "Pf", "Pi", "Ps", "Po", "Pd", "Sm", "Sc", "Sk", "So", "Cc", "Co", "Cf", "Cn", "Zs", "Zl", "Zp"})
SLUG_KEPT = frozenset(" -")
FENCE_OUTSIDE = ""
FENCE_OPENER = "opener"
FENCE_BODY = "body"
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


def _location(target: str) -> str:
    """The file part of a link target, its anchor and query removed and its percent-encoding decoded."""
    return unquote(target.split("#", 1)[0].split("?", 1)[0])


def _escapes_folder(target: str, path: Path, folder: Path) -> bool:
    location = _location(target)

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
                f"links outside its own skill folder to {target}. A consumer may not have that path, "
                "so name another skill in backticks instead of linking it",
            )

    return failures


def _fenced_lines(lines: list[str], first_index: int = 0) -> Iterator[tuple[int, str, str]]:
    """Yield (line number, line, fence) for every line from `first_index` on.

    `fence` is FENCE_OPENER on the line that opens a fenced code block,
    FENCE_BODY on every line inside the block and on its closer, and
    FENCE_OUTSIDE on any other line. Fences follow CommonMark: a closer uses
    the opener's character, is at least as long, and has no info string.
    """
    in_fence = False
    fence_char = ""
    fence_marker_len = 0

    for line_no, line in enumerate(lines, start=1):
        if line_no - 1 < first_index:
            continue

        m = FENCE_OPEN.match(line)

        if m and not in_fence:
            in_fence = True
            fence_char = m.group(2)[0]
            fence_marker_len = len(m.group(2))

            yield line_no, line, FENCE_OPENER
            continue

        if not in_fence:
            yield line_no, line, FENCE_OUTSIDE
            continue

        yield line_no, line, FENCE_BODY

        is_closer = (
            m is not None
            and m.group(2)[0] == fence_char
            and len(m.group(2)) >= fence_marker_len
            and m.group(3).strip() == ""
        )

        if is_closer:
            in_fence = False


def _outside_fences(lines: list[str], first_index: int = 0) -> Iterator[tuple[int, str]]:
    """Yield (line number, line) for every line outside a fenced code block.

    Lines before `first_index` are skipped.
    """
    for line_no, line, fence in _fenced_lines(lines, first_index):
        if fence == FENCE_OUTSIDE:
            yield line_no, line


def check_lines(lines: list[str], path: Path) -> int:
    """Pure linter. Returns the violation count for one file's lines.

    Separated from file I/O so unit tests can pass synthetic `lines`
    without touching the filesystem.
    """
    failures = 0
    folder = skill_folder(path)

    for line_no, line in _outside_fences(lines, _body_start(lines)):
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
                f"level-2 heading. Sections start at level 3, level 1 is the title only: {preview}"
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
    """True for a file inside one of the generated subagent trees, flat or in its own folder."""
    parts = path.parts

    if path.suffix not in GENERATED_AGENT_SUFFIXES:
        return False

    flat = len(parts) >= 3 and tuple(parts[-3:-1]) in GENERATED_AGENT_TREES
    nested = len(parts) >= 4 and tuple(parts[-4:-2]) in GENERATED_AGENT_TREES and parts[-2] == path.name.split(".")[0]

    return flat or nested


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
                    f'real hash pin "{match.group(0)}". Show the pin as a placeholder such as '
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
                    f'dated or "current version" baseline "{match.group(0)}". It goes stale unseen, '
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


def _body_start(lines: list[str]) -> int:
    """The index of the first line after a closed leading front matter block, 0 when there is none."""
    if lines and lines[0].strip() == FRONT_MATTER_FENCE:
        return _front_matter_end(lines) + 1

    return 0


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
            f"description opens with the YAML indicator {raw[0]!r} and is not quoted. "
            "Wrap the whole value in double quotes"
        )

    if ": " in raw or raw.endswith(":"):
        return (
            "description holds an unquoted colon, which YAML reads as a nested mapping. "
            "Wrap the whole value in double quotes and escape any inner double quote"
        )

    return ""


def _description_size_problem(description: str, kind: str) -> str:
    """The reason a description is too long for its kind, empty when it fits."""
    limit, wording = DESCRIPTION_LIMITS[kind]

    if len(description) <= limit:
        return ""

    return f"description is {len(description)} characters, over the {limit} {wording}"


def check_front_matter(lines: list[str], path: Path) -> int:
    """Validate the front matter of a skill manifest or a subagent source.

    Returns the violation count, and 0 for any path outside those two kinds.
    """
    target = front_matter_target(path)

    if target is None:
        return 0

    kind, expected_name = target

    if not lines or lines[0].strip() != FRONT_MATTER_FENCE:
        return _violation(path, 1, f"{kind} front matter missing. The file has to open with a --- block")

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
            f"name is {name!r} but the {source} is {expected_name!r}. They have to match",
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
    elif problem := _description_size_problem(description, kind):
        failures += _violation(path, description_line, problem)

    if kind == "skill":
        allowed = ", ".join(SKILL_ALLOWED_KEYS)

        if MODEL_KEY in data:
            failures += _violation(
                path,
                key_lines.get(MODEL_KEY, 1),
                f"key {MODEL_KEY!r} is not allowed. Remove it, because skills never pin a model "
                "and run on the user's default model",
            )

        for key in sorted(set(data) - set(SKILL_ALLOWED_KEYS) - {MODEL_KEY}, key=str):
            failures += _violation(
                path,
                key_lines.get(str(key), 1),
                f"key {key!r} is not in the Agent Skills specification. Allowed keys are {allowed}",
            )

    return failures + check_manifest_version(data, kind, path, key_lines)


def check_manifest_version(data: dict, kind: str, path: Path, key_lines: dict[str, int]) -> int:
    """Require the plugin version a skill or a subagent carries. Returns the violation count.

    A skill keeps it under `metadata`, the map the Agent Skills specification
    leaves to the author, as `metadata.version`. A subagent keeps it as a
    top-level `version`, which the generator copies into the marketplace and
    never into a generated agent file. Either is MAJOR.MINOR.PATCH.
    """
    if kind == "skill":
        metadata = data.get(SKILL_VERSION_KEY)
        version = metadata.get(VERSION_KEY) if isinstance(metadata, dict) else None
        label, line = f"{SKILL_VERSION_KEY}.{VERSION_KEY}", key_lines.get(SKILL_VERSION_KEY, 1)
    else:
        version = data.get(VERSION_KEY)
        label, line = VERSION_KEY, key_lines.get(VERSION_KEY, 1)

    if version is None:
        return _violation(path, line, f"{label} is missing. Give the {kind} a MAJOR.MINOR.PATCH version such as 1.0.0")

    if not isinstance(version, str) or not SEMANTIC_VERSION.fullmatch(version):
        return _violation(
            path,
            line,
            f"{label} is {version!r}, not a MAJOR.MINOR.PATCH version such as 1.0.0. Write it as a quoted string",
        )

    return 0


def check_skill_manifest_size(text: str, path: Path) -> int:
    """Report a skill manifest over the size limit. Returns the violation count.

    The size is the character count of the whole file, front matter included,
    because the agent loads all of it. Every other path returns 0.
    """
    target = front_matter_target(path)

    if target is None or target[0] != "skill":
        return 0

    size = len(text)

    if size <= MAX_SKILL_MANIFEST_CHARACTERS:
        return 0

    return _violation(
        path,
        1,
        f"skill manifest is {size} characters, over the {MAX_SKILL_MANIFEST_CHARACTERS} character limit. "
        "Keep the technology-neutral rules and the routing table here and move the depth into references/, "
        "one file per technology",
    )


def _heading(line: str) -> tuple[int, str] | None:
    """The level and the title of a heading line, None for any other line.

    The title comes without emphasis marks and without a trailing colon, so
    `### **Checklist:**` and `### Checklist` give the same title.
    """
    match = HEADING_TEXT.match(line)

    if match is None:
        return None

    title = EMPHASIS_MARKS.sub("", match.group(2)).strip().rstrip(":").strip()

    return len(match.group(1)), title


def _section_key(title: str) -> str:
    """A heading title folded for comparison, without case and without a plural "s"."""
    return title.casefold().removesuffix("s")


def check_manifest_sections(lines: list[str], path: Path) -> int:
    """Report every section a skill manifest may not carry. Returns the violation count."""
    failures = 0

    for line_no, line in _outside_fences(lines, _body_start(lines)):
        heading = _heading(line)

        if heading is None:
            continue

        title = heading[1]
        advice = FORBIDDEN_MANIFEST_SECTIONS.get(_section_key(title))

        if advice:
            failures += _violation(path, line_no, f'section "{title}" is not allowed in a skill manifest. {advice}')

    return failures


def _when_not_to_activate_lines(lines: list[str]) -> Iterator[tuple[int, str, str, bool]]:
    """Yield (line number, line, fence, opens) for every line of a "When not to activate" section.

    `opens` is True on the heading of the section and `fence` is the value
    `_fenced_lines` gives the line. The section runs to the next heading of the
    same level or a higher one, so a deeper heading under it is part of it, and
    a heading inside a fenced block is no heading.
    """
    section_level = 0

    for line_no, line, fence in _fenced_lines(lines, _body_start(lines)):
        heading = _heading(line) if fence == FENCE_OUTSIDE else None
        opens = heading is not None and _section_key(heading[1]) == WHEN_NOT_TO_ACTIVATE

        if opens:
            section_level = heading[0]
        elif heading is not None and heading[0] <= section_level:
            section_level = 0

        if section_level:
            yield line_no, line, fence, opens


def check_when_not_to_activate(lines: list[str], path: Path) -> int:
    """Hold "When not to activate" to a few one-line items that each name a skill or an agent.

    Returns the violation count. A fenced block is reported once, on the line
    that opens it.
    """
    failures = 0
    items = 0
    heading_line = 1

    for line_no, line, fence, opens in _when_not_to_activate_lines(lines):
        if opens:
            heading_line = line_no
            continue

        if fence == FENCE_BODY or not line.strip() or HORIZONTAL_RULE.match(line):
            continue

        if fence == FENCE_OPENER or not LIST_ITEM.match(line):
            failures += _violation(
                path,
                line_no,
                'line under "When not to activate" is not a one-line list item. '
                "Write each item on one line and keep nothing else in the section",
            )
            continue

        items += 1

        if not BACKTICKED_NAME.search(line):
            failures += _violation(
                path,
                line_no,
                '"When not to activate" item names no skill or agent. Name the skill or the agent that owns '
                "the job in backticks, as in use `bash`",
            )

    if items > MAX_WHEN_NOT_TO_ACTIVATE_ITEMS:
        failures += _violation(
            path,
            heading_line,
            f'"When not to activate" holds {items} items, over the limit of {MAX_WHEN_NOT_TO_ACTIVATE_ITEMS}. '
            "Keep the nearest neighbouring jobs only",
        )

    return failures


def _body_link_targets(lines: list[str]) -> Iterator[tuple[int, str]]:
    """Yield (line number, target) for every local link in the body, outside fences and inline code."""
    for line_no, line in _outside_fences(lines, _body_start(lines)):
        for target in _link_targets(line):
            yield line_no, target


def check_skill_links_resolve(lines: list[str], path: Path, folder: Path) -> int:
    """Report every link inside the skill folder whose file does not exist. Returns the violation count.

    A link that leaves the folder is left to the rule in `check_lines`, which
    reports it whether or not the file exists.
    """
    failures = 0

    for line_no, target in _body_link_targets(lines):
        location = _location(target)

        if not location or _escapes_folder(target, path, folder):
            continue

        if not os.path.exists(os.path.join(path.parent, location)):
            failures += _violation(
                path,
                line_no,
                f"links to {target}, which does not exist. Fix the path or remove the link",
            )

    return failures


def _manifest_link_locations(folder: Path) -> set[str] | None:
    """Every path the skill's manifest links, relative to the skill folder, None when it cannot be read."""
    try:
        lines = (folder / SKILL_MANIFEST).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None

    return {os.path.normpath(_location(target)) for _, target in _body_link_targets(lines) if _location(target)}


def check_reference_placement(path: Path, folder: Path, relative: Path) -> int:
    """Report a reference that sits in a subfolder or that its manifest never links. Returns the violation count.

    A reference whose manifest cannot be read is left alone, because the folder
    is then no skill this rule can speak for.
    """
    shown = relative.as_posix()
    failures = 0

    if len(relative.parts) > 2:
        failures += _violation(
            path,
            1,
            f"{shown} sits deeper than one level under {REFERENCES_DIRECTORY}/. Move it directly into that folder",
        )

    linked = _manifest_link_locations(folder)

    if linked is not None and os.path.normpath(relative) not in linked:
        failures += _violation(
            path,
            1,
            f"{shown} is not linked from {SKILL_MANIFEST}. Add it to the routing table with a cue saying "
            "when to open it, or delete the file",
        )

    return failures


def _contents_items(lines: list[str]) -> list[tuple[int, str]]:
    """The items of the Contents list a file opens with, as (line number, text).

    Empty when no Contents marker followed by a list comes before the first
    section heading.
    """
    items: list[tuple[int, str]] = []
    marker_seen = False

    for line_no, line in _outside_fences(lines, _body_start(lines)):
        text = line.strip()

        if not text:
            continue

        if marker_seen:
            if not LIST_ITEM.match(text):
                break

            items.append((line_no, text))
            continue

        if CONTENTS_MARKER.match(text):
            marker_seen = True
            continue

        heading = HEADING.match(line)

        if heading and len(heading.group(1)) > 1:
            break

    return items


def _links_a_section(item: str) -> bool:
    """True when a list item holds a link to an anchor of its own file, outside inline code."""
    targets = INLINE_LINK_TARGET.findall(INLINE_CODE.sub("", item))

    return any(target.startswith(SECTION_ANCHOR) for target in targets)


def github_slug(title: str) -> str:
    """The anchor GitHub gives a heading title, before a repeated title gets its -1, -2 suffix.

    Markup goes first: a code span keeps its text, a link or an image keeps
    its text, an HTML tag goes, a backslash escape keeps the character it
    escapes, and any other underscore that is no part of a word is emphasis.
    A Unicode mark such as the variation selector after an emoji stays, as it
    does on GitHub. Then the title is lowercased, every character in SLUG_REMOVED
    categories goes unless it is a letter, a space or a hyphen, and each space
    turns into a hyphen. SLUG_REMOVED is the category list of github-slugger,
    https://github.com/Flet/github-slugger/blob/master/script/generate-regex.js,
    and the rules match "Section links" in
    https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax.
    """
    pieces = []

    for index, piece in enumerate(HEADING_CODE_SPAN.split(title)):
        if index % 3 == 2:
            pieces.append(piece)
        elif index % 3 == 0:
            text = HEADING_LINK.sub(r"\1", piece)
            pieces.append(ESCAPE_OR_EMPHASIS_UNDERSCORE.sub(lambda match: match.group(1) or "", HTML_TAG.sub("", text)))

    kept = (
        character
        for character in "".join(pieces).lower()
        if character in SLUG_KEPT or character.isalpha() or unicodedata.category(character) not in SLUG_REMOVED
    )

    return "".join(kept).replace(" ", "-")


def heading_anchors(lines: list[str]) -> set[str]:
    """Every anchor GitHub gives the headings of a file, outside fenced code, repeats numbered."""
    anchors: set[str] = set()
    seen: dict[str, int] = {}

    for _, line in _outside_fences(lines, _body_start(lines)):
        match = HEADING_TEXT.match(line)

        if match is None:
            continue

        base = github_slug(match.group(2).strip())
        anchor = base

        while anchor in anchors:
            seen[base] = seen.get(base, 0) + 1
            anchor = f"{base}-{seen[base]}"

        anchors.add(anchor)

    return anchors


def check_contents_anchors(lines: list[str], path: Path, items: list[tuple[int, str]]) -> int:
    """Report every Contents link to an anchor that no heading of the same file produces. Returns the count."""
    anchors = heading_anchors(lines)
    failures = 0

    for line_no, item in items:
        for target in INLINE_LINK_TARGET.findall(INLINE_CODE.sub("", item)):
            if not target.startswith(SECTION_ANCHOR) or unquote(target[1:]) in anchors:
                continue

            failures += _violation(
                path,
                line_no,
                f"Contents link {target} matches no heading in this file. "
                "Use the anchor GitHub makes from the heading, as in [Setup steps](#setup-steps)",
            )

    return failures


def check_reference_contents(lines: list[str], path: Path) -> int:
    """Report a long reference that does not open with a Contents list linking its sections.

    Returns the violation count. A list with items that link no section is
    reported once, on the first such item, and each link to an anchor no
    heading of the file produces is reported on its own line.
    """
    if len(lines) <= MAX_REFERENCE_LINES_WITHOUT_CONTENTS:
        return 0

    items = _contents_items(lines)

    if not items:
        return _violation(
            path,
            1,
            f"reference is {len(lines)} lines, over {MAX_REFERENCE_LINES_WITHOUT_CONTENTS}, and has no Contents list "
            'before its first section. Open it with "Contents:" and a list that links its sections',
        )

    failures = check_contents_anchors(lines, path, items)
    unlinked = [line_no for line_no, item in items if not _links_a_section(item)]

    if not unlinked:
        return failures

    return failures + _violation(
        path,
        unlinked[0],
        f"Contents list items without a link to a section: {len(unlinked)} of {len(items)}, the first on this line. "
        "Write each item as a link to its section, as in [Setup](#setup)",
    )


def check_skill_layout(text: str, lines: list[str], path: Path) -> int:
    """Run the layout rules of a skill folder on one of its files. Returns the violation count.

    A manifest is held to its size and its sections. A file under
    `references/` is held to its place, its link from the manifest and its
    Contents list. Every file in the folder is held to links that resolve. A
    path outside a skill folder returns 0, and so does a file that sits
    directly in `.agents/skills/`, in no skill of its own.
    """
    folder = skill_folder(path)

    if folder is None:
        return 0

    failures = check_skill_links_resolve(lines, path, folder)
    relative = Path(os.path.relpath(path, folder))

    if relative.parts == (SKILL_MANIFEST,):
        return (
            failures
            + check_skill_manifest_size(text, path)
            + check_manifest_sections(lines, path)
            + check_when_not_to_activate(lines, path)
        )

    if relative.parts[:1] == (REFERENCES_DIRECTORY,) and path.suffix == ".md":
        return failures + check_reference_placement(path, folder, relative) + check_reference_contents(lines, path)

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

    return (
        check_lines(lines, path)
        + check_front_matter(lines, path)
        + check_skill_layout(text, lines, path)
        + check_dated_baselines(lines, path)
        + pins
    )


def default_targets(repo_root: Path) -> list[Path]:
    targets = [
        repo_root / "README.md",
        repo_root / "AGENTS.md.example",
        # Only the agent-standards readme. The tools beside it are Robert C. Martin's, vendored in his own style.
        repo_root / ".metrics" / "tools" / "README.md",
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
        found = [*directory.glob("*"), *directory.glob("*/*")]
        targets.extend(sorted(p for p in found if p.is_file() and p.suffix in GENERATED_AGENT_SUFFIXES))

    return targets


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]

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
