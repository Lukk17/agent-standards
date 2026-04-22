## Agent Standards

---

### Overview

This repository is a centralized source of truth for AI coding agent instructions and skills. It supports Claude Code, Kilo Code, OpenCode, and Codex CLI. By importing it into your projects, all agents follow the same standards and workflows across your organization.

---

### Repository Structure

```
agent-standards/
  .agents/
    skills/                      # 71+ SKILL.md files (canonical source of truth)
  .claude/
    CLAUDE.md                    # @imports ../AGENTS.md (Claude Code bridge)
    skills -> ../.agents/skills/ # symlink for Claude Code compatibility
  .kilocode/
    skills -> ../.agents/skills/ # symlink for OpenSpec compatibility
  .opencode/
    skills -> ../.agents/skills/ # symlink for OpenSpec compatibility
  .codex/
    skills -> ../.agents/skills/ # symlink for OpenSpec compatibility
  AGENTS.md                      # Shared instructions (auto-read by Kilo, OpenCode, Codex)
  AGENTS.md.example              # Template for target project AGENTS.md
  kilo.jsonc.example             # Kilo Code config template
  opencode.json.example          # OpenCode config template (must stay at root)
```

---

### Agent Compatibility Matrix

#### Skills Discovery

| Agent | Native skill paths | Our solution |
|---|---|---|
| Claude Code | `.claude/skills/` | Symlink `.claude/skills/ → ../.agents/skills/` |
| Kilo Code | `.kilo/skills/`, `.agents/skills/`, `.claude/skills/` | Reads `.agents/skills/` natively |
| OpenCode | `.opencode/skills/`, `.agents/skills/`, `.claude/skills/` | Reads `.agents/skills/` natively |
| Codex CLI | `.agents/skills/` | Reads `.agents/skills/` natively |

#### Instructions Discovery

| Agent | Instruction file | How it loads |
|---|---|---|
| Claude Code | `CLAUDE.md` | `.claude/CLAUDE.md` imports `@../AGENTS.md` |
| Kilo Code | `AGENTS.md` | Auto-read from project root |
| OpenCode | `AGENTS.md` | Auto-read from project root (falls back to `CLAUDE.md`) |
| Codex CLI | `AGENTS.md` | Auto-read from project root (walks up from cwd) |

---

### Instruction Precedence (per agent)

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

```
1. Global config: ~/.config/kilo/kilo.jsonc
2. Project root: kilo.jsonc
3. Project directory: .kilo/kilo.jsonc (takes priority over root kilo.jsonc)
4. AGENTS.md at project root (auto-read)
5. Skills from .kilo/skills/, .agents/skills/, .claude/skills/ (auto-discovered)
```

#### OpenCode

```
1. Remote config (.well-known/opencode) — organizational defaults
2. Global config (~/.config/opencode/opencode.json) — user preferences
3. Custom config (OPENCODE_CONFIG env var)
4. Project config (opencode.json at project root)
5. .opencode/ directories (agents/, commands/, plugins/, skills/)
6. Inline config (OPENCODE_CONFIG_CONTENT env var) — highest JSON override
7. Managed config files (system directories)
```

Note: `opencode.json` must be at the project root, not inside `.opencode/`. The `.opencode/` directory holds subdirectories (skills/, commands/, agents/).

#### Codex CLI

```
1. Global: ~/.codex/AGENTS.md (or AGENTS.override.md if exists)
2. Project root: AGENTS.md (or AGENTS.override.md if exists)
3. Subdirectories: AGENTS.md walking down from root to cwd
4. AGENTS.override.md at any level takes precedence over AGENTS.md at same level
5. Skills from .agents/skills/ (primary), walking up from cwd to repo root
```

Codex has no project-level config file. Global settings live in `~/.codex/config.toml`. Skills are scanned from `.agents/skills/` at every directory level up to the repo root.

---

### Project Integration via Git Selective Checkout

Import these standards into a new project without overwriting existing files using Git Selective Checkout.

#### Step 1: Initial Setup in a New Project

Enable symlink support in Git (required for Windows):

```shell
# Globally
git config --global core.symlinks true

# Or locally for this repository only
git config core.symlinks true
```

Add the remote, disable pushing, and extract the payload files:

```bash
git remote add agent-standards https://github.com/Lukk17/agent-standards
git remote set-url --push agent-standards no_push
git fetch agent-standards
git checkout agent-standards/master -- .agents .claude .kilocode .opencode .codex AGENTS.md.example kilo.jsonc.example opencode.json.example
git commit -m "Import central agent-standards"
```

Create the symlinks for agent tool compatibility (required once after cloning, Windows requires `core.symlinks true`).

Run these from the **project root**. The symlink target path (`../.agents/skills`) is relative to the symlink's own location (e.g. `.kilocode/`), so `../` steps up from `.kilocode/` back to the project root before entering `.agents/skills`.

```bash
# Linux/macOS — run from project root
mkdir -p .kilocode .opencode .codex
ln -s ../.agents/skills .kilocode/skills
ln -s ../.agents/skills .opencode/skills
ln -s ../.agents/skills .codex/skills

# Windows — run from project root (as Administrator or with Developer Mode enabled)
mkdir .kilocode .opencode .codex
mklink /D .kilocode\skills ..\.agents\skills
mklink /D .opencode\skills ..\.agents\skills
mklink /D .codex\skills ..\.agents\skills
```

Then copy the example files to activate them:

```bash
# Copy the AGENTS.md template and fill in your project details
cp AGENTS.md.example AGENTS.md

# Kilo Code config (optional — Kilo reads .agents/skills/ natively)
cp kilo.jsonc.example kilo.jsonc

# OpenCode config (optional — OpenCode reads .agents/skills/ natively)
cp opencode.json.example opencode.json
```

#### Step 2: Pulling Future Updates

```bash
git fetch agent-standards
git checkout agent-standards/master -- .agents .claude .kilocode .opencode .codex
git commit -m "Update AI standards from central repository"
```

---

### Usage with Claude Code

Claude Code reads `.claude/CLAUDE.md`, which imports `AGENTS.md` via:

```markdown
@../AGENTS.md
```

Skills in `.claude/skills/` (symlinked to `.agents/skills/`) are automatically discovered. No additional configuration required.

---

### Usage with Kilo Code

Kilo Code reads `AGENTS.md` from the project root automatically and discovers skills from `.agents/skills/` natively.

Optionally copy `kilo.jsonc.example` to `kilo.jsonc` at the project root to enable additional instruction globs:

```jsonc
{
  "instructions": ["AGENTS.md"]
}
```

---

### Usage with OpenCode

OpenCode reads `AGENTS.md` automatically and discovers skills from `.agents/skills/` natively.

Optionally copy `opencode.json.example` to `opencode.json` for additional configuration:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": ["AGENTS.md"]
}
```

`opencode.json` must remain at the project root (not inside `.opencode/`).

---

### Usage with Codex CLI

Codex reads `AGENTS.md` from the project root and discovers skills from `.agents/skills/` automatically. No project-level config file is required.

For global Codex settings, edit `~/.codex/config.toml`:

```toml
# Optional: increase instruction size limit (default: 32 KiB)
project_doc_max_bytes = 65536
```


---

### OpenSpec Integration

[OpenSpec](https://github.com/Fission-AI/OpenSpec) is a spec-driven development framework that installs skills and commands into each agent's native directories.

#### How the symlinks work with OpenSpec

The `.kilocode/skills/`, `.opencode/skills/`, and `.codex/skills/` directories are all symlinked to `.agents/skills/`. When `openspec init` writes skills to any of these directories, they land in `.agents/skills/` — the canonical location already read by all agents.

Commands are tool-specific (different formats per agent) and cannot be centralized. OpenSpec creates them in each tool's native commands directory, which is expected and correct.
#### Using OpenSpec in a project that imports agent-standards

After running Step 1 above, initialize OpenSpec in your project:

```bash
# Install OpenSpec globally
npm install -g @fission-ai/openspec@latest

# Initialize with all agents
# Skills land in .agents/skills/ via existing symlinks
# Commands are created in each tool's native commands directory
openspec init --tools "claude,kilocode,opencode,codex"
```

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
.kilocode/workflows/opsx-propose.md
.opencode/commands/opsx-propose.md
```

Restart IDE and terminal after openspec initialization.

#### OpenSpec tool directories reference

| Tool | Skills written to | Commands written to |
|---|---|---|
| Claude Code | `.claude/skills/openspec-*/` -> `.agents/skills/` | `.claude/commands/opsx/*.md` |
| Kilo Code | `.kilocode/skills/openspec-*/` -> `.agents/skills/` | `.kilocode/workflows/opsx-*.md` |
| OpenCode | `.opencode/skills/openspec-*/` -> `.agents/skills/` | `.opencode/commands/opsx-*.md` |
| Codex | `.codex/skills/openspec-*/` -> `.agents/skills/` | `$CODEX_HOME/prompts/opsx-*.md` |

#### Command Syntax Variations

Because the AI coding landscape is fragmented, OpenSpec generates files for two different architectures. Depending on your specific agent UI, your commands will appear in one of two ways:
* Standalone Markdown Commands: Agents that read flat files will show commands with extensions in their dropdowns (e.g., /opsx-propose.md).
* Agent Skills: Agents that parse semantic SKILL.md metadata or have native integration will use standard slash syntax (e.g., /opsx:propose).

Use the syntax that appears in your agent's autocomplete menu.

#### The Full OpenSpec Workflow

Once initialized, invoke OpenSpec skills from your agent using the full artifact-driven lifecycle:

#### 0. Run Coding Agent
You need to start coding agent first - for example, by running in terminal:
```shell
claude
```
#### 1. Propose the change
Use multiline prompts to include logs or detailed context.
Inside coding agent shell run your specific command variation:

```text
/opsx:propose add dark mode support
```

```text
/opsx-propose.md add dark mode support
```
The agent creates the proposal, design, and implementation tasks under `openspec/changes/`.

#### 2. Apply the code
Review the generated `tasks.md` by manually editing md files or just telling agent what is wrong with it.

After plan approval agent can start implementation:

```text
/opsx:apply
```

```text
/opsx-apply.md
```
The agent writes the code and checks off the boxes in your `tasks.md`.

#### 3. Verify and refine
If bugs occur or tests fail, pass the logs back to refine the implementation.

```text
/opsx:verify The toggle button is invisible on mobile. Fix it.
```

```text
/opsx-verify.md The toggle button is invisible on mobile. Fix it.
```

#### 4. Archive the change
Once the code is working and tested, merge the documentation.

```text
/opsx:archive
```

```text
/opsx-archive.md
```
The agent merges the delta specs into `openspec/specs/` and moves the change folder to `openspec/changes/archive/`.
