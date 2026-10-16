#!/usr/bin/env python3
"""Links every shared skill into the agents that write into their own skills folder.

The global install in docs/GLOBAL_SETUP.md keeps the skills in
~/.config/agents/skills. Two agents cannot be pointed at that folder with one
directory link, because each writes into its own skills folder as well: Claude
Code puts the skills it syncs from claude.ai in ~/.claude/skills/synced/, and
Codex puts its bundled skills in $CODEX_HOME/skills/.system/. Through a
whole-directory link either lands in the shared tree that every other agent
scans. So both folders stay real directories holding one link per shared
skill, and this script keeps that set current in each:

- ~/.claude/skills, when ~/.claude exists;
- $CODEX_HOME/skills, or ~/.config/codex/skills when CODEX_HOME is unset,
  when that Codex home exists.

Claude Code runs it on SessionStart for startup and resume, and both global
updaters run it after an update. In each folder it:

1. links every folder in the source that holds a SKILL.md and has no entry of
   that name yet;
2. removes a link that points into the source at a folder with no SKILL.md any
   more, which is what an upstream rename or a deleted skill leaves behind.

It never touches `synced`, `.trash`, a dot entry such as `.system`, a real
directory, or a link that points anywhere but the source. A folder that is
itself a link, which is the layout before the migration, is left alone.

On Windows it does nothing. Creating per-skill junctions there was never
tested, so the guide keeps the Windows install on directory junctions.

It lives in a subdirectory of .agents/hooks/ so the OpenCode and Kilo Code
runner, which discovers only the files directly in that directory, never runs
it on a tool call. Every outcome, an error included, exits 0, and the report
goes to stderr, because Claude Code adds a SessionStart hook's stdout to the
model's context.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional

SOURCE = (".config", "agents", "skills")
CLAUDE_HOME = (".claude",)
DEFAULT_CODEX_HOME = (".config", "codex")
SKILLS = "skills"
SKILL_FILE = "SKILL.md"
RESERVED = frozenset({"synced", ".trash"})


def _is_reserved(name: str) -> bool:
    return name.lower() in RESERVED or name.startswith(".")


def _is_link(path: Path) -> bool:
    return path.is_symlink() or bool(getattr(os.path, "isjunction", lambda _path: False)(path))


def _link_target(link: Path) -> Path:
    """The path the link names, joined lexically, without following it."""
    return Path(os.path.normpath(os.path.join(link.parent, os.readlink(link))))


def _inside(candidate: Path, source: Path) -> bool:
    try:
        return candidate.parent == source or candidate.parent.resolve() == source.resolve()
    except OSError:
        return False


def _codex_home(home: Path) -> Path:
    configured: Optional[str] = os.environ.get("CODEX_HOME")

    if configured and os.path.isabs(configured):
        return Path(configured)

    return home.joinpath(*DEFAULT_CODEX_HOME)


def targets(home: Path) -> List[Path]:
    """Every skills folder to keep in step, one per agent home that exists."""
    return [agent_home / SKILLS for agent_home in (home.joinpath(*CLAUDE_HOME), _codex_home(home)) if agent_home.is_dir()]


def sync_one(source: Path, target: Path) -> List[str]:
    if _is_link(target):
        return []

    target.mkdir(exist_ok=True)
    changes: List[str] = []

    for skill in sorted(source.iterdir()):
        if _is_reserved(skill.name) or not (skill / SKILL_FILE).is_file():
            continue

        link = target / skill.name

        if _is_link(link) or link.exists():
            continue

        link.symlink_to(os.path.relpath(skill, target), target_is_directory=True)
        changes.append("linked " + skill.name)

    for link in sorted(target.iterdir()):
        if _is_reserved(link.name) or not link.is_symlink():
            continue

        pointed = _link_target(link)

        if _inside(pointed, source) and not (pointed / SKILL_FILE).is_file():
            link.unlink()
            changes.append("unlinked " + link.name)

    return changes


def main() -> int:
    try:
        home = Path.home()
        source = home.joinpath(*SOURCE)

        if sys.platform == "win32" or not source.is_dir():
            return 0

        for target in targets(home):
            try:
                changes = sync_one(source, target)
            except OSError as error:
                print("skill links: " + str(target) + " skipped (" + str(error) + ")", file=sys.stderr)
                continue

            if changes:
                print("skill links: " + str(target) + ": " + ", ".join(changes), file=sys.stderr)
    except Exception as error:  # a broken sync must never break a session
        print("skill links: skipped (" + str(error) + ")", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
