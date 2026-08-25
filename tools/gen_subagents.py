#!/usr/bin/env python3
"""Generate per-tool subagent files from canonical subagents/*.md

Source of truth:  subagents/<name>.md             (this repo only; not shipped to consumers)
Generated:        .claude/agents/<name>.md        (Claude Code)
                  .agents/agents/<name>.md        (OpenCode format, shared)
                  .codex/agents/<name>.toml       (Codex CLI + IDE custom agents)
                  .github/agents/<name>.agent.md  (GitHub Copilot, VS Code + JetBrains + CLI)

Symlinked, not generated:
                  .opencode/agents -> ../.agents/agents
                  .kilo/agents     -> ../.agents/agents

OpenCode and Kilo Code share one format and both follow symlinks when scanning
agent directories, so a single tree serves both. Neither tool has a config key
naming an agent directory, which is why this is a symlink rather than a setting.
Codex reads TOML custom agents from .codex/agents/. GitHub Copilot needs its own
.agent.md format in .github/agents/ and cannot read either of the others.

Consumer repos pull only the generated trees plus skills — they never see the
canonical subagents/ source or this generator.

Usage:
  python tools/gen_subagents.py            # generate all targets
  python tools/gen_subagents.py --check    # exit 1 if any output is stale
"""
from __future__ import annotations

import os
import pathlib
import re
import shutil
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "subagents"

TARGETS = {
    "claude": (ROOT / ".claude" / "agents", ".md"),
    "agents": (ROOT / ".agents" / "agents", ".md"),
    "codex": (ROOT / ".codex" / "agents", ".toml"),
    "copilot": (ROOT / ".github" / "agents", ".agent.md"),
}

SYMLINKS = {
    ROOT / ".opencode" / "agents": "../.agents/agents",
    ROOT / ".kilo" / "agents": "../.agents/agents",
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
    model = fm.get("model", "sonnet")
    if model not in MODEL["claude"]:
        valid = ", ".join(sorted(MODEL["claude"]))
        sys.exit(f"ERROR {path}: unknown model {model!r}. Valid: {valid}")
    unknown_tools = [t for t in fm.get("tools", []) if t not in CLAUDE_TOOLS]
    if unknown_tools:
        valid = ", ".join(sorted(CLAUDE_TOOLS))
        sys.exit(
            f"ERROR {path}: unknown tool(s) {unknown_tools!r}. Valid: {valid}"
        )
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


def emit_copilot(fm: dict, body: str) -> str:
    lines = [
        "---",
        f"name: {fm['name']}",
        f"description: {fm['description'].strip()}",
        "---",
        "",
        body.rstrip() + skills_block(fm.get("skills")),
    ]
    return "\n".join(lines).rstrip() + "\n"


def _toml_basic(s: str) -> str:
    esc = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t").replace("\r", "")
    return f'"{esc}"'


def emit_codex(fm: dict, body: str) -> str:
    content = body.rstrip() + skills_block(fm.get("skills"))
    if "'''" in content:
        sys.exit(f"ERROR {fm['name']}: body contains ''' which breaks the Codex TOML literal string")
    lines = [
        f"name = {_toml_basic(fm['name'])}",
        f"description = {_toml_basic(fm['description'].strip())}",
        "developer_instructions = '''",
        content,
        "'''",
    ]
    return "\n".join(lines).rstrip() + "\n"


def render(tool: str, fm: dict, body: str) -> str:
    if tool == "claude":
        return emit_claude(fm, body)
    if tool == "codex":
        return emit_codex(fm, body)
    if tool == "copilot":
        return emit_copilot(fm, body)
    return emit_opencode(fm, body)


def ensure_symlinks(check: bool) -> list[str]:
    """Point the OpenCode and Kilo agent dirs at the shared tree."""
    problems: list[str] = []
    for link, target in SYMLINKS.items():
        if link.is_symlink():
            if os.readlink(link).replace(os.sep, "/") == target:
                continue
            problems.append(f"WRONG TARGET: {link.relative_to(ROOT)}")
            if not check:
                link.unlink()
            else:
                continue
        elif link.exists():
            problems.append(f"NOT A SYMLINK: {link.relative_to(ROOT)}")
            if not check:
                shutil.rmtree(link)
            else:
                continue
        else:
            problems.append(f"MISSING: {link.relative_to(ROOT)}")
        if not check:
            link.parent.mkdir(parents=True, exist_ok=True)
            try:
                link.symlink_to(target.replace("/", os.sep), target_is_directory=True)
            except OSError as exc:
                sys.exit(
                    f"ERROR cannot create symlink {link.relative_to(ROOT)} -> {target}: {exc}. "
                    "On Windows this needs Developer Mode or an elevated shell."
                )
    return problems


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

        for tool, (outdir, ext) in TARGETS.items():
            outdir.mkdir(parents=True, exist_ok=True)
            target = outdir / f"{fm['name']}{ext}"
            new = render(tool, fm, body).encode("utf-8")
            old = target.read_bytes() if target.exists() else None
            if old != new:
                stale_paths.append(target)
                if not check:
                    target.write_bytes(new)
                    written += 1

    orphans: list[pathlib.Path] = []
    for tool, (outdir, ext) in TARGETS.items():
        if not outdir.is_dir():
            continue
        for f in outdir.glob(f"*{ext}"):
            name = f.name[: -len(ext)]
            if name not in canonical_names:
                orphans.append(f)
                if not check:
                    f.unlink()

    link_problems = ensure_symlinks(check)

    if check:
        if stale_paths or orphans or link_problems:
            for msg in link_problems:
                print(f"SYMLINK {msg}")
            for p in stale_paths:
                print(f"STALE: {p.relative_to(ROOT)}")
            for p in orphans:
                print(f"ORPHAN: {p.relative_to(ROOT)}")
            sys.exit("STALE: run `python tools/gen_subagents.py` and commit")
        print(f"ok: {len(canonical_names)} agents x {len(TARGETS)} targets up to date")
        return

    if orphans:
        for p in orphans:
            print(f"removed orphan: {p.relative_to(ROOT)}")
    for msg in link_problems:
        print(f"symlink fixed: {msg}")
    print(
        f"done: {len(canonical_names)} agents -> {len(TARGETS)} targets "
        f"({written} written, {len(orphans)} orphans removed)"
    )


if __name__ == "__main__":
    main()
