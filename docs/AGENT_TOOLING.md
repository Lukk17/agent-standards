# Agent Standards & OpenSpec

This project imports a central set of AI agent standards from a shared repo:

- **Skills** in `.agents/skills/` — reusable procedural guidance loaded by all four supported agents.
- **Subagents** in `.claude/agents/` and `.opencode/agents/` — specialised agent definitions the main session delegates to.
- **Instructions** in `AGENTS.md` — shared rules auto-read by Kilo Code, OpenCode, and Codex CLI; imported into Claude Code via `.claude/CLAUDE.md`.
- **OpenSpec** scaffold for spec-driven feature work.

---

## Agent standards import

The central AI standards are imported into this project via Git selective checkout. Only the production-ready folders and template files are pulled in. The remote is configured as read-only — its push URL is set to an invalid address so updates can be pulled but pushes are blocked.

### Step 1 — Initial setup

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
git checkout agent-standards/master -- .agents .claude .opencode .codex docs/AGENT_TOOLING.md AGENTS.md.example kilo.jsonc.example opencode.json.example
```

```bash
git commit -m "Import central agent-standards"
```

What this pulls:

- `.agents/skills/` — 73 canonical skill files.
- `.claude/CLAUDE.md`, `.claude/skills/` (symlink), `.claude/agents/` — Claude Code wiring + 26 subagent files.
- `.opencode/skills/` (symlink), `.opencode/agents/` — OpenCode subagent files, also read natively by Kilo Code.
- `.codex/skills/` (symlink) — Codex skill discovery path.
- `docs/AGENT_TOOLING.md` — this document, kept in sync with the central repo.
- `AGENTS.md.example`, `kilo.jsonc.example`, `opencode.json.example` — templates you rename and customise.

What this does **not** pull:

- `subagents/` (canonical templates) and `tools/` (generator) live only in the agent-standards repo and are never imported into consumer projects.

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

The two `.example` configs are optional — copy them only if you need extra agent-specific configuration.

### Step 2 — Pulling future updates

```bash
git fetch agent-standards
```

```bash
git checkout agent-standards/master -- .agents .claude .opencode .codex docs/AGENT_TOOLING.md
```

```bash
git commit -m "Update AI standards from central repository"
```

This refreshes:

- The skill catalogue (`.agents/skills/`).
- The regenerated subagent files (`.claude/agents/` and `.opencode/agents/` — Kilo Code reads from the OpenCode directory natively).
- This tooling document.

The `.example` templates and your local `AGENTS.md` are intentionally not touched by updates — they belong to your project once copied.

---

## Subagents

Subagents are specialised agents the main session delegates to. They live in `.claude/agents/<name>.md` and `.opencode/agents/<name>.md`. Kilo Code reads `.opencode/agents/` natively, so OpenCode and Kilo share the same directory. Codex CLI has no per-agent file mechanism — it sees `AGENTS.md` plus skills only.

These files are **generated artifacts**. Do not hand-edit them — your changes will be overwritten on the next pull. To modify a subagent permanently, change its canonical source in the agent-standards repo (`subagents/<name>.md`), run `python tools/gen-subagents.py` there, and re-import via Step 2.

The 26 subagents cover code review, architecture, debugging, stack experts (Java, Python, Flutter, Angular, React/Next.js), DevOps, databases, APIs, security, design, accessibility, docs, content, and legal. List them with `ls .claude/agents/` or browse them in the agent-standards repo.

---

## OpenSpec integration

OpenSpec installs skills and commands into each agent's native directories.

### How symlinks work with OpenSpec

The `.claude/skills/`, `.opencode/skills/`, and `.codex/skills/` directories are symlinked to `.agents/skills/`. Kilo Code reads `.agents/skills/` natively without a symlink. When `openspec init` writes skills to any of the symlinked directories, they land in `.agents/skills/` — the canonical location read by every agent.

Commands are tool-specific (different formats per agent) and cannot be centralised. OpenSpec writes them into each tool's native commands directory, which is expected.

### Initialising OpenSpec

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

That will create a `.kilocode/workflows/` directory in your project. The agent-standards repo itself does not ship a `.kilocode/` directory — Kilo Code reads skills from `.agents/skills/` and subagents from `.opencode/agents/` natively.

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

### Tool directories reference

| Tool        | Skills written to                                          | Commands written to                                                         |
| ----------- | ---------------------------------------------------------- | --------------------------------------------------------------------------- |
| Claude Code | `.claude/skills/openspec-*/` → `.agents/skills/`           | `.claude/commands/opsx/*.md`                                                |
| Kilo Code   | reads `.agents/skills/` natively (no symlink needed)       | `.kilocode/workflows/opsx-*.md` (only if you ran `--tools kilocode`)        |
| OpenCode    | `.opencode/skills/openspec-*/` → `.agents/skills/`         | `.opencode/commands/opsx-*.md`                                              |
| Codex       | `.codex/skills/openspec-*/` → `.agents/skills/`            | `$CODEX_HOME/prompts/opsx-*.md`                                             |

### Command syntax variations

OpenSpec generates files for two agent architectures:

- **Standalone Markdown commands** — agents that read flat files show commands with extensions (e.g. `/opsx-propose.md`).
- **Agent skills** — agents that parse semantic `SKILL.md` metadata or have native integration use slash syntax (e.g. `/opsx:propose`).

Use whichever form appears in your agent's autocomplete menu.

---

## OpenSpec workflow

### 0. Run the coding agent

```shell
claude
```

### 1. Propose a change

```text
/opsx:propose add dark mode support
```

```text
/opsx-propose.md add dark mode support
```

The agent creates the proposal, design, and implementation tasks under `openspec/changes/`.

### 2. Apply the code

Review the generated `tasks.md` (edit directly or have the agent revise it). Then:

```text
/opsx:apply
```

```text
/opsx-apply.md
```

The agent writes the code and checks off boxes in `tasks.md`.

### 3. Verify and refine

If bugs occur or tests fail, pass logs back:

```text
/opsx:verify The toggle button is invisible on mobile. Fix it.
```

```text
/opsx-verify.md The toggle button is invisible on mobile. Fix it.
```

### 4. Archive the change

```text
/opsx:archive
```

```text
/opsx-archive.md
```

The agent merges delta specs into `openspec/specs/` and moves the change folder to `openspec/changes/archive/`.
