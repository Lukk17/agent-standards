# Refreshing shared agent tooling

---

[agent-standards](https://github.com/Lukk17/agent-standards) is upstream for [.agents/skills/](../.agents/skills/),
the five generated subagent trees ([.claude/agents/](../.claude/agents/), [.opencode/agents/](../.opencode/agents/),
`.kilocode/agents/`, `.codex/agents/`, [.github/agents/](../.github/agents/)), the preflight adapters
([.opencode/plugin/](../.opencode/plugin/), `.kilocode/rules/`, `.codex/hooks.json`, and `.github/hooks/`),
[AGENT_TOOLING.md](AGENT_TOOLING.md), [MCP_SETUP.md](MCP_SETUP.md), and [AGENTS-UPDATE.md](AGENTS-UPDATE.md) (this
file).

The bootstrap import in [AGENT_TOOLING.md](AGENT_TOOLING.md) pulls everything from upstream. That is fine the first
time. On every later update it re-adds skills and subagents you removed on purpose.

The commands below refresh **only what is already in the working tree**. Skills added locally that do not exist
upstream stay untouched. Skills deleted locally stay deleted. [.claude/skills](../.claude/skills) is a symlink into
[.agents/skills/](../.agents/skills/), so it updates with it; every other agent reads
[.agents/skills/](../.agents/skills/) directly.

To pull a brand-new upstream skill or subagent, run a one-off `git checkout agent-standards/master -- <path>` first.
Later refreshes will then keep it current.

Run from the repo root. Each block is one paste. Review `git diff --stat` after the last block. Commit when satisfied.

---

### Unix shell

Fetch upstream first.

```bash
git fetch agent-standards
```

Refresh the shipped docs (including this file).

```bash
git checkout agent-standards/master -- docs/AGENT_TOOLING.md docs/MCP_SETUP.md docs/AGENTS-UPDATE.md
```

Refresh the preflight enforcement adapters (OpenCode plugin, Kilo rule, Codex hook, Copilot hook). The Claude hook in
`.claude/settings.json` is deliberately excluded so per-project permissions there survive.

```bash
for p in .opencode/plugin .kilocode/rules .codex/hooks.json .github/hooks; do [ -e "$p" ] && git checkout agent-standards/master -- "$p" 2>/dev/null || true; done
```

Iterate every skill currently present and pull its upstream copy. Missing-upstream errors are swallowed.

```bash
for d in .agents/skills/*/; do [ -d "$d" ] || continue; git checkout agent-standards/master -- "$d" 2>/dev/null || true; done
```

Iterate every subagent currently present in any generated tree and pull its upstream copy.

```bash
for f in .claude/agents/*.md .opencode/agents/*.md .kilocode/agents/*.md .codex/agents/*.toml .github/agents/*.agent.md; do [ -e "$f" ] || continue; git checkout agent-standards/master -- "$f" 2>/dev/null || true; done
```

---

### PowerShell (5.1 and 7+)

Fetch upstream first.

```powershell
git fetch agent-standards
```

Refresh the shipped docs (including this file).

```powershell
git checkout agent-standards/master -- docs/AGENT_TOOLING.md docs/MCP_SETUP.md docs/AGENTS-UPDATE.md
```

Refresh the preflight enforcement adapters (OpenCode plugin, Kilo rule, Codex hook, Copilot hook). The Claude hook in
`.claude/settings.json` is deliberately excluded so per-project permissions there survive.

```powershell
foreach ($p in '.opencode/plugin', '.kilocode/rules', '.codex/hooks.json', '.github/hooks') { if (Test-Path $p) { git checkout agent-standards/master -- $p 2>$null } }
```

Iterate every skill currently present and pull its upstream copy.

```powershell
if (Test-Path .agents/skills) { foreach ($d in Get-ChildItem -Directory .agents/skills) { git checkout agent-standards/master -- ".agents/skills/$($d.Name)/" 2>$null } }
```

Iterate every subagent currently present in any generated tree and pull its upstream copy.

```powershell
foreach ($base in '.claude/agents', '.opencode/agents', '.kilocode/agents', '.codex/agents', '.github/agents') { if (Test-Path $base) { foreach ($f in Get-ChildItem $base -File) { git checkout agent-standards/master -- "$base/$($f.Name)" 2>$null } } }
```

---

### What this skips intentionally

These paths are deliberately not refreshed:

- [.claude/skills/](../.claude/skills): the one remaining skill symlink, pointing at
  [.agents/skills/](../.agents/skills/). It updates automatically when the canonical directory does; every other agent
  reads [.agents/skills/](../.agents/skills/) directly.
- [.claude/CLAUDE.md](../.claude/CLAUDE.md): consumer-owned entry point. It imports `AGENTS.md` files and stays under
  your control.
- [.claude/settings.json](../.claude/settings.json): ships the preflight hook on initial import, then becomes
  consumer-owned (this is where per-project permissions live). Not refreshed, so your settings survive.
- [AGENTS.md.example](../AGENTS.md.example), [opencode.json.example](../opencode.json.example),
  [.mcp.json.example](../.mcp.json.example), the `.kilocode/*.example` templates
  (`.kilocode/kilo.jsonc.example`, `.kilocode/mcp.json.example`), `.codex/config.toml.example`, and
  [.vscode/mcp.json.example](../.vscode/mcp.json.example): template files consumed once at initial setup.
  The adapter refresh above pulls the plugin, rule, and hook files by exact path, so these `.example` templates are
  never clobbered.
- The customised [AGENTS.md](../AGENTS.md) at the repo root: source of truth for project conventions. Owned by this
  consumer, not by upstream.

---

### Maintenance

This file ships from upstream and refreshes itself (it is in the checkout list above), so a normal refresh keeps it
current with the agent-standards layout. Hand-edit the commands only if a layout change (a renamed directory, a split
file, a new top-level shipped doc) breaks the self-refresh before you can pull the corrected version. The selective
approach keeps that a conscious choice, not an accident.
