# AGENTS.md

Instructions for agents working on agent-standards itself. This file is never shipped. Consumers get
[AGENTS.md.example](AGENTS.md.example), the only `.example` file, because every other configuration file ships
unchanged.

---

## Required opening move

Before any code work on a task, name the skill(s) and subagent(s) that own it and invoke them, or state "none apply"
and why, as the first line of your reply. This is a hard gate.

Follow [.agents/instructions/reply-rules.md](.agents/instructions/reply-rules.md) when writing to the user. Name skills and ownership in the footer status tail it defines, never as the reply first line.

The gate is enforcing, not advisory. One shared rule in
[.agents/hooks/preflight_gate.py](.agents/hooks/preflight_gate.py) decides every tool call, on every agent:

- It denies the main thread a write of any file inside the repository, by any tool or shell, markdown, configuration
  and documentation included. A write outside it, to the null device or to `tasks.md` at the root, and git branch
  switching stay allowed. How the gate places a path and reads a command is in
  [docs/agent-compatibility.md](docs/agent-compatibility.md) under "Hook enforcement".
- It denies any tool call from a subagent whose own definition declares no skills. An unknown or unreadable
  `agent_type` allows rather than denies.
- It denies the main thread a web fetch or web search tool on Claude Code, the one format whose tool names are
  confirmed. Codex has no confirmed tool name for this yet. The main thread spawns a subagent to do the research.
- It denies the main thread running a script or a module, because the gate cannot see what a script writes, unless
  the command passes `MAIN_THREAD_ALLOWLIST` in the gate or an entry of the project's own `main-thread-allowlist.txt`.
  The rules are in [docs/GLOBAL_SETUP.md](docs/GLOBAL_SETUP.md) under "What the main thread may run". This
  repository's own checks sit in [main-thread-allowlist.txt](main-thread-allowlist.txt), which never ships.
- Every rule fires only on a caller positively identified as the main thread. Claude Code and Codex send `agent_id`
  only inside a subagent. An unknown caller is allowed: GitHub Copilot on every call, and an OpenCode or Kilo Code
  call whose session the plugin could not read.
- It fails open: a parse error, a missing key, an unexpected payload, an unknown `--format`, or a top-level command
  it cannot lex allows the call. The exception is a path or write target the gate cannot place, such as the `$f` in
  `rm $f`, which denies on the main thread. The list is in [docs/agent-compatibility.md](docs/agent-compatibility.md).
- No MCP tool is gated, and `playwright` and `chrome-devtools` in [.mcp.json](.mcp.json) can write local files. The
  vendor quotes are in [docs/agent-compatibility.md](docs/agent-compatibility.md).
- Known limits of the write rule are accepted rather than open, and listed under "What the gate cannot place" in
  [docs/agent-compatibility.md](docs/agent-compatibility.md). Re-audit only when the rule changes, and record a new
  limit there rather than chasing it.

Each agent wires that one script, and the hooks beside it, to its own hook surface. Before you touch any wiring, read
"Wiring details per surface" in [docs/agent-compatibility.md](docs/agent-compatibility.md).

| Agent | Wiring | Gate matcher |
| --- | --- | --- |
| Claude Code | [.claude/settings.json](.claude/settings.json) | `^(Edit\|Write\|MultiEdit\|NotebookEdit\|Bash\|PowerShell\|WebFetch\|WebSearch)$` |
| Codex | inline `[[hooks.*]]` tables in [.codex/config.toml](.codex/config.toml) | `^(Bash\|shell\|apply_patch\|Edit\|Write\|NotebookEdit)$` |
| OpenCode and Kilo Code | [.agents/plugin/hooks.js](.agents/plugin/hooks.js), declared once by path in the `plugin` array of [opencode.json](opencode.json), which both tools read | none, every tool call |
| GitHub Copilot | [.github/hooks/preflight.json](.github/hooks/preflight.json) | `bash\|powershell\|create\|edit\|apply_patch` |

Verified against Claude Code 2.1.281, Codex 0.156.1, OpenCode 1.18.32, and Kilo Code 7.7.9. GitHub Copilot CLI was
last verified on 1.0.81 and is not installed here, so nothing above was re-measured against it.

---

## What this repo is

agent-standards is a single source of AI-agent configuration (skills, subagents, MCP servers, preflight hooks, shared
instructions) that other projects import and update by Git selective checkout. The canonical
[subagents/](subagents/) source and the [tools/](tools/) generator stay here and are never imported downstream.

The load-bearing distinction is **canonical vs generated**. Some trees are hand-edited here, some are emitted by a
script and must never be hand-edited, and some are symlinks the generator creates and repairs.

| Tree | Status | How to edit |
| --- | --- | --- |
| `subagents/*.md` | canonical | edit directly, then regenerate |
| `.agents/skills/*/SKILL.md` and its `references/*.md` | canonical | edit directly, keep the manifest short and the depth in `references/` |
| `.agents/hooks/preflight_gate.py`, `.agents/hooks/no_ai_markers_check.py`, `.agents/hooks/task_list_sync.py`, `.agents/hooks/markdown_lint_check.py`, `.agents/hooks/question_numbering_check.py`, `.agents/hooks/status_block_check.py`, `.agents/hooks/task_watchdog.py`, `.agents/hooks/copilot/prompt_reminder.py` | canonical | edit directly, then run the pytest suite |
| `tasks.md` | runtime state, git-ignored | written by the hook and by the model, never committed |
| `.agents/plugin/hooks.js` | canonical | edit directly |
| `AGENTS.md.example`, `docs/*.md` | canonical | edit directly |
| `tools/*.py`, `tools/tests/*.py`, `tools/pyproject.toml` | canonical | edit directly, then run the pytest suite |
| `global/bin/update-global.sh`, `global/bin/update-global.ps1` | canonical, shipped only by the global install to `~/.agents/bin` | edit both together, then run `python -m pytest tools/tests/test_update_global.py` |
| `main-thread-allowlist.txt` | canonical, this repo only, never shipped | edit directly, then run `python -m pytest tools/` |
| `.claude/agents/*.md` | generated (Claude front matter with a `skills` key) | never hand-edit, run the generator |
| `.agents/agents/*.md` | generated (OpenCode format) | never hand-edit, run the generator |
| `.codex/agents/*.toml` | generated (Codex TOML) | never hand-edit, run the generator |
| `.github/agents/*.agent.md` | generated (Copilot `*.agent.md`) | never hand-edit, run the generator |
| `.opencode/agents`, `.kilo/agents` | symlinks to `../.agents/agents` | created and repaired by the generator |
| `.claude/skills` | symlink to `../.agents/skills` | never edit through the link |

Regenerate the subagent trees and repair the symlinks after any `subagents/*.md` change:

```bash
python tools/gen_subagents.py
```

On Windows, every symlink checks out as a plain text file unless Developer Mode is on and `core.symlinks` is set before
cloning. The commands are under "Cloning on Windows" in [CONTRIBUTING.md](CONTRIBUTING.md).

Full layout: [docs/repository-layout.md](docs/repository-layout.md). Who reads what:
[docs/agent-compatibility.md](docs/agent-compatibility.md). This repo uses no OpenSpec. The template's is for consumers.

---

## Repo conventions

On top of the global rules in `~/.claude/CLAUDE.md`:

- **The consumer boundary is the filename case.** A consumer gets the configuration the import pulls and the UPPERCASE
  documents under `docs/`. Lowercase documents, [README.md](README.md), [e2e/](e2e/), [sandbox-agent/](sandbox-agent/),
  [subagents/](subagents/) and [tools/](tools/) never ship, so no shipped document may link into them: the link
  resolves here and 404s there. [global/](global/) ships only through the global install in
  [docs/GLOBAL_SETUP.md](docs/GLOBAL_SETUP.md), so no project-import pathspec may name it.
  [main-thread-allowlist.txt](main-thread-allowlist.txt) never ships by either route.
- **Markdown lint.** [tools/check-markdown.py](tools/check-markdown.py) covers every human-facing document but this
  `AGENTS.md`, whose style matches anyway. One runnable command per fenced code block, language tag, no `#` comments.
- **One server set, one schema per file.** Change all five MCP files together: [.mcp.json](.mcp.json),
  [opencode.json](opencode.json), [.codex/config.toml](.codex/config.toml), [.vscode/mcp.json](.vscode/mcp.json) and
  [.github/mcp.json](.github/mcp.json). Which agent reads which, and why, is in [docs/MCP_SETUP.md](docs/MCP_SETUP.md).
- **No substitution token may appear in [opencode.json](opencode.json).** Kilo Code rejects the whole file on a
  `{env:VAR}`, which drops the MCP block and the `plugin` array that declares the gate. Local servers inherit the
  environment instead, and `context7` ships with no `headers` block. The detail is in
  [docs/MCP_SETUP.md](docs/MCP_SETUP.md) and nowhere else.
- **One gate, one rule, one wording.** A behaviour change is a change to
  [.agents/hooks/preflight_gate.py](.agents/hooks/preflight_gate.py) plus a case in
  [tools/tests/test_preflight_gate.py](tools/tests/test_preflight_gate.py), never a second copy of the logic. The
  `tools/tests/test_reminder_*.py` suites compare each reminder copy in a wiring file to its canonical source.
- **One tail, one check, one wording.** [.agents/instructions/reply-rules.md](.agents/instructions/reply-rules.md),
  [.agents/hooks/status_block_check.py](.agents/hooks/status_block_check.py) and its tests ship as one
  consistent set with no conflicts, and the hook is the enforcement.
- **The tooling is a package under [tools/](tools/).** [tools/pyproject.toml](tools/pyproject.toml) is the only place
  a dependency or a version is written, each an exact pin with no lock file, and `--group` needs pip 25.1 or newer.
- This file and the template obey the rules they ship. `AGENTS.md` and `AGENTS.md.example` follow "Writing
  AGENTS.md files" in [AGENTS.md.example](AGENTS.md.example), and [tools/check-agents-md.py](tools/check-agents-md.py)
  fails CI on a tracked `CLAUDE.md` or a file over its limit. Detail goes to `docs/`, never back in here.
- **CI runs on every pull request and every push to `master`,** with three parallel jobs: `actionlint`, `validate` for
  the local checks, and `sandbox` for the containerised suite. Before you push, run every command under "Local checks"
  in [CONTRIBUTING.md](CONTRIBUTING.md), which are the checks `validate` runs.
- **[.github/workflows/agent-live-tests.yml](.github/workflows/agent-live-tests.yml) is a separate workflow and never
  part of CI.** It runs only on `workflow_dispatch` and drives each agent against a real model with
  `REQUESTY_API_KEY` (Claude Code, OpenCode, Kilo Code) or `OPENAI_API_KEY` (Codex and Copilot on `gpt-6-luna`), so
  every run spends money. Start it only with the user's explicit approval for that one run.

---

## Adding or changing things

- **A skill or a subagent:** before adding one, read "Adding a new skill" or "Adding a new subagent" in
  [CONTRIBUTING.md](CONTRIBUTING.md). A subagent's source and its four generated trees are committed together, and
  each kind bumps its count badge in [README.md](README.md).
- **An MCP server:** add the block to all five MCP files (the ones listed under Repo conventions), document it in
  [docs/MCP_SETUP.md](docs/MCP_SETUP.md), and bump the MCP-count badge.
- **A shipped document:** name it in UPPERCASE under `docs/`, add its path to every
  `git checkout agent-standards/master --` pathspec that delivers documents (the Quickstart and all five per-agent
  blocks in [README.md](README.md), the import in [docs/AGENT_TOOLING.md](docs/AGENT_TOOLING.md), and both shell
  sections of [docs/AGENTS-UPDATE.md](docs/AGENTS-UPDATE.md)), and list it under Shipped in the README docs map. A
  document a consumer cannot pull is not shipped, whatever its name says.
- **A gate rule:** follow "One gate, one rule, one wording" above, and leave the wiring files alone unless the hook
  surface itself changed. A wiring change also needs the sandbox in [sandbox-agent/](sandbox-agent/README.md).

---

## Subagents and skills

`agent-engineer` owns every skill, subagent definition, hook wiring, MCP server block and this file, and does the web
research the gate denies the main thread. `markdown-writer` owns docs, `python-patterns` the generator, hooks and lint
scripts, `bash` and `powershell` the update scripts in [docs/AGENTS-UPDATE.md](docs/AGENTS-UPDATE.md), and
`code-reviewer` runs before any merge.

---

## Working Principles

1. **Think, simplify, stay surgical, verify.** The four principles in [AGENTS.md.example](AGENTS.md.example) apply
   here unchanged, and the `coding-standards` skill governs what the code should look like.
2. **Live progress by tool, not prose.** Keep a todowrite list current on any task of more than one step, start a
   session goal with the goal tool for long work, and use notify_user only when the user must act right now. The
   reply status tail follows [.agents/instructions/reply-rules.md](.agents/instructions/reply-rules.md).
3. **Number every question,** one continuous sequence per conversation, subpoints like 13.1. The
   question_numbering_check hook denies the next tool call when a reply carries an unnumbered question.

---

## Maintenance follow-ups

- **Copilot `userPromptTransformed` is documented only for the CLI and the cloud agent**
  (`https://docs.github.com/en/copilot/reference/hooks-reference`). Confirm VS Code and JetBrains fire it, note it here.
- **The Copilot `preToolUse` payload carries no agent identifier,** so no gate rule fires on that surface. When one
  lands, pass it with `--subagent` from [.github/hooks/preflight.json](.github/hooks/preflight.json) and set
  `GATE_KNOWN_GAP=0` in [sandbox-agent/live/copilot.sh](sandbox-agent/live/copilot.sh) in the same change.
- **The Copilot CLI tells every custom subagent not to write files.** CLI 1.0.81 appends
  `**CRITICAL: Do NOT write output to files.**` to its prompt (live run 36176881215), so live test 2 reports
  `KNOWN-GAP` through `SUBAGENT_NO_WRITE_MARKER` in [sandbox-agent/live/copilot.sh](sandbox-agent/live/copilot.sh).
  Recheck each CLI release, and remove that marker in the same change that sees the block gone.
- **Whether a Codex `Stop` hook can reject a reply is not measured.** Confirm it and say so plainly here. The markdown
  lint stays Claude-only, because Codex has no post-tool event.
- **JetBrains Copilot MCP is global-only and undocumented,** read from `~/.config/github-copilot/intellij/mcp.json`,
  so no JetBrains MCP file ships here. Ship one if GitHub documents a per-project path
  (`https://docs.github.com/en/copilot/how-tos/provide-context/use-mcp/extend-copilot-chat-with-mcp`).
