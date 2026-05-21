# Agent Standards & OpenSpec

This project imports a central set of AI agent standards from a shared repo:

- **Skills** in [.agents/skills/](../.agents/skills/): reusable procedural guidance loaded by all four supported
  agents.
- **Subagents** in [.claude/agents/](../.claude/agents/) and [.opencode/agents/](../.opencode/agents/): specialised
  agent definitions the main session delegates to.
- **Instructions** in [AGENTS.md](../AGENTS.md): shared rules auto-read by Kilo Code, OpenCode, and Codex CLI;
  imported into Claude Code via [.claude/CLAUDE.md](../.claude/CLAUDE.md).
- **OpenSpec** scaffold for spec-driven feature work.

---

### Agent standards import

The central AI standards are imported into this project via Git selective checkout. Only the production-ready folders
and template files are pulled in. The remote is configured as read-only: its push URL is set to an invalid address so
updates can be pulled but pushes are blocked.

#### Step 1, initial setup

Enable symlink support in Git (globally, or just for this repo):

```shell
git config --global core.symlinks true
```

```shell
git config core.symlinks true
```

Add the read-only remote and extract the standards:

```bash
git remote add agent-standards https://github.com/Lukk17/agent-standards
```

```bash
git remote set-url --push agent-standards no_push
```

```bash
git fetch agent-standards
```

```bash
git checkout agent-standards/master -- .agents .claude .opencode .codex docs/AGENT_TOOLING.md docs/MCP_SETUP.md AGENTS.md.example kilo.jsonc.example opencode.json.example .mcp.json.example
```

Commit the imported files when you're ready.

What this pulls:

- [.agents/skills/](../.agents/skills/): canonical skill files.
- [.claude/CLAUDE.md](../.claude/CLAUDE.md), [.claude/skills/](../.claude/skills/) (symlink),
  [.claude/agents/](../.claude/agents/): Claude Code wiring plus generated subagent files.
- [.opencode/skills/](../.opencode/skills/) (symlink), [.opencode/agents/](../.opencode/agents/): OpenCode subagent
  files, also read natively by Kilo Code.
- [.codex/skills/](../.codex/skills/) (symlink): Codex skill discovery path.
- [docs/AGENT_TOOLING.md](AGENT_TOOLING.md): this document, kept in sync with the central repo.
- [docs/MCP_SETUP.md](MCP_SETUP.md): human-side MCP setup guide (env vars, keys, OS-specific commands).
- [AGENTS.md.example](../AGENTS.md.example), [kilo.jsonc.example](../kilo.jsonc.example),
  [opencode.json.example](../opencode.json.example), [.mcp.json.example](../.mcp.json.example): templates you rename
  and customise.

What this does **not** pull:

- `subagents/` (canonical templates) and `tools/` (generator) live only in the agent-standards repo and are never
  imported into consumer projects.

Then copy the templates into place:

```bash
cp AGENTS.md.example AGENTS.md
```

```bash
cp kilo.jsonc.example kilo.jsonc
```

```bash
cp opencode.json.example opencode.json
```

```bash
cp .mcp.json.example .mcp.json
```

The `kilo.jsonc`, `opencode.json`, and `.mcp.json` copies are optional. Only `AGENTS.md` is required.

Copy the optional templates when you want shared MCP servers (see [MCP servers](#mcp-servers) below) or agent-specific
configuration.

#### Step 2, pulling future updates

```bash
git fetch agent-standards
```

```bash
git checkout agent-standards/master -- .agents .claude .opencode .codex docs/AGENT_TOOLING.md docs/MCP_SETUP.md .mcp.json.example opencode.json.example
```

Commit the refreshed files.

This refreshes:

- The skill catalogue in [.agents/skills/](../.agents/skills/).
- The regenerated subagent files in [.claude/agents/](../.claude/agents/) and [.opencode/agents/](../.opencode/agents/)
  (Kilo Code reads from the OpenCode directory natively).
- This tooling document and [docs/MCP_SETUP.md](MCP_SETUP.md).
- The MCP templates [.mcp.json.example](../.mcp.json.example) and [opencode.json.example](../opencode.json.example) so
  new servers and schema changes flow downstream.

The [AGENTS.md.example](../AGENTS.md.example) and [kilo.jsonc.example](../kilo.jsonc.example) templates and your local
`AGENTS.md` are intentionally not touched by updates. They belong to your project once copied.

---

### Subagents

Subagents are specialised agents the main session delegates to. They live in [.claude/agents/](../.claude/agents/) and
[.opencode/agents/](../.opencode/agents/). Kilo Code reads [.opencode/agents/](../.opencode/agents/) natively, so
OpenCode and Kilo share the same directory. Codex CLI has no per-agent file mechanism; it sees
[AGENTS.md](../AGENTS.md) plus skills only.

These files are **generated artifacts**. Do not hand-edit them. Your changes will be overwritten on the next pull. To
modify a subagent permanently, change its canonical source in the agent-standards repo (`subagents/<name>.md`), run
`python tools/gen-subagents.py` there, and re-import via Step 2.

The catalogue covers code review, architecture, debugging, stack experts (Java, Python, Flutter, Angular,
React/Next.js), DevOps, databases, APIs, security, design, accessibility, docs, content, and legal. List the active
set with `ls .claude/agents/` or browse the canonical sources in the agent-standards repo.

---

### Invoking skills

Skills are invoked from inside the agent shell using slash syntax. Examples:

```text
/code-reviewer
```

```text
/security-review
```

```text
/coding-standards
```

Depending on the agent UI, slash commands may appear as `/name` or `/name.md` in the autocomplete menu. Use whichever
your agent shows.

The full catalogue lives in [.agents/skills/](../.agents/skills/) (one directory per skill, each holding a
`SKILL.md`).

---

### MCP servers

Two committed templates ship the default MCP servers: [.mcp.json.example](../.mcp.json.example) (Claude Code) and the
`mcp` block in [opencode.json.example](../opencode.json.example) (OpenCode plus Kilo Code).

Copy them into place when you want the shared server set:

```bash
cp .mcp.json.example .mcp.json
```

```bash
cp opencode.json.example opencode.json
```

Full human setup (prerequisites, key acquisition, environment-variable export per OS, Claude Desktop and Codex CLI
global configs, verification) lives in [MCP_SETUP.md](MCP_SETUP.md). The AI agent does not run that setup; a person
configures the machine once.

Default servers: `context7`, `mongodb`, `grafana`, `playwright`, `chrome-devtools`, `redis`, `sonarqube`, `n8n`.

---

### OpenSpec integration

OpenSpec installs skills and commands into each agent's native directories.

#### How symlinks work with OpenSpec

The [.claude/skills/](../.claude/skills/), [.opencode/skills/](../.opencode/skills/), and
[.codex/skills/](../.codex/skills/) directories are symlinked to [.agents/skills/](../.agents/skills/). Kilo Code
reads [.agents/skills/](../.agents/skills/) natively without a symlink. When `openspec init` writes skills to any of
the symlinked directories, they land in [.agents/skills/](../.agents/skills/), the canonical location read by every
agent.

Commands are tool-specific (different formats per agent) and cannot be centralised. OpenSpec writes them into each
tool's native commands directory, which is expected.

#### Initialising OpenSpec

After running Step 1:

```bash
npm install -g @fission-ai/openspec@latest
```

```bash
openspec init --tools "claude,opencode,codex"
```

Kilo Code users who want OpenSpec slash-workflows specifically for Kilo can run a separate init pass:

```bash
openspec init --tools kilocode
```

That will create a `.kilocode/workflows/` directory in your project. The agent-standards repo itself does not ship a
`.kilocode/` directory; Kilo Code reads skills from [.agents/skills/](../.agents/skills/) and subagents from
[.opencode/agents/](../.opencode/agents/) natively.

What `openspec init` creates:

```text
openspec/
  config.yaml              # OpenSpec project config
  specs/                   # Living documentation of your system
  changes/                 # Active feature work
    archive/               # Completed changes

# Skills (via symlinks, all land in .agents/skills/):
.agents/skills/openspec-workflow/SKILL.md
.agents/skills/openspec-specs/SKILL.md

# Commands (tool-specific, not symlinked):
.claude/commands/opsx/propose.md
.opencode/commands/opsx-propose.md
```

Restart your IDE and terminal after initialisation.

#### Optional: install a custom schema for e2e capability tests

For projects that want spec-driven end-to-end capability tests through OpenSpec's lifecycle (`/opsx:new` → `/opsx:continue`
→ `/opsx:apply`), install the
[`e2e-runbooks`](https://github.com/Lukk17/openspec-schemas/tree/master/e2e-runbooks) schema from the
companion repo. OpenSpec has no schema-install CLI yet, so copy the bundle into the project's `openspec/schemas/`
directory.

Linux / macOS:

```bash
git clone --depth 1 https://github.com/Lukk17/openspec-schemas /tmp/lukk17-schemas
```

```bash
cp -r /tmp/lukk17-schemas/e2e-runbooks openspec/schemas/
```

```bash
rm -rf /tmp/lukk17-schemas
```

Windows (PowerShell 7+):

```powershell
git clone --depth 1 https://github.com/Lukk17/openspec-schemas $env:TEMP\lukk17-schemas
```

```powershell
Copy-Item -Recurse $env:TEMP\lukk17-schemas\e2e-runbooks openspec\schemas\
```

```powershell
Remove-Item -Recurse -Force $env:TEMP\lukk17-schemas
```

Use it per-change:

```bash
openspec new --schema e2e-runbooks "add weather-mcp capability test"
```

Or set as the project default in `openspec/config.yaml`:

```yaml
default_schema: e2e-runbooks
```

The methodology behind the schema is documented in the [`e2e-runbooks` skill](../.agents/skills/e2e-runbooks/SKILL.md);
the schema operationalises the same methodology for OpenSpec users. Either works alone, both reinforce each other.

#### Tool directories reference

| Tool        | Skills written to                                          | Commands written to                                                         |
| ----------- | ---------------------------------------------------------- | --------------------------------------------------------------------------- |
| Claude Code | `.claude/skills/openspec-*/` → `.agents/skills/`           | `.claude/commands/opsx/*.md`                                                |
| Kilo Code   | reads `.agents/skills/` natively (no symlink needed)       | `.kilocode/workflows/opsx-*.md` (only if you ran `--tools kilocode`)        |
| OpenCode    | `.opencode/skills/openspec-*/` → `.agents/skills/`         | `.opencode/commands/opsx-*.md`                                              |
| Codex       | `.codex/skills/openspec-*/` → `.agents/skills/`            | `$CODEX_HOME/prompts/opsx-*.md`                                             |

#### Command syntax variations

OpenSpec generates files for two agent architectures:

- **Standalone Markdown commands**: agents that read flat files show commands with extensions
  (e.g. `/opsx-propose.md`).
- **Agent skills**: agents that parse semantic `SKILL.md` metadata or have native integration use slash syntax
  (e.g. `/opsx:propose`).

Use whichever form appears in your agent's autocomplete menu.

---

### OpenSpec workflow

#### 0. Run the coding agent

```shell
claude
```

#### 1. Propose a change

```text
/opsx:propose add dark mode support
```

```text
/opsx-propose.md add dark mode support
```

The agent creates the proposal, design, and implementation tasks under `openspec/changes/`.

#### 2. Apply the code

Review the generated `tasks.md` (edit directly or have the agent revise it).

Then:

```text
/opsx:apply
```

```text
/opsx-apply.md
```

The agent writes the code and checks off boxes in `tasks.md`.

#### 3. Verify and refine

If bugs occur or tests fail, pass logs back:

```text
/opsx:verify The toggle button is invisible on mobile. Fix it.
```

```text
/opsx-verify.md The toggle button is invisible on mobile. Fix it.
```

#### 4. Archive the change

```text
/opsx:archive
```

```text
/opsx-archive.md
```

The agent merges delta specs into `openspec/specs/` and moves the change folder to `openspec/changes/archive/`.
