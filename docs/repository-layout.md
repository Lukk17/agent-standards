# Repository layout

Reference material for how the agent-standards repo and consumer projects are structured, which files are canonical,
which are generated, which are symlinks, and the precedence order each agent applies when loading instructions.

This file stays in the agent-standards repo only. It is not shipped to consumer projects.

---

### Canonical, generated, symlink

Three categories, and mixing them up is the one mistake that breaks a rebuild.

| Category | Paths | How to change it |
| --- | --- | --- |
| Canonical | `subagents/*.md`, `.agents/skills/*/SKILL.md`, `.agents/hooks/*.py`, `.agents/plugin/hooks.js`, `docs/*.md` | edit directly |
| Canonical config | `.mcp.json`, `opencode.json`, `.codex/config.toml`, `.vscode/mcp.json`, `.claude/settings.json`, `.github/hooks/preflight.json` | edit directly, keep the server set and the gate wording in sync |
| Generated | `.claude/agents/*.md`, `.agents/agents/*.md`, `.codex/agents/*.toml`, `.github/agents/*.agent.md` | never hand-edit, run `python tools/gen_subagents.py` |
| Symlink | `.opencode/agents`, `.kilo/agents`, `.claude/skills` | never edit through the link, fix the link itself |

The generator owns two of the three symlinks. `.opencode/agents` and `.kilo/agents` both point at `../.agents/agents`,
and `python tools/gen_subagents.py` recreates them if they go missing. `.claude/skills` points at `../.agents/skills`
and is maintained separately, because it has nothing to do with subagent generation.

Config files are real files, not templates. The only remaining `.example` in the repo is
[AGENTS.md.example](../AGENTS.md.example), which consumers rename to `AGENTS.md`.

---

### Repository structure

This repo, full layout:

```text
agent-standards/
  .agents/
    skills/                      # CANONICAL SKILL.md files, shipped to consumers
    agents/                      # GENERATED, OpenCode-format subagents, shared by OpenCode and Kilo Code
    hooks/
      preflight_gate.py          # CANONICAL, the one shared gate rule for every agent surface
      no_ai_markers_check.py     # CANONICAL, formatting checker run by the Claude Code Stop hook
    plugin/
      hooks.js                   # CANONICAL, OpenCode and Kilo Code adapter that shells out to preflight_gate.py
  subagents/                     # CANONICAL subagent sources, this repo only
  tools/                         # Generator, linter and tests, this repo only
    gen_subagents.py             # Emits four trees plus the two agent symlinks
    check-markdown.py            # Markdown lint used by CI
    pyproject.toml               # CANONICAL, the only pinned dependency and pytest configuration
    tests/                       # CANONICAL pytest suite for the two hook scripts
  e2e/                           # Capability test specs, templates and run records, this repo only
  sandbox-agent/                 # Containerised sandbox that runs those specs, this repo only
  openspec/schemas/e2e-runbooks/ # Vendored companion schema, reference copy, this repo runs no OpenSpec workflow
  .claude/
    CLAUDE.md                    # imports ../AGENTS.md, the Claude Code bridge
    settings.json                # PreToolUse, SessionStart, UserPromptSubmit and Stop hooks
    skills -> ../.agents/skills  # SYMLINK, the only way Claude Code sees the canonical skills
    agents/                      # GENERATED, Claude-format subagents
  .opencode/
    agents -> ../.agents/agents  # SYMLINK maintained by the generator
  .kilo/
    agents -> ../.agents/agents  # SYMLINK maintained by the generator
  .codex/
    agents/                      # GENERATED, Codex custom agents (*.toml)
    config.toml                  # Codex MCP servers plus the inline [[hooks.*]] gate tables
  .github/
    agents/                      # GENERATED, GitHub Copilot subagents (*.agent.md)
    hooks/preflight.json         # Copilot hook config, camelCase events
    workflows/                   # CI and release, both manual-trigger only
  .vscode/
    mcp.json                     # GitHub Copilot in VS Code, key "servers"
  AGENTS.md                      # This repo's own instructions, never shipped downstream
  AGENTS.md.example              # The template consumers rename to AGENTS.md
  opencode.json                  # OpenCode and Kilo Code, MCP plus the plugin declaration, no substitution tokens
  .mcp.json                      # Claude Code and the GitHub Copilot CLI, key "mcpServers"
  README.md                      # Project front door, this repo only
  CONTRIBUTING.md                # Contribution rules and local checks, this repo only
  CHANGELOG.md                   # Release history, this repo only
  LICENSE                        # MIT
  docs/
    AGENT_TOOLING.md             # Setup walkthrough shipped to consumers
    MCP_SETUP.md                 # Human MCP setup, keys and environment variables
    AGENTS-UPDATE.md             # Selective update commands shipped to consumers, self-refreshing
    GLOBAL_SETUP.md              # Per-agent home-directory install, shipped to consumers
    repository-layout.md         # This file, project-only reference
    agent-compatibility.md       # Project-only per-surface matrix
    hooks-contract.md            # Project-only hook runner contract, envelope, ordering and exit codes
    manual-setup.md              # Project-only manual fallback and per-agent start commands
    bootstrap-prompt.md          # Project-only first-run verification prompt
    assets/                      # README demo gif and social card
```

`.kilocode/` is gone. Kilo Code moved its configuration root to `.kilo/`, so nothing in this repo writes to the old
directory any more.

Consumer-project layout after import. The [subagents/](../subagents/) source and [tools/](../tools/) generator are
intentionally absent:

```text
your-project/
  .agents/skills/                # canonical skills, read natively by every agent except Claude Code
  .agents/agents/                # generated OpenCode-format subagents
  .agents/hooks/                 # the shared gate script and the formatting checker
  .agents/plugin/hooks.js        # the OpenCode and Kilo Code gate adapter
  .claude/CLAUDE.md              # imports ../AGENTS.md
  .claude/settings.json          # Claude Code hooks, consumer-owned after import
  .claude/skills                 # symlink to ../.agents/skills
  .claude/agents/                # generated Claude-format subagents
  .opencode/agents               # symlink to ../.agents/agents
  .kilo/agents                   # symlink to ../.agents/agents
  .codex/agents/                 # generated Codex custom agents (*.toml)
  .codex/config.toml             # Codex MCP servers plus the inline gate hooks
  .github/agents/                # generated Copilot subagents (*.agent.md)
  .github/hooks/preflight.json   # Copilot hook config
  .vscode/mcp.json               # Copilot in VS Code MCP servers
  .mcp.json                      # Claude Code and Copilot CLI MCP servers
  opencode.json                  # OpenCode and Kilo Code MCP servers plus the plugin declaration
  AGENTS.md                      # renamed from AGENTS.md.example, then filled in
  docs/                          # only the UPPERCASE docs: AGENT_TOOLING, MCP_SETUP, AGENTS-UPDATE, GLOBAL_SETUP
```

---

### Who reads what

The short version. The full per-surface matrix, including hook enforcement and the Copilot client split, lives in
[agent-compatibility.md](agent-compatibility.md).

| Agent | Instructions | Skills | Subagents | MCP |
| --- | --- | --- | --- | --- |
| Claude Code | `.claude/CLAUDE.md` imports `../AGENTS.md` | `.claude/skills` symlink | `.claude/agents/` | `.mcp.json` |
| OpenCode | `AGENTS.md` natively | `.agents/skills/` natively | `.opencode/agents` symlink | `opencode.json` |
| Kilo Code | `AGENTS.md` natively | `.agents/skills/` natively | `.kilo/agents` symlink | `opencode.json` |
| Codex | `AGENTS.md` natively | `.agents/skills/` natively | `.codex/agents/` | `.codex/config.toml` |
| GitHub Copilot | `AGENTS.md` natively | `.agents/skills/` natively | `.github/agents/` | per client, see the matrix |

Two facts drive the whole layout. Skills and instructions converged on open locations that four of the five agents
read without help, so `.agents/skills/` and `AGENTS.md` are canonical and Claude Code reaches both through a bridge
(a symlink for skills, an `@` import for instructions), which Claude Code's own documentation supports. Subagent
definitions did not converge: Claude, Codex and Copilot each need a different file format, so the generator fans one
canonical source out to four trees. Only OpenCode and Kilo Code share a format, which is why they share one tree
through symlinks instead of getting a copy each.

---

### Instruction precedence

How each agent merges instructions when several sources exist. Higher-numbered entries override lower-numbered ones on
conflict. Skills load on demand and sit outside this ordering.

#### Claude Code

```text
1. Organization managed CLAUDE.md (system directories)
2. User level: ~/.claude/CLAUDE.md
3. Ancestor CLAUDE.md files, walking up from the working directory
4. Project level: ./CLAUDE.md or ./.claude/CLAUDE.md
5. Project level: ./CLAUDE.local.md (personal, not versioned)
6. .claude/rules/*.md (path-scoped rules, auto-loaded)
7. @imported files, expanded inline, up to five levels deep
8. Skills, loaded on demand
```

Claude Code does not read `AGENTS.md`. Entry 7 is what makes the setup work: [.claude/CLAUDE.md](../.claude/CLAUDE.md)
contains nothing but `@../AGENTS.md` plus a comment, so the shared instructions arrive inline.

#### OpenCode

```text
1. Remote config (.well-known/opencode), organizational defaults
2. Global config (~/.config/opencode/opencode.json)
3. Custom config (OPENCODE_CONFIG environment variable)
4. Project config (opencode.json at the project root, or .opencode/opencode.json)
5. .opencode/ directories (agents/, commands/, plugins/)
6. Inline config (OPENCODE_CONFIG_CONTENT environment variable)
7. Managed config files (system directories)
```

The one `opencode.json` sits at the project root, because that is also the only place Kilo Code will look for it.
OpenCode would additionally read a project file at `.opencode/opencode.json` and deep-merge it over the root one, but
this repo ships none: a second file that only one of the two tools reads is a second place for the server set to
drift, and there is no longer any value that needs it. [.opencode/](../.opencode/) therefore holds nothing but the
`agents` symlink. `AGENTS.md` is auto-read from the project root, falling back to `CLAUDE.md` when no `AGENTS.md`
exists.

#### Kilo Code

Kilo ships as a VS Code extension, a JetBrains plugin, and a separate command-line client. All of them load
instructions in this order, higher overrides lower:

```text
1. Mode-specific rules: .kilo/rules-{mode}/
2. Project rules: .kilo/rules/, auto-loaded every task
3. AGENTS.md at the project root, auto-read every task
4. Global rules: ~/.kilo/rules/
5. Custom instructions from the client settings
6. Skills from .agents/skills/, auto-discovered
```

Kilo accepts `opencode.json` as a valid project config filename, which is why this repo ships one file for both Kilo
and OpenCode instead of a Kilo-specific twin. The catch is what Kilo does with an environment reference in that file.
It does not leave `{env:VAR}` literal, it rejects the entire file, which would cost Kilo both the MCP servers and the
`plugin` array that declares the preflight gate. Only the rejected file is dropped, the rest of Kilo's config chain
still loads. That is why the shared file carries no references, and why no `.kilo/kilo.jsonc` needs to exist. Details
in [MCP_SETUP.md](MCP_SETUP.md).

#### Codex

```text
1. Global: ~/.codex/AGENTS.md (or AGENTS.override.md when present)
2. Project root: AGENTS.md (or AGENTS.override.md when present)
3. Subdirectories: AGENTS.md walking down from the root to the working directory
4. AGENTS.override.md beats AGENTS.md at the same level
5. Skills from .agents/skills/, scanned from the working directory up to the repo root
```

Codex loads the project `.codex/` layer (custom agents, MCP servers, hooks) only after the project is trusted, so a
fresh clone runs neither the MCP servers nor the gate until the user approves the project once. Global settings still
live in `~/.codex/config.toml`.

#### GitHub Copilot

```text
1. Repository custom instructions (.github/copilot-instructions.md), when present
2. AGENTS.md at the project root
3. Nested AGENTS.md files, nearest to the edited file wins
4. Path-specific instruction files (.github/instructions/*.instructions.md)
5. Skills from .agents/skills/, auto-discovered
```

This repo ships no `.github/copilot-instructions.md`, because VS Code agent mode, the CLI, the cloud agent, and the
JetBrains plugin in agent mode all read `AGENTS.md` directly. Add one yourself only if you target Copilot code review
(the pull-request bot) or the editors that read nothing else, such as Visual Studio, Xcode, and Eclipse.
