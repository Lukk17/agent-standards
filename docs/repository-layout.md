# Repository layout

Reference material for how the agent-standards repo and consumer projects are structured, which agent reads what, and
the precedence order each agent applies when loading instructions.

This file stays in the agent-standards repo only. It is not shipped to consumer projects.

---

### Repository structure

This repo (full layout):

```
agent-standards/
  .agents/
    skills/                      # canonical SKILL.md files (shipped to consumers)
  subagents/                     # canonical subagent templates (this repo only)
  tools/                         # Generator + deps (this repo only)
    gen_subagents.py             # Emits .claude/, .opencode/, .kilocode/, .codex/, .github/ agent trees
    pyproject.toml               # Python deps (pyyaml)
  .claude/
    CLAUDE.md                    # @imports ../AGENTS.md (Claude Code bridge)
    settings.json                # UserPromptSubmit preflight hook (consumer-owned after import)
    skills -> ../.agents/skills/ # symlink for Claude Code (the only agent that needs one)
    agents/                      # GENERATED, shipped to consumers
  .opencode/
    agents/                      # GENERATED, OpenCode subagents
    plugin/preflight.js          # OpenCode preflight adapter (chat.system.transform)
  .codex/
    agents/                      # GENERATED, Codex custom agents (*.toml)
    hooks.json                   # Codex preflight adapter (UserPromptSubmit hook)
    config.toml.example          # Codex project MCP template (copy to .codex/config.toml)
  .kilocode/
    agents/                      # GENERATED, Kilo Code subagents (OpenCode-format *.md)
    rules/00-preflight.md        # Kilo Code preflight adapter (rule; the extension has no hook surface)
    kilo.jsonc.example           # Kilo config template, instructions + mcp (extension and CLI; copy to .kilocode/kilo.jsonc)
  .github/
    agents/                      # GENERATED, GitHub Copilot subagents (*.agent.md), shipped to consumers
    hooks/preflight.json         # Copilot sessionStart preflight adapter (once per session)
  .vscode/
    mcp.json.example             # GitHub Copilot MCP template (copy to .vscode/mcp.json)
  AGENTS.md                      # This repo's own instructions (source repo, not shipped to consumers)
  AGENTS.md.example              # Template for consumer-project AGENTS.md (the real AGENTS.md is created downstream)
  opencode.json.example          # OpenCode config template (must stay at root)
  .mcp.json.example              # Claude Code MCP config template (project scope, root only)
  docs/
    AGENT_TOOLING.md             # Setup walkthrough shipped to consumers
    MCP_SETUP.md                 # Human MCP setup (env vars, keys, OS commands)
    AGENTS-UPDATE.md             # Selective update commands shipped to consumers (self-refreshing)
    repository-layout.md         # This file, project-only reference
    manual-setup.md              # Project-only manual fallback + per-agent commands
    bootstrap-prompt.md          # Project-only first-run verification prompt
```

Consumer-project layout after import (the [subagents/](../subagents/) source and [tools/](../tools/) are intentionally
absent):

```
your-project/
  .agents/skills/                # pulled from agent-standards (read natively by every agent but Claude Code)
  .claude/CLAUDE.md
  .claude/settings.json          # preflight hook
  .claude/skills/                # symlink (Claude Code only)
  .claude/agents/                # generated subagent files
  .opencode/agents/              # generated subagent files
  .opencode/plugin/preflight.js  # preflight adapter
  .codex/agents/                 # generated Codex custom agents (*.toml)
  .codex/hooks.json              # Codex preflight hook
  .codex/config.toml.example     # Codex MCP template
  .kilocode/agents/              # generated Kilo subagent files (OpenCode-format *.md)
  .kilocode/rules/               # preflight rule
  .kilocode/kilo.jsonc.example   # Kilo config template (instructions + MCP, extension and CLI)
  .github/agents/                # generated GitHub Copilot subagent files (*.agent.md)
  .github/hooks/preflight.json   # Copilot sessionStart preflight hook
  .vscode/mcp.json.example       # GitHub Copilot MCP template
  AGENTS.md                      # renamed from AGENTS.md.example
  .mcp.json                      # optional, renamed from .mcp.json.example (Claude Code MCP, root only)
  opencode.json                  # optional, renamed from opencode.json.example (OpenCode MCP, root)
  .kilocode/kilo.jsonc           # optional, renamed from .kilocode/kilo.jsonc.example (Kilo config + MCP, extension and CLI)
  .codex/config.toml             # optional, renamed from .codex/config.toml.example (Codex MCP)
  .vscode/mcp.json               # optional, renamed from .vscode/mcp.json.example (Copilot MCP)
```

---

### Agent compatibility matrix

The full per-surface matrix (skills, instructions, subagents, preflight, and MCP, with GitHub Copilot split by client)
lives in its own file: [agent-compatibility.md](agent-compatibility.md). It is the single source for what each agent
reads and where. The instruction-merge precedence for each agent follows below.

---

### Instruction precedence

How each agent merges instructions when multiple sources exist. Higher-numbered entries override lower-numbered ones
on conflict; skills load on demand independently.

#### Claude Code

```
1. Organization managed CLAUDE.md (/etc/claude-code/ or system dirs)
2. User-level: ~/.claude/CLAUDE.md
3. Ancestor CLAUDE.md files (walking up from cwd)
4. Project-level: ./CLAUDE.md or ./.claude/CLAUDE.md
5. Project-level: ./CLAUDE.local.md (personal, not versioned)
6. .claude/rules/*.md (path-scoped rules, auto-loaded)
7. @imported files (expanded inline, max 5 levels deep)
8. Skills (loaded on demand when invoked or matched)
```

#### Kilo Code

Kilo ships as two products. The **VS Code extension** (what most users run) loads instructions in this order, higher
overrides lower:

```
1. Mode-specific rules: .kilocode/rules-{mode}/ (e.g. .kilocode/rules-code/)
2. Project rules: .kilocode/rules/ (all files, auto-loaded every task)
3. AGENTS.md at project root (auto-read every task)
4. Global rules: ~/.kilocode/rules/
5. Custom instructions from extension settings
6. Skills from .agents/skills/ (auto-discovered)
```

Kilo unified MCP config across its clients: the VS Code extension, the JetBrains plugin, and the separate Kilo CLI (an
OpenCode fork) all read `kilo.jsonc` with the `mcp` key, loaded from `.kilocode/` as well as the project root. That is
where `.kilocode/kilo.jsonc.example` applies, and it is why the old `.kilocode/mcp.json` (keyed `mcpServers`) template
was dropped. Everything Kilo lives under `.kilocode/` so the project keeps a single Kilo directory (OpenSpec's
`--tools kilocode` also writes `.kilocode/workflows/` there). Kilo's newer `.kilo/` directory supersedes `.kilocode/`
upstream, but `.kilocode/` stays backward-compatible and is what this repo currently targets.

#### OpenCode

```
1. Remote config (.well-known/opencode), organizational defaults
2. Global config (~/.config/opencode/opencode.json), user preferences
3. Custom config (OPENCODE_CONFIG env var)
4. Project config (opencode.json at project root)
5. .opencode/ directories (agents/, commands/, plugins/, skills/)
6. Inline config (OPENCODE_CONFIG_CONTENT env var), highest JSON override
7. Managed config files (system directories)
```

Note: `opencode.json` must be at the project root, not inside [.opencode/](../.opencode/). The
[.opencode/](../.opencode/) directory holds subdirectories (`skills/`, `commands/`, `agents/`).

#### Codex CLI

```
1. Global: ~/.codex/AGENTS.md (or AGENTS.override.md if exists)
2. Project root: AGENTS.md (or AGENTS.override.md if exists)
3. Subdirectories: AGENTS.md walking down from root to cwd
4. AGENTS.override.md at any level takes precedence over AGENTS.md at same level
5. Skills from .agents/skills/ (primary), walking up from cwd to repo root
```

Codex now supports project-level config in a `.codex/` directory alongside the global `~/.codex/`. This repo ships
[.codex/agents/](../.codex/agents/) (TOML custom agents), [.codex/hooks.json](../.codex/hooks.json) (the
`UserPromptSubmit` preflight hook, which injects the gate every turn via `hookSpecificOutput.additionalContext`), and
[.codex/config.toml.example](../.codex/config.toml.example) (project MCP servers, for trusted projects). Global settings
still live in `~/.codex/config.toml`. Skills are scanned from [.agents/skills/](../.agents/skills/) at every directory
level up to the repo root.
