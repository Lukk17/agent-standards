# Agent Standards and OpenSpec

This project imports a central set of AI agent standards from a shared repository:

- **Skills** in [.agents/skills/](../.agents/skills/): reusable procedural guidance. Codex, OpenCode, Kilo Code, and
  every GitHub Copilot surface read this directory natively. Claude Code reaches it through a symlink.
- **Subagents** generated into [.claude/agents/](../.claude/agents/) (Claude markdown),
  [.agents/agents/](../.agents/agents/) (OpenCode markdown, shared by OpenCode and Kilo Code through symlinks),
  [.codex/agents/](../.codex/agents/) (TOML), and [.github/agents/](../.github/agents/) (`*.agent.md`).
- **Instructions** in [AGENTS.md](../AGENTS.md): shared rules read natively by Codex, OpenCode, Kilo Code, and GitHub
  Copilot, and imported into Claude Code through [.claude/CLAUDE.md](../.claude/CLAUDE.md).
- **A preflight gate** in [.agents/hooks/preflight_gate.py](../.agents/hooks/preflight_gate.py), one shared rule wired
  into every agent's hook surface, that actually blocks work rather than just asking for it.
- **MCP servers** in four real config files, one per agent surface.
- **OpenSpec**, optional, for spec-driven feature work.

---

### Importing the standards

The standards arrive through a Git selective checkout. Only production-ready folders and the one template file are
pulled. The remote is read-only: its push URL is set to an invalid address, so you can pull updates but never push.

#### Step 0, Windows only

Three paths in this setup are symlinks (`.claude/skills`, `.opencode/agents`, `.kilo/agents`). Without symlink support
git writes them as ordinary text files holding the target path, and the agents that depend on them silently see
nothing. Turn on Developer Mode (Settings, System, For developers), then tell git to honour symlinks.

PowerShell, this repository only:

```powershell
git config core.symlinks true
```

PowerShell, globally:

```powershell
git config --global core.symlinks true
```

Unix shells need nothing here.

#### Step 1, initial import

Add the read-only remote. PowerShell or Unix shell, same command:

```bash
git remote add agent-standards https://github.com/Lukk17/agent-standards
```

Block pushes to it:

```bash
git remote set-url --push agent-standards no_push
```

Fetch:

```bash
git fetch agent-standards
```

Pull the production-ready paths:

```bash
git checkout agent-standards/master -- .agents .claude .opencode .kilo .codex .github/agents .github/hooks .vscode/mcp.json .mcp.json opencode.json docs/AGENT_TOOLING.md docs/MCP_SETUP.md docs/AGENTS-UPDATE.md AGENTS.md.example
```

Rename the one template. PowerShell:

```powershell
Rename-Item AGENTS.md.example AGENTS.md
```

Unix shell:

```bash
mv AGENTS.md.example AGENTS.md
```

That is the whole setup. Commit when you are ready.

What you just pulled:

- [.agents/skills/](../.agents/skills/), the canonical skills, plus [.agents/agents/](../.agents/agents/), the shared
  OpenCode-format subagents, [.agents/hooks/](../.agents/hooks/), the gate script and the formatting checker, and
  [.agents/plugin/hooks.js](../.agents/plugin/hooks.js), the OpenCode and Kilo adapter for the gate.
- [.claude/](../.claude/): the `CLAUDE.md` bridge, the `skills` symlink, the generated `agents/` tree, and
  `settings.json` carrying the Claude Code hooks.
- `.opencode/agents` and `.kilo/agents`: symlinks into [.agents/agents/](../.agents/agents/). One tree, two agents.
- [.codex/](../.codex/): the generated TOML custom agents and `config.toml`, which holds both the Codex MCP servers
  and the Codex gate hooks inline.
- [.github/agents/](../.github/agents/) and [.github/hooks/preflight.json](../.github/hooks/preflight.json): Copilot
  subagents and its hook configuration.
- [.mcp.json](../.mcp.json), [opencode.json](../opencode.json), and [.vscode/mcp.json](../.vscode/mcp.json): the
  remaining MCP config files. These are real files, ready to use, not templates.
- The three shipped documents, and [AGENTS.md.example](../AGENTS.md.example) to rename.

What you did not pull, and never will: the `subagents/` canonical source and the `tools/` generator. Both stay
upstream.

Verify the symlinks survived before you go further. PowerShell:

```powershell
Get-Item .claude/skills, .opencode/agents, .kilo/agents | Select-Object Name, LinkType, Target
```

Unix shell:

```bash
ls -l .claude/skills .opencode/agents .kilo/agents
```

If any of them came through as a small text file instead of a link, go back to Step 0 and redo the checkout.

#### Step 2, pulling future updates

[docs/AGENTS-UPDATE.md](AGENTS-UPDATE.md) ships from upstream, holds the per-shell update commands, and refreshes
itself on every run. Open it and run the block for your shell. It refreshes the shipped documents, the gate script and
plugin, the Copilot hook file, and only the skills and subagents already present in your tree. Nothing new appears
behind your back.

It deliberately leaves your `AGENTS.md`, your MCP config files, `.claude/settings.json`, and `.claude/CLAUDE.md`
alone. Those are yours.

---

### The preflight gate

The `## Required opening move` section of [AGENTS.md](../AGENTS.md) is the canonical rule: before code work, name the
skills and subagents that own the task and invoke them, or say none apply and why. A rule read once at session start
loses its grip over a long session, so the gate is also enforced mechanically.

One shared script does the deciding, [.agents/hooks/preflight_gate.py](../.agents/hooks/preflight_gate.py). It reads
the hook payload and denies two things:

- A source-file edit coming straight from the main thread. The main thread delegates to a subagent that owns the area.
- Any edit from a subagent whose own definition declares no skills. Spawn a specialist that names its skills instead.

Markdown, configuration files, and anything under `docs/` stay editable from the main thread, so writing a note or
adjusting a config never trips it. Every error path allows the call, because a gate that breaks a session is worse
than no gate.

Each agent wires that same script through its own hook surface:

| Agent | Where the hooks live | What it can stop |
| --- | --- | --- |
| Claude Code | [.claude/settings.json](../.claude/settings.json) | blocks the tool call, injects the gate every turn, and blocks a reply through a `Stop` hook |
| Codex | inline `[[hooks.*]]` tables in [.codex/config.toml](../.codex/config.toml) | blocks the tool call, injects the gate every turn and on subagent start |
| OpenCode | plugin [.agents/plugin/hooks.js](../.agents/plugin/hooks.js), declared in [opencode.json](../opencode.json) | blocks the tool call |
| Kilo Code | the same plugin, the same declaration | blocks the tool call |
| GitHub Copilot | [.github/hooks/preflight.json](../.github/hooks/preflight.json) | blocks the tool call, injects the gate once per session and on subagent start |

Two limits are worth knowing before you trust the gate too far. GitHub Copilot's pre-tool payload carries no agent
identifier, so it cannot tell a subagent from the main thread and the delegation rule cannot be applied selectively
there. OpenCode and Kilo Code have no event that can block a reply, so on those two the enforcement is the pre-tool
block plus per-agent tool permissions and nothing after the fact. Claude Code is the only surface that can stop a
finished reply.

Codex loads its whole `.codex/` layer, hooks included, only after you trust the project once.

---

### Subagents

Subagents are specialised agents the main session delegates to. One canonical file per agent fans out to four trees:
[.claude/agents/](../.claude/agents/) in Claude markdown, [.agents/agents/](../.agents/agents/) in OpenCode markdown,
[.codex/agents/](../.codex/agents/) in TOML, and [.github/agents/](../.github/agents/) as `*.agent.md`. OpenCode and
Kilo Code both read the OpenCode format and both follow symlinks when scanning an agent directory, so `.opencode/agents`
and `.kilo/agents` are symlinks into the shared tree rather than two more copies. Claude Code, Codex, and Copilot each
need their own format, which is why the other three trees exist at all.

These are **generated artifacts**. Do not hand-edit them, your changes vanish on the next pull. To change a subagent
for good, edit its canonical source in the agent-standards repository (`subagents/<name>.md`), run
`python tools/gen_subagents.py` there, and re-import through Step 2.

The catalogue covers code review, architecture, debugging, stack specialists (Java, Python, Flutter, Angular, React
and Next.js), DevOps, databases, APIs, security, design, accessibility, documentation, content, and legal drafting.

List what you have. PowerShell:

```powershell
Get-ChildItem .agents/agents -Name
```

Unix shell:

```bash
ls .agents/agents
```

---

### GitHub Copilot

Copilot reads this setup natively across its surfaces, so it needs no bridge instruction file.

- **Skills**: read from [.agents/skills/](../.agents/skills/) natively in VS Code, the JetBrains plugin, the CLI, and
  the cloud agent. No symlink, no copy.
- **Subagents**: [.github/agents/](../.github/agents/) as `*.agent.md`, generated from the same canonical sources as
  every other tree.
- **Instructions**: [AGENTS.md](../AGENTS.md) is read natively by VS Code agent mode, the CLI, and the cloud agent.
  The JetBrains plugin reads it in agent mode too, per the March 2026 JetBrains changelog, even though GitHub's own
  published support matrix still leaves JetBrains out of the `AGENTS.md` column. The behaviour is real, the
  documentation is behind. Add a `.github/copilot-instructions.md` yourself only if you target Copilot code review or
  the editors that read nothing else (Visual Studio, Xcode, Eclipse).
- **MCP**: Copilot in VS Code reads [.vscode/mcp.json](../.vscode/mcp.json), key `servers`. The Copilot CLI reads the
  project [.mcp.json](../.mcp.json), the same file Claude Code uses, and it is the only Copilot surface that can. The
  JetBrains plugin reads a global file only, and the cloud agent takes JSON pasted into a repository settings page.
  Both manual blocks are in [MCP_SETUP.md](MCP_SETUP.md).
- **Preflight**: [.github/hooks/preflight.json](../.github/hooks/preflight.json), camelCase events, injecting the gate
  on `sessionStart` and `subagentStart` and blocking on `preToolUse`. The pre-tool payload carries no agent
  identifier, so the delegation half of the gate is weaker on Copilot than elsewhere. Copilot in JetBrains fires only
  six events, has no subagent event, and reads hook configuration only from `.github/hooks/`.

---

### Invoking skills

Skills are invoked from inside the agent shell with slash syntax:

```text
/code-reviewer
```

```text
/security-review
```

```text
/coding-standards
```

Depending on the agent, the autocomplete may show `/name` or `/name.md`. Use whichever form yours offers. The full
catalogue is [.agents/skills/](../.agents/skills/), one directory per skill, each holding a `SKILL.md`.

---

### MCP servers

Four real config files ship the same eight servers, one per agent surface:

| File | Schema key | Serves |
| --- | --- | --- |
| [.mcp.json](../.mcp.json) | `mcpServers` | Claude Code and the GitHub Copilot CLI |
| [opencode.json](../opencode.json) | `mcp` | OpenCode and Kilo Code |
| [.codex/config.toml](../.codex/config.toml) | `[mcp_servers.*]` | Codex |
| [.vscode/mcp.json](../.vscode/mcp.json) | `servers` | GitHub Copilot in VS Code |

Only the file name, the schema key, the `type` value, and the environment-variable syntax differ. Nothing needs
renaming, they arrive ready to use. Two Copilot surfaces get no file at all, the JetBrains plugin because it reads a
global path only, and the cloud agent because its configuration lives in a repository settings page.

Kilo Code accepts `opencode.json` as a project config filename, which is how one file serves both it and OpenCode.
Kilo does not expand `{env:VAR}` in project-level config, though, so Kilo users see the placeholder literally and have
to paste real values into their local copy.

The full human setup, prerequisites, key acquisition, environment variables per operating system, the two manual
Copilot blocks, and verification, lives in [MCP_SETUP.md](MCP_SETUP.md). A person does that once per machine, not the
agent.

---

### OpenSpec integration

OpenSpec is a spec-driven workflow: propose a change, let the agent write the tasks, apply them, then archive the
result into living specifications. It is optional, and it is entirely a consumer concern. The agent-standards
repository ships no `openspec-*` skills of its own.

#### Initialising it

Install it globally. PowerShell:

```powershell
npm install -g @fission-ai/openspec@latest
```

Unix shell:

```bash
npm install -g @fission-ai/openspec@latest
```

Initialise with the vendor-neutral target, and only that one. PowerShell:

```powershell
openspec init --tools agents
```

Unix shell:

```bash
openspec init --tools agents
```

`--tools agents` writes OpenSpec's skills into `.agents/skills/` and creates no per-tool directories. That single
target covers every agent here, because Codex, OpenCode, Kilo Code, and Copilot all read `.agents/skills/` natively
and Claude Code reaches the same files through its `.claude/skills` symlink. Any per-tool target would fragment a
layout built to have exactly one skills directory.

Avoid `--tools kilocode` in particular. OpenSpec 1.10.0 still hardcodes the old `.kilocode` directory for its Kilo
target, and Kilo Code has since moved its configuration root to `.kilo`, so that target writes into a directory
nothing reads.

What the init creates:

```text
openspec/
  config.yaml              OpenSpec project config
  specs/                   living documentation of your system
  changes/                 active feature work
    archive/               completed changes
.agents/skills/openspec-workflow/SKILL.md
.agents/skills/openspec-specs/SKILL.md
```

Restart your editor and terminal afterwards so the new skills are picked up.

Slash-command names still vary per agent, because command formats genuinely differ between tools. Agents that read
flat command files show `/opsx-propose.md`; agents with native skill integration show `/opsx:propose`. Use whichever
appears in your autocomplete.

#### Optional, a custom schema for end-to-end capability tests

For projects that want spec-driven end-to-end capability tests inside the OpenSpec lifecycle, install the
[e2e-runbooks](https://github.com/Lukk17/openspec-schemas/tree/master/e2e-runbooks) schema from the companion
repository. OpenSpec has no schema-install command yet, so you copy the bundle into `openspec/schemas/`.

Unix shell:

```bash
git clone --depth 1 https://github.com/Lukk17/openspec-schemas /tmp/lukk17-schemas
```

```bash
cp -r /tmp/lukk17-schemas/e2e-runbooks openspec/schemas/
```

```bash
rm -rf /tmp/lukk17-schemas
```

PowerShell:

```powershell
git clone --depth 1 https://github.com/Lukk17/openspec-schemas $env:TEMP\lukk17-schemas
```

```powershell
Copy-Item -Recurse $env:TEMP\lukk17-schemas\e2e-runbooks openspec\schemas\
```

```powershell
Remove-Item -Recurse -Force $env:TEMP\lukk17-schemas
```

Use it for one change:

```bash
openspec new --schema e2e-runbooks "add weather-mcp capability test"
```

Or make it the project default in `openspec/config.yaml`:

```yaml
default_schema: e2e-runbooks
```

The methodology behind the schema is documented in the
[e2e-runbooks skill](../.agents/skills/e2e-runbooks/SKILL.md). Either works alone, and they reinforce each other.

---

### OpenSpec workflow

Start the agent:

```shell
claude
```

Propose a change:

```text
/opsx:propose add dark mode support
```

The agent writes the proposal, the design, and the task list under `openspec/changes/`. Review the generated
`tasks.md`, edit it directly or have the agent revise it, then apply:

```text
/opsx:apply
```

The agent writes the code and ticks the boxes in `tasks.md`. When something breaks, hand the evidence back:

```text
/opsx:verify The toggle button is invisible on mobile. Fix it.
```

Archive when it is done:

```text
/opsx:archive
```

The agent merges the delta specifications into `openspec/specs/` and moves the change folder into
`openspec/changes/archive/`.
