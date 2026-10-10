#!/usr/bin/env python3
"""Guard that the agent instruction files stay small enough to be read whole.

Three rules, each over the files git tracks, so an ignored or untracked file never counts and a
tracked file already deleted from the working tree is treated as gone:

1. No file named CLAUDE.md exists anywhere. Any CLAUDE.md in the project switches off Claude
   Code's native AGENTS.md loading, so every other agent and Claude Code would read different
   instructions.
2. The root AGENTS.md, and the AGENTS.md.example template a project renames into one, each have
   fewer than ROOT_MAX_LINES lines and are under ROOT_MAX_BYTES bytes, the most Codex reads by
   default before it truncates silently.
3. Every other AGENTS.md has fewer than NESTED_MAX_LINES lines.

Exit codes: 0 every rule holds, 1 a rule is broken and the output names the file, the measured
value and the limit, 2 git could not list the files or a tracked file could not be read.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

ROOT_MAX_LINES = 200
ROOT_MAX_BYTES = 32768
NESTED_MAX_LINES = 60

AGENTS_FILE_NAME = "AGENTS.md"
TEMPLATE_FILE_NAME = "AGENTS.md.example"
FORBIDDEN_FILE_NAME = "CLAUDE.md"


def tracked_files(root: Path) -> list[str]:
    """Every path git tracks under root that still exists on disk, in POSIX form."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=root, capture_output=True, text=True, encoding="utf-8", check=False,
        )
    except OSError as error:
        print(f"could not run git in {root}: {error}", file=sys.stderr)
        raise SystemExit(2)
    if result.returncode != 0:
        print(f"git ls-files failed in {root}: {result.stderr.strip()}", file=sys.stderr)
        raise SystemExit(2)
    return sorted(entry for entry in result.stdout.split("\0") if entry and (root / entry).is_file())


def read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        print(f"could not read {path}: {error}", file=sys.stderr)
        raise SystemExit(2)


def line_count(content: bytes) -> int:
    """Lines as an editor numbers them, so a last line with no newline still counts."""
    return len(content.splitlines())


def check_no_claude_md(paths: list[str]) -> list[str]:
    return [
        f"{path} exists. Any {FORBIDDEN_FILE_NAME} in the project switches off Claude Code's native "
        f"{AGENTS_FILE_NAME} loading. Delete it and keep the instructions in {AGENTS_FILE_NAME}."
        for path in paths
        if Path(path).name.casefold() == FORBIDDEN_FILE_NAME.casefold()
    ]


def check_root_file(root: Path, name: str) -> list[str]:
    content = read_bytes(root / name)
    findings = []
    lines = line_count(content)
    if lines >= ROOT_MAX_LINES:
        findings.append(f"{name} has {lines} lines, the limit is fewer than {ROOT_MAX_LINES}.")
    if len(content) >= ROOT_MAX_BYTES:
        findings.append(
            f"{name} is {len(content)} bytes, the limit is under {ROOT_MAX_BYTES} bytes, "
            f"the most Codex reads by default."
        )
    return findings


def check_nested_agents_md(root: Path, paths: list[str]) -> list[str]:
    findings = []
    for path in paths:
        lines = line_count(read_bytes(root / path))
        if lines >= NESTED_MAX_LINES:
            findings.append(f"{path} has {lines} lines, the limit is fewer than {NESTED_MAX_LINES}.")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    root: Path = args.root

    paths = tracked_files(root)
    agents_files = [path for path in paths if Path(path).name == AGENTS_FILE_NAME]
    nested = [path for path in agents_files if path != AGENTS_FILE_NAME]

    findings = check_no_claude_md(paths)
    for name in (AGENTS_FILE_NAME, TEMPLATE_FILE_NAME):
        if name in paths:
            findings += check_root_file(root, name)
    findings += check_nested_agents_md(root, nested)

    for finding in findings:
        print(finding, file=sys.stderr)

    if findings:
        return 1

    print(f"No {FORBIDDEN_FILE_NAME} is tracked, and all {len(agents_files)} {AGENTS_FILE_NAME} files "
          f"are within their limits.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
