# Refreshing shared agent tooling

---

### What upstream owns

[agent-standards](https://github.com/Lukk17/agent-standards) is upstream for these paths in your project:

- [.agents/skills/](../.agents/skills/), the canonical skills every agent loads.
- [.agents/agents/](../.agents/agents/), the OpenCode-format subagents shared by OpenCode and Kilo Code, plus the
  three per-tool trees generated beside it: [.claude/agents/](../.claude/agents/), [.codex/agents/](../.codex/agents/),
  and [.github/agents/](../.github/agents/).
- [.agents/hooks/](../.agents/hooks/), the shared preflight gate and the formatting checker, and
  [.agents/plugin/hooks.js](../.agents/plugin/hooks.js), the OpenCode and Kilo Code adapter for that gate.
- [.github/hooks/preflight.json](../.github/hooks/preflight.json), the GitHub Copilot hook configuration.
- [AGENT_TOOLING.md](AGENT_TOOLING.md), [MCP_SETUP.md](MCP_SETUP.md), [GLOBAL_SETUP.md](GLOBAL_SETUP.md), and
  [AGENTS-UPDATE.md](AGENTS-UPDATE.md), this file, which refreshes itself.

The first-time import in [AGENT_TOOLING.md](AGENT_TOOLING.md) pulls all of it at once. That is right the first time
and wrong every time after, because it re-adds skills and subagents you removed on purpose.

The routine refresh, the Unix shell and PowerShell sections below, touches only what is already in your working
tree. A skill you added locally that does not exist upstream is left alone. A skill you deleted stays deleted. To
adopt a brand-new upstream skill or subagent, run a one-off `git checkout agent-standards/master -- <path>` for it
once, and later refreshes will keep it current.

Your configuration files are outside that routine entirely. Each shell section below ends with the two commands that
handle them, and [what this skips](#what-this-skips-and-why) says which half of each file is yours.

Run everything from the repository root. Each block is one paste. Review `git diff --stat` when you have finished a
section, then commit when you are happy.

---

### Windows prerequisite

Three paths in this setup are symlinks: `.claude/skills`, `.opencode/agents`, and `.kilo/agents`. Git on Windows
writes them as ordinary text files containing the target path unless symlink support is on, and every agent that
depends on them then quietly sees nothing.

Turn on Developer Mode first (Settings, System, For developers, Developer Mode), then tell git to honour symlinks.
For this repository only, PowerShell:

```powershell
git config core.symlinks true
```

Or globally, PowerShell:

```powershell
git config --global core.symlinks true
```

The Unix shells need neither, symlinks work out of the box.

---

### Unix shell

Fetch upstream first.

```bash
git fetch agent-standards
```

Refresh the shipped documents, including this one.

```bash
git checkout agent-standards/master -- docs/AGENT_TOOLING.md docs/MCP_SETUP.md docs/GLOBAL_SETUP.md docs/AGENTS-UPDATE.md
```

Refresh the shared gate script, the formatting checker, the OpenCode and Kilo plugin, and the Copilot hook file.

```bash
for p in .agents/hooks .agents/plugin .github/hooks; do [ -e "$p" ] && git checkout agent-standards/master -- "$p" 2>/dev/null || true; done
```

Pull the upstream copy of every skill you currently have. Skills missing upstream are skipped silently.

```bash
for d in .agents/skills/*/; do [ -d "$d" ] || continue; git checkout agent-standards/master -- "$d" 2>/dev/null || true; done
```

Pull the upstream copy of every subagent you currently have, across the four generated trees.

```bash
for f in .agents/agents/*.md .claude/agents/*.md .codex/agents/*.toml .github/agents/*.agent.md; do [ -e "$f" ] || continue; git checkout agent-standards/master -- "$f" 2>/dev/null || true; done
```

---

#### ⚠️ Stop here before the destructive part

The last command in this section overwrites all six configuration files with the upstream copies. What you lose:

- API tokens you inlined.
- Servers you disabled or repointed.
- Permissions you granted.

Diff first, and run the checkout only once you are sure nothing of yours is in them.

Your six configuration files are kept out of the loops above, for the reasons under
[what this skips](#what-this-skips-and-why). See what upstream would change in them.

```bash
git diff agent-standards/master -- .mcp.json opencode.json .vscode/mcp.json .github/mcp.json .codex/config.toml .claude/settings.json
```

Take upstream's copy of all six once the diff has shown you nothing of yours is in them.

```bash
git checkout agent-standards/master -- .mcp.json opencode.json .vscode/mcp.json .github/mcp.json .codex/config.toml .claude/settings.json
```

---

### PowerShell

Fetch upstream first.

```powershell
git fetch agent-standards
```

Refresh the shipped documents, including this one.

```powershell
git checkout agent-standards/master -- docs/AGENT_TOOLING.md docs/MCP_SETUP.md docs/GLOBAL_SETUP.md docs/AGENTS-UPDATE.md
```

Refresh the shared gate script, the formatting checker, the OpenCode and Kilo plugin, and the Copilot hook file.

```powershell
foreach ($p in '.agents/hooks', '.agents/plugin', '.github/hooks') { if (Test-Path $p) { git checkout agent-standards/master -- $p 2>$null } }
```

Pull the upstream copy of every skill you currently have.

```powershell
if (Test-Path .agents/skills) { foreach ($d in Get-ChildItem -Directory .agents/skills) { git checkout agent-standards/master -- ".agents/skills/$($d.Name)/" 2>$null } }
```

Pull the upstream copy of every subagent you currently have, across the four generated trees.

```powershell
foreach ($base in '.agents/agents', '.claude/agents', '.codex/agents', '.github/agents') { if (Test-Path $base) { foreach ($f in Get-ChildItem $base -File) { git checkout agent-standards/master -- "$base/$($f.Name)" 2>$null } } }
```

---

#### ⚠️ Stop here before the destructive part

The last command in this section overwrites all six configuration files with the upstream copies. What you lose:

- API tokens you inlined.
- Servers you disabled or repointed.
- Permissions you granted.

Diff first, and run the checkout only once you are sure nothing of yours is in them.

Your six configuration files are kept out of the loops above, for the reasons under
[what this skips](#what-this-skips-and-why). See what upstream would change in them.

```powershell
git diff agent-standards/master -- .mcp.json opencode.json .vscode/mcp.json .github/mcp.json .codex/config.toml .claude/settings.json
```

Take upstream's copy of all six once the diff has shown you nothing of yours is in them.

```powershell
git checkout agent-standards/master -- .mcp.json opencode.json .vscode/mcp.json .github/mcp.json .codex/config.toml .claude/settings.json
```

---

### What this skips and why

Nothing in this list is refreshed. Each one is either derived or yours.

- The three symlinks, `.claude/skills`, `.opencode/agents`, and `.kilo/agents`. They point at
  [.agents/skills/](../.agents/skills/) and [.agents/agents/](../.agents/agents/), so they update the moment those
  directories do. Pulling the link itself would only risk turning it into a file.
- [.claude/CLAUDE.md](../.claude/CLAUDE.md), your Claude Code entry point. It imports `AGENTS.md` and stays under
  your control.
- [.claude/settings.json](../.claude/settings.json), which ships the Claude Code hooks on first import and then
  becomes yours, because it is also where your project permissions live.
- [opencode.json](../opencode.json) and [.codex/config.toml](../.codex/config.toml). Both carry your MCP servers
  next to a piece of gate wiring: `opencode.json` declares the plugin path, `.codex/config.toml` holds the Codex hook
  tables inline.
- [.mcp.json](../.mcp.json), [.vscode/mcp.json](../.vscode/mcp.json), and [.github/mcp.json](../.github/mcp.json),
  your MCP server sets.
- [AGENTS.md.example](../AGENTS.md.example) and your own `AGENTS.md`. The first is consumed once at setup, the
  second is the source of truth for your project's conventions.

Six of those are the configuration files: [.mcp.json](../.mcp.json), [opencode.json](../opencode.json),
[.vscode/mcp.json](../.vscode/mcp.json), [.github/mcp.json](../.github/mcp.json),
[.codex/config.toml](../.codex/config.toml), and [.claude/settings.json](../.claude/settings.json). Between them
they carry every MCP server, your Claude Code settings, and three of the six pieces of preflight wiring. That is why
they get their own two commands at the end of each shell section instead of riding the loops: `git checkout`
replaces a file whole, and everything local in it goes with it, an inlined token, a server you disabled, a host you
repointed, a permission you granted. Diff first, every time, and run the checkout only once you are sure nothing of
yours is in them.

Who owns which half:

| File | Yours to customise | Tracks upstream |
| --- | --- | --- |
| [.mcp.json](../.mcp.json) | the whole file: server set, hosts, tokens | nothing |
| [.vscode/mcp.json](../.vscode/mcp.json) | the whole file: server set, hosts, tokens | nothing |
| [.github/mcp.json](../.github/mcp.json) | the whole file: server set, hosts, tokens | nothing |
| [opencode.json](../opencode.json) | the `mcp` block | the `plugin` array, which declares the gate |
| [.codex/config.toml](../.codex/config.toml) | the `[mcp_servers.*]` tables | the `[[hooks.*]]` tables, which declare the gate |
| [.claude/settings.json](../.claude/settings.json) | anything you add beside the hooks, typically a `permissions` block | the `hooks` block, which declares the gate |

The three MCP-only files become yours outright at import and never need to follow upstream again, unless you want a
newly added server. The other three are split: the gate half should stay identical to upstream so the preflight rule
keeps firing, and it shares a file with something of yours, so an upstream gate change is merged by hand rather than
checked out. The release notes say when there is one. Read upstream's copy with
`git show agent-standards/master:opencode.json` and paste across the block you need.

---

### Initialising OpenSpec

This repository ships no `openspec-*` skills of its own. OpenSpec is a consumer concern, and it matters here only
because a careless init scatters per-tool directories across a layout that deliberately has one.

Install it globally, PowerShell:

```powershell
npm install -g @fission-ai/openspec@latest
```

Unix shell:

```bash
npm install -g @fission-ai/openspec@latest
```

Then initialise with the vendor-neutral target, and only that one. PowerShell:

```powershell
openspec init --tools agents
```

Unix shell:

```bash
openspec init --tools agents
```

`--tools agents` writes its skills into `.agents/skills/` and creates no per-tool directories at all. That single
target covers every agent you run: Codex, OpenCode, Kilo Code, and GitHub Copilot read `.agents/skills/` natively, and
Claude Code reaches the same files through its `.claude/skills` symlink.

Do not reach for a per-tool target. `--tools kilocode` is the clearest example of why: OpenSpec 1.10.0 still hardcodes
the old `.kilocode` directory for its Kilo target, which Kilo Code itself has moved away from in favour of `.kilo`, so
you would get a directory neither tool reads. The neutral target sidesteps that and every other per-tool split.

Keeping OpenSpec's own files current is a separate command, and it takes no tools flag: `openspec update` regenerates
the per-agent files for the tools already configured in the project. PowerShell:

```powershell
openspec update
```

Unix shell:

```bash
openspec update
```

Slash-command names still vary by agent, since command formats are genuinely per-tool. Use whichever form your agent
shows in its autocomplete, `/opsx:propose` or `/opsx-propose.md`.

---

### Maintenance

This file ships from upstream and is in its own refresh list, so a normal update keeps it current with the
agent-standards layout. Hand-edit the commands only when a layout change (a renamed directory, a split file, a new
top-level document) breaks the self-refresh before you can pull the corrected version. Keeping the update selective
makes that a conscious choice rather than an accident.
