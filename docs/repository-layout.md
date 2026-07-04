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
    kilo.jsonc.example           # Kilo CLI config template, instructions + mcp (copy to .kilocode/kilo.jsonc)
    mcp.json.example             # Kilo extension MCP template (copy to .kilocode/mcp.json)
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
  .kilocode/*.example            # Kilo config templates (kilo.jsonc.example, mcp.json.example)
  .github/agents/                # generated GitHub Copilot subagent files (*.agent.md)
  .github/hooks/preflight.json   # Copilot sessionStart preflight hook
  .vscode/mcp.json.example       # GitHub Copilot MCP template
  AGENTS.md                      # renamed from AGENTS.md.example
  .mcp.json                      # optional, renamed from .mcp.json.example (Claude Code MCP, root only)
  opencode.json                  # optional, renamed from opencode.json.example (OpenCode MCP, root)
  .kilocode/mcp.json             # optional, renamed from .kilocode/mcp.json.example (Kilo extension MCP)
  .kilocode/kilo.jsonc           # optional, renamed from .kilocode/kilo.jsonc.example (Kilo CLI config + MCP)
  .codex/config.toml             # optional, renamed from .codex/config.toml.example (Codex MCP)
  .vscode/mcp.json               # optional, renamed from .vscode/mcp.json.example (Copilot MCP)
```

---

### Agent compatibility matrix

#### Skills discovery

| Agent | Native skill paths | Our solution |
|---|---|---|
| Claude Code | `.claude/skills/` | Symlink `.claude/skills/ → ../.agents/skills/` (Claude Code does not read `.agents/skills/`) |
| Kilo Code | `.kilo/skills/`, `.agents/skills/`, `.claude/skills/` | Reads `.agents/skills/` natively |
| OpenCode | `.opencode/skills/`, `.agents/skills/`, `.claude/skills/` | Reads `.agents/skills/` natively |
| Codex CLI | `.agents/skills/` | Reads `.agents/skills/` natively |
| GitHub Copilot | `.github/skills/`, `.claude/skills/`, `.agents/skills/` | Reads `.agents/skills/` natively (VS Code, JetBrains plugin, Copilot CLI) |

Only Claude Code needs a symlink; every other agent reads the canonical `.agents/skills/` directly, which is why the
`.opencode/skills/` and `.codex/skills/` symlinks were removed.

#### Subagents discovery

| Agent | Native subagent path | Our solution |
|---|---|---|
| Claude Code | `.claude/agents/` | Generated by [tools/gen_subagents.py](../tools/gen_subagents.py) |
| Kilo Code | `.kilocode/agents/` (`*.md`) | Generated by [tools/gen_subagents.py](../tools/gen_subagents.py) (OpenCode format) |
| OpenCode | `.opencode/agents/` | Generated by [tools/gen_subagents.py](../tools/gen_subagents.py) |
| Codex CLI | `.codex/agents/` (`*.toml`) | Generated by [tools/gen_subagents.py](../tools/gen_subagents.py) |
| GitHub Copilot | `.github/agents/` (`*.agent.md`) | Generated by [tools/gen_subagents.py](../tools/gen_subagents.py) |

Canonical source: [subagents/](../subagents/) `*.md` (only in the agent-standards repo). One canonical file fans out to
five per-tool trees because no shared subagent format exists: OpenCode and Kilo take OpenCode-format markdown in their
own directories, Codex takes TOML, Copilot takes `*.agent.md`. Never hand-edit the generated trees; re-run the
generator and let it propagate.

#### Instructions discovery

| Agent | Instruction file | How it loads |
|---|---|---|
| Claude Code | `CLAUDE.md` | [.claude/CLAUDE.md](../.claude/CLAUDE.md) imports `@../AGENTS.md` (Claude Code does not read `AGENTS.md` natively) |
| Kilo Code | `AGENTS.md`, `.kilocode/rules/` | Both auto-read from project root every task |
| OpenCode | `AGENTS.md` | Auto-read from project root (falls back to `CLAUDE.md`) |
| Codex CLI | `AGENTS.md` | Auto-read from project root (walks up from cwd) |
| GitHub Copilot | `AGENTS.md` | The JetBrains plugin (since 1.6.1, March 2026), VS Code, and CLI all read `AGENTS.md` natively. No bridge file ships; Copilot code review and IDEs that read only `.github/copilot-instructions.md` (Visual Studio, Xcode, Eclipse) are out of scope |

#### Preflight enforcement

| Agent | Adapter | Mechanism | Cadence |
|---|---|---|---|
| Claude Code | `.claude/settings.json` | `UserPromptSubmit` hook | every turn |
| Codex | `.codex/hooks.json` | `UserPromptSubmit` hook (injects `additionalContext`) | every turn |
| OpenCode | `.opencode/plugin/preflight.js` | `chat.system.transform` plugin | every turn |
| Kilo Code | `.kilocode/rules/00-preflight.md` | rule loaded into context | every task |
| GitHub Copilot | `.github/hooks/preflight.json` | `sessionStart` hook (injects `additionalContext`) | once per session |

Copilot cannot re-inject per turn: its `userPromptSubmitted` hook output is discarded, so the `sessionStart` hook fires
once and the gate otherwise rides in `AGENTS.md`, which Copilot reads natively. Every adapter repeats the same canonical
wording from the `## Required opening move` section of `AGENTS.md`.

#### MCP configuration

| Agent | Config file | Schema key | HTTP `type` | Env-var syntax |
|---|---|---|---|---|
| Claude Code | `.mcp.json` | `mcpServers` | `http` | `${VAR}`, `${VAR:-default}` |
| OpenCode | `opencode.json` | `mcp` | `remote` | `{env:VAR}` |
| Kilo Code (VS Code extension) | `.kilocode/mcp.json` | `mcpServers` | `streamable-http` | `{env:VAR}` |
| Kilo Code (CLI) | `.kilocode/kilo.jsonc` | `mcp` | `remote` | `{env:VAR}` |
| Codex | `.codex/config.toml` | `[mcp_servers]` | n/a (`command` or `url`) | none (literal) |
| GitHub Copilot (VS Code) | `.vscode/mcp.json` | `servers` | `http` | `${env:VAR}` |
| GitHub Copilot (JetBrains) | global `~/.config/github-copilot/intellij/mcp.json` | `servers` | `url` (no `type`) | none documented |

MCP config cannot be centralised: every tool demands its own filename and schema. The same eight servers are mirrored
across all templates; only the three columns above differ. The JetBrains Copilot plugin is global-only, has no
per-project file, and its path is community-known rather than officially documented (GitHub documents only the in-IDE
UI), so no JetBrains template ships. Full human setup is in [MCP_SETUP.md](MCP_SETUP.md).

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

The extension reads MCP from `.kilocode/mcp.json` (project) or `mcp_settings.json` (global), keyed `mcpServers`. The
separate **Kilo CLI** (an OpenCode fork) instead reads `kilo.jsonc` / `opencode.json` with the `mcp` key, and loads it
from `.kilocode/` as well as the project root; that is where `.kilocode/kilo.jsonc.example` applies. Everything Kilo
lives under `.kilocode/` so the project keeps a single Kilo directory (OpenSpec's `--tools kilocode` also writes
`.kilocode/workflows/` there).

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
