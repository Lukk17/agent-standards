# AGENTS.md

Instructions for AI coding agents working on the **agent-standards repo itself**. This is the upstream source, not a
consumer project. Claude Code loads this file via [.claude/CLAUDE.md](.claude/CLAUDE.md) (`@../AGENTS.md`). Kilo Code,
OpenCode, Codex, and GitHub Copilot read it from the project root.

[AGENTS.md.example](AGENTS.md.example) is the consumer-facing template and the only `.example` file left in the repo.
Everything else (hooks, MCP configuration, skills, subagents) is universal and ships as a real committed file that a
consumer pulls and uses unchanged. Only `AGENTS.md` carries repo-specific content, which is why only it needs a
template. This real `AGENTS.md` describes how to work on the standards themselves and is never shipped downstream.

---

## Required opening move

Before any code work on a task, name the skill(s) and subagent(s) that own it and invoke them, or state "none apply"
and why. State this as the first line of your reply. It is a required output you produce, not a passive banner to skim
past. This is a hard gate.

Investigation, review, and bounded implementation are delegated by default. Doing a specialist's work inline from the
main session is the failure mode this gate prevents. Re-run the check at the start of every task. Most work in this
repo is documentation and the Python tooling, so `markdown-writer`, `python-patterns`, and `python-testing` are the
usual owners, with `code-reviewer` before any merge.

The gate is enforcing, not advisory. One shared rule in
[.agents/hooks/preflight_gate.py](.agents/hooks/preflight_gate.py) decides every tool call, on every agent:

- It denies a source-file edit made from the main thread and tells the caller to delegate the change instead.
- It denies an edit from a subagent whose own definition declares no skills, because that agent is not a specialist.
- It allows markdown, configuration, and documentation edits from the main thread.
- It fails open. Any parse error, missing key, or unexpected payload allows the call, because a broken gate must never
  break a session.

Each agent wires that one script to its own hook surface:

| Agent | Wiring | Events |
| --- | --- | --- |
| Claude Code | [.claude/settings.json](.claude/settings.json) | `UserPromptSubmit`, `SessionStart`, `PreToolUse` (matcher `Edit`, `Write`, `NotebookEdit`, `Bash`), `Stop` for the formatting checker |
| Codex | inline `[[hooks.*]]` tables in [.codex/config.toml](.codex/config.toml) | `UserPromptSubmit`, `SubagentStart`, `PreToolUse` |
| OpenCode and Kilo Code | [.agents/plugin/hooks.js](.agents/plugin/hooks.js), declared once by path in the `plugin` array of [opencode.json](opencode.json), which both tools read | `tool.execute.before` |
| GitHub Copilot | [.github/hooks/preflight.json](.github/hooks/preflight.json) | `sessionStart`, `subagentStart`, `preToolUse` |

Per-surface details worth knowing before you touch any of them:

- Claude Code detects a subagent by the presence of `agent_id` in the hook payload, which it documents as present only
  inside a subagent.
- Codex supports both inline `[[hooks.*]]` tables and a separate `hooks.json`, and warns when a single configuration
  layer carries both. The tables therefore live in `.codex/config.toml` and `.codex/hooks.json` no longer exists.
- Copilot hooks are no longer CLI-only. They run in VS Code and in JetBrains as well, from the same `.github/hooks/`
  path. Event names are camelCase, and each command is an object with a `bash` key and a `powershell` key.
- The Copilot CLI additionally reads hooks from `.claude/settings.json`. The JetBrains plugin does not: its bundled
  agent hardcodes `.github/hooks/**/*.json` and rejects PascalCase event names.
- The JetBrains plugin scans `.claude/agents`, but it only understands its own `*.agent.md` format, so subagent
  definitions cannot be shared between Copilot and Claude Code or OpenCode.
- OpenCode and Kilo Code have no event that can block a finished reply, so their plugin runs both checks at
  `tool.execute.before`. It calls the gate first, then feeds the latest assistant text to
  [.agents/hooks/no_ai_markers_check.py](.agents/hooks/no_ai_markers_check.py) in its `--text` mode and throws when the
  prose carries an em dash, an en dash, a clause-joining semicolon, or bold. Each message is checked once per session.

Verified against Claude Code 2.1.245, Codex 0.149.1, OpenCode 1.18.23, and Kilo Code 7.4.23.

---

## What this repo is

agent-standards is a single source of AI-agent configuration (skills, subagents, MCP servers, preflight hooks, shared
instructions) imported into other projects via Git selective checkout. Consumer projects pull production-ready folders
and pull updates with one `git fetch`. The canonical [subagents/](subagents/) source and the [tools/](tools/) generator
stay here and are never imported downstream.

The load-bearing distinction is **canonical vs generated**. Some trees are hand-edited here, some are emitted by a
script and must never be hand-edited, and some are symlinks the generator creates and repairs.

| Tree | Status | How to edit |
| --- | --- | --- |
| `subagents/*.md` | canonical | edit directly, then regenerate |
| `.agents/skills/*/SKILL.md` | canonical | edit directly |
| `.agents/hooks/preflight_gate.py`, `.agents/hooks/no_ai_markers_check.py` | canonical | edit directly, then run the pytest suite |
| `.agents/plugin/hooks.js` | canonical | edit directly |
| `AGENTS.md.example`, `docs/*.md` | canonical | edit directly |
| `tools/*.py`, `tools/tests/*.py`, `tools/pyproject.toml` | canonical | edit directly, then run the pytest suite |
| `.claude/agents/*.md` | generated (Claude front matter with a `skills` key) | never hand-edit, run the generator |
| `.agents/agents/*.md` | generated (OpenCode format) | never hand-edit, run the generator |
| `.codex/agents/*.toml` | generated (Codex TOML) | never hand-edit, run the generator |
| `.github/agents/*.agent.md` | generated (Copilot `*.agent.md`) | never hand-edit, run the generator |
| `.opencode/agents`, `.kilo/agents` | symlinks to `../.agents/agents` | created and repaired by the generator |
| `.claude/skills` | symlink to `../.agents/skills` | never edit through the link |

The generated subagent trees are per tool because no shared subagent format exists. Kilo Code moved its configuration
root from `.kilocode/` to `.kilo/`, and `.kilocode/` is gone from this repo entirely.

Regenerate the subagent trees and repair the symlinks after any `subagents/*.md` change:

```bash
python tools/gen_subagents.py
```

Windows prerequisite: the symlinks only survive a checkout when Git is allowed to create them. Turn on Windows
Developer Mode and set the Git option below before cloning. Without both, Git checks each link out as a plain text
file holding its target path, and every agent that follows the link finds nothing.

```powershell
git config core.symlinks true
```

Full layout reference: [docs/repository-layout.md](docs/repository-layout.md). This repo does not use OpenSpec itself.
The OpenSpec sections in the `.example` are for consumers.

### Which parts of .agents/ serve which agent

`.agents/` is not one shared tree with one audience. Each subdirectory has a different reader set:

- [.agents/skills/](.agents/skills/) is read by all five agents. OpenCode, Kilo Code, Codex, and GitHub Copilot read
  the directory natively. Only Claude Code needs a symlink, `.claude/skills`, which is why that one link exists.
- [.agents/agents/](.agents/agents/) is the OpenCode-format subagent tree, and only OpenCode and Kilo Code use it, both
  through the `.opencode/agents` and `.kilo/agents` symlinks. Claude Code, Codex, and Copilot each read their own
  generated tree instead, because none of the three formats is interchangeable.
- [.agents/hooks/](.agents/hooks/) and [.agents/plugin/](.agents/plugin/) are invoked by every adapter. The two Python
  scripts hold the only copy of the gate logic and of the response formatting check, and the plugin is a thin shim with
  no rules of its own that hands OpenCode and Kilo tool calls to the same Python script.

---

## Repo conventions

On top of the global rules in `~/.claude/CLAUDE.md`:

- **Never hand-edit generated subagent files.** Edit `subagents/<name>.md`, then run the generator. CI fails if the
  generated trees drift from canonical.
- **Markdown lint.** `README.md`, `AGENTS.md.example`, `docs/*.md`, and `.agents/skills/**/*.md` must contain no
  em-dashes or en-dashes, no prose line over 120 characters, and no level-2 heading. This real `AGENTS.md` is not in
  the lint scope, but match the style anyway.
- **One runnable command per fenced code block** in any doc a human copies, with the matching language tag and no
  `#` comment lines inside the block (global rule).
- **One server set, one schema per file.** [.mcp.json](.mcp.json) (key `mcpServers`) serves Claude Code and the GitHub
  Copilot CLI, which reads a repo-root `.mcp.json` with the same schema. [opencode.json](opencode.json) (key `mcp`)
  serves OpenCode and Kilo Code, which accepts `opencode.json` as a valid config filename.
  [.codex/config.toml](.codex/config.toml) (`[mcp_servers.*]` tables) serves Codex. [.vscode/mcp.json](.vscode/mcp.json)
  (key `servers`) serves GitHub Copilot in VS Code. Change all four together. Only the top-level key, the `type` value,
  and the environment-variable syntax differ. Copilot in JetBrains reads only a global
  `~/.config/github-copilot/intellij/mcp.json`, so no project file exists for it, and the Copilot cloud agent is
  configured on a repository settings page rather than in a file. Full human setup in
  [docs/MCP_SETUP.md](docs/MCP_SETUP.md), per-surface matrix in
  [docs/agent-compatibility.md](docs/agent-compatibility.md).
- **No substitution token may appear in [opencode.json](opencode.json).** Kilo Code does not leave `{env:VAR}` literal
  the way this repo used to claim. It treats any `{env:VAR}` in a project config file as a fatal error, rejects that
  entire file, and carries on with the rest of its config chain. For `opencode.json` that would drop the MCP block and
  the `plugin` array that declares the preflight gate, so a single token would leave Kilo Code running ungated. A
  `{env:VAR}` or `{file:...}` inside an MCP `headers` block is milder, Kilo drops only that server, but
  `kilocode config check` still exits 1 on the warning. The file therefore carries neither form. Local servers need no
  token in it: both tools spawn them with the environment of the process that started the agent and merge any
  `environment` block on top of it, so exporting the variable is enough. The one value that cannot be inherited is the
  Context7 API key, which travels as an HTTP header, so `context7` is declared here with no `headers` block at all and
  both tools use the free tier. There is no project-level overlay to put it in: `.opencode/opencode.json` is deleted,
  and the only place an authenticated Context7 block belongs is a user's own global config. Say that in
  [docs/MCP_SETUP.md](docs/MCP_SETUP.md) and nowhere else.
- **One gate, one rule, one wording.** The canonical text is the Required opening move above and the canonical rule is
  [.agents/hooks/preflight_gate.py](.agents/hooks/preflight_gate.py). Every adapter calls that one script, so a
  behaviour change is a change to the script plus a case in
  [tools/tests/test_preflight_gate.py](tools/tests/test_preflight_gate.py), never a second copy of the logic. Keep the
  injected wording identical in every wiring file that injects it. The OpenCode and Kilo Code plugin injects nothing,
  because neither tool has a stable per-turn injection hook, so it only calls the script.
- **The tooling is a package under [tools/](tools/).** Sources sit at the top ([tools/gen_subagents.py](tools/gen_subagents.py),
  [tools/check-markdown.py](tools/check-markdown.py)), tests sit in [tools/tests/](tools/tests/) with an `__init__.py`
  and a `conftest.py`. [tools/pyproject.toml](tools/pyproject.toml) is the only place a dependency or a version is
  written by hand, and it also holds the pytest configuration, so `testpaths` is relative to `tools/`.
- **There is no lock file.** Every version in [tools/pyproject.toml](tools/pyproject.toml) is an exact pin, which is
  reproducible without hashes, so nothing is compiled and nothing is generated. Runtime dependencies sit in
  `[project.dependencies]`, test dependencies in the `dev` dependency group, and the build backend in `[build-system]`.
  CI installs the project and the `dev` group in one command, and pins pip first because `--group` needs pip 25.1 or
  newer.
- **CI is manual.** Workflows run on `workflow_dispatch` / `workflow_call` only, so nothing runs on push. Verify
  locally before declaring work done.

Local verification (the same checks CI runs). Install the pinned dependencies first, with pip 25.1 or newer:

```bash
pip install ./tools --group ./tools/pyproject.toml:dev
```

```bash
python tools/gen_subagents.py --check
```

```bash
python tools/check-markdown.py
```

```bash
python -m pytest tools/
```

```bash
python -c "import json; [json.load(open(f)) for f in ['.mcp.json','opencode.json','.vscode/mcp.json','.claude/settings.json','.github/hooks/preflight.json']]"
```

```bash
python -c "import tomllib; tomllib.load(open('.codex/config.toml','rb'))"
```

---

## Adding or changing things

- **A skill:** create `.agents/skills/<name>/SKILL.md` (plus a `references/` subdir if it needs depth). Four agents
  pick it up from the directory itself and the `.claude/skills` symlink covers Claude Code, so no wiring is needed.
  Bump the skill-count badge in [README.md](README.md).
- **A subagent:** add or edit `subagents/<name>.md`, run the generator, and commit the canonical source and the four
  generated trees together. Bump the subagent-count badge.
- **An MCP server:** add the block to all four MCP files (the ones listed under Repo conventions), document it in
  [docs/MCP_SETUP.md](docs/MCP_SETUP.md), and bump the MCP-count badge.
- **A gate rule:** edit [.agents/hooks/preflight_gate.py](.agents/hooks/preflight_gate.py), add the case to
  [tools/tests/test_preflight_gate.py](tools/tests/test_preflight_gate.py), and leave the wiring files alone unless the
  hook surface itself changed. When the wiring does change, the unit tests are not enough: run the containerised
  sandbox in [sandbox-agent/](sandbox-agent/README.md), which asserts what each agent actually discovers.

---

## Subagents and skills

Use subagents proactively, not reactively, and spawn them in parallel when the work is independent (one message,
multiple `Agent` calls). Direct a generalist subagent to invoke specific skills as part of its task. Full catalogue:
list `.claude/agents/*.md` or `.agents/agents/*.md`, and browse skills in [.agents/skills/](.agents/skills/).

For this repo specifically: `markdown-writer` owns doc work, `python-patterns` and `python-testing` own the generator,
the hook scripts, and the lint script, `code-reviewer` runs before any merge, and `bash` / `powershell` own the update
scripts in [docs/AGENTS-UPDATE.md](docs/AGENTS-UPDATE.md).

---

## Working Principles

Apply these to every task, in order. They govern how you work, and the `coding-standards` skill governs what the code
should look like.

1. **Think before coding.** State assumptions. When the prompt is ambiguous, surface the interpretations and ask
   rather than silently picking one. Propose a simpler approach if one exists.
2. **Simplicity first.** Write the minimum that solves the problem. No unrequested features, abstractions, or
   configurability. If 200 lines could be 50, rewrite it.
3. **Surgical changes.** Touch only what the task requires. Do not "improve" adjacent code or reformat untouched
   lines. Match existing style. Remove only the imports and helpers your own change orphans.
4. **Goal-driven execution.** Convert vague asks into verifiable checks, state the plan, then loop until each check
   passes. Do not claim a task is done without running the verification.

---

## Maintenance follow-ups

- **OpenCode per-turn gate injection still needs an experimental hook.** Enforcement now rides the stable
  `tool.execute.before` hook in [.agents/plugin/hooks.js](.agents/plugin/hooks.js), so the gate blocks calls
  without any experimental surface. Injecting the gate text into context every turn still requires
  `experimental.chat.system.transform`, which is unchanged and still experimental in OpenCode 1.18.23. Periodically
  recheck `https://opencode.ai/docs/plugins/`. When it stabilises, add per-turn injection to the plugin so OpenCode and
  Kilo Code match the other three, then remove this note. Tracked in project memory so it resurfaces each session.
- **Kilo Code is settled, no action outstanding.** Kilo reads `.agents/skills/` natively, so it needs no skill symlink.
  Its subagent tree is the `.kilo/agents` symlink to `../.agents/agents`, which the generator creates and repairs, so
  there is nothing per-Kilo to generate. It accepts the root `opencode.json` for MCP servers and for the plugin
  declaration, and `.kilocode/` is deleted. No `.kilo/kilo.jsonc` ships, because Kilo needs no per-tool copy of
  anything once the shared file carries no substitution tokens. The one live constraint, that a `{env:VAR}` anywhere
  in project config makes Kilo reject the whole file, is recorded under Repo conventions rather than here.
- **GitHub Copilot per-turn injection is available and not yet adopted.** Copilot now exposes a `userPromptTransformed`
  event on the CLI and on the cloud agent, so the old claim that it cannot re-inject per turn is wrong.
  [.github/hooks/preflight.json](.github/hooks/preflight.json) still injects only at `sessionStart` and
  `subagentStart`. Add a `userPromptTransformed` entry with the same wording, confirm the JetBrains plugin tolerates
  the extra event, and check `https://docs.github.com/en/copilot/reference/hooks-reference` for the exact payload
  shape before wiring it.
- **The Copilot `preToolUse` payload carries no agent identifier.** There is no `agent_id` or equivalent field, so
  [.agents/hooks/preflight_gate.py](.agents/hooks/preflight_gate.py) cannot tell a Copilot subagent from the Copilot
  main thread. Rule B (deny a subagent that declares no skills) therefore never fires on Copilot, and Rule A (deny a
  main-thread source edit) applies to Copilot subagents as well, which fails in the safe direction but is stricter
  than intended. Recheck the hooks reference for an agent identifier and pass it through with `--subagent` when one
  lands.
- **JetBrains Copilot MCP is global-only and officially undocumented.** The plugin reads MCP from
  `~/.config/github-copilot/intellij/mcp.json`. There is no per-project MCP file, and GitHub documents only the in-IDE
  UI rather than the path, so no JetBrains MCP file ships here. Recheck whether GitHub adds a documented per-project
  path (`https://docs.github.com/en/copilot/how-tos/provide-context/use-mcp/extend-copilot-chat-with-mcp`) and ship one
  if it lands.
