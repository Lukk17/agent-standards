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

- It denies a main-thread write of any file resolving inside the repository working tree, with no exemption for
  markdown, configuration, or documentation, and tells the caller to delegate the change instead. A write outside the
  repository, a write to the null device, and git branch switching stay allowed, so the main thread keeps full use of
  git.
- It denies an edit from a subagent whose own definition declares no skills, because that agent is not a specialist.
- It denies the main thread from running a web fetch or web search tool directly, on the one format where that
  tool's name is confirmed (Claude Code today; Codex has no confirmed equivalent name yet, see Maintenance
  follow-ups below). It spawns a subagent to do the research and report back instead.
- Every rule above fires only once the caller is positively identified as the main thread. A format whose payload
  carries nothing that could identify the caller, currently GitHub Copilot, is left ungated rather than guessed at,
  because denying blind risks blocking a legitimate subagent as often as it blocks the main thread.
- It fails open. Any parse error, missing key, or unexpected payload allows the call, because a broken gate must never
  break a session.

Each agent wires that one script to its own hook surface:

| Agent | Wiring | Events |
| --- | --- | --- |
| Claude Code | [.claude/settings.json](.claude/settings.json) | `UserPromptSubmit`, `PreToolUse` (matcher `^(Edit\|Write\|NotebookEdit\|Bash\|WebFetch\|WebSearch)$`), `Stop` for the formatting checker |
| Codex | inline `[[hooks.*]]` tables in [.codex/config.toml](.codex/config.toml) | `UserPromptSubmit`, `SubagentStart`, `PreToolUse` (matcher `^(Bash\|shell\|apply_patch\|Edit\|Write\|NotebookEdit)$`) |
| OpenCode and Kilo Code | [.agents/plugin/hooks.js](.agents/plugin/hooks.js), declared once by path in the `plugin` array of [opencode.json](opencode.json), which both tools read | `tool.execute.before` |
| GitHub Copilot | [.github/hooks/preflight.json](.github/hooks/preflight.json) | `sessionStart`, `subagentStart`, `preToolUse` (matcher `bash\|powershell\|create\|edit`) |

Per-surface details worth knowing before you touch any of them:

- Claude Code detects a subagent by the presence of `agent_id` in the hook payload, which it documents as present only
  inside a subagent.
- Every wiring anchors the gate at the project root, and a missing gate script allows. A session started in a
  subdirectory resolved the relative script path to nothing, and Python exits 2 when it cannot open the file it was
  handed, which is the deny code on Claude Code and Codex and denies on Copilot too. Each wiring therefore moves to the
  project root first: `${CLAUDE_PROJECT_DIR}` on Claude Code, `git rev-parse --show-toplevel` on Codex, `"cwd": "."` on
  Copilot, the runtime's `worktree` in the plugin. The claude, codex and copilot formats deny with exit 0 and JSON on
  stdout and never use a non-zero exit, so forcing a zero exit on those three turns any error back into an allow. Codex
  and Copilot each carry a separate command field per shell, so they spell it per shell: `|| exit 0` wherever a POSIX
  shell or cmd runs the line, `; exit 0` in Copilot's `powershell` field. Claude Code has one field and picks the shell
  itself, so it uses `; exit 0` everywhere, which bash and PowerShell both parse. After `||` PowerShell reads `exit` as
  a command name and errors, which is why the `||` form cannot be used there. The plugin cannot force a zero exit at
  all, because its plain format does use exit 2 as the denial, so it reads each hook file before spawning it and drops
  the ones it cannot open.
- Claude Code's `PreToolUse` command now calls the gate directly, with no wrapper. Its single command field still
  picks the shell itself, so no redirect token means the same thing in both shells it may pick (`2>/dev/null` opens a
  literal `dev` directory in PowerShell, `2>$null` is ambiguous in bash), which is still why the gate owns its own
  silence rather than relying on one: `preflight_gate.py` swaps `sys.stderr` for a null sink for the call and
  restores it in a `finally`. The `plain` format that OpenCode and Kilo Code use still writes its deny message to
  standard error, so that deny channel is unaffected. Codex and Copilot keep the per-shell redirects their variant
  fields let them write.
- Codex supports both inline `[[hooks.*]]` tables and a separate `hooks.json`, and warns when a single configuration
  layer carries both. The tables therefore live in `.codex/config.toml` and `.codex/hooks.json` no longer exists.
- Copilot hooks are no longer CLI-only. They run in VS Code and in JetBrains as well, from the same `.github/hooks/`
  path. Event names are camelCase, and a hook entry carries `bash` and `powershell` as sibling string fields next to
  `type`, not a nested `command` object. A nested one is silently ignored, which leaves that surface ungated.
- The Copilot CLI additionally reads hooks from `.claude/settings.json`. The JetBrains plugin does not: its bundled
  agent hardcodes `.github/hooks/**/*.json` and rejects PascalCase event names. That borrowed Claude wiring is inert on
  the CLI, and it is meant to stay that way. Copilot names its tools in lower case, the same `bash`, `powershell`,
  `create` and `edit` its own matcher lists, and it compares a matcher anchored and case sensitively, so the PascalCase
  Claude pattern matches nothing there. Nothing is ungated, because
  [.github/hooks/preflight.json](.github/hooks/preflight.json) already covers that surface. Do not widen the Claude
  pattern to Copilot's tool names to make it fire: the CLI reads both files, so it would then run the gate twice on
  every tool call.
- The JetBrains plugin scans `.claude/agents`, but it only understands its own `*.agent.md` format, so subagent
  definitions cannot be shared between Copilot and Claude Code or OpenCode.
- OpenCode and Kilo Code have no event that can block a finished reply, so their plugin does everything at
  `tool.execute.before`. It is a runner rather than a fixed wiring: on every tool call it discovers every hook in
  [.agents/hooks/](.agents/hooks/), runs them in the order each hook declares, and hands each one a versioned JSON
  envelope on standard input with `--format plain`. Adding a hook file is the whole registration step. The contract,
  including the envelope fields, the ordering rule, the deny exit code, and the fail-open rules, is written up in
  [docs/hooks-contract.md](docs/hooks-contract.md).

Verified against Claude Code 2.1.250, Codex 0.150.1, OpenCode 1.18.25, Kilo Code 7.5.5, and GitHub Copilot CLI
1.0.81.

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
  scripts hold the only copy of the gate logic and of the response formatting check, and the plugin is a thin runner
  with no rules of its own that hands every OpenCode and Kilo Code tool call to every hook in that directory.

---

## Repo conventions

On top of the global rules in `~/.claude/CLAUDE.md`:

- **The consumer boundary is the filename case.** A consumer receives exactly two kinds of thing: the agent
  configuration files the import pulls, and the UPPERCASE-named markdown documents under `docs/`. Every lowercase
  document under `docs/` is ours and never ships. [README.md](README.md) is the one uppercase file that stays here.
  [e2e/](e2e/), [sandbox-agent/](sandbox-agent/), [subagents/](subagents/), and [tools/](tools/) are test and build
  material and never reach a consumer, so no shipped document may link into them. A shipped document linking to a
  lowercase one is the same defect: the link resolves here and 404s there.
- **Never hand-edit generated subagent files.** Edit `subagents/<name>.md`, then run the generator. CI fails if the
  generated trees drift from canonical.
- **Markdown lint.** `README.md`, `AGENTS.md.example`, `docs/*.md`, and `.agents/skills/**/*.md` must contain no
  em-dashes or en-dashes, no prose line over 120 characters, and no level-2 heading. This real `AGENTS.md` is not in
  the lint scope, but match the style anyway.
- **One runnable command per fenced code block** in any doc a human copies, with the matching language tag and no
  `#` comment lines inside the block (global rule).
- **One server set, one schema per file.** [.mcp.json](.mcp.json) (key `mcpServers`) serves Claude Code only.
  [opencode.json](opencode.json) (key `mcp`) serves OpenCode and Kilo Code, which accepts `opencode.json` as a valid
  config filename. [.codex/config.toml](.codex/config.toml) (`[mcp_servers.*]` tables) serves Codex.
  [.vscode/mcp.json](.vscode/mcp.json) (key `servers`) serves GitHub Copilot in VS Code. [.github/mcp.json](.github/mcp.json)
  (key `mcpServers`, `"type": "local"` for a stdio server rather than `.mcp.json`'s `"type": "stdio"`) serves the
  GitHub Copilot CLI, per the CLI's own documented schema. Change all five together. Only the top-level key, the
  `type` value, and the environment-variable syntax differ. Copilot in JetBrains reads only a global
  `~/.config/github-copilot/intellij/mcp.json`, so no project file exists for it, and the Copilot cloud agent is
  configured on a repository settings page rather than in a file. Full human setup in
  [docs/MCP_SETUP.md](docs/MCP_SETUP.md), per-surface matrix in
  [docs/agent-compatibility.md](docs/agent-compatibility.md).
- **`.github/mcp.json` exists because the Copilot CLI is capable of reading `.mcp.json` but this repo does not let
  it.** The Copilot CLI documents two project-level MCP sources, `.mcp.json` and `.github/mcp.json`, and reads both
  when both exist. `.mcp.json` carries Claude Code's `${VAR:-default}` syntax, which the CLI has no substitution
  engine for and would pass through as the literal, unresolved string, so the CLI needs a file of its own with plain
  literal values, matching how every other local server in this repo ships with no token in its config and gets its
  secret from the process environment instead. The unavoidable side effect: the CLI's own precedence rule makes
  `.mcp.json` win over `.github/mcp.json` whenever both files live in the same directory and define the same server
  name, which is true for all eight servers here. Measured directly (`copilot mcp get context7 --json` with both
  files present, Copilot CLI 1.0.81): the CLI resolves `context7` from `.mcp.json`, and its `headers` block shows the
  literal string `${CONTEXT7_API_KEY:-}` rather than a real header, exactly the failure `.github/mcp.json` exists to
  avoid but, as things stand, does not fully avoid. Removing `.mcp.json` from the same directory (not currently an
  option, since it is Claude Code's file) makes the CLI resolve every server from `.github/mcp.json` correctly. There
  is no CLI flag or setting to make it skip one workspace source and honour the other, only per-server-name
  `--disable-mcp-server` and a `/mcp disable` command that both persist to the CLI's own configuration rather than to
  this repo's files. This is a known, documented limitation of shipping both files side by side, not a defect in
  `.github/mcp.json` itself.
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
  because neither tool has a stable per-turn injection hook, so it only runs the hooks.
- **The tooling is a package under [tools/](tools/).** Sources sit at the top ([tools/gen_subagents.py](tools/gen_subagents.py),
  [tools/check-markdown.py](tools/check-markdown.py)), tests sit in [tools/tests/](tools/tests/) with an `__init__.py`
  and a `conftest.py`. [tools/pyproject.toml](tools/pyproject.toml) is the only place a dependency or a version is
  written by hand, and it also holds the pytest configuration, so `testpaths` is relative to `tools/`.
- **There is no lock file.** Every version in [tools/pyproject.toml](tools/pyproject.toml) is an exact pin, which is
  reproducible without hashes, so nothing is compiled and nothing is generated. Runtime dependencies sit in
  `[project.dependencies]`, test dependencies in the `dev` dependency group, and the build backend in `[build-system]`.
  CI installs the project and the `dev` group in one command, and pins pip first because `--group` needs pip 25.1 or
  newer.
- **CI runs on every pull request and on every push to `master`,** and `workflow_dispatch` still starts it by hand.
  Three jobs run in parallel and none gates another: `actionlint` on the workflow YAML, `validate` for the local
  checks listed below, and `sandbox` for the containerised suite, which builds the image once and then runs the
  per-project import assertions, a global install run twice, and a scoped single-agent global install. The sandbox job
  is the long one. Verify locally before you push, because the pipeline is the second opinion rather than the first.

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
python tools/check-badges.py
```

```bash
python -m pytest tools/
```

```bash
python -c "import json; [json.load(open(f)) for f in ['.mcp.json','opencode.json','.vscode/mcp.json','.github/mcp.json','.claude/settings.json','.github/hooks/preflight.json']]"
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
- **An MCP server:** add the block to all five MCP files (the ones listed under Repo conventions), document it in
  [docs/MCP_SETUP.md](docs/MCP_SETUP.md), and bump the MCP-count badge.
- **A shipped document:** name it in UPPERCASE under `docs/`, add its path to every
  `git checkout agent-standards/master --` pathspec that delivers documents (the Quickstart and all five per-agent
  blocks in [README.md](README.md), the import in [docs/AGENT_TOOLING.md](docs/AGENT_TOOLING.md), and both shell
  sections of [docs/AGENTS-UPDATE.md](docs/AGENTS-UPDATE.md)), and list it under Shipped in the README docs map. A
  document a consumer cannot pull is not shipped, whatever its name says.
- **A gate rule:** edit [.agents/hooks/preflight_gate.py](.agents/hooks/preflight_gate.py), add the case to
  [tools/tests/test_preflight_gate.py](tools/tests/test_preflight_gate.py), and leave the wiring files alone unless the
  hook surface itself changed. When the wiring does change, the unit tests are not enough: run the containerised
  sandbox in [sandbox-agent/](sandbox-agent/README.md), which asserts what each agent actually discovers. CI runs the
  same suite on every pull request, so a wiring change that breaks discovery fails the build either way.

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
- **The Copilot `preToolUse` payload carries no agent identifier, and its wiring never passes `--subagent` either.**
  There is no `agent_id` or equivalent field in Copilot's own payload, and
  [.github/hooks/preflight.json](.github/hooks/preflight.json) never sets `--subagent` on the `preToolUse` call, so
  [.agents/hooks/preflight_gate.py](.agents/hooks/preflight_gate.py) cannot tell a Copilot subagent from the Copilot
  main thread. Caller identity resolves to unknown on every call, so neither Rule A, Rule B, nor Rule C ever fires on
  this surface: the whole surface is unenforced, which fails in the unsafe direction rather than the safe one.
  Recheck the hooks reference for an agent identifier and pass it through with `--subagent` when one lands.
- **JetBrains Copilot MCP is global-only and officially undocumented.** The plugin reads MCP from
  `~/.config/github-copilot/intellij/mcp.json`. There is no per-project MCP file, and GitHub documents only the in-IDE
  UI rather than the path, so no JetBrains MCP file ships here. Recheck whether GitHub adds a documented per-project
  path (`https://docs.github.com/en/copilot/how-tos/provide-context/use-mcp/extend-copilot-chat-with-mcp`) and ship one
  if it lands.
