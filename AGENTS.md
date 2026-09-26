# AGENTS.md

Instructions for agents working on agent-standards itself. This file is never shipped. Consumers get
[AGENTS.md.example](AGENTS.md.example), the only `.example` file, because every other configuration file ships
unchanged.

---

## Required opening move

Before any code work on a task, name the skill(s) and subagent(s) that own it and invoke them, or state "none apply"
and why, as the first line of your reply. This is a hard gate.

Every wiring injects the first text below into each main-thread prompt, word for word. A subagent gets the second text
instead, because a subagent told to delegate turns its own task away. Line breaks and blank lines are part of the
wording. How each wiring prints them is in [docs/hooks-contract.md](docs/hooks-contract.md).

```text
PREFLIGHT: before code work, name the skills and subagents that own this task and invoke them, or say none apply and why. Delegate investigation, review and bounded implementation by default. Follow the user-communication skill when writing to the user. If the prompt asks anything, answer every question first, then start the work. End every reply to the user with this block, exactly as shown: no heading, no bullets, no numbered list, plain lines only, keeping every blank line:

Running: `running task name` (or: nothing)

~~DONE: older finished task~~
~~DONE: most recent finished task~~

**NOW: what is being done right now**

Next: the next task
Then: the task after that

Waiting on: what you wait for (or: nothing)

When several tasks run, list each name in backticks on the Running line, separated by commas.
```

The subagent text:

```text
PREFLIGHT for a subagent: you are a subagent, and the main thread delegated this task to you. Do the work yourself with your own tools and load the skills your definition names. The rules that the main thread must delegate and may not write files apply to the main thread only, so do not hand this task on and do not refuse it for that reason. The preflight gate still checks every tool call you make. Report back what you changed and how you verified it.
```

The gate is enforcing, not advisory. One shared rule in
[.agents/hooks/preflight_gate.py](.agents/hooks/preflight_gate.py) decides every tool call, on every agent:

- It denies the main thread a write of any file inside the repository, by any tool or shell, with no exemption for
  markdown, configuration, or documentation, and tells it to delegate the change instead. The repository is the
  process working directory, the project root the payload names in `cwd`, and the gate's own project two folders up.
  A write outside it, a write to the null device, a write to `tasks.md` at the project root, and git branch switching
  stay allowed. How the gate places a path and reads commands, wrappers and inline code is in
  [docs/agent-compatibility.md](docs/agent-compatibility.md) under "Hook enforcement".
- It denies any tool call, not only an edit, from a subagent whose own definition declares no skills, because that
  agent is not a specialist. The rule reads `agent_type` out of the payload and looks the definition up in the six
  agent trees, so an unknown or unreadable `agent_type` allows rather than denies.
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
- Known limits of the write rule, accepted rather than open: a write form the gate does not know passes, a top-level
  command it cannot parse allows, MCP tools are not gated, code run by an allowlisted tool is trusted rather than read,
  Copilot's main thread is not gated, the risky variable and option lists come from knowledge rather than vendor
  documentation, and a loopback share whose folder cannot be determined denies. Re-audit only when the rule changes,
  and record a new limit here rather than chasing it.

Each agent wires that one script, and the hooks beside it, to its own hook surface. The events per surface are in
[docs/agent-compatibility.md](docs/agent-compatibility.md).

| Agent | Wiring | Gate matcher |
| --- | --- | --- |
| Claude Code | [.claude/settings.json](.claude/settings.json) | `^(Edit\|Write\|MultiEdit\|NotebookEdit\|Bash\|PowerShell\|WebFetch\|WebSearch)$` |
| Codex | inline `[[hooks.*]]` tables in [.codex/config.toml](.codex/config.toml) | `^(Bash\|shell\|apply_patch\|Edit\|Write\|NotebookEdit)$` |
| OpenCode and Kilo Code | [.agents/plugin/hooks.js](.agents/plugin/hooks.js), declared once by path in the `plugin` array of [opencode.json](opencode.json), which both tools read | none, every tool call |
| GitHub Copilot | [.github/hooks/preflight.json](.github/hooks/preflight.json) | `bash\|powershell\|create\|edit\|apply_patch` |

Per-surface details worth knowing before you touch any of them:

- Claude Code's `SessionStart` also injects the subagent supervision text, plain context with no script behind it.
  [docs/GLOBAL_SETUP.md](docs/GLOBAL_SETUP.md) and [sandbox-agent/setup-global.sh](sandbox-agent/setup-global.sh)
  carry it word for word.
- Every hook runs on `-S -E` under `python3`, falling back to `python`.
- No hook uses `argparse`, which exits 2 on a usage error. Two is the deny code in the plain format, so a stray flag
  would read as a block. Each hook scans `sys.argv` by hand instead and treats an unknown flag as an allow.
- Every wiring moves to the project root before it calls a hook, and forces a zero exit where its format allows, so a
  missing script allows. A session started in a subdirectory once denied every call, because Python exits 2 on a
  file it cannot open. Codex's `commandWindows` runs under PowerShell and ends in `; exit 0`, because Windows
  PowerShell 5.1 has no `||`. The plugin cannot force a zero exit, so it drops a hook file it cannot open.
- Claude Code runs every command hook in shell form, Git Bash on Windows
  (`https://code.claude.com/docs/en/hooks#exec-form-and-shell-form`, measured on 2.1.281). Without Git Bash every
  Claude hook fails to parse and allows, so the setup docs require Git for Windows.
- The Claude Code matcher names `PowerShell` beside `Bash`, because on Windows "A hook that matches only `Bash` never
  fires there" (`https://code.claude.com/docs/en/hooks#powershell`).
- Codex hooks live inline in `.codex/config.toml`. Codex warns when one layer also carries a `hooks.json`, so
  `.codex/hooks.json` does not exist.
- Copilot hooks are no longer CLI-only. They run in VS Code and in JetBrains as well, from the same `.github/hooks/`
  path. Event names are camelCase, and a hook entry carries `bash` and `powershell` as sibling string fields next to
  `type`, not a nested `command` object. A nested one is silently ignored, which leaves that surface ungated.
- The Copilot CLI also runs the hooks in `.claude/settings.json`, with a Claude-shaped payload and no `agent_id`. The
  gate reads a claude-format call carrying `COPILOT_CLI=1` and no `transcript_path` as an unknown caller. Do not widen
  the Claude matcher to Copilot's tool names. The measurements are in [docs/hooks-contract.md](docs/hooks-contract.md).
- The formatting checker fixes what it can on every surface that can rewrite the display, and blocks only on what is
  left. Detail is in [docs/hooks-contract.md](docs/hooks-contract.md).
- OpenCode and Kilo Code run every hook directly in [.agents/hooks/](.agents/hooks/) on every `tool.execute.before`,
  through the plugin runner. Adding a hook file is the whole registration step. The contract is in
  [docs/hooks-contract.md](docs/hooks-contract.md).
- Every wiring that can reach a subagent injects the subagent text and never the reminder. The per-agent evidence is
  in [docs/hooks-contract.md](docs/hooks-contract.md).
- Copilot gets the reminder on every prompt from `userPromptTransformed` through
  [.agents/hooks/copilot/prompt_reminder.py](.agents/hooks/copilot/prompt_reminder.py), which sits in a subdirectory
  so the OpenCode and Kilo Code runner skips it.
- [sandbox-agent/live/](sandbox-agent/live/) proves the wiring against a real model, run by the manual live workflow
  under Repo conventions. On Copilot, tests 1 and 2 can report `KNOWN-GAP`, as the Maintenance follow-ups record.
  Test detail is in [sandbox-agent/README.md](sandbox-agent/README.md).

Verified against Claude Code 2.1.281, Codex 0.156.1, OpenCode 1.18.32, and Kilo Code 7.7.9. GitHub Copilot CLI was
last verified on 1.0.81 and is not installed here, so nothing above was re-measured against it.

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
| `.agents/skills/*/SKILL.md` and its `references/*.md` | canonical | edit directly, keep the manifest short and the depth in `references/` |
| `.agents/hooks/preflight_gate.py`, `.agents/hooks/no_ai_markers_check.py`, `.agents/hooks/task_list_sync.py`, `.agents/hooks/markdown_lint_check.py`, `.agents/hooks/copilot/prompt_reminder.py` | canonical | edit directly, then run the pytest suite |
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

The generated subagent trees are per tool because no shared subagent format exists.

Regenerate the subagent trees and repair the symlinks after any `subagents/*.md` change:

```bash
python tools/gen_subagents.py
```

On Windows, turn on Developer Mode and set the Git option below before cloning, or every symlink checks out as a plain
text file:

```powershell
git config core.symlinks true
```

Full layout reference: [docs/repository-layout.md](docs/repository-layout.md). Which agent reads which part of
`.agents/` is in [docs/agent-compatibility.md](docs/agent-compatibility.md). This repo does not use OpenSpec
itself. The OpenSpec sections in the `.example` are for consumers.

---

## Repo conventions

On top of the global rules in `~/.claude/CLAUDE.md`:

- **The consumer boundary is the filename case.** A consumer receives exactly two kinds of thing: the agent
  configuration files the import pulls, and the UPPERCASE-named markdown documents under `docs/`. Every lowercase
  document under `docs/` is ours and never ships. [README.md](README.md) is the one uppercase file that stays here.
  [e2e/](e2e/), [sandbox-agent/](sandbox-agent/), [subagents/](subagents/), and [tools/](tools/) are test and build
  material and never reach a consumer, so no shipped document may link into them. A shipped document linking to a
  lowercase one is the same defect: the link resolves here and 404s there.
  [global/](global/) ships only through the global install in [docs/GLOBAL_SETUP.md](docs/GLOBAL_SETUP.md), which
  copies [global/bin/](global/bin/) to `~/.agents/bin`, and never through a project import, so no project-import
  pathspec may name it. [main-thread-allowlist.txt](main-thread-allowlist.txt) is this repository's own and never
  ships by either route.
- **Markdown lint.** [tools/check-markdown.py](tools/check-markdown.py) checks `README.md`, `AGENTS.md.example`,
  `docs/*.md`, `.agents/skills/**/*.md` and `subagents/*.md` for dashes, prose lines over 120 characters, level-2
  headings, and skill and subagent front matter. This `AGENTS.md` is out of scope, but match the style anyway.
- **One runnable command per fenced code block** in any doc a human copies, with the matching language tag and no
  `#` comment lines inside the block (global rule).
- **One server set, one schema per file.** Change all five MCP files together: [.mcp.json](.mcp.json) for Claude
  Code, [opencode.json](opencode.json) for OpenCode and Kilo Code, [.codex/config.toml](.codex/config.toml) for Codex,
  [.vscode/mcp.json](.vscode/mcp.json) for Copilot in VS Code, and [.github/mcp.json](.github/mcp.json) for the
  Copilot CLI. Only the top-level key, the `type` value, and the environment-variable syntax differ. Why the CLI has
  its own file, and why `.mcp.json` still shadows it, is in [docs/MCP_SETUP.md](docs/MCP_SETUP.md). The per-surface
  matrix is in [docs/agent-compatibility.md](docs/agent-compatibility.md).
- **No substitution token may appear in [opencode.json](opencode.json).** Kilo Code rejects the whole file on a
  `{env:VAR}`, which drops the MCP block and the `plugin` array that declares the gate. Local servers inherit the
  environment instead, and `context7` ships with no `headers` block. The detail is in
  [docs/MCP_SETUP.md](docs/MCP_SETUP.md) and nowhere else.
- **One gate, one rule, one wording.** A behaviour change is a change to
  [.agents/hooks/preflight_gate.py](.agents/hooks/preflight_gate.py) plus a case in
  [tools/tests/test_preflight_gate.py](tools/tests/test_preflight_gate.py), never a second copy of the logic. Every
  wiring injects the Required opening move texts word for word, and
  [tools/tests/test_prompt_reminder.py](tools/tests/test_prompt_reminder.py) compares them, line breaks included.
- **The tooling is a package under [tools/](tools/).** [tools/pyproject.toml](tools/pyproject.toml) is the only place
  a dependency or a version is written by hand, and it holds the pytest configuration too.
- **There is no lock file.** Every version in [tools/pyproject.toml](tools/pyproject.toml) is an exact pin, and
  `--group` needs pip 25.1 or newer.
- **CI runs on every pull request and every push to `master`,** with three parallel jobs: `actionlint`, `validate` for
  the local checks below, and `sandbox` for the containerised suite. Verify locally before you push.
- **[.github/workflows/agent-live-tests.yml](.github/workflows/agent-live-tests.yml) is a separate workflow and never
  part of CI.** Its only trigger is `workflow_dispatch`, so no push and no pull request ever starts it. It needs two
  repository secrets, because it drives each agent against a real model: `REQUESTY_API_KEY` for Claude Code, OpenCode
  and Kilo Code on Requesty, and `OPENAI_API_KEY` for Codex and GitHub Copilot on OpenAI's own API with
  `gpt-6-luna`. Each job receives only the key its agent needs. Every run spends money on those keys. Start it only
  with the user's explicit approval for that one run.

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

- **A skill:** create `.agents/skills/<name>/SKILL.md`, with depth in `references/`. No wiring is needed. The front
  matter carries `name`, `description`, and optionally `license`, `compatibility` or `metadata`
  (`https://agentskills.io/specification`). Write the description in trigger form: what it covers, the phrases a user
  says, and what it is not for. Prefer one hub with a reference file per topic. Bump the skill-count badge in
  [README.md](README.md).
- **A subagent:** edit `subagents/<name>.md`, run the generator, and commit the source and the four generated trees
  together. The generator rejects a skill with no folder, an unknown tool, and an unknown model. Bump the
  subagent-count badge.
- **An MCP server:** add the block to all five MCP files (the ones listed under Repo conventions), document it in
  [docs/MCP_SETUP.md](docs/MCP_SETUP.md), and bump the MCP-count badge.
- **A shipped document:** name it in UPPERCASE under `docs/`, add its path to every
  `git checkout agent-standards/master --` pathspec that delivers documents (the Quickstart and all five per-agent
  blocks in [README.md](README.md), the import in [docs/AGENT_TOOLING.md](docs/AGENT_TOOLING.md), and both shell
  sections of [docs/AGENTS-UPDATE.md](docs/AGENTS-UPDATE.md)), and list it under Shipped in the README docs map. A
  document a consumer cannot pull is not shipped, whatever its name says.
- **A gate rule:** edit [.agents/hooks/preflight_gate.py](.agents/hooks/preflight_gate.py), add the case to
  [tools/tests/test_preflight_gate.py](tools/tests/test_preflight_gate.py), and leave the wiring files alone unless the
  hook surface itself changed. A wiring change also needs the containerised sandbox in
  [sandbox-agent/](sandbox-agent/README.md).

---

## Subagents and skills

For this repo specifically: `agent-engineer` owns the agent configuration itself, which is every skill, every subagent
definition, every hook wiring, every MCP server block, and this file. It is also the agent the main thread hands web
research to, because the gate denies the main thread a web fetch or web search directly. `markdown-writer` owns doc
work, `python-patterns` owns the generator, the hook scripts, and the lint scripts,
`code-reviewer` runs before any merge, and `bash` and `powershell` own the update scripts in
[docs/AGENTS-UPDATE.md](docs/AGENTS-UPDATE.md).

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

- **Copilot `userPromptTransformed` is documented only for the CLI and the cloud agent**
  (`https://docs.github.com/en/copilot/reference/hooks-reference`). Confirm that VS Code and JetBrains fire it, or at
  least tolerate the entry, and record the result here.
- **The Copilot `preToolUse` payload carries no agent identifier.** The gate therefore cannot tell a Copilot subagent
  from the main thread, and no rule ever fires on that surface. Recheck the hooks reference for an agent identifier
  and pass it with `--subagent` from [.github/hooks/preflight.json](.github/hooks/preflight.json) when one lands. In
  the same change set `GATE_KNOWN_GAP=0` in [sandbox-agent/live/copilot.sh](sandbox-agent/live/copilot.sh), so live
  test 1 has to pass there.
- **The Copilot CLI tells every custom subagent not to write files.** Copilot CLI 1.0.81 appends
  `**CRITICAL: Do NOT write output to files.**` to a custom subagent's system prompt, and in live run 36176881215 the
  subagent wrote nothing. Live test 2 reports `KNOWN-GAP` for it through `SUBAGENT_NO_WRITE_MARKER` in
  [sandbox-agent/live/copilot.sh](sandbox-agent/live/copilot.sh). Recheck each CLI release, and remove that marker in
  the same change that sees the block gone.
- **Codex runs the formatting check on `Stop`, but whether that `Stop` can reject a reply is not measured.** Confirm it
  and say so plainly here. The markdown lint stays Claude-only, because Codex has no post-tool event.
- **JetBrains Copilot MCP is global-only and officially undocumented.** The plugin reads MCP from
  `~/.config/github-copilot/intellij/mcp.json`. There is no per-project MCP file, and GitHub documents only the in-IDE
  UI rather than the path, so no JetBrains MCP file ships here. Recheck whether GitHub adds a documented per-project
  path (`https://docs.github.com/en/copilot/how-tos/provide-context/use-mcp/extend-copilot-chat-with-mcp`) and ship one
  if it lands.
