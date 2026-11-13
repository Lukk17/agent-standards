#!/usr/bin/env python3
"""List the release tag of every plugin version in the marketplace that has no tag yet.

Each plugin in .claude-plugin/marketplace.json is tagged the way Claude Code
resolves a dependency's version range: "Tag each release as
`<plugin-name>--v<version>`", and for a plugin listed by a relative path the
tags go on "the marketplace repository, so the marketplace maintainer creates
the tags" (https://code.claude.com/docs/en/plugins/dependencies, "Tag plugin
releases for version resolution"). The Plugins workflow creates the tags this
prints on every push to master, so a version is tagged once, at the commit
that first shipped it.

Usage:
  python tools/plugin_tags.py              print every missing tag, one per line
  python tools/plugin_tags.py --all        print the tag of every plugin version
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
TAG_SEPARATOR = "--v"


def tag_names(document: dict) -> list[str]:
    """The tag of every plugin version the marketplace lists, in marketplace order."""
    return [f"{entry['name']}{TAG_SEPARATOR}{entry['version']}" for entry in document["plugins"]]


def missing(document: dict, existing: set[str]) -> list[str]:
    """The tags of the marketplace that are not among the existing ones."""
    return [tag for tag in tag_names(document) if tag not in existing]


def existing_tags(root: pathlib.Path) -> set[str]:
    listed = subprocess.run(
        ["git", "-C", str(root), "tag", "--list", f"*{TAG_SEPARATOR}*"], capture_output=True, text=True, check=True
    )
    return set(listed.stdout.split())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List plugin release tags that do not exist yet.")
    parser.add_argument("--all", action="store_true", help="list every plugin version's tag, existing or not")
    args = parser.parse_args(argv)
    document = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    tags = tag_names(document) if args.all else missing(document, existing_tags(ROOT))
    sys.stdout.write("".join(f"{tag}\n" for tag in tags))
    return 0


if __name__ == "__main__":
    sys.exit(main())
