#!/usr/bin/env python3
"""Check every plugin release tag against the marketplace on master. Never writes anything.

The Plugins workflow tags each plugin version `<name>--v<version>` at the
master commit that first ships it, and Claude Code resolves a dependency's
version range against those tags
(https://code.claude.com/docs/en/plugins/dependencies, "Tag plugin releases
for version resolution"). A tag that moved, or one that was deleted, would
make it install something master never shipped, so this check fails on:

- a tag that is not `<name>--v<version>`;
- a tag whose commit is not on master;
- a tag whose commit's committed .claude-plugin/marketplace.json does not list
  plugin `<name>` at exactly `<version>`;
- a missing tag: a version master's marketplace held at or after the oldest
  tagged commit, for a plugin master still lists at that version or a higher
  one, that has no tag. Versions master moved past before the first tag was
  ever pushed were never tagged and are not asked for.

A GitHub tag ruleset on `*--v*` that lets only GitHub Actions create a tag and
nobody update or delete one is the prevention. The Plugin tags workflow runs
this check on every tag push, every tag deletion and once a day, as the
detection.

Usage:
  python tools/check_tags.py                      check against origin/master
  python tools/check_tags.py --master <ref>       check against another master ref

Exit codes: 0 every tag matches, 1 one or more do not, 2 git cannot be read.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass

from plugin_model import KEBAB, MARKETPLACE_FILE, SEMVER

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_MASTER = "origin/master"
TAG_SEPARATOR = "--v"
TAG_PATTERN = re.compile(rf"({KEBAB.pattern}){re.escape(TAG_SEPARATOR)}({SEMVER.pattern})", re.ASCII)


class TagCheckError(Exception):
    """git could not be read."""


@dataclass(frozen=True, slots=True)
class Tag:
    name: str
    commit: str


def git(root: pathlib.Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=check)
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        raise TagCheckError(f"git {' '.join(args)} failed: {detail}") from exc


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def plugin_tags(root: pathlib.Path) -> list[Tag]:
    """Every tag holding the separator, with the commit it points at."""
    listed = git(root, "for-each-ref", "--format=%(refname:strip=2)", f"refs/tags/*{TAG_SEPARATOR}*").stdout.split()
    return [Tag(name, git(root, "rev-parse", "--verify", "--end-of-options", f"refs/tags/{name}^{{commit}}").stdout.strip()) for name in listed]


def listed_versions(root: pathlib.Path, commit: str) -> dict[str, str]:
    """Plugin name to version in the marketplace a commit commits, empty when it commits none."""
    shown = git(root, "show", f"{commit}:{MARKETPLACE_FILE}", check=False)
    if shown.returncode != 0:
        return {}
    try:
        return {str(entry["name"]): str(entry["version"]) for entry in json.loads(shown.stdout)["plugins"]}
    except (ValueError, KeyError, TypeError) as exc:
        raise TagCheckError(f"the marketplace at {commit[:12]} cannot be read: {exc}") from exc


def on_master(root: pathlib.Path, commit: str, master: str) -> bool:
    return git(root, "merge-base", "--is-ancestor", commit, master, check=False).returncode == 0


def tag_problems(root: pathlib.Path, tags: list[Tag], master: str) -> list[str]:
    """Every tag that does not name a version master shipped at its commit."""
    problems = []
    for tag in tags:
        match = TAG_PATTERN.fullmatch(tag.name)
        if not match:
            problems.append(f"tag {tag.name}: not <name>--v<version>")
        elif not on_master(root, tag.commit, master):
            problems.append(f"tag {tag.name}: points at {tag.commit[:12]}, which is not on {master}")
        elif (listed := listed_versions(root, tag.commit).get(match.group(1))) != match.group(2):
            shown = f"lists {match.group(1)} at {listed}" if listed else f"does not list {match.group(1)}"
            problems.append(f"tag {tag.name}: the marketplace at {tag.commit[:12]} {shown}")
    return problems


def shipped_since(root: pathlib.Path, oldest: str, master: str) -> set[tuple[str, str]]:
    """Every plugin version master's marketplace held at the oldest tagged commit or after it."""
    changed = git(root, "rev-list", "--ancestry-path", f"{oldest}..{master}", "--", str(MARKETPLACE_FILE)).stdout.split()
    return {pair for commit in [oldest, *changed] for pair in listed_versions(root, commit).items()}


def missing_problems(root: pathlib.Path, tags: list[Tag], master: str) -> list[str]:
    """Every version that should have kept its tag and has none."""
    tagged = [tag for tag in tags if TAG_PATTERN.fullmatch(tag.name) and on_master(root, tag.commit, master)]
    if not tagged:
        return []
    tagged_commits = {tag.commit for tag in tagged}
    history = git(root, "rev-list", "--topo-order", "--reverse", master).stdout.split()
    oldest = next(commit for commit in history if commit in tagged_commits)
    current = listed_versions(root, master)
    names = {tag.name for tag in tags}
    problems = []
    for name, version in sorted(shipped_since(root, oldest, master)):
        if name in current and version_key(version) <= version_key(current[name]):
            expected = f"{name}{TAG_SEPARATOR}{version}"
            if expected not in names:
                problems.append(f"tag {expected}: missing, though {master} shipped {name} {version} after the first tag and lists it at {current[name]}")
    return problems


def check(root: pathlib.Path, master: str) -> list[str]:
    tags = plugin_tags(root)
    return tag_problems(root, tags, master) + missing_problems(root, tags, master)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check every plugin release tag against the marketplace on master.")
    parser.add_argument("--master", default=DEFAULT_MASTER, help=f"the master ref, default {DEFAULT_MASTER}")
    args = parser.parse_args(argv)
    try:
        git(ROOT, "rev-parse", "--verify", f"{args.master}^{{commit}}")
        problems = check(ROOT, args.master)
        count = len(plugin_tags(ROOT))
    except TagCheckError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
    for problem in problems:
        print(f"::error::{problem}")
    print(f"Checked {count} plugin tags against {args.master}. Violations: {len(problems)}.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
