# Agent Standards & OpenSpec

This project imports a central set of AI agent standards from a shared repo:

- **Skills** in [.agents/skills/](../.agents/skills/): reusable procedural guidance every supported agent reads
  natively, except Claude Code which reaches them through a symlink.
- **Subagents** generated per tool into [.claude/agents/](../.claude/agents/),
  [.opencode/agents/](../.opencode/agents/), `.kilocode/agents/`, `.codex/agents/` (TOML), and
  [.github/agents/](../.github/agents/) (`*.agent.md`): specialised agent definitions the main session delegates to.
- **Instructions** in [AGENTS.md](../AGENTS.md): shared rules auto-read by Kilo Code, OpenCode, Codex, and GitHub
  Copilot (JetBrains, VS Code, and CLI); imported into Claude Code via [.claude/CLAUDE.md](../.claude/CLAUDE.md).
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
git checkout agent-standards/master -- .agents .claude .opencode .codex .kilocode .github/agents .github/hooks .vscode/mcp.json.example docs/AGENT_TOOLING.md docs/MCP_SETUP.md docs/AGENTS-UPDATE.md AGENTS.md.example opencode.json.example .mcp.json.example
```

Commit the imported files when you're ready.

What this pulls:

- [.agents/skills/](../.agents/skills/): canonical skill files.
- [.claude/CLAUDE.md](../.claude/CLAUDE.md), [.claude/skills/](../.claude/skills/) (symlink),
  [.claude/agents/](../.claude/agents/): Claude Code wiring plus generated subagent files.
  [.claude/settings.json](../.claude/settings.json): the `UserPromptSubmit` preflight hook.
- [.opencode/agents/](../.opencode/agents/): OpenCode subagent files. [.opencode/plugin/](../.opencode/plugin/): the
  preflight plugin. OpenCode reads skills from [.agents/skills/](../.agents/skills/) natively, so there is no symlink.
- `.codex/`: generated Codex custom agents (`agents/*.toml`), the preflight hook (`hooks.json`), and the project MCP
  template (`config.toml.example`). Codex reads skills from [.agents/skills/](../.agents/skills/) natively.
- `.kilocode/`: generated Kilo subagents (`agents/*.md`, OpenCode format), the Kilo preflight rule
  (`rules/00-preflight.md`, the extension has no hook surface), and the Kilo config templates (`kilo.jsonc.example`,
  carrying instructions plus MCP for the CLI, and `mcp.json.example` for the extension's MCP).
- `.github/agents/`: generated GitHub Copilot subagent files (`*.agent.md`), read by Copilot in VS Code, the JetBrains
  plugin, and the Copilot CLI. `.github/hooks/preflight.json`: the Copilot `sessionStart` preflight hook. Copilot reads
  `AGENTS.md` and `.agents/skills/` natively, so no bridge instruction file ships.
- [.vscode/mcp.json.example](../.vscode/mcp.json.example): the GitHub Copilot MCP template you copy to
  `.vscode/mcp.json`.
- [docs/AGENT_TOOLING.md](AGENT_TOOLING.md): this document, kept in sync with the central repo.
- [docs/MCP_SETUP.md](MCP_SETUP.md): human-side MCP setup guide (env vars, keys, OS-specific commands).
- [docs/AGENTS-UPDATE.md](AGENTS-UPDATE.md): the per-OS selective update procedure, kept in sync with the central
  repo (it refreshes itself).
- [AGENTS.md.example](../AGENTS.md.example), [opencode.json.example](../opencode.json.example),
  [.mcp.json.example](../.mcp.json.example), the `.kilocode/*.example` templates
  (`.kilocode/kilo.jsonc.example`, `.kilocode/mcp.json.example`), `.codex/config.toml.example`, and
  [.vscode/mcp.json.example](../.vscode/mcp.json.example): templates you rename and customise.

What this does **not** pull:

- `subagents/` (canonical templates) and `tools/` (generator) live only in the agent-standards repo and are never
  imported into consumer projects.

Then rename each template you activate to its real name, dropping the `.example` suffix. The `.example` suffix is only
meaningful upstream; in your project a rename leaves a clean active file, and any template still named `.example` marks
one you have not activated yet. Stage and commit with `git add -A` afterwards so the renames are recorded.

`AGENTS.md` is required:

```bash
mv AGENTS.md.example AGENTS.md
```

```bash
mv .kilocode/kilo.jsonc.example .kilocode/kilo.jsonc
```

```bash
mv opencode.json.example opencode.json
```

```bash
mv .mcp.json.example .mcp.json
```

For the Kilo Code VS Code extension, MCP servers go in `.kilocode/mcp.json`:

```bash
mv .kilocode/mcp.json.example .kilocode/mcp.json
```

For GitHub Copilot in VS Code, MCP servers go in `.vscode/mcp.json`:

```bash
mv .vscode/mcp.json.example .vscode/mcp.json
```

For Codex, project MCP servers go in `.codex/config.toml`:

```bash
mv .codex/config.toml.example .codex/config.toml
```

The `.kilocode/kilo.jsonc`, `opencode.json`, `.mcp.json`, `.kilocode/mcp.json`, `.codex/config.toml`, and
`.vscode/mcp.json` renames are optional; only `AGENTS.md` is required. Rename the optional templates when you want
shared MCP servers (see [MCP servers](#mcp-servers) below) or agent-specific configuration. One exception: if your team
keeps real secrets in an MCP config and gitignores it, `cp` that one template instead of renaming, so the committed
`.example` stays as the tracked reference.

#### Step 2, pulling future updates

This project ships [docs/AGENTS-UPDATE.md](AGENTS-UPDATE.md) from upstream. It holds the per-OS update commands and
refreshes itself on every run, so it stays current with the central repo.

Open [docs/AGENTS-UPDATE.md](AGENTS-UPDATE.md) and run the commands for your shell (Unix bash/zsh or PowerShell).
They:

- Refresh the shipped docs: [AGENT_TOOLING.md](AGENT_TOOLING.md), [MCP_SETUP.md](MCP_SETUP.md), and
  [AGENTS-UPDATE.md](AGENTS-UPDATE.md) itself.
- Enumerate the skills already in [.agents/skills/](../.agents/skills/) and pull only those.
- Enumerate the subagents already in the generated trees ([.claude/agents/](../.claude/agents/),
  [.opencode/agents/](../.opencode/agents/), `.kilocode/agents/`, `.codex/agents/`, and
  [.github/agents/](../.github/agents/)) and pull only those.

Commit the refreshed files when ready.

Files intentionally NOT touched by the update: the [.claude/skills/](../.claude/skills/) symlink (the only skill
symlink left, since every other agent reads [.agents/skills/](../.agents/skills/) natively),
[.claude/CLAUDE.md](../.claude/CLAUDE.md), [AGENTS.md.example](../AGENTS.md.example),
the `.kilocode/*.example` templates, [.mcp.json.example](../.mcp.json.example),
[opencode.json.example](../opencode.json.example), and your customised `AGENTS.md`. These are templates and personal
config set once at initial setup.

If [docs/AGENTS-UPDATE.md](AGENTS-UPDATE.md) is missing (the project was imported before this doc shipped), pull it
with a one-off `git checkout agent-standards/master -- docs/AGENTS-UPDATE.md`, then use it for every later refresh.

---

### Subagents

Subagents are specialised agents the main session delegates to. One canonical file per agent fans out to five
per-tool trees: [.claude/agents/](../.claude/agents/), [.opencode/agents/](../.opencode/agents/), `.kilocode/agents/`
(OpenCode-format markdown, read natively by Kilo Code), `.codex/agents/` (TOML custom agents read by Codex), and
[.github/agents/](../.github/agents/) (`*.agent.md`, read by GitHub Copilot in VS Code, the JetBrains plugin, and the
Copilot CLI). No shared subagent format exists across the tools, which is why the generator emits five trees.

These files are **generated artifacts**. Do not hand-edit them. Your changes will be overwritten on the next pull. To
modify a subagent permanently, change its canonical source in the agent-standards repo (`subagents/<name>.md`), run
`python tools/gen_subagents.py` there, and re-import via Step 2.

The catalogue covers code review, architecture, debugging, stack experts (Java, Python, Flutter, Angular,
React/Next.js), DevOps, databases, APIs, security, design, accessibility, docs, content, and legal. List the active
set with `ls .claude/agents/` or browse the canonical sources in the agent-standards repo.

---

### Preflight enforcement adapters

The `## Required opening move` section in [AGENTS.md](../AGENTS.md) is the canonical rule: name and invoke the
owning skill(s) and subagent(s) before code work, or state none apply. A rule read once at session start loses
salience over a long session, so the gate is re-injected per turn wherever the runtime supports it:

| Agent | Adapter | Mechanism |
| ----- | ------- | --------- |
| Claude Code | [.claude/settings.json](../.claude/settings.json) | `UserPromptSubmit` hook, fires every turn |
| Codex | `.codex/hooks.json` | `UserPromptSubmit` hook, injects `additionalContext` every turn |
| OpenCode | [.opencode/plugin/preflight.js](../.opencode/plugin/preflight.js) | `chat.system.transform` plugin hook |
| Kilo Code | `.kilocode/rules/00-preflight.md` | rule file loaded into context per task |
| GitHub Copilot | `.github/hooks/preflight.json` | `sessionStart` hook (once per session), gate otherwise in `AGENTS.md` |

Claude Code, Codex, and OpenCode re-inject the gate every turn through a hook or plugin. Kilo Code loads it as a rule
per task. GitHub Copilot cannot re-inject per turn, because its `userPromptSubmitted` hook output is discarded, so it
fires a `sessionStart` hook once per session and otherwise relies on the gate in `AGENTS.md`, which it reads natively.
Keep every wording in sync; the canonical text is the `AGENTS.md` section. The Claude `settings.json` ships the hook
only; if you add project-local permissions there, the update flow leaves your file untouched (it is not in the refresh
list), so merge hook changes by hand on a major update.

---

### GitHub Copilot

GitHub Copilot reads this setup natively across surfaces, so it needs no bridge instruction file.

- Skills: Copilot reads [.agents/skills/](../.agents/skills/) natively in VS Code, the JetBrains plugin, and the
  Copilot CLI (skills went GA in JetBrains plugin 1.10.0, June 2026), the same canonical directory every other agent
  uses. No symlink or copy needed.
- Subagents: generated to [.github/agents/](../.github/agents/) as `*.agent.md` files, read by Copilot in VS Code, the
  JetBrains plugin (custom agents GA since plugin 1.6.1, March 2026), and the Copilot CLI. They come from the same
  canonical `subagents/*.md` sources as the other trees.
- Instructions: the JetBrains plugin (since 1.6.1), VS Code, and the CLI all read [AGENTS.md](../AGENTS.md) natively,
  so no `.github/copilot-instructions.md` ships. The only surfaces that would still need one are Copilot code review
  (the GitHub pull-request bot) and the IDEs that read only it (Visual Studio, Xcode, Eclipse); add one yourself if you
  target those.
- MCP: Copilot in VS Code reads `.vscode/mcp.json` with the top-level `servers` key. Copy it from
  [.vscode/mcp.json.example](../.vscode/mcp.json.example). The JetBrains plugin reads MCP only from the global file
  `~/.config/github-copilot/intellij/mcp.json` (no per-project file exists, and GitHub documents only the in-IDE UI,
  not the path), so no JetBrains template ships; see [MCP_SETUP.md](MCP_SETUP.md).
- Preflight gate: Copilot cannot re-inject per turn (its `userPromptSubmitted` hook output is discarded), so the gate
  ships as a `sessionStart` hook in `.github/hooks/preflight.json` (injected once per session) and otherwise rides in
  `AGENTS.md`, which Copilot reads natively. Per-turn enforcement is not yet possible on Copilot.

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

The committed templates ship the same default MCP servers, one per agent surface:
[.mcp.json.example](../.mcp.json.example) (Claude Code), the `mcp` block in
[opencode.json.example](../opencode.json.example) (OpenCode),
[.kilocode/mcp.json.example](../.kilocode/mcp.json.example) (Kilo Code VS Code extension), the `mcp` block in
[.kilocode/kilo.jsonc.example](../.kilocode/kilo.jsonc.example) (Kilo CLI),
[.vscode/mcp.json.example](../.vscode/mcp.json.example) (GitHub Copilot in VS Code), and the `[mcp_servers]` tables in
[.codex/config.toml.example](../.codex/config.toml.example) (Codex). Only the top-level key, the `type` value, and the
env-var syntax differ per surface.

Rename the ones you use into place (or `cp` instead for any config you gitignore, so the template stays committed):

```bash
mv .mcp.json.example .mcp.json
```

```bash
mv opencode.json.example opencode.json
```

```bash
mv .kilocode/mcp.json.example .kilocode/mcp.json
```

```bash
mv .vscode/mcp.json.example .vscode/mcp.json
```

```bash
mv .codex/config.toml.example .codex/config.toml
```

Full human setup (prerequisites, key acquisition, environment-variable export per OS, Claude Desktop and Codex global
configs, the JetBrains Copilot MCP path, verification, and the full default-server list) lives in
[MCP_SETUP.md](MCP_SETUP.md). The AI agent does not run that setup; a person configures the machine once.

---

### OpenSpec integration

OpenSpec installs skills and commands into each agent's native directories.

#### How skills land with OpenSpec

Only [.claude/skills/](../.claude/skills/) is symlinked to [.agents/skills/](../.agents/skills/), because Claude Code
is the one agent that does not read the canonical directory natively. OpenCode, Kilo Code, Codex, and GitHub Copilot
all read [.agents/skills/](../.agents/skills/) directly. When `openspec init` writes skills through the Claude symlink
they land in [.agents/skills/](../.agents/skills/); for the other tools OpenSpec writes into that tool's own skills
directory, which the tool still reads natively.

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

That will create a `.kilocode/workflows/` directory in your project. The agent-standards repo already ships a
`.kilocode/` directory (the preflight rule, config templates, and the generated `.kilocode/agents/` subagents); Kilo
Code reads skills from [.agents/skills/](../.agents/skills/) natively and its subagents from `.kilocode/agents/`.

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

For projects that want spec-driven end-to-end capability tests through OpenSpec's lifecycle
(`/opsx:new` → `/opsx:continue` → `/opsx:apply`), install the
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
| OpenCode    | `.opencode/skills/openspec-*/` (read natively)            | `.opencode/commands/opsx-*.md`                                              |
| Codex       | reads `.agents/skills/` natively (no symlink needed)       | `$CODEX_HOME/prompts/opsx-*.md`                                             |

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
