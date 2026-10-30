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

import json
import os
import pathlib
import re
import shutil
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "subagents"
SKILLS = ROOT / ".agents" / "skills"

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
    "websearch": "WebSearch",
    # Claude Code renamed the spawning tool from Task to Agent in 2.1.63, and
    # keeps Task only as an alias (https://code.claude.com/docs/en/sub-agents).
    "task": "Agent",
}

COPILOT_TOOLS = {
    "read": ("read",),
    "grep": ("search",),
    "glob": ("search",),
    "write": ("create", "apply_patch"),
    "edit": ("edit", "apply_patch"),
    "bash": ("bash", "powershell"),
    # Copilot's `web` alias covers both: "`web` | `WebSearch`, `WebFetch` |
    # Allows fetching content from URLs and performing a web search"
    # (https://docs.github.com/en/copilot/reference/custom-agents-configuration).
    "webfetch": ("web",),
    "websearch": ("web",),
}

READ_ONLY_TOOLS = frozenset({"read", "grep", "glob"})

# A canonical `readonly: true` keeps bash but limits it to these commands, plus
# any the definition adds under `readonly-commands`. Every target gets the list
# as a READ_ONLY_HEADING body section, which the preflight gate's Rule E reads
# and enforces on every format whose hook names the subagent. OpenCode and Kilo
# Code also enforce it natively through the bash permission map below.
READ_ONLY_COMMANDS = ("git diff*", "git log*", "git show*", "git status*")
READ_ONLY_HEADING = "Read-only shell"
READ_ONLY_FORBIDDEN_TOOLS = frozenset({"write", "edit", "task"})

# OpenCode and Kilo Code read `tools` as overrides on top of everything the
# agent already has, so a map listing only read, grep and glob still leaves
# edit and bash on. Each write-capable permission is therefore denied outright
# unless one of the canonical tools that grants it is listed.
OPENCODE_WRITE_PERMISSIONS = {
    "edit": ("write", "edit"),
    "bash": ("bash",),
}

# Plan mode is a native layer only. Claude Code ignores a subagent's
# permissionMode while the main conversation is in auto, acceptEdits or
# bypassPermissions mode (https://code.claude.com/docs/en/sub-agents, "Permission
# modes"), and a `touch` from a plan-mode subagent ran under an auto-mode session
# on Claude Code 2.1.314. Rule E in the preflight gate is what enforces a
# read-only agent there.
CLAUDE_READ_ONLY_PERMISSION_MODE = "plan"

# Subagents never pin a model, and every target omits the key. Each agent then
# falls back to the user's configured subagent default, else the session model:
# Claude Code reads CLAUDE_CODE_SUBAGENT_MODEL, then the main conversation's model
# (https://code.claude.com/docs/en/sub-agents, "Choose a model"), and Codex reads
# agents.default_subagent_model, then the parent's model.


def installed_skills() -> set[str]:
    """Every skill name that has a folder under .agents/skills/."""
    if not SKILLS.is_dir():
        sys.exit(f"ERROR missing skills dir {SKILLS}")
    return {p.name for p in SKILLS.iterdir() if p.is_dir()}


def parse(path: pathlib.Path, skills: set[str] | None = None) -> tuple[dict, str]:
    txt = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", txt, re.S)
    if not m:
        sys.exit(f"ERROR no frontmatter: {path}")
    fm = yaml.safe_load(m.group(1)) or {}
    for req in ("name", "description"):
        if req not in fm:
            sys.exit(f"ERROR {path} missing required field '{req}'")
    if "model" in fm:
        sys.exit(
            f"ERROR {path}: remove the 'model' key. Subagents never pin a model, "
            "so every agent runs on the user's session model."
        )
    unknown_tools = [t for t in fm.get("tools", []) if t not in CLAUDE_TOOLS]
    if unknown_tools:
        valid = ", ".join(sorted(CLAUDE_TOOLS))
        sys.exit(
            f"ERROR {path}: unknown tool(s) {unknown_tools!r}. Valid: {valid}"
        )
    validate_read_only(path, fm)
    declared = fm.get("skills")
    if declared is not None and not isinstance(declared, list):
        sys.exit(
            f"ERROR {path}: 'skills' must be a list of skill names, got "
            f"{type(declared).__name__}. Write 'skills:' followed by one '- name' per line."
        )
    known = installed_skills() if skills is None else skills
    dangling = [s for s in declared or [] if s not in known]
    if dangling:
        sys.exit(
            f"ERROR {path}: skill(s) with no folder under {SKILLS.name}/: "
            f"{', '.join(dangling)}"
        )
    return fm, m.group(2).lstrip("\n")


def validate_read_only(path: pathlib.Path, fm: dict) -> None:
    """Reject a `readonly` marker the generator could not honour on every target."""
    readonly = fm.get("readonly", False)
    extra = fm.get("readonly-commands")
    if not isinstance(readonly, bool):
        sys.exit(f"ERROR {path}: 'readonly' must be true or false, got {readonly!r}")
    if extra is not None and not readonly:
        sys.exit(f"ERROR {path}: 'readonly-commands' needs 'readonly: true'")
    if extra is not None and not (isinstance(extra, list) and all(isinstance(c, str) and c.strip() for c in extra)):
        sys.exit(f"ERROR {path}: 'readonly-commands' must be a list of command patterns")
    granted = READ_ONLY_FORBIDDEN_TOOLS.intersection(fm.get("tools") or [])
    if readonly and granted:
        sys.exit(f"ERROR {path}: a readonly agent may not list {', '.join(sorted(granted))}")
    if readonly and "bash" not in (fm.get("tools") or []):
        sys.exit(f"ERROR {path}: 'readonly: true' limits bash, so list bash or drop the marker")


def read_only_commands(fm: dict) -> list[str]:
    """The shell commands a read-only agent may run, or an empty list when it is not read-only."""
    if not fm.get("readonly"):
        return []
    return [*READ_ONLY_COMMANDS, *(fm.get("readonly-commands") or [])]


def read_only_block(fm: dict, shell: bool = True) -> str:
    """The body section the gate's Rule E reads, worded for a target with or without a shell."""
    commands = read_only_commands(fm)
    if not commands:
        return ""
    items = "\n".join(f"- `{c}`" for c in commands)
    if not shell:
        return (
            f"\n\n### {READ_ONLY_HEADING}\n\n"
            "This agent is read-only and gets no shell on this agent, because nothing here "
            "could hold the shell to the read-only commands below. Work from the diff and "
            "context the caller supplies and the files you can read. Elsewhere it runs only:\n\n"
            f"{items}\n"
        )
    return (
        f"\n\n### {READ_ONLY_HEADING}\n\n"
        "This agent is read-only. Edit no file, and run only these shell commands, from "
        "the project root, with no redirect to a file and no pipe into another program. "
        "Return any other command to the caller as a proposal. The preflight gate denies "
        "everything else.\n\n"
        f"{items}\n"
    )


def _yaml_double_quoted(value: str) -> str:
    """A YAML double-quoted scalar, safe for a value holding a colon or a quote.

    json.dumps emits exactly the double-quoted form YAML 1.2 defines, escapes
    included, so a description is never re-read as a mapping by a strict parser.
    """
    return json.dumps(value)


def skills_block(skills: list[str] | None) -> str:
    if not skills:
        return ""
    items = "\n".join(f"- `{s}`" for s in skills)
    return (
        "\n\n### Preloaded skills\n\n"
        "Load and follow these skills before acting. Load a skill by name, or read "
        "`<name>/SKILL.md` from the skills folder this agent was installed with: "
        "`.agents/skills/` in a project, the global skills folder otherwise. A skill "
        "this prompt names to load on demand is found the same way. The skills "
        "contain the reusable procedure and patterns, and this prompt only defines "
        "persona and scope.\n\n"
        f"{items}\n"
    )


def body_with_blocks(fm: dict, body: str, shell: bool = True) -> str:
    """The prompt body with the read-only section and the skills section appended."""
    return body.rstrip() + read_only_block(fm, shell) + skills_block(fm.get("skills"))


def emit_claude(fm: dict, body: str) -> str:
    lines = [
        "---",
        f"name: {fm['name']}",
        f"description: {_yaml_double_quoted(fm['description'].strip())}",
    ]
    tools = [CLAUDE_TOOLS.get(t, t) for t in fm.get("tools", [])]
    if tools:
        lines.append("tools: " + ", ".join(tools))
    if set(fm.get("tools") or []) == READ_ONLY_TOOLS or fm.get("readonly"):
        lines.append("permissionMode: " + CLAUDE_READ_ONLY_PERMISSION_MODE)
    if fm.get("skills"):
        lines.append("skills:")
        lines += [f"  - {s}" for s in fm["skills"]]
    lines += ["---", "", body_with_blocks(fm, body)]
    return "\n".join(lines).rstrip() + "\n"


def emit_opencode(fm: dict, body: str) -> str:
    lines = [
        "---",
        f"description: {_yaml_double_quoted(fm['description'].strip())}",
        "mode: subagent",
    ]
    if fm.get("tools"):
        denied = opencode_denied_permissions(fm["tools"])
        commands = read_only_commands(fm)
        if denied or commands:
            lines.append("permission:")
            lines += [f"  {permission}: deny" for permission in denied]
        if commands:
            # OpenCode evaluates "with the last matching rule winning", so the
            # catch-all deny goes first (https://opencode.ai/docs/permissions/).
            lines.append("  bash:")
            lines.append('    "*": deny')
            lines += [f"    {_yaml_double_quoted(c)}: allow" for c in commands]
        lines.append("tools:")
        lines += [f"  {t}: true" for t in fm["tools"]]
    lines += ["---", "", body_with_blocks(fm, body)]
    return "\n".join(lines).rstrip() + "\n"


def opencode_denied_permissions(tools: list[str]) -> list[str]:
    """Every write-capable OpenCode permission that none of the listed tools grants."""
    return [
        permission
        for permission, granting in OPENCODE_WRITE_PERMISSIONS.items()
        if not any(tool in tools for tool in granting)
    ]


def copilot_tools(tools: list[str]) -> list[str]:
    """Map canonical tool names onto Copilot's own names, in order, deduped.

    A canonical tool with no entry in COPILOT_TOOLS is dropped from the output,
    so an agent whose whole list maps to nothing comes back empty. The caller
    still writes the key in that case: no key at all means Copilot grants the
    full tool set, which is the opposite of what the definition asked for.
    """
    mapped: list[str] = []
    for tool in tools:
        for name in COPILOT_TOOLS.get(tool, ()):
            if name not in mapped:
                mapped.append(name)
    return mapped


def emit_copilot(fm: dict, body: str) -> str:
    lines = [
        "---",
        f"name: {fm['name']}",
        f"description: {_yaml_double_quoted(fm['description'].strip())}",
    ]
    canonical = fm.get("tools") or []
    if fm.get("readonly"):
        # Copilot grants `bash` whole and its preToolUse payload names no agent,
        # so nothing could hold a read-only agent to its command list there.
        canonical = [t for t in canonical if t != "bash"]
    tools = copilot_tools(canonical)
    if canonical:
        lines.append("tools: [" + ", ".join(f'"{t}"' for t in tools) + "]")
    lines += [
        "---",
        "",
        body_with_blocks(fm, body, shell=not fm.get("readonly")),
    ]
    return "\n".join(lines).rstrip() + "\n"


def _toml_basic(s: str) -> str:
    esc = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t").replace("\r", "")
    return f'"{esc}"'


def emit_codex(fm: dict, body: str) -> str:
    content = body_with_blocks(fm, body)
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

    skills = installed_skills()

    for f in sorted(SRC.glob("*.md")):
        fm, body = parse(f, skills)
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
