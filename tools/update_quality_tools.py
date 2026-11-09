#!/usr/bin/env python3
"""Copy newer pinned commits of Robert C. Martin's crapper, dryer and mutator into .metrics/tools/.

His code is copied unchanged: every file git tracks at the chosen commit, byte for byte from the object store,
with its mode, and nothing else. The script reads each tool's repository from .metrics/tools/VERSIONS, takes the
commit, tag or branch named on the command line or else the upstream HEAD, resolves it to the full commit,
refuses a commit whose LICENSE is no longer the BSD Zero Clause License or that brings a CLAUDE.md, and only then
replaces the three folders and rewrites VERSIONS. Nothing changes when one tool fails. Every other file in
.metrics/tools, such as .gitattributes, README.md and the wrapper, belongs to agent-standards and is kept.

With verification on, the default, it then resolves the newest tree-sitter and tree-sitter-language-pack the three
tools install with into a scratch environment, pins them in constraints.txt, runs each tool's own test suite there,
and runs the CI check on the Python sample. Any failure exits 1, with the copies left in place for the reviewer.
One crapper test starts babashka (`bb`), so without `bb` on PATH expect that single failure and judge the rest.

This script is for agent-standards maintainers and never ships.

Usage:
  python tools/update_quality_tools.py                                  each tool at its upstream HEAD
  python tools/update_quality_tools.py --crapper <rev> --dryer <rev> --mutator <rev>
  python tools/update_quality_tools.py --no-verify                      copy and pin only

Exit codes: 0 updated and verified, 1 a verification step failed, 2 usage, git or licence error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import venv
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / ".metrics" / "tools"
TOOLS = ("crapper", "dryer", "mutator")
VERSIONS_NAME = "VERSIONS"
CONSTRAINTS_NAME = "constraints.txt"
RESOLVED_PACKAGES = ("tree-sitter", "tree-sitter-language-pack")
LICENSE_FIRST_LINE = "BSD Zero Clause License"
FORBIDDEN_NAMES = frozenset({"CLAUDE.md"})
COMMIT = re.compile(r"[0-9a-f]{40}")
# git's modes for an executable file and a symbolic link in a tree. Only regular files are vendored.
EXECUTABLE_MODE = "100755"
SYMLINK_MODE = "120000"
SAMPLE_CHECK = REPO_ROOT / "tools" / "tests" / "quality_samples" / "run_sample.py"


class UpdateError(Exception):
    """The update cannot go ahead, and nothing was changed."""


@dataclass(frozen=True, slots=True)
class Pin:
    tool: str
    url: str
    commit: str


def parse_versions(text: str) -> dict[str, Pin]:
    """VERSIONS holds one `<tool> <repository url> <40-character commit>` line per tool."""
    pins: dict[str, Pin] = {}
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 3 or fields[0] not in TOOLS or not COMMIT.fullmatch(fields[2]):
            raise UpdateError(f"{VERSIONS_NAME} line {number} is not '<tool> <url> <commit>': {line!r}")
        pins[fields[0]] = Pin(*fields)
    return pins


def render_versions(pins: Iterable[Pin]) -> str:
    return "".join(f"{pin.tool} {pin.url} {pin.commit}\n" for pin in pins)


def updated_constraints(text: str, resolved: dict[str, str]) -> str:
    """The constraints with each resolved package moved to its new version, every other line as it was."""
    lines = []
    for line in text.splitlines():
        name = line.split("==", 1)[0].strip()
        lines.append(f"{name}=={resolved[name]}" if "==" in line and name in resolved else line)
    return "\n".join(lines) + "\n"


def _git(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise UpdateError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def check_tree(tool: str, tree: Path) -> list[str]:
    """Reasons a copied tree must not be vendored."""
    problems = []
    license_file = tree / "LICENSE"
    first = license_file.read_text(encoding="utf-8").splitlines()[0] if license_file.is_file() else ""
    if first.strip() != LICENSE_FIRST_LINE:
        problems.append(f"{tool}: LICENSE is no longer the {LICENSE_FIRST_LINE}, review it before vendoring")
    problems += [f"{tool}: brings {path.relative_to(tree)}" for path in tree.rglob("*") if path.name in FORBIDDEN_NAMES]
    return problems


def clone(tool: str, url: str, scratch: Path) -> Path:
    repository = scratch / "clones" / tool
    _git("clone", "--quiet", "--no-checkout", url, str(repository))
    return repository


def resolve(repository: Path, revision: str) -> str:
    """The full commit a short commit, a tag, a branch or HEAD names, so VERSIONS always pins 40 characters."""
    return _git("-C", str(repository), "rev-parse", "--verify", "--end-of-options", f"{revision}^{{commit}}")


def _blob(repository: Path, blob: str) -> bytes:
    result = subprocess.run(["git", "-C", str(repository), "cat-file", "blob", blob], capture_output=True, check=False)
    if result.returncode != 0:
        raise UpdateError(f"git cat-file blob {blob} failed: {result.stderr.decode(errors='replace').strip()}")
    return result.stdout


def export(tool: str, repository: Path, commit: str, scratch: Path) -> Path:
    """Every file git tracks at the commit, as its stored bytes and mode, in a fresh folder. Raises UpdateError on
    a symbolic link or a submodule.

    The bytes come straight from the object store, so neither the tool's own .gitattributes (export-ignore,
    export-subst, eol) nor the local core.autocrlf can alter a file the way git archive or a checkout would.
    """
    tree = scratch / "trees" / tool
    tree.mkdir(parents=True)
    listing = subprocess.run(
        ["git", "-C", str(repository), "ls-tree", "-r", "-z", "--full-tree", commit], capture_output=True, check=False
    )
    if listing.returncode != 0:
        raise UpdateError(f"git ls-tree {commit} failed for {tool}")
    for entry in filter(None, listing.stdout.split(b"\0")):
        header, _, raw_path = entry.partition(b"\t")
        mode, kind, blob = header.decode("ascii").split()
        relative = os.fsdecode(raw_path)
        if kind != "blob" or mode == SYMLINK_MODE:
            # A plugin ships real files only, and a link could point outside the project.
            raise UpdateError(f"{tool}: {relative} is not a regular file, so it cannot be vendored")
        target = tree / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_blob(repository, blob))
        target.chmod(0o755 if mode == EXECUTABLE_MODE else 0o644)
    return tree


def replace_tools(tools_dir: Path, trees: dict[str, Path]) -> None:
    for tool, tree in trees.items():
        target = tools_dir / tool
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(tree, target, symlinks=True)


def _run(argv: Sequence[str], cwd: Path) -> int:
    print(f"+ {' '.join(argv)}", flush=True)
    return subprocess.run(list(argv), cwd=cwd, check=False).returncode


def run_suites(python: Path, tools_dir: Path, run=None) -> dict[str, bool]:
    """Each tool's own test suite, every one of them even after a failure, as tool to passed."""
    run = run or _run
    return {tool: run([str(python), "-m", "pytest", "-q", "-p", "no:cacheprovider"], tools_dir / tool) == 0 for tool in TOOLS}


def resolve_and_test(tools_dir: Path, scratch: Path) -> tuple[dict[str, str] | None, bool]:
    """Install the three tools unpinned into one scratch environment, read what resolved, and run their tests."""
    environment = scratch / "resolve"
    venv.create(environment, with_pip=True)
    python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    install = [str(python), "-m", "pip", "install", "--disable-pip-version-check", "--quiet"]
    editable = [part for tool in TOOLS for part in ("-e", str(tools_dir / tool))]
    if _run([*install, "pytest", *editable], tools_dir) != 0:
        return None, False
    listed = subprocess.run([str(python), "-m", "pip", "list", "--format=json"], capture_output=True, text=True, check=True)
    installed = {item["name"].lower(): item["version"] for item in json.loads(listed.stdout)}
    resolved = {name: installed[name] for name in RESOLVED_PACKAGES if name in installed}
    results = run_suites(python, tools_dir)
    failed = [tool for tool, passed in results.items() if not passed]
    if failed:
        print(f"Test suites that failed: {', '.join(failed)}. Read their output above.", file=sys.stderr)
    return resolved, not failed


def parser() -> argparse.ArgumentParser:
    commands = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands.add_argument("--tools-dir", type=Path, default=TOOLS_DIR, help="the .metrics/tools folder to update")
    for tool in TOOLS:
        commands.add_argument(f"--{tool}", metavar="REV", help=f"the {tool} commit, tag or branch, default its upstream HEAD")
    commands.add_argument("--no-verify", action="store_true", help="copy and pin only, without tests or constraints")
    return commands


def vendor(tools_dir: Path, wanted: dict[str, str | None], scratch: Path) -> list[Pin]:
    """Export and check all three tools, then replace them together. Raises UpdateError before any change."""
    current = parse_versions((tools_dir / VERSIONS_NAME).read_text(encoding="utf-8"))
    pins: list[Pin] = []
    trees: dict[str, Path] = {}
    for tool in TOOLS:
        repository = clone(tool, current[tool].url, scratch)
        pin = Pin(tool, current[tool].url, resolve(repository, wanted.get(tool) or "HEAD"))
        trees[tool] = export(tool, repository, pin.commit, scratch)
        pins.append(pin)
    problems = [problem for tool, tree in trees.items() for problem in check_tree(tool, tree)]
    if problems:
        raise UpdateError("\n  ".join(["a tool cannot be vendored:", *problems]))
    replace_tools(tools_dir, trees)
    (tools_dir / VERSIONS_NAME).write_text(render_versions(pins), encoding="utf-8")
    return pins


def verify(tools_dir: Path, scratch: Path) -> bool:
    resolved, tests_pass = resolve_and_test(tools_dir, scratch)
    if resolved is None:
        print("The tools did not install into a scratch environment.", file=sys.stderr)
        return False
    constraints = tools_dir / CONSTRAINTS_NAME
    constraints.write_text(updated_constraints(constraints.read_text(encoding="utf-8"), resolved), encoding="utf-8")
    print(f"Pinned {', '.join(f'{name}=={version}' for name, version in sorted(resolved.items()))}")
    sample_passes = _run([sys.executable, str(SAMPLE_CHECK), "python"], REPO_ROOT) == 0
    return tests_pass and sample_passes


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    tools_dir: Path = arguments.tools_dir.resolve()
    wanted = {tool: getattr(arguments, tool) for tool in TOOLS}
    with tempfile.TemporaryDirectory(prefix="quality-tools-") as temporary:
        scratch = Path(temporary)
        try:
            pins = vendor(tools_dir, wanted, scratch)
        except UpdateError as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 2
        for pin in pins:
            print(f"{pin.tool} {pin.commit}")
        if arguments.no_verify:
            return 0
        return 0 if verify(tools_dir, scratch) else 1


if __name__ == "__main__":
    sys.exit(main())
