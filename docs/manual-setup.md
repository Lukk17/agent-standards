# Manual setup

Fallback steps when the standard import flow needs manual help, plus per-agent start commands. The standard
[docs/AGENT_TOOLING.md](AGENT_TOOLING.md) Quickstart usually handles everything via `git checkout`. Reach for this
file only when:

- Symlinks did not survive the checkout (common on Windows without Developer Mode).
- You want a reference of which command starts which agent.
- You are setting up a project without the `git remote add` flow.

This file stays in the agent-standards repo only. It is not shipped to consumer projects.

---

### Activating the imported files manually

If the standard checkout worked, skip to the per-agent commands below. If symlinks did not survive (most often on
Windows), recreate them, then copy the example configs.

Only [.claude/skills/](../.claude/skills/) is a symlink now. OpenCode, Kilo Code, Codex, and GitHub Copilot all read
[.agents/skills/](../.agents/skills/) natively, so they need no symlink to recreate.

#### Linux or macOS, recreate the symlink

Run from the project root, only if the symlink did not survive the checkout:

```bash
ln -s ../.agents/skills .claude/skills
```

#### Windows, recreate the symlink

Run from the project root, as Administrator or with Developer Mode enabled:

```cmd
mklink /D .claude\skills ..\.agents\skills
```

#### Copy the example configs

[AGENTS.md](../AGENTS.md.example) is required. The other three are optional.

```bash
cp AGENTS.md.example AGENTS.md
```

```bash
cp .kilocode/kilo.jsonc.example .kilocode/kilo.jsonc
```

```bash
cp opencode.json.example opencode.json
```

```bash
cp .mcp.json.example .mcp.json
```

For MCP, follow [docs/MCP_SETUP.md](MCP_SETUP.md) to install prerequisites, acquire keys, and export the env vars so
the `${VAR}` and `{env:VAR}` placeholders resolve at agent startup.

---

### Per-agent start reference

Quick reference for the five supported agents. How each one loads instructions and skills, plus the command to start
it from the project root. All of them read [AGENTS.md](../AGENTS.md.example) (Claude Code through the `@` import) and
discover skills from [.agents/skills/](../.agents/skills/) automatically. Pick whichever agent you prefer; they share
the same instructions and skills.

#### Claude Code

Claude Code reads [.claude/CLAUDE.md](../.claude/CLAUDE.md), which imports [AGENTS.md](../AGENTS.md.example) via
`@../AGENTS.md`. Skills in [.claude/skills/](../.claude/skills/) (symlinked to [.agents/skills/](../.agents/skills/))
are auto-discovered. No additional config required.

Start it from the project root:

```shell
claude
```

#### Kilo Code

Kilo Code reads [AGENTS.md](../AGENTS.md.example) from the project root automatically and discovers skills from
[.agents/skills/](../.agents/skills/) natively.

Optionally copy [.kilocode/kilo.jsonc.example](../.kilocode/kilo.jsonc.example) to `.kilocode/kilo.jsonc` to enable
additional instruction globs (Kilo CLI):

```json
{
  "instructions": ["AGENTS.md"]
}
```

#### OpenCode

OpenCode reads [AGENTS.md](../AGENTS.md.example) automatically and discovers skills from
[.agents/skills/](../.agents/skills/) natively.

Optionally copy [opencode.json.example](../opencode.json.example) to `opencode.json` for additional configuration:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": ["AGENTS.md"]
}
```

`opencode.json` must remain at the project root, not inside [.opencode/](../.opencode/).

#### Codex CLI

Codex reads [AGENTS.md](../AGENTS.md.example) from the project root and discovers skills from
[.agents/skills/](../.agents/skills/) automatically. This repo ships Codex custom agents in `.codex/agents/` (`*.toml`),
the preflight hook `.codex/hooks.json`, and the project MCP template `.codex/config.toml.example`. No project-level
config file is strictly required.

Start it from the project root:

```shell
codex
```

For global Codex settings, edit `~/.codex/config.toml`:

```toml
project_doc_max_bytes = 65536
```

#### GitHub Copilot

GitHub Copilot reads [AGENTS.md](../AGENTS.md.example) natively in the JetBrains plugin, VS Code, and the CLI, and
discovers skills from [.agents/skills/](../.agents/skills/) natively. Subagents live in `.github/agents/`
(`*.agent.md`) and the preflight gate ships as a `sessionStart` hook in `.github/hooks/preflight.json`. No bridge
instruction file is needed; add your own `.github/copilot-instructions.md` only if you target Copilot code review or
the IDEs that read only it (Visual Studio, Xcode, Eclipse). Start it inside your IDE or via the `copilot` CLI.

#### Invoking skills

Slash-syntax reference lives in [docs/AGENT_TOOLING.md](AGENT_TOOLING.md#invoking-skills) so consumer projects get it
via the shipped doc. Same content, one source.
