#!/usr/bin/env python3
"""Generate per-tool subagent files from canonical subagents/*.md

Source of truth:  subagents/<name>.md          (this repo only; not shipped to consumers)
Generated:        .claude/agents/<name>.md     (Claude Code)
                  .opencode/agents/<name>.md   (OpenCode + Kilo Code, shared)

Kilo Code reads .opencode/agents/*.md natively per its current docs, so there is
no separate .kilo/agents/ output.

Consumer repos pull only the generated trees plus skills — they never see the
canonical subagents/ source or this generator.

Usage:
  python tools/gen-subagents.py            # generate all targets
  python tools/gen-subagents.py --check    # exit 1 if any output is stale
"""
from __future__ import annotations

import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "subagents"

TARGETS = {
    "claude": ROOT / ".claude" / "agents",
    "opencode": ROOT / ".opencode" / "agents",
}

CLAUDE_TOOLS = {
    "read": "Read",
    "write": "Write",
    "edit": "Edit",
    "grep": "Grep",
    "glob": "Glob",
    "bash": "Bash",
    "webfetch": "WebFetch",
    "task": "Task",
}

MODEL = {
    "claude": {
        "opus": "opus",
        "sonnet": "sonnet",
        "haiku": "haiku",
        "inherit": "inherit",
    },
    "opencode": {
        "opus": "anthropic/claude-opus-4-7",
        "sonnet": "anthropic/claude-sonnet-4-6",
        "haiku": "anthropic/claude-haiku-4-5",
        "inherit": None,
    },
}


def parse(path: pathlib.Path) -> tuple[dict, str]:
    txt = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", txt, re.S)
    if not m:
        sys.exit(f"ERROR no frontmatter: {path}")
    fm = yaml.safe_load(m.group(1)) or {}
    for req in ("name", "description"):
        if req not in fm:
            sys.exit(f"ERROR {path} missing required field '{req}'")
    return fm, m.group(2).lstrip("\n")


def skills_block(skills: list[str] | None) -> str:
    if not skills:
        return ""
    items = "\n".join(f"- `{s}`" for s in skills)
    return (
        "\n\n## Preloaded skills\n\n"
        "Load and follow these skills from `.agents/skills/` before acting. "
        "They contain the reusable procedure and patterns; this prompt only "
        "defines persona and scope.\n\n"
        f"{items}\n"
    )


def emit_claude(fm: dict, body: str) -> str:
    lines = [
        "---",
        f"name: {fm['name']}",
        f"description: {fm['description'].strip()}",
    ]
    tools = [CLAUDE_TOOLS.get(t, t) for t in fm.get("tools", [])]
    if tools:
        lines.append("tools: " + ", ".join(tools))
    lines.append("model: " + MODEL["claude"][fm.get("model", "sonnet")])
    if fm.get("skills"):
        lines.append("skills:")
        lines += [f"  - {s}" for s in fm["skills"]]
    lines += ["---", "", body.rstrip() + skills_block(fm.get("skills"))]
    return "\n".join(lines).rstrip() + "\n"


def emit_opencode(fm: dict, body: str) -> str:
    lines = [
        "---",
        f"description: {fm['description'].strip()}",
        "mode: subagent",
    ]
    model_id = MODEL["opencode"][fm.get("model", "sonnet")]
    if model_id:
        lines.append(f"model: {model_id}")
    if fm.get("tools"):
        lines.append("tools:")
        lines += [f"  {t}: true" for t in fm["tools"]]
    if fm.get("permissions"):
        lines.append("permissions:")
        lines += [f"  {k}: {v}" for k, v in fm["permissions"].items()]
    lines += ["---", "", body.rstrip() + skills_block(fm.get("skills"))]
    return "\n".join(lines).rstrip() + "\n"


def render(tool: str, fm: dict, body: str) -> str:
    if tool == "claude":
        return emit_claude(fm, body)
    return emit_opencode(fm, body)


def main() -> None:
    check = "--check" in sys.argv
    if not SRC.is_dir():
        sys.exit(f"ERROR missing canonical source dir {SRC}")

    canonical_names: set[str] = set()
    stale_paths: list[pathlib.Path] = []
    written = 0

    for f in sorted(SRC.glob("*.md")):
        fm, body = parse(f)
        if fm["name"] in canonical_names:
            sys.exit(f"ERROR duplicate agent name: {fm['name']}")
        canonical_names.add(fm["name"])

        for tool, outdir in TARGETS.items():
            outdir.mkdir(parents=True, exist_ok=True)
            target = outdir / f"{fm['name']}.md"
            new = render(tool, fm, body)
            old = target.read_text(encoding="utf-8") if target.exists() else None
            if old != new:
                stale_paths.append(target)
                if not check:
                    target.write_text(new, encoding="utf-8")
                    written += 1

    orphans: list[pathlib.Path] = []
    for tool, outdir in TARGETS.items():
        if not outdir.is_dir():
            continue
        for f in outdir.glob("*.md"):
            if f.stem not in canonical_names:
                orphans.append(f)
                if not check:
                    f.unlink()

    if check:
        if stale_paths or orphans:
            for p in stale_paths:
                print(f"STALE: {p.relative_to(ROOT)}")
            for p in orphans:
                print(f"ORPHAN: {p.relative_to(ROOT)}")
            sys.exit("STALE: run `python tools/gen-subagents.py` and commit")
        print(f"ok: {len(canonical_names)} agents x {len(TARGETS)} targets up to date")
        return

    if orphans:
        for p in orphans:
            print(f"removed orphan: {p.relative_to(ROOT)}")
    print(
        f"done: {len(canonical_names)} agents -> {len(TARGETS)} targets "
        f"({written} written, {len(orphans)} orphans removed)"
    )


if __name__ == "__main__":
    main()
