#!/usr/bin/env python3
"""Guard that wording kept word for word the same in several files stays so.

tools/shared-wording.yaml lists each shared wording as an entry: an `id`, the
canonical `text`, and the `files` that must each hold that text. A file holds
it when the text appears there as whole lines, in order and together. Only
line endings may differ, so a changed word, a dropped or reordered line, or a
copy edited in one file and not the others fails the check.

Exit codes: 0 every listed file holds every text, 1 a copy is missing or
differs and the output names the file, the entry id and the first canonical
line that differs where the copy should stand, 2 the map or a listed file could
not be read or the map does not have the shape above, a listed path included
when it is absolute or climbs out of the root with `..`.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = Path("tools") / "shared-wording.yaml"
ENTRY_KEYS = frozenset({"id", "files", "text"})
MINIMUM_FILES = 2


class SharedWordingError(Exception):
    """The map or a file it lists cannot be read, or the map has the wrong shape."""


@dataclass(frozen=True, slots=True)
class SharedWording:
    entry_id: str
    text: str
    files: tuple[str, ...]


def normalise_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def read_text(path: Path, shown_as: str) -> str:
    """Return the file's text with its line endings normalised to LF.

    Raises:
        SharedWordingError: the file is missing, unreadable or not UTF-8.
    """
    try:
        return normalise_line_endings(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as error:
        raise SharedWordingError(f"{shown_as} is not valid UTF-8: {error}") from error
    except OSError as error:
        raise SharedWordingError(f"could not read {shown_as}: {error}") from error


def is_inside_root(relative: str) -> bool:
    """Tell whether `relative` names a path under the root, with no anchor and no `..` part on any platform."""
    path = PureWindowsPath(relative)

    return not path.anchor and ".." not in path.parts


def parse_files(raw: object, where: str) -> tuple[str, ...]:
    if not isinstance(raw, list) or not all(isinstance(item, str) and item for item in raw):
        raise SharedWordingError(f"{where} `files` must be a list of file paths")

    files = tuple(raw)
    outside = next((path for path in files if not is_inside_root(path)), None)

    if outside is not None:
        raise SharedWordingError(f"{where} `files` must name paths inside the root, not `{outside}`")

    if len(files) < MINIMUM_FILES or len(set(files)) != len(files):
        raise SharedWordingError(f"{where} `files` must name at least {MINIMUM_FILES} different files")

    return files


def parse_entry(raw: object, position: int) -> SharedWording:
    where = f"{MAP_PATH.as_posix()}: entry {position}"

    if not isinstance(raw, dict) or set(raw) != ENTRY_KEYS:
        raise SharedWordingError(f"{where} must be a mapping with exactly the keys {', '.join(sorted(ENTRY_KEYS))}")

    entry_id, text = raw["id"], raw["text"]

    if not isinstance(entry_id, str) or not entry_id:
        raise SharedWordingError(f"{where} `id` must be a non-empty string")

    if not isinstance(text, str) or not text.strip():
        raise SharedWordingError(f"{where} `text` must be a non-empty string")

    return SharedWording(entry_id, normalise_line_endings(text), parse_files(raw["files"], where))


def load_map(root: Path) -> list[SharedWording]:
    """Read and validate the map under `root`.

    Raises:
        SharedWordingError: the map is unreadable, not YAML, or not the documented shape.
    """
    shown_as = MAP_PATH.as_posix()

    try:
        document = yaml.safe_load(read_text(root / MAP_PATH, shown_as))
    except yaml.YAMLError as error:
        raise SharedWordingError(f"{shown_as} is not valid YAML: {error}") from error

    if not isinstance(document, dict) or set(document) != {"entries"}:
        raise SharedWordingError(f"{shown_as} must be a mapping with the single key `entries`")

    raw_entries = document["entries"]

    if not isinstance(raw_entries, list) or not raw_entries:
        raise SharedWordingError(f"{shown_as} `entries` must be a non-empty list")

    entries = [parse_entry(raw, position) for position, raw in enumerate(raw_entries, 1)]
    ids = [entry.entry_id for entry in entries]
    duplicates = sorted({entry_id for entry_id in ids if ids.count(entry_id) > 1})

    if duplicates:
        raise SharedWordingError(f"{shown_as} repeats the id {', '.join(duplicates)}")

    return entries


def holds_text(content: str, text: str) -> bool:
    """Tell whether `text` appears in `content` as whole lines, in order and together."""
    block = text if text.endswith("\n") else f"{text}\n"
    haystack = content if content.endswith("\n") else f"{content}\n"

    return f"\n{block}" in f"\n{haystack}"


def split_lines(text: str) -> list[str]:
    return text.removesuffix("\n").split("\n")


def matching_run(lines: list[str], start: int, canonical: list[str]) -> int:
    run = 0

    while run < len(canonical) and start + run < len(lines) and lines[start + run] == canonical[run]:
        run += 1

    return run


def drift_detail(content: str, text: str) -> str:
    """Name the first canonical line that differs where the copy matches the longest run of leading lines."""
    lines, canonical = split_lines(content), split_lines(text)
    start, run = max(
        ((start, matching_run(lines, start, canonical)) for start in range(len(lines))),
        key=lambda candidate: candidate[1],
    )
    expected = canonical[run]

    if run == 0:
        return f'it lacks the line "{expected}"'

    if start + run == len(lines):
        return f'the file ends after line {len(lines)} where the shared wording continues with "{expected}"'

    return f'line {start + run + 1} reads "{lines[start + run]}" where the shared wording has "{expected}"'


def find_drift(root: Path, entries: list[SharedWording]) -> list[str]:
    """Return one finding per listed file that does not hold its entry's text.

    Raises:
        SharedWordingError: a listed file cannot be read.
    """
    findings = []

    for entry in entries:
        for relative in entry.files:
            content = read_text(root / relative, f"{relative}, listed for `{entry.entry_id}` in {MAP_PATH.as_posix()}")

            if not holds_text(content, entry.text):
                findings.append(
                    f"{relative} does not hold the shared wording `{entry.entry_id}` from {MAP_PATH.as_posix()} "
                    "word for word. Change every copy listed for it, and its text in the map, together. "
                    f"First difference: {drift_detail(content, entry.text)}"
                )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    root: Path = args.root

    try:
        entries = load_map(root)
        findings = find_drift(root, entries)
    except SharedWordingError as error:
        print(error, file=sys.stderr)
        return 2

    for finding in findings:
        print(finding, file=sys.stderr)

    if findings:
        return 1

    print(f"Every shared wording in {MAP_PATH.as_posix()} matches in every file it lists.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
