# Manual setup

Fallback steps for when the standard import needs a hand, plus a per-agent start reference. The Step 1 checkout in
[AGENT_TOOLING.md](AGENT_TOOLING.md) normally does everything. Reach for this file when:

- Symlinks did not survive the checkout, which is the usual Windows failure.
- You want to know which command starts which agent.
- You are wiring a project up without the `git remote add` flow.

This file stays in the agent-standards repo only. It is not shipped to consumer projects.

---

### Repairing the symlinks

Three paths are symlinks, and all three are load-bearing:

| Link | Points at | Who breaks without it |
| --- | --- | --- |
| `.claude/skills` | `../.agents/skills` | Claude Code, which reads no other skills path |
| `.opencode/agents` | `../.agents/agents` | OpenCode, which then has no subagents |
| `.kilo/agents` | `../.agents/agents` | Kilo Code, same |

Check what you actually have before repairing anything. PowerShell:

```powershell
Get-Item .claude/skills, .opencode/agents, .kilo/agents | Select-Object Name, LinkType, Target
```

Unix shell:

```bash
ls -l .claude/skills .opencode/agents .kilo/agents
```

A healthy result shows three links. A broken checkout leaves small text files containing the target path instead. If
that is what you see, delete them and recreate the links.

#### Windows

Enable Developer Mode first (Settings, System, For developers), or run the shell as Administrator. Then, from the
project root:

```powershell
New-Item -ItemType SymbolicLink -Path .claude\skills -Target ..\.agents\skills
```

```powershell
New-Item -ItemType SymbolicLink -Path .opencode\agents -Target ..\.agents\agents
```

```powershell
New-Item -ItemType SymbolicLink -Path .kilo\agents -Target ..\.agents\agents
```

Then tell git to honour symlinks so the next checkout does not undo this:

```powershell
git config core.symlinks true
```

#### Linux or macOS

From the project root:

```bash
ln -s ../.agents/skills .claude/skills
```

```bash
ln -s ../.agents/agents .opencode/agents
```

```bash
ln -s ../.agents/agents .kilo/agents
```

Inside this repository there is a shortcut for the two agent links, because the generator owns them:

```bash
python tools/gen_subagents.py
```

That recreates `.opencode/agents` and `.kilo/agents` if they are missing or pointing at the wrong place. It does not
touch `.claude/skills`, which has nothing to do with subagent generation.

---

### Activating the imported files

There is only one rename left. Config files ship as real files now.

PowerShell:

```powershell
Rename-Item AGENTS.md.example AGENTS.md
```

Unix shell:

```bash
mv AGENTS.md.example AGENTS.md
```

[.mcp.json](../.mcp.json), [opencode.json](../opencode.json), [.codex/config.toml](../.codex/config.toml), and
[.vscode/mcp.json](../.vscode/mcp.json) arrive ready to use. Follow [MCP_SETUP.md](MCP_SETUP.md) to install the
prerequisites, acquire the keys, and export the environment variables. Only `.mcp.json` resolves a placeholder,
`${VAR}` with a default. The other three read no placeholders at all: a local MCP server inherits the environment of
the process that started the agent, so exporting the variable is what makes the token arrive.

---

### Per-agent start reference

All five agents share the same instructions and the same skills. Pick whichever you prefer.

#### Claude Code

Reads [.claude/CLAUDE.md](../.claude/CLAUDE.md), which is nothing but `@../AGENTS.md` plus a comment, so the shared
instructions arrive inline. Skills come through the `.claude/skills` symlink, subagents from
[.claude/agents/](../.claude/agents/), hooks from [.claude/settings.json](../.claude/settings.json). No further
configuration.

```shell
claude
```

#### Codex

Reads [AGENTS.md](../AGENTS.md) and [.agents/skills/](../.agents/skills/) natively. Custom agents come from
[.codex/agents/](../.codex/agents/) as TOML, and [.codex/config.toml](../.codex/config.toml) carries both the MCP
servers and the gate hooks.

```shell
codex
```

Codex loads that whole project layer only after you trust the project once, so approve it on first run or nothing in
`.codex/` applies. Global settings stay in `~/.codex/config.toml`:

```toml
project_doc_max_bytes = 65536
```

#### OpenCode

Reads [AGENTS.md](../AGENTS.md) and [.agents/skills/](../.agents/skills/) natively, subagents through the
`.opencode/agents` symlink. [opencode.json](../opencode.json) at the project root carries the MCP servers and declares
the gate plugin by path.

```shell
opencode
```

`opencode.json` stays at the project root, because that is the only place Kilo Code looks. OpenCode would also read a
second file at `.opencode/opencode.json` and merge it over the root one, but none ships: `.opencode/` holds nothing
but the `agents` symlink.

#### Kilo Code

Reads [AGENTS.md](../AGENTS.md) and [.agents/skills/](../.agents/skills/) natively, subagents through the
`.kilo/agents` symlink. Kilo accepts [opencode.json](../opencode.json) as a project config filename, so it picks up
the same MCP block and the same plugin declaration as OpenCode. Its own configuration root is `.kilo/`, not the old
`.kilocode/`.

Kilo does not expand `{env:VAR}` in project-level config, and it does not leave the placeholder standing either. It
treats an environment reference as a fatal error and rejects the whole file, which would leave Kilo with no MCP
servers and no preflight gate, so `opencode.json` ships without any. Run `kilocode config check` after editing it: it
prints `No config warnings.` when the file is accepted. Local servers get their tokens from the environment you
exported. Context7 therefore ships unauthenticated. For a paid key, put the full `context7` block in your global
`~/.config/kilo/kilo.jsonc`, where environment references are allowed.

#### GitHub Copilot

Reads [AGENTS.md](../AGENTS.md) and [.agents/skills/](../.agents/skills/) natively across VS Code, the JetBrains
plugin, the CLI, and the cloud agent. Subagents live in [.github/agents/](../.github/agents/) as `*.agent.md`, and the
gate ships as [.github/hooks/preflight.json](../.github/hooks/preflight.json). No bridge instruction file is needed.
Start it inside your editor, or from a terminal:

```shell
copilot
```

MCP differs per surface: VS Code reads [.vscode/mcp.json](../.vscode/mcp.json), the CLI reads the project
[.mcp.json](../.mcp.json), the JetBrains plugin reads a global file only, and the cloud agent takes JSON pasted into
a repository settings page. See [MCP_SETUP.md](MCP_SETUP.md).

---

### Invoking skills

The slash-syntax reference lives in [AGENT_TOOLING.md](AGENT_TOOLING.md#invoking-skills), so consumer projects get it
through the shipped document. Same content, one source.
