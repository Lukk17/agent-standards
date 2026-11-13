#!/usr/bin/env python3
"""Fail when a marketplace plugin changed since the merge base and its version did not go up.

Every skill, subagent, hook, server and bundle in .claude-plugin/marketplace.json
is its own plugin, and Claude Code keeps a user on the cached copy of a plugin
until its version string changes
(https://code.claude.com/docs/en/plugins/loading, "How Claude Code computes the
version"). So a change that keeps the version never reaches anyone who already
installed the plugin.

This check reads the plugin catalog of the merge base of HEAD and the base
branch from that commit's own .claude-plugin/marketplace.json, renders the
catalog of the tracked files of the working tree with tools/gen_plugins.py,
and compares each plugin present in both:

- what it ships changed and its version is not strictly higher: fail;
- its version went down: fail;
- anything else, including a plugin the base does not have: pass.

The base is read rather than rendered, so a rule the head adds to the plugin
map never makes an older base unreadable. A base that commits no marketplace,
the one before this check existed, counts every plugin as new. Any other base
that cannot be read is an error.

What a plugin ships is its marketplace entry without the version, plus every
file under the paths gen_plugins.owned_paths names for it, read through any
symlink that stays inside the repository, the way Claude Code copies it.

Usage:
  python tools/check_versions.py                   compare against the merge base with origin/master
  python tools/check_versions.py --base <ref>      compare against the merge base with <ref>

Exit codes: 0 every changed plugin raised its version, 1 one or more did not,
2 the base or the working tree could not be read.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass

import gen_plugins

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_BASE = "origin/master"
# Local leftovers that are never part of a plugin, even in a tracked folder's working copy.
IGNORED_NAMES = frozenset({"__pycache__", ".DS_Store", ".venv"})
IGNORED_SUFFIXES = (".pyc", ".egg-info")


class VersionCheckError(Exception):
    """The base or the working tree could not be read."""


@dataclass(frozen=True, slots=True)
class Shipped:
    """One plugin as the check compares it: its version and a digest of everything it ships."""

    version: str
    digest: str


def version_key(version: str) -> tuple[int, int, int]:
    """MAJOR.MINOR.PATCH as numbers, so 1.10.0 sorts above 1.9.0."""
    major, minor, patch = (int(part) for part in version.split("."))
    return major, minor, patch


def git(root: pathlib.Path, *args: str) -> bytes:
    try:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = exc.stderr.decode(errors="replace").strip() if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        raise VersionCheckError(f"git {' '.join(args)} failed: {detail}") from exc


def merge_base(root: pathlib.Path, base: str) -> str:
    return git(root, "merge-base", "HEAD", base).decode().strip()


def extract_commit(root: pathlib.Path, commit: str, target: pathlib.Path) -> None:
    """The committed tree of one commit, symlinks included, written under target."""
    archive = git(root, "archive", "--format=tar", commit)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(target, filter="tar")


GITLINK_MODE = "160000"


def copy_tracked(root: pathlib.Path, target: pathlib.Path) -> None:
    """Every tracked file of the working tree, as it is on disk now, written under target.

    A submodule, which git tracks as a gitlink and not as files, is left out.
    """
    for record in git(root, "ls-files", "-z", "--cached", "--stage").decode().split("\0"):
        mode, name = record.partition(" ")[0], record.partition("\t")[2]
        source = root / name
        if not name or mode == GITLINK_MODE or not os.path.lexists(source):
            continue
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_symlink():
            destination.symlink_to(os.readlink(source))
        else:
            destination.write_bytes(source.read_bytes())
            destination.chmod(source.stat().st_mode & 0o777)


def _ignored(relative: pathlib.Path) -> bool:
    return any(part in IGNORED_NAMES or part.endswith(IGNORED_SUFFIXES) for part in relative.parts)


def shipped_files(root: pathlib.Path, path: pathlib.PurePosixPath) -> Iterator[tuple[str, pathlib.Path]]:
    """Every file under one owned path, by its path relative to root, read through links that stay in root."""
    start = root / path
    if start.is_file():
        yield path.as_posix(), start
        return
    resolved_root = root.resolve()
    visited: set[pathlib.Path] = set()
    for directory, folders, files in os.walk(start, followlinks=True):
        current = pathlib.Path(directory)
        real = current.resolve()
        if real in visited:
            folders[:] = []
            continue
        visited.add(real)
        folders[:] = sorted(
            f for f in folders
            if f not in IGNORED_NAMES
            and (current / f).resolve().is_relative_to(resolved_root)
            and (current / f).resolve() not in visited
        )
        for name in sorted(files):
            file = current / name
            relative = file.relative_to(root)
            if not _ignored(relative) and file.resolve().is_relative_to(resolved_root):
                yield relative.as_posix(), file


def digest(root: pathlib.Path, entry: dict[str, object]) -> str:
    """A digest of what one plugin ships: its entry without the version, and its files."""
    hasher = hashlib.sha256()
    described = {key: value for key, value in entry.items() if key != "version"}
    hasher.update(json.dumps(described, sort_keys=True).encode("utf-8"))
    for path in gen_plugins.owned_paths(entry):
        for relative, file in shipped_files(root, path):
            executable = b"x" if os.access(file, os.X_OK) else b"-"
            for part in (relative.encode("utf-8"), executable, file.read_bytes()):
                hasher.update(len(part).to_bytes(8, "big"))
                hasher.update(part)
    return hasher.hexdigest()


def shipped(root: pathlib.Path, document: dict) -> dict[str, Shipped]:
    """Every plugin of a marketplace document, by name, with what it ships under root."""
    return {str(entry["name"]): Shipped(str(entry["version"]), digest(root, entry)) for entry in document["plugins"]}


def catalog(root: pathlib.Path) -> dict[str, Shipped]:
    """Every plugin of the marketplace rendered from root, by name.

    Raises:
        gen_plugins.PluginMapError: root holds no renderable plugin map.
    """
    try:
        document = gen_plugins.marketplace(gen_plugins.load_sources(root))
    except SystemExit as exc:
        raise gen_plugins.PluginMapError(str(exc)) from exc
    return shipped(root, document)


def committed_catalog(root: pathlib.Path) -> dict[str, Shipped] | None:
    """Every plugin of the marketplace root commits, or None when it commits none.

    Raises:
        VersionCheckError: the committed marketplace cannot be read.
    """
    path = root / gen_plugins.MARKETPLACE_FILE
    if not path.is_file():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        return shipped(root, document)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise VersionCheckError(f"cannot read the base's {gen_plugins.MARKETPLACE_FILE}: {exc}") from exc


def problems(base: dict[str, Shipped], head: dict[str, Shipped]) -> list[str]:
    """Every plugin whose version does not account for its change, with the reason."""
    found = []
    for name, now in sorted(head.items()):
        before = base.get(name)
        if before is None:
            continue
        if version_key(now.version) < version_key(before.version):
            found.append(f"{name}: version {now.version} is lower than {before.version} on the base")
        elif now.digest != before.digest and version_key(now.version) <= version_key(before.version):
            found.append(f"{name}: changed since the base but still at {now.version}, raise it (patch for a fix, minor for new behaviour, major for a breaking change)")
    return found


def compare(root: pathlib.Path, base_ref: str) -> tuple[str, dict[str, Shipped], dict[str, Shipped], str]:
    """The merge base, both catalogs, and a note when the base has none.

    Raises:
        VersionCheckError: git cannot find the merge base or read a tree.
        gen_plugins.PluginMapError: the working tree's plugin map cannot be rendered.
    """
    commit = merge_base(root, base_ref)
    note = ""
    with tempfile.TemporaryDirectory(prefix="check-versions-") as scratch:
        base_root, head_root = pathlib.Path(scratch, "base"), pathlib.Path(scratch, "head")
        extract_commit(root, commit, base_root)
        copy_tracked(root, head_root)
        head = catalog(head_root)
        base = committed_catalog(base_root)
        if base is None:
            base = {}
            note = f"the base {commit[:12]} has no committed {gen_plugins.MARKETPLACE_FILE}, so every plugin counts as new"
    return commit, base, head, note


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail when a changed plugin kept its version.")
    parser.add_argument("--base", default=DEFAULT_BASE, help=f"the branch to compare against, default {DEFAULT_BASE}")
    args = parser.parse_args(argv)
    try:
        commit, base, head, note = compare(ROOT, args.base)
    except (VersionCheckError, gen_plugins.PluginMapError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
    if note:
        print(f"note: {note}")
    found = problems(base, head)
    for problem in found:
        print(f"::error::{problem}")
    changed = sum(1 for name, now in head.items() if name in base and now.digest != base[name].digest)
    added = sum(1 for name in head if name not in base)
    print(f"Checked {len(head)} plugins against {commit[:12]}: {changed} changed, {added} new. Violations: {len(found)}.")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
