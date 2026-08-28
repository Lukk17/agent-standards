# Agent compatibility matrix

What each supported agent reads, where it reads it from, what it can actually block, and the few places our layout
has to work around a tool limitation. Checked against vendor documentation on 2026-08-25, against Claude Code 2.1.250,
Codex 0.150.1, OpenCode 1.18.25, and Kilo Code 7.5.5. Cells that rest on something less than official documentation
say so.

This file stays in the agent-standards repo only. For the full repository tree and each agent's instruction-merge
precedence, see [repository-layout.md](repository-layout.md). For human MCP setup (keys, environment variables,
per-operating-system commands), see [MCP_SETUP.md](MCP_SETUP.md).

---

### The one-paragraph version

Two things converged across the tools and one thing did not. Skills at `.agents/skills/` and shared instructions in
`AGENTS.md` are read natively by Codex, OpenCode, Kilo Code, and every GitHub Copilot surface, so both are canonical
here. Claude Code reads neither path natively, so it reaches skills through the `.claude/skills` symlink and
instructions through the `@../AGENTS.md` import in `.claude/CLAUDE.md`. Both bridges are patterns Claude Code's own
documentation supports, not hacks. Subagent definitions did not converge at all: Claude Code, Codex, and Copilot each
demand a different format, so one canonical source is generated into four trees, and only OpenCode and Kilo Code are
close enough to share one.

---

### Skills discovery

| Agent | Native project path | Native global path | How we serve it |
| --- | --- | --- | --- |
| Claude Code | `.claude/skills/` | `~/.claude/skills/` | symlink `.claude/skills -> ../.agents/skills`, because Claude Code does not read `.agents/skills/` |
| Codex | `.agents/skills/` | `~/.agents/skills/` | native, scanned from the working directory up to the repo root |
| OpenCode | `.agents/skills/`, `.opencode/skills/` | `~/.agents/skills/` | native |
| Kilo Code | `.agents/skills/`, `.kilo/skills/` | `~/.agents/skills/` | native |
| GitHub Copilot | `.agents/skills/`, `.github/skills/`, `.claude/skills/` | `~/.agents/skills/`, `~/.copilot/skills/` | native on VS Code, JetBrains, CLI, and the cloud agent |

One symlink for one agent. Everything else reads the canonical directory directly, which is why no `.opencode/skills`,
`.kilo/skills`, or `.codex/skills` symlink exists.

---

### Instructions discovery

| Agent | Instruction file | How it loads |
| --- | --- | --- |
| Claude Code | `CLAUDE.md` | [.claude/CLAUDE.md](../.claude/CLAUDE.md) contains `@../AGENTS.md`, the documented import pattern; Claude Code never reads `AGENTS.md` itself |
| Codex | `AGENTS.md` | native, walks nested `AGENTS.md` from the root down to the working directory, `AGENTS.override.md` wins at each level |
| OpenCode | `AGENTS.md` | native from the project root, falls back to `CLAUDE.md` when absent |
| Kilo Code | `AGENTS.md`, `.kilo/rules/` | both auto-read from the project root on every task |
| GitHub Copilot | `AGENTS.md` | native in VS Code agent mode, the CLI, and the cloud agent; the JetBrains plugin reads it in agent mode too |

The JetBrains row needs a caveat spelled out. The March 2026 JetBrains plugin changelog states that agent mode reads
`AGENTS.md`, and it does. GitHub's own published support matrix for custom instructions still omits JetBrains from the
`AGENTS.md` column, so the two sources disagree. Treat the behaviour as real and the documentation as behind.

Copilot code review (the pull-request bot) and the editors that read only `.github/copilot-instructions.md` (Visual
Studio, Xcode, Eclipse) are out of scope. Add that bridge yourself per project if you target them. Plain Copilot chat
outside agent mode also does not read `AGENTS.md`.

---

### Subagents discovery

| Agent | Path it reads | Format | Kind |
| --- | --- | --- | --- |
| Claude Code | `.claude/agents/` | Claude markdown | generated tree |
| Codex | `.codex/agents/` | TOML | generated tree |
| GitHub Copilot | `.github/agents/` | `*.agent.md` | generated tree |
| OpenCode | `.opencode/agents` | OpenCode markdown | symlink to `.agents/agents/` |
| Kilo Code | `.kilo/agents` | OpenCode markdown | symlink to `.agents/agents/` |

[../tools/gen_subagents.py](../tools/gen_subagents.py) emits four trees from the one canonical
[../subagents/](../subagents/) source and recreates the two symlinks when they are missing. Agent definitions cannot be
shared across formats, so Claude Code, Codex, and Copilot each get their own copy. OpenCode and Kilo Code accept the
same file, and both follow symlinks when scanning an agent directory, so they share `.agents/agents/`. Neither tool
exposes a config key naming an agent directory, which is why this is a symlink rather than a setting. Never hand-edit
a generated tree.

---

### Hook enforcement, what each agent can actually block

The gate is one shared rule in [../.agents/hooks/preflight_gate.py](../.agents/hooks/preflight_gate.py). It reads a
hook payload on standard input and denies three things: a write of any file resolving inside the repository working
tree coming from the main thread, with no exemption left for markdown, configuration, or `docs/` (delegate the change
to a subagent that owns the area instead), any edit from a subagent whose own definition declares no skills (spawn a
specialist instead), and a web fetch or web search called straight from the main thread on the one format whose
payload names that tool today, Claude Code. A write outside the repository, the null device, and switching a git
branch stay allowed, and the main thread keeps full use of git otherwise. Caller identity is a tri-state, subagent,
main thread, or unknown when a payload carries nothing that could tell the two apart, and none of the three rules
fires on an unknown caller. Every failure path also allows the call, because a broken gate must never break a
session.

Each agent wires that one script through its own hook surface, and the surfaces differ in what they can stop.

| Agent | Hook config | Blocks a tool call | Injects context | Blocks a reply | Tells subagent from main thread |
| --- | --- | --- | --- | --- | --- |
| Claude Code | [.claude/settings.json](../.claude/settings.json) | yes, `PreToolUse` | yes, `UserPromptSubmit` on every turn including the first | yes, `Stop` | yes, `agent_id` is present only inside a subagent |
| Codex | inline `[[hooks.*]]` in [.codex/config.toml](../.codex/config.toml) | yes, `PreToolUse` | yes, `UserPromptSubmit` and `SubagentStart` | no | yes, `agent_id` is present only inside a subagent |
| OpenCode | plugin [.agents/plugin/hooks.js](../.agents/plugin/hooks.js), declared by path in [opencode.json](../opencode.json) | yes, throwing from `tool.execute.before` | no per-turn channel | no | yes, via the acting agent on the payload and the session `parentID` |
| Kilo Code | the same plugin, same declaration | yes, throwing from `tool.execute.before` | no per-turn channel | no | yes, same mechanism |
| GitHub Copilot | [.github/hooks/preflight.json](../.github/hooks/preflight.json), camelCase events | fires on `preToolUse`, but caller identity there always resolves to unknown, so the gate always allows | yes, `sessionStart` and `subagentStart` | no | no, the `preToolUse` payload carries no agent identifier |

Reading the table row by row:

- Every row anchors the gate at the project root before calling it, so a session started in a subdirectory still finds
  [../.agents/hooks/preflight_gate.py](../.agents/hooks/preflight_gate.py), and a missing script allows rather than
  denies. Python exits 2 when it cannot open the file it was handed, and 2 is the deny code, so an unanchored path used
  to block every tool call.
- Claude Code is the only surface with a reply-level block. Its `Stop` hook runs
  [../.agents/hooks/no_ai_markers_check.py](../.agents/hooks/no_ai_markers_check.py), which rejects a reply whose prose
  carries an em dash, an en dash, a semicolon, or a bold marker, and asks for a rewrite.
- Codex carries its hooks inline in `.codex/config.toml`, the same file that holds its MCP servers. There is no
  separate `.codex/hooks.json` any more. Codex also loads that whole layer only after the project is trusted.
- OpenCode and Kilo Code run one plugin file between them. Neither has an event that can block a reply, so on those two
  the enforcement is the pre-tool block plus per-agent tool permissions, and nothing after the fact.
- GitHub Copilot's `preToolUse` payload carries no agent identifier at all, so caller identity there resolves to
  unknown every time and none of the gate's three rules ever fires. The hook is wired and runs, but it always allows:
  that surface is entirely unenforced by the gate, not merely weaker, and the `AGENTS.md` text plus the
  `sessionStart` injection carry the whole weight instead.
- Copilot in JetBrains fires only six events, has no subagent event at all, and reads hook configuration only from
  `.github/hooks/`. A hook file anywhere else is ignored by that client.

The canonical wording of the gate itself lives in the `## Required opening move` section of `AGENTS.md`. Every adapter
repeats it verbatim. Change one, change all of them.

---

### MCP configuration

One row per file. Several agents ship more than one client, and the clients disagree, so read this table by file
rather than by agent.

| File | Schema key | Serves | Environment-variable syntax |
| --- | --- | --- | --- |
| [.mcp.json](../.mcp.json) | `mcpServers` | Claude Code | `${VAR}`, `${VAR:-default}` |
| [opencode.json](../opencode.json) at the project root | `mcp` | OpenCode and Kilo Code | none, a token here voids the file for Kilo |
| [.codex/config.toml](../.codex/config.toml) | `[mcp_servers.*]` tables | Codex | none, values are literal |
| [.vscode/mcp.json](../.vscode/mcp.json) | `servers` | GitHub Copilot in VS Code | `${env:VAR}`, `${input:NAME}` |
| [.github/mcp.json](../.github/mcp.json) | `mcpServers` | the GitHub Copilot CLI | none, values are literal |
| `~/.config/github-copilot/intellij/mcp.json` | `servers` | GitHub Copilot in JetBrains, global only | none documented |
| repository settings page | pasted JSON | GitHub Copilot cloud agent | none, values are literal |

The same eight servers are mirrored across the five project files. Only the file name, the schema key, the `type`
value, and the environment-variable syntax differ. The last two rows are not project files at all, which is why they
carry no template.

Two rows ship no template and cannot. The JetBrains Copilot plugin reads MCP only from the global path above, with no
per-project file, so a shipped file would never be read. The cloud agent takes JSON pasted into a page in the
repository settings, so there is nothing to commit. Of the four Copilot surfaces, VS Code reads
[.vscode/mcp.json](../.vscode/mcp.json) and the CLI reads [.github/mcp.json](../.github/mcp.json). Both manual blocks
are written out in [MCP_SETUP.md](MCP_SETUP.md).

The Copilot CLI is also documented as capable of reading a project-level `.mcp.json`, the same file and schema Claude
Code uses, and its own precedence rule makes `.mcp.json` win over `.github/mcp.json` whenever both exist in the same
directory and name the same server, which is true for all eight servers here. `.mcp.json` carries Claude Code's
`${VAR:-default}` syntax, which the CLI does not evaluate, so as things stand the CLI resolves its servers from
`.mcp.json` with every substitution left as a literal, unresolved string, not from the clean `.github/mcp.json` this
repo ships for it. See [MCP_SETUP.md](MCP_SETUP.md#the-cli-mcpjson-and-why-a-fifth-file-exists) for the measurement
that confirmed it and why `.github/mcp.json` still ships regardless.

Kilo Code accepts `opencode.json` as a valid project config filename, which is why one file serves both it and
OpenCode. What it does with an environment reference is where sharing the file costs something, and it is harsher than
a literal placeholder. A `{env:VAR}` anywhere in project-level config makes Kilo reject that entire file, so the MCP
block and the `plugin` array declaring the preflight gate both vanish at once. The rest of Kilo's configuration chain
survives, only the rejected file is dropped. A reference confined to an MCP `headers` block costs just that server,
but `kilocode config check` still exits non-zero. The shared file therefore ships free of references, and local
servers inherit their tokens from the environment of the process that starts the agent. The one value that cannot be
inherited that way is the Context7 API key, which is an HTTP header, so `context7` ships with no `headers` block and
runs on the free tier. There is no project-level overlay for it: an authenticated block belongs in a user's global
OpenCode or Kilo config, as [MCP_SETUP.md](MCP_SETUP.md) describes.

---

### Per-agent caveats worth remembering

- Claude Code is the only agent that reads neither `AGENTS.md` nor `.agents/skills/` natively. Both bridges, the
  `@` import and the `.claude/skills` symlink, must survive every update or the whole setup silently does nothing.
- Kilo Code moved its configuration root from `.kilocode/` to `.kilo/`. Nothing in this repo writes to `.kilocode/`
  any more. OpenSpec 1.10.0 still hardcodes `.kilocode` for its Kilo target, which is one of the reasons consumers
  should initialise it with the vendor-neutral target instead (see [AGENTS-UPDATE.md](AGENTS-UPDATE.md)).
- Codex loads the whole `.codex/` project layer, custom agents, MCP servers, and hooks alike, only after the project
  is trusted. On a fresh clone the gate does not run until the user approves the project once.
- GitHub Copilot ships four surfaces (VS Code, JetBrains, CLI, cloud agent) that differ on hooks, on MCP, and on
  documentation quality. Never answer a Copilot question without naming the surface.
- On Windows the two agent symlinks and the skills symlink need `git config core.symlinks true` and Developer Mode
  enabled before the checkout, otherwise git writes plain text files containing the target path and every agent that
  depends on them sees nothing.
