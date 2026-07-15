<div align="center">

# Agent Standards

**One `git checkout` drops a shared AI coding setup (skills, subagents, MCP servers, OpenSpec scaffolding) into any
project.**

[![Agents](https://img.shields.io/badge/agents-Claude%20Code%20%7C%20Kilo%20%7C%20OpenCode%20%7C%20Codex%20%7C%20Copilot-blueviolet)](https://github.com/Lukk17/agent-standards)
[![Skills](https://img.shields.io/badge/skills-84-blueviolet)](.agents/skills/)
[![Subagents](https://img.shields.io/badge/subagents-30-blueviolet)](subagents/)
[![MCP](https://img.shields.io/badge/mcp_servers-8-blueviolet)](docs/MCP_SETUP.md)
[![OpenSpec](https://img.shields.io/badge/openspec-ready-blueviolet)](docs/AGENT_TOOLING.md#openspec-integration)
[![CI](https://github.com/Lukk17/agent-standards/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/Lukk17/agent-standards/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-success)](docs/repository-layout.md)

![agent-standards quickstart demo](docs/assets/demo.gif)

</div>

---

### Why it exists

For developers and teams running multiple AI coding agents across multiple repos. Every project drifts (different
prompt files, skill versions, MCP configs, subagent definitions). This repo is the single source: import once, pull
updates with one `git fetch`. Used across every project in the portfolio.

Consumer projects pull only production-ready content: skills, generated subagent files, the tooling doc, and config
templates. The canonical [subagents/](subagents/) source and [tools/](tools/) generator stay here.

The canonical source is [.agents/skills/](.agents/skills/), the same directory GitHub Copilot and Cursor read natively
for agent skills. The layout follows the cross-tool AGENTS.md and SKILL.md conventions, so the setup stays portable
across the supported agents rather than tied to one tool.

---

### Quickstart

```bash
git config core.symlinks true
```

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

```bash
mv AGENTS.md.example AGENTS.md
```

That's it. Open the project in Claude Code, Kilo Code, OpenCode, Codex, or GitHub Copilot and skills are live.

Optional next step: rename [.mcp.json.example](.mcp.json.example) to `.mcp.json` (Claude Code),
[opencode.json.example](opencode.json.example) to `opencode.json` (OpenCode),
[.kilocode/kilo.jsonc.example](.kilocode/kilo.jsonc.example) to `.kilocode/kilo.jsonc` (Kilo Code),
[.vscode/mcp.json.example](.vscode/mcp.json.example) to `.vscode/mcp.json` (GitHub Copilot in VS Code), and
[.codex/config.toml.example](.codex/config.toml.example) to `.codex/config.toml` (Codex) to enable the shared MCP
server set.

Human-side MCP setup lives in [docs/MCP_SETUP.md](docs/MCP_SETUP.md).

Full walkthrough lives in [docs/AGENT_TOOLING.md](docs/AGENT_TOOLING.md).

---

### Architecture

```mermaid
graph LR
    subgraph AS[agent-standards repo]
      ASK[.agents/skills/<br/>canonical SKILL.md files]
      SU[subagents/<br/>canonical templates]
      GEN[tools/gen_subagents.py]
      SU --> GEN
    end
    AS -->|git checkout production-ready dirs only| P[Your project]
    P --> SK[.agents/skills/]
    P --> CA[.claude/agents/<br/>generated]
    P --> OA[.opencode/agents/<br/>generated]
    P --> KA[.kilocode/agents/<br/>generated]
    P --> CXA[.codex/agents/<br/>generated TOML]
    P --> GH[.github/agents/<br/>generated]
    P --> AG[AGENTS.md]
    SK -.symlink.-> CL[.claude/skills/]
    CL --> Claude[Claude Code]
    SK --> OpenCode[OpenCode]
    SK --> Kilo[Kilo Code]
    SK --> Codex[Codex CLI]
    SK --> Copilot[GitHub Copilot]
    CA --> Claude
    OA --> OpenCode
    KA --> Kilo
    CXA --> Codex
    GH --> Copilot
    AG --> Claude
    AG --> OpenCode
    AG --> Kilo
    AG --> Codex
    AG --> Copilot

    classDef src fill:#ede0ff,stroke:#7c3aed,color:#1a1033
    classDef consumer fill:#fff7e0,stroke:#d97706,color:#1a1033
    classDef tool fill:#e0f2fe,stroke:#0284c7,color:#1a1033
    class AS,ASK,SU,GEN src
    class P,SK,CA,OA,KA,CXA,GH,AG,CL consumer
    class Claude,Kilo,OpenCode,Codex,Copilot tool
```

Two canonical sources in this repo: [.agents/skills/](.agents/skills/) and [subagents/](subagents/). Consumer projects
receive only the production-ready dirs: [.agents/skills/](.agents/skills/) plus the five generated subagent trees
([.claude/agents/](.claude/agents/), [.opencode/agents/](.opencode/agents/), `.kilocode/agents/`, `.codex/agents/`, and
[.github/agents/](.github/agents/)). The [subagents/](subagents/) source and the [tools/](tools/) generator never ship
to consumers.

Full agent compatibility matrix (what each agent reads and where):
[docs/agent-compatibility.md](docs/agent-compatibility.md). Full repository layout and per-agent instruction
precedence: [docs/repository-layout.md](docs/repository-layout.md).

---

### Agent support

Every agent reads the same [AGENTS.md](AGENTS.md.example) and [.agents/skills/](.agents/skills/); only Claude Code
needs a skills symlink. Subagents, preflight hooks, and MCP each use per-tool files because no shared format exists
across the tools. Full per-surface detail lives in [docs/agent-compatibility.md](docs/agent-compatibility.md).

| Agent | Instructions | Skills | Subagents | Preflight | MCP config |
| --- | --- | --- | --- | --- | --- |
| Claude Code | `CLAUDE.md` imports `AGENTS.md` | `.claude/skills/` (symlink) | `.claude/agents/` | `UserPromptSubmit` hook, per turn | `.mcp.json` |
| OpenCode | `AGENTS.md` (native) | `.agents/skills/` (native) | `.opencode/agents/` | plugin, per turn | `opencode.json` |
| Kilo Code | `AGENTS.md` (native) | `.agents/skills/` (native) | `.kilocode/agents/` | rule, per task | `.kilocode/kilo.jsonc` |
| Codex | `AGENTS.md` (native) | `.agents/skills/` (native) | `.codex/agents/` (TOML) | `UserPromptSubmit` hook, per turn | `.codex/config.toml` |
| GitHub Copilot | `AGENTS.md` (native) | `.agents/skills/` (native) | `.github/agents/` (`*.agent.md`) | `sessionStart` hook, per session | `.vscode/mcp.json` |

---

### What's in the box

- **[.agents/skills/](.agents/skills/)**: canonical `SKILL.md` files. Source of truth, shared by every agent, shipped
  to consumers. Browse the catalogue to see what's available.
- **[subagents/](subagents/)** *(this repo only)*: canonical subagent templates. Generator emits per-tool copies.
- **[tools/](tools/)** *(this repo only)*: `gen_subagents.py` and `pyproject.toml`. Emits five per-tool subagent trees:
  [.claude/agents/](.claude/agents/), [.opencode/agents/](.opencode/agents/), `.kilocode/agents/`, `.codex/agents/`
  (TOML), and [.github/agents/](.github/agents/).
- **[.claude/](.claude/)**: Claude Code bridge. [.claude/CLAUDE.md](.claude/CLAUDE.md) imports
  [AGENTS.md](AGENTS.md.example), a `skills/` symlink, generated `agents/`.
- **OpenSpec scaffold**: spec-driven workflow. `openspec init` creates the `openspec/` directory in the consumer
  project; commands land in each tool's native dir.
  See [docs/AGENT_TOOLING.md](docs/AGENT_TOOLING.md#openspec-integration) for the full workflow.
- **Companion OpenSpec schema** *(optional)*:
  [Lukk17/openspec-schemas](https://github.com/Lukk17/openspec-schemas) ships an `e2e-runbooks` schema for
  spec-driven end-to-end capability tests through OpenSpec's lifecycle
  (`/opsx:new --schema e2e-runbooks`). Install steps live in
  [docs/AGENT_TOOLING.md](docs/AGENT_TOOLING.md#optional-install-a-custom-schema-for-e2e-capability-tests).
- **[AGENTS.md](AGENTS.md.example)**: shared instructions auto-read by Kilo, OpenCode, Codex, and GitHub Copilot
  (JetBrains, VS Code, and CLI). [AGENTS.md.example](AGENTS.md.example) is the template you rename to `AGENTS.md`.
- **GitHub Copilot**: [.github/agents/](.github/agents/) holds generated `*.agent.md` subagents, and
  `.github/hooks/preflight.json` is the `sessionStart` gate hook. Copilot reads `AGENTS.md` and `.agents/skills/`
  natively (JetBrains plugin, VS Code, CLI), so no bridge instruction file is needed.
- **MCP scaffolds**: [.mcp.json.example](.mcp.json.example), [opencode.json.example](opencode.json.example), the
  `mcp` block in [.kilocode/kilo.jsonc.example](.kilocode/kilo.jsonc.example) (Kilo Code),
  [.vscode/mcp.json.example](.vscode/mcp.json.example), [.codex/config.toml.example](.codex/config.toml.example), and
  [docs/MCP_SETUP.md](docs/MCP_SETUP.md) for the human setup.

Server list and configuration live in [docs/MCP_SETUP.md](docs/MCP_SETUP.md). All entries use `${VAR}` or `{env:VAR}`
substitution with defaults baked in.

---

### How it compares

| Approach | What you get | Trade-off |
| --- | --- | --- |
| Copy-paste a single `AGENTS.md` | Fast start, one file | Drifts the moment upstream changes; no skills, no subagents, no MCP |
| Personal dotfiles repo | Total control | Manual sync; not designed for cross-tool agent setup |
| Tool-native rules (Cursor rules, Claude Projects) | Works in that tool | Locks you in; no portability across the supported agents |
| Awesome lists / prompt collections | Inspiration | Curated reading, not an installable setup |
| **agent-standards** | One `git checkout` brings skills, subagents, MCP servers across every supported agent | Adds an `agent-standards` git remote; Windows symlinks need Developer Mode |

Where this loses: setup overhead (one-time), the remote dependency, and Windows symlink ergonomics.

Where it wins: a single source for the whole agent surface (skills, subagents, MCP, OpenSpec scaffolding), refreshed
with one `git fetch`.

---

### Working with subagents

The specialised subagents live as one canonical Markdown file each in [subagents/](subagents/) (this repo's root,
*not* shipped to consumer projects). A generator emits the five tool-specific copies that *are* shipped.

After editing any canonical file:

```bash
python tools/gen_subagents.py
```

CI gate (fails if generated tree is stale relative to canonical):

```bash
python tools/gen_subagents.py --check
```

Rules:

- **Edit [subagents/<name>.md](subagents/) only.** The generator overwrites all five trees:
  [.claude/agents/](.claude/agents/), [.opencode/agents/](.opencode/agents/), `.kilocode/agents/`, `.codex/agents/`,
  and [.github/agents/](.github/agents/).
- **Each tool gets its own format.** OpenCode and Kilo Code take OpenCode-format markdown in separate directories,
  Codex takes TOML, GitHub Copilot takes `*.agent.md`. No shared subagent format exists across the tools.
- **Run the generator after any canonical change** and commit both the source and the generated output.
- **Consumer projects pull only the generated trees.** They never see [subagents/](subagents/) or [tools/](tools/).

Adding a new subagent: drop a frontmatter-headed Markdown file in [subagents/](subagents/) and re-run the generator.

Removing one: delete the canonical file and re-run. Orphaned outputs are pruned automatically.

---

### Pulling updates

Updates are driven from [docs/AGENTS-UPDATE.md](docs/AGENTS-UPDATE.md), a doc shipped from upstream that refreshes
itself on every run. It contains bash and PowerShell commands that:

- Refresh the shipped docs (`docs/AGENT_TOOLING.md`, `docs/MCP_SETUP.md`, and `docs/AGENTS-UPDATE.md` itself).
- Enumerate the skills already in the consumer's `.agents/skills/` and pull only those (no surprise additions).
- Enumerate the subagents already in the five generated trees (`.claude/agents/`, `.opencode/agents/`,
  `.kilocode/agents/`, `.codex/agents/`, `.github/agents/`) and pull only those.

Files intentionally NOT touched by the update: the `.claude/skills/` symlink (the only skill symlink left, since every
other agent reads `.agents/skills/` natively), `.claude/CLAUDE.md`, `AGENTS.md.example`, the `.kilocode/*.example`
templates, `opencode.json.example`, `.mcp.json.example`, `.codex/config.toml.example`, and the consumer's customised
`AGENTS.md`.

If your project was imported before this doc shipped and has no `docs/AGENTS-UPDATE.md`, pull it with a one-off
`git checkout agent-standards/master -- docs/AGENTS-UPDATE.md`, then use it for every later refresh.

Full walkthrough lives in [docs/AGENT_TOOLING.md](docs/AGENT_TOOLING.md).

---

### Docs map

Naming convention: **UPPERCASE** filenames ship to consumer projects via the `git checkout` above; **lowercase**
filenames stay in this repo only.

**Shipped to consumer projects:**

| File | What's in it |
| --- | --- |
| [docs/AGENT_TOOLING.md](docs/AGENT_TOOLING.md) | Initial import flow, future updates, subagents, MCP overview, full OpenSpec integration and workflow. |
| [docs/MCP_SETUP.md](docs/MCP_SETUP.md) | Prerequisites, key acquisition, env-var export per OS, Claude Desktop and Codex CLI global configs, verification. |
| [docs/AGENTS-UPDATE.md](docs/AGENTS-UPDATE.md) | Per-OS selective update commands. Refreshes the shipped docs, plus the skills and subagents already present, and itself. |

**This repo only:**

| File | What's in it |
| --- | --- |
| [docs/agent-compatibility.md](docs/agent-compatibility.md) | Per-surface matrix of what each agent reads (skills, instructions, subagents, preflight, MCP) and why Claude Code needs a symlink. |
| [docs/repository-layout.md](docs/repository-layout.md) | Repo structure and instruction precedence per agent. |
| [docs/manual-setup.md](docs/manual-setup.md) | Fallback steps when the standard `git checkout` flow needs manual help (symlink recreation per OS) plus per-agent start commands. |
| [docs/bootstrap-prompt.md](docs/bootstrap-prompt.md) | First-run verification prompt to paste into the agent after import. Checks skills, subagents, MCP runtime, OpenSpec, instruction tree. |

**Template:**

| File | What's in it |
| --- | --- |
| [AGENTS.md.example](AGENTS.md.example) | Source instructions template. Rename to `AGENTS.md` after import; consumer projects fill the project-specific sections. |

---

### Contributing

Issues and pull requests welcome. For non-trivial changes please open an issue first to discuss the approach. The repo
is opinionated by design and direction matters.

Maintained by [Łukasz Sarna](https://github.com/Lukk17).

---

### License

MIT, see [LICENSE](LICENSE).
