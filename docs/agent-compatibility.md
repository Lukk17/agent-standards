# Agent compatibility matrix

What each supported agent reads, where it reads it from, what it can actually block, and the few places our layout
has to work around a tool limitation. Checked against vendor documentation on 2026-08-25, against Claude Code 2.1.250,
Codex 0.150.1, OpenCode 1.18.25, Kilo Code 7.5.5, and GitHub Copilot CLI 1.0.81. The gate matcher paragraph under Hook
enforcement and its four subsections, from the repository boundary through MCP tools, were checked later against
Claude Code 2.1.281, Codex 0.156.1, OpenCode 1.18.32 and Kilo Code 7.7.9, and not against Copilot. Cells that rest on
something less than official documentation say so.

This file stays in the agent-standards repo only. For the full repository tree and each agent's instruction-merge
precedence, see [repository-layout.md](repository-layout.md). For human MCP setup (keys, environment variables,
per-operating-system commands), see [MCP_SETUP.md](MCP_SETUP.md).

---

### The one-paragraph version

Two things converged across the tools and one thing did not. Skills at `.agents/skills/` and shared instructions in
`AGENTS.md` are read natively by Codex, OpenCode, Kilo Code, and every GitHub Copilot surface, so both are canonical
here. Claude Code 2.1.277 and later reads `AGENTS.md` natively too, but only while the project holds no `CLAUDE.md`,
so no project file ships one. It still does not read `.agents/skills/`, so it reaches the skills through the
`.claude/skills` symlink, a pattern its own documentation supports. Subagent definitions did not converge at all:
Claude Code, Codex, and Copilot each demand a different format, so one canonical source is generated into four trees,
and only OpenCode and Kilo Code are close enough to share one.

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
| Claude Code | `AGENTS.md`, when no `CLAUDE.md` exists | native from 2.1.277: every `AGENTS.md` from the working directory up at session start, and a subdirectory's `AGENTS.md` when Claude reads a file there. Any `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` in the working directory or above turns it off, `~/.claude/CLAUDE.md` does not |
| Codex | `AGENTS.md` | native, walks nested `AGENTS.md` from the root down to the working directory, `AGENTS.override.md` wins at each level |
| OpenCode | `AGENTS.md` | native from the project root, falls back to `CLAUDE.md` when absent |
| Kilo Code | `AGENTS.md`, `.kilo/rules/` | both auto-read from the project root on every task |
| GitHub Copilot | `AGENTS.md` | native in VS Code agent mode, the CLI, and the cloud agent; the JetBrains plugin reads it in agent mode too |

The JetBrains row needs a caveat spelled out. The March 2026 JetBrains plugin changelog states that agent mode reads
`AGENTS.md`, and it does. GitHub's own published support matrix for custom instructions still omits JetBrains from the
`AGENTS.md` column, so the two sources disagree. Treat the behaviour as real and the documentation as behind.

The Claude Code row rests on the [memory docs](https://code.claude.com/docs/en/memory), read on 2026-10-10 against
Claude Code 2.1.281: "By default, Claude reads `AGENTS.md` only when you have no `CLAUDE.md` in your working directory
or above it", and "Reading `AGENTS.md` directly requires Claude Code v2.1.277 or later". An `@` import saves nothing,
because "imported files also load at launch". [tools/check-agents-md.py](../tools/check-agents-md.py) fails CI on any
tracked `CLAUDE.md`, and the shipped template tells a project never to add one.

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

The gate is one shared rule in [../.agents/hooks/preflight_gate.py](../.agents/hooks/preflight_gate.py). It reads a hook
payload on standard input and denies five things: a write of any file resolving inside the repository working tree
coming from the main thread, with no exemption left for markdown, configuration, or `docs/` (delegate the change to a
subagent that owns the area instead), any tool call at all from a subagent whose own definition declares no skills
(spawn a specialist instead), an edit, any tool outside a fixed read set, or a shell command outside its own list
from a subagent whose definition is marked read-only, a web fetch or web search called straight from the main thread on the one format whose
payload names that tool today, Claude Code, and a script or module run from the main thread, because the gate cannot see
what a script writes. The allowlist that lifts the last rule is in
[What the main thread may run](GLOBAL_SETUP.md#what-the-main-thread-may-run). A relative path is resolved against
whatever a leading `cd` in the command moved to, so changing directory first buys nothing. A write outside the
repository, the null device, `tasks.md` at the project root, and switching a git branch stay allowed, and the main
thread keeps full use of git otherwise. Caller identity is a tri-state, subagent, main thread, or unknown when a payload
carries nothing that could tell the two apart, and none of the five rules fires on an unknown caller. Every failure path
also allows the call, because a broken gate must never break a session, with two deliberate exceptions: a path none of
the three repository-boundary helpers can resolve is treated as inside, which denies, and a command a read-only subagent
sends that the lexer cannot read denies, because it matches nothing on that agent's list.

Three more hooks live beside it in [../.agents/hooks/](../.agents/hooks/) and ride the same wirings:
`no_ai_markers_check.py` checks the reply, `markdown_lint_check.py` lints a file just after it was edited, and
`task_list_sync.py` mirrors the session task list into `tasks.md`. Every hook is invoked on `-S -E`, under the
first of `python3` and `python` its wiring resolves, and none of them uses `argparse`, because it exits 2 on a
usage error and 2 is the deny code in the plain format.

Each agent wires those scripts through its own hook surface, and the surfaces differ in what they can stop.

| Agent | Hook config | Blocks a tool call | Injects context | Blocks a reply | Tells subagent from main thread |
| --- | --- | --- | --- | --- | --- |
| Claude Code | [.claude/settings.json](../.claude/settings.json) | yes, `PreToolUse` | yes, `SessionStart` and `UserPromptSubmit` on every turn, and the subagent text on `SubagentStart` | yes, `Stop` on the main thread only, after `MessageDisplay` fixes the display | yes, `agent_id` is present only inside a subagent |
| Codex | inline `[[hooks.*]]` in [.codex/config.toml](../.codex/config.toml) | yes, `PreToolUse` | yes, `UserPromptSubmit`, and the subagent text on `SubagentStart` | runs the check on `Stop` | yes, `agent_id` is present only inside a subagent |
| OpenCode | plugin [.agents/plugin/hooks.js](../.agents/plugin/hooks.js), declared by its directory under singular `plugin` in [opencode.json](../opencode.json), `server` on 1.x and `setup` on 2.x. Singular `plugin` loads on 1.x and on 2.0.26, measured 2026-10-15: `opencode plugin list` from the repo shows the repo copy beside the global copy | yes, throwing from `tool.execute.before` | yes, `chat.message` on every root-session prompt, as a synthetic text part, and the subagent text in a child session | no, but `experimental.text.complete` stores a fixed text part | yes, the session `parentID` read through `client.session.get` |
| Kilo Code | the same plugin, same declaration | yes, throwing from `tool.execute.before` | yes, same mechanism | no | yes, same mechanism |
| GitHub Copilot | [.github/hooks/preflight.json](../.github/hooks/preflight.json), camelCase events | fires on `preToolUse`, but caller identity there always resolves to unknown, so the gate always allows | yes, `sessionStart` and `userPromptTransformed` on every prompt, and the subagent text on `subagentStart` | yes, `agentStop` forces a correction turn | no, the `preToolUse` payload carries no agent identifier |

The full event set per surface, beyond the gate itself:

| Agent | Gate | Formatting check | Markdown lint | Task list |
| --- | --- | --- | --- | --- |
| Claude Code | `SessionStart`, `UserPromptSubmit`, `SubagentStart`, `PreToolUse` | `MessageDisplay`, `Stop` | `PostToolUse`, matcher `^(Edit\|Write\|MultiEdit)$` | `TaskCreated`, `TaskUpdated`, `TaskCompleted`, `SessionStart`, `PreCompact`, `Stop` |
| Codex | `UserPromptSubmit`, `SubagentStart`, `PreToolUse` | `Stop` | not wired, no matching event | `SessionStart` |
| OpenCode and Kilo Code | `tool.execute.before` | same event, the runner passes every hook, plus `experimental.text.complete` | same event | same event |
| GitHub Copilot | `sessionStart`, `subagentStart`, `userPromptTransformed`, `preToolUse` | `agentStop` | not wired | `sessionStart` |

The gate's tool matcher per wiring is `^(Edit|Write|MultiEdit|NotebookEdit|Bash|PowerShell|WebFetch|WebSearch)$` on
Claude Code, `^(Bash|shell|apply_patch|Edit|Write|NotebookEdit)$` on Codex, and
`bash|powershell|create|edit|apply_patch` on GitHub Copilot. Claude Code's `SessionStart` also injects the
subagent supervision text, which has no script behind it. OpenCode and Kilo Code match nothing, because the
runner hands every tool call to every hook.

Reading the tables row by row:

- Every row anchors the gate at the project root before calling it, so a session started in a subdirectory still finds
  [../.agents/hooks/preflight_gate.py](../.agents/hooks/preflight_gate.py), and a missing script allows rather than
  denies. Python exits 2 when it cannot open the file it was handed, and 2 is the deny code, so an unanchored path used
  to block every tool call.
- [../.agents/hooks/no_ai_markers_check.py](../.agents/hooks/no_ai_markers_check.py) finds an em dash, an en dash, a
  semicolon, or a bold or italic marker, asterisk or underscore form, and asks only for `Correction:` lines. Claude
  Code first fixes dashes, bold and italic on screen through `MessageDisplay`, so its `Stop` blocks only on what that
  fix leaves, a semicolon above all. No subagent's reply is checked on any agent, because only the main thread's reply reaches the user. Codex runs the full check on `Stop`.
  GitHub Copilot runs it on `agentStop`, reading the reply from the transcript file the payload names, and a block
  there forces one more turn with the reason as its prompt. OpenCode and Kilo Code store a fixed copy of each
  finished text part and check what remains at the next tool call.
- Only Claude Code has task events, and no agent has a task-updated event, so `task_list_sync.py` writes `open` and
  `done` and the model sets `in progress` and `blocked` by editing `tasks.md` itself. That is the one path Rule A
  exempts. Elsewhere the hook only injects the file at session start, which is also how the list survives a
  compaction, since `SessionStart` fires again with `source` set to `compact` and no agent delivers
  `additionalContext` out of a pre-compact event today.
- Codex carries its hooks inline in `.codex/config.toml`, the same file that holds its MCP servers. There is no
  separate `.codex/hooks.json` any more. Codex also loads that whole layer only after the project is trusted.
- OpenCode and Kilo Code run one plugin file between them. Neither has an event that can block a reply, so on those two
  the enforcement is the pre-tool block plus per-agent tool permissions, and the only thing after the fact is the
  stored fix of a finished text part. OpenCode 2.x has not even that: no hook runs after a finished reply, so the
  formatting check sees a reply only when the next tool call starts. 2.x also ignores the `instructions` key and does
  not fall back to `~/.claude/CLAUDE.md`, so the plugin's 2.x entry point adds the reply rules through the session
  `context` hook itself. Measured on OpenCode 2.0.26.
- The per-agent tool permissions are the generator's `permission` block. OpenCode and Kilo Code read a subagent's
  `tools` map as overrides on top of everything it already has, so a read-only definition listing only `read`, `grep`
  and `glob` still had `edit` and `bash`. The generator now writes `edit: deny` unless `write` or `edit` is listed and
  `bash: deny` unless `bash` is. A definition marked `readonly: true` instead gets `edit: deny`, `task: deny`, denies
  for `webfetch`, `websearch`, `todowrite`, `lsp` and `"*_*"`, and a `bash` map with `"*": deny` first, its allowed
  commands after it, and denies last, because OpenCode lets the last matching rule win: an output option, a `$`, a
  redirect, gh's `--web`, `-w`, `--jq`, `-q`, `--template` and `-t`, and the characters `"`, `'`, `{`, a backtick, `<`, `;`, `&`, `|`, `[`, a newline and a
  carriage return. OpenCode matches a permission key against the tool name, "so the same syntax works for built-ins,
  custom tools, and MCP tools", and names an MCP tool `<server>_<tool>`
  ([agents, "Permissions"](https://opencode.ai/docs/agents/), fetched 2026-10-30), so `"*_*"` denies every MCP tool.
  It also matches the built-in guards `external_directory` and `doom_loop`, which deny for such an agent instead of
  asking. Two refusals of the gate have no rule: a backslash, because `Wildcard.match` rewrites every backslash to
  `/` in the rule and the command alike, so `*\*` would deny every path; and `?`, a one-character wildcard there, so
  `*?*` would deny every command (`packages/core/src/util/wildcard.ts` at OpenCode `v1.19.5`, whose regex also
  carries the `s` flag, so `*` matches across lines). The map matches command text only, so it cannot see the
  `workdir` key either. The native map is therefore not a security boundary on its own: the plugin gate is the
  boundary, and the map only narrows what reaches it. The same V1 front shape loads on OpenCode 2.0.26, measured 2026-10-15: `debug agents` from the repo lists 35 project agents plus 7 built in, and the live view shows the `tools` map as a `permissions` list.
- As a runner-independent backstop the project also ships [.opencode/opencode.json](../.opencode/opencode.json) with `edit` denied and only `tasks.md` allowed. The plugin gate never fires on some runtimes, measured 2026-10-26, so this file blocks main-thread writes through permissions instead. Subagent rights are untouched because agent rules are appended after project rules, and Kilo Code reads the file with no warnings.
- A read-only subagent keeps `bash` but runs only the commands listed under the "Read-only shell" heading the generator
  writes into every format. Rule E reads that list from the definition, the way Rule B reads the skills. It allows
  only the read, grep, glob and list tools under each agent's name for them, the skill loader, and a shell not
  started on a terminal (`tty: true` denies, because Codex's `write_stdin` feeds such a shell later with no command
  the gate can read), so an edit, an agent spawn, a web fetch and an MCP tool all deny. The shell call may carry no
  key beyond `command`, `cmd`, `description`, `timeout`, `yield_time_ms`, `max_output_tokens` and
  `run_in_background`, plus `tty` and Claude Code's `dangerouslyDisableSandbox` while they are false, because any
  other key moves the command or swaps its shell without changing its text: `workdir` on the OpenCode 1.19.5 and
  Kilo Code 7.8.18 bash tool (read from the shipped binaries, whose schema has `command`, `timeout`, `workdir` and,
  on Kilo Code, `description`), and `workdir`, `shell` and `login` on Codex's `exec_command`. The payload's `cwd`
  has to be the gate's own working directory or a plain folder inside it: Codex from `rust-v0.166.0` hands the hook
  only `{"command": ...}` and reports the call's resolved `workdir` as `cwd` while the hook still runs in the session
  directory ("Local tool cwd for hook stdin ... The hook process still runs in `cwd`",
  [pre_tool_use.rs at rust-v0.166.0](https://raw.githubusercontent.com/openai/codex/rust-v0.166.0/codex-rs/hooks/src/events/pre_tool_use.rs),
  fetched 2026-10-30), so a `cwd` outside the project, or below it inside a folder that holds `.git` or is itself a
  git directory such as a committed bare repository, denies. Before it lexes a command it holds every character to a
  fixed set: letters, digits, a blank, a newline and `._/:=,@^~%+-`, with `2>/dev/null` and `2>&1` as the only
  redirects. A quote of either kind, a backslash, a `$`, a backtick, a glob, a brace, a separator, a pipe, a carriage
  return and any non-ASCII character deny there. No quote is accepted, because each shell an agent may run reads a
  quoted span its own way, so a git format spells a space `%x20` and a newline `%n`, as in
  `git log --format=%h%x20%an%x20%s` (measured on git 2.43.0). Every command left has to match the list. No word,
  nor any comma-separated part of one, may hold a `$`, a backslash, a brace expansion or a git output option in any
  abbreviation, open with `@`, or be PowerShell's stop-parsing `--%`, after which PowerShell still substitutes
  "environment variables that use standard Windows notation, such as `%USERPROFILE%`". That holds in both dialects,
  because the OpenCode bash tool may run either shell, and because PowerShell reads `a,b` as an array for a cmdlet, a
  function or an alias, a `git` a profile wraps included. For a native program the same page says commas "are
  interpreted as part of the expandable string"
  ([about_Parsing](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_parsing),
  5.1 and 7.4 views dated 2026-06-29, fetched 2026-10-30), which no run here has measured. A `^` denies
  at the start of a word and anywhere in a word opening with `-`, because zsh with `EXTENDED_GLOB` reads it as a
  negated glob: in a folder holding the files `--out` and `--output=pwned`, zsh 5.9 expanded `--out^x` to both names,
  while `HEAD^:src/app.py` matched only names starting with `HEAD`. A word opening with `@` is a splat or a hashtable
  in PowerShell, so `@{u}` and `@~1` deny too, and a read-only reviewer names the upstream branch instead, as in
  `git log origin/main..HEAD`. gh may not open a browser (`--web`, `-w`, `-w=true`, `-cw`) or name another host by a
  URL argument, and `-R` or `--repo` must be exactly `OWNER/REPO` of letters, digits, `.`, `_` and `-`, because
  `--repo` takes `[HOST/]OWNER/REPO` ([gh pr view](https://cli.github.com/manual/gh_pr_view)), so a host part and
  an scp-style `git@host:owner/repo` deny alike. Nor may gh run a `--jq` or `-q` expression: go-gh
  compiles it with `gojq.WithEnvironLoader(func() []string { return os.Environ() })`
  ([pkg/jq/jq.go at go-gh v2.13.0](https://raw.githubusercontent.com/cli/go-gh/v2.13.0/pkg/jq/jq.go), the version gh
  2.89.0 pins, fetched 2026-10-30), and gojq's loader "allows to configure the environment variables referenced by
  `env` and `$ENV`" ([gojq README](https://raw.githubusercontent.com/itchyny/gojq/main/README.md)), so `--jq env`
  prints every variable, tokens included. `--template` and `-t` deny with it. A gh template has no environment function, but neither flag then
  carries code. Every `command` and `cmd` value is judged, not only the first. Unlike every other rule, any failure while lexing or matching denies here, a parse error and
  any other exception alike, and so does a tool the gate does not know that carries a command. Rule E applies when
  any definition the name resolves to is read-only: the calling format's own tree is read first and decides Rule B,
  and every other tree still counts for Rule E. A plugin subagent, which Claude Code names `<plugin>:<name>`, is
  also looked up in the plugin cache at `plugins/cache/<marketplace>/<plugin>/<version>/agents/<name>.md` under
  `CLAUDE_CONFIG_DIR` and `~/.claude` (measured on Claude Code 2.1.314), and a name part that holds a path or is
  `.` is refused a lookup. A `CLAUDE_CONFIG_DIR` the gate cannot expand, such as an unknown `~user`, is skipped
  rather than allowing the call. A definition that exists but cannot be read counts as read-only with no command allowed. A
  heading inside a fenced code block marks nothing. On Claude Code this
  is the only enforcement that holds: a subagent's `permissionMode: plan` is ignored while the session is in auto,
  `acceptEdits` or `bypassPermissions` mode, and a `tools` entry such as `Bash(git log *)` did not narrow the tool, so
  a `touch` from either ran on Claude Code 2.1.314 under an auto-mode session. Its `tools` list is an allowlist, so
  such an agent gets no MCP tool there either. Codex has no per-agent tool field, and a custom agent file cannot
  narrow the sandbox: "Other session settings, including `sandbox_mode`, `approval_policy`, `model_provider`, and
  `mcp_servers`, don't override the parent configuration when placed in a custom agent file"
  ([subagents, "Custom agents"](https://developers.openai.com/codex/subagents), fetched 2026-10-30). Read-only is
  not confirmed as enforced on Codex, because whether its `PreToolUse` payload carries `agent_type` is unmeasured:
  the hooks page lists `agent_id` and `agent_type` only for `SubagentStart` and `SubagentStop`
  ([hooks](https://learn.chatgpt.com/docs/hooks), fetched 2026-10-30), the generated schema lists both as optional
  `PreToolUse` fields, and no run here has seen them arrive. A payload without them is allowed. Even where they
  arrive, Codex's own `PreToolUse` input for a shell call is `serde_json::json!({ "command": args.cmd })`
  (`exec_command.rs` at `rust-v0.156.1` and at `main` on 2026-10-30), so `tty`, `shell` and `login` never reach the
  gate there, and before `rust-v0.166.0` neither does `workdir`. Its `write_stdin` tool, which types into a shell
  started with `tty: true`, "doesn't run `PreToolUse` again when it sends input or polls a command that already
  passed `PreToolUse`" (same hooks page), and the page itself says to "Treat tool hooks as a useful guardrail, not a
  complete enforcement boundary". Rule E denies the `tty: true` start wherever the gate sees it, which is Claude
  Code and the OpenCode and Kilo Code runner. Copilot gets no shell for such an agent, as the next item explains.
- GitHub Copilot's `preToolUse` payload carries no agent identifier at all, so caller identity there resolves to
  unknown every time and none of the gate's five rules ever fires. The hook is wired and runs, but it always allows:
  that surface is entirely unenforced by the gate, not merely weaker, and the `AGENTS.md` text plus the
  `sessionStart` and `userPromptTransformed` injections carry the whole weight instead.
- Copilot in JetBrains fires only six events, has no subagent event at all, and reads hook configuration only from
  `.github/hooks/`. A hook file anywhere else is ignored by that client.

#### Where the write rule draws the repository boundary

"Inside the repository" is the gate's own roots rather than a git query: the process working directory, the project
root the hook payload names in its `cwd` field, and the gate script's own on-disk location two parents up, that last
one only while it is a real project and not the user's home directory or a directory above it. That is what lets the
user-level install in [GLOBAL_SETUP.md](GLOBAL_SETUP.md) protect the open project instead of everything the user owns.
A relative path resolves against whichever directory a leading `cd` in the command moved to, and against every root
when the command never changed directory. On Windows, a Git Bash drive path such as `/c/Users/x` is read as
`C:/Users/x` before it is placed, for a `cd` operand and a write target alike.

Deleting, moving, or renaming the repository root or any directory above it counts as a write inside it, so
`rm -rf ..`, `rm -rf ~`, `Remove-Item -Recurse` or `rmdir /s` on a parent, and `mv` or `Move-Item` of a parent are
denied, while the same command on a sibling folder that holds no root is allowed. A wildcard operand counts when any
path it could match, compared one component at a time and case-insensitively on Windows, is the root, a directory
above it, or a path inside it, so `rm -rf ../agent-*` and `Remove-Item ..\*` are denied.

A write outside the repository, a write to the null device or to a PowerShell drive that holds no files such as `Env:`
or `Function:`, a write to `tasks.md` at the project root, and git branch switching stay allowed, so the main thread
keeps full use of git and keeps ownership of its own task list.

#### How the write rule reads a command

Each shell's own quoting applies: a backslash escapes only in a POSIX shell, PowerShell escapes with a backtick and
splits an unquoted `a,..` into two paths, and cmd escapes with a caret, so `Remove-Item "D:\parent\"` is read as the
path it names. The same checks reach inside a wrapper: `cmd /c` and `cmd /k`, `bash -c`, `sh -c`, `zsh -c`, and
`powershell` or `pwsh` with `-Command`, `-c` or a decoded `-EncodedCommand`, nested up to three deep. They also reach
code a shell or interpreter takes some other way: a heredoc or here-string, a piped `echo`, `printf` or `cat`,
`xargs`, `eval`, `Invoke-Expression`, and a file run with `source` or `.`. An encoded value that does not decode is an
unlexable command and allows, since PowerShell refuses to run it. Inline Python is parsed and inline JavaScript read
for the path each actually writes, through import aliases and renamed bindings, rather than for every string it holds.

Codex's `apply_patch` call carries a patch body rather than a file path, and the key that holds that body in the
payload is not confirmed. The gate therefore reads the file headers out of every string value in the call rather than
out of one named key, and denies the call when it finds no path key and no file header, because an edit whose target
it cannot resolve is not trusted.

The writers the gate knows include `find -delete` and `find -exec`, `git clean`, `git rm`, `git mv`,
`git reset --hard`, `git stash`, `git checkout -f` and `git checkout` or `git restore` of a path, `curl -o` and `-O`,
`wget`, `touch`, `mkdir`, `install -d`, `tar` and `unzip` extraction, the `[System.IO.File]` and
`[System.IO.Directory]` methods, and the PowerShell item and content cmdlets, bound the way PowerShell binds their
parameters. The .NET methods are read whatever shell the tool name claims, because Codex on Windows names its shell
tool `Bash` and runs the command in PowerShell, so `[System.IO.File]::WriteAllText($target, ...)` under `Bash` denies
the same way it does under `PowerShell`.

Beyond the plain writers, the rule reads a hard link whose source is a project file (`ln` without `-s`, `cp -l`,
`fsutil hardlink create`, `New-Item -ItemType HardLink`, `mklink /H`), a Windows device, extended-length or loopback
administrative-share spelling of a project path, command substitution inside double quotes and backquotes, a line
continuation before CR LF in PowerShell and cmd (a POSIX shell joins a line only on backslash LF, and keeps a lone
carriage return inside its word), a PowerShell cmdlet fed its path through the pipeline, `pushd`, `popd`, `Push-Location`,
`Pop-Location`, `env --chdir`, `sudo --chdir` and `pwsh -WorkingDirectory`, parentheses that are a subshell only in a
POSIX shell, `xcopy`, `robocopy`, `replace`, `expand`, `esentutl`, `certutil`, `bitsadmin`, `mklink`,
`Start-Transcript`, every `Export-*` cmdlet, `Start-Process` with its redirects and argument list,
`Set-ItemProperty`, any other `System.IO` use, in-place editors and formatters, writes and processes inside an `awk`
or `sed` program, Lua, R, Julia, `sqlite3`, PHP, Perl and Ruby code, and the runners `busybox`, `toybox`, `su -c`,
`setsid`, `flock`, `watch`, `script`, `wsl` and `git -c alias.x=!...`. It also reads the file a git output option
names (`--output` and its abbreviations on the diff family, `format-patch`, which writes into the working directory
unless `--stdout`, `archive -o`, `bundle create`), a `git config` write, which lands in `.git/config` or the `-f`
file, and hard links made from Python and JavaScript, where the source counts as written too. The standard-library
writers the inline Python reader places include archive extraction, URL download to a file, database files, logging
file handlers, and temporary files created in a named directory.

#### What the gate cannot place

The gate fails open almost everywhere, but not on the repository boundary. The three helpers that decide it,
`_resolves_inside_repo`, `_path_exists_in_repo` and `_contains_repo`, fail toward True on a path none of them can
resolve, which denies, because deciding what Rule A protects is their whole job. On Windows that includes a loopback
UNC path to a share that is not an administrative drive share, such as `\\localhost\share` or `\\127.0.0.1\share`,
because only the share definition knows which folder it maps to, an administrative drive share such as
`\\fileserver\C$` on any host, because the gate cannot prove that host is another machine, and a volume GUID or
`GLOBALROOT` path. This machine is recognised by its loopback and unspecified addresses in every spelling,
IPv4-mapped IPv6 included, by its own name with or without a domain or a trailing dot, and by any name or LAN address
that resolves to one of its own addresses. The loopback mapping runs again on the resolved path, so a link that
resolves to an administrative share of the project is still inside.

A write the gate recognises but cannot place denies the same way on the main thread. A write target the shell has not
expanded yet, such as the `$f` in `rm $f`, is the common case, and so is any target holding an unexpanded `$VAR`,
`{a,b}`, `%VAR%` or `!VAR!`. The others are a command nested or wrapped deeper than the gate reads, code piped into a
shell or interpreter from a program whose output the gate cannot know, as in `curl ... | bash`, a sourced file it
cannot read, `eval` or `Invoke-Expression` of a variable, and inline code that starts a process or reaches a file
call through a computed name. Only the running program knows where such a write lands, so the write goes to a
subagent or is spelled with a literal path.

Each of the following cannot be placed either and denies on the main thread:

- A leading assignment, an `env`, `export`, cmd `set`, `setx`, `$env:`, `Env:` or `SetEnvironmentVariable` setting of
  a variable that changes which program or file a command uses: git's configuration, directory, work tree, pager,
  editor and external diff, a library preload, `NODE_OPTIONS`, `PYTHONPATH`, `PYTHONSTARTUP`, `PERL5OPT`, `RUBYOPT`,
  `BASH_ENV`, `ENV`, `PATH`, `PYTEST_ADDOPTS`, the temporary directory, and the rest of `_UNPLACEABLE_ENVIRONMENT`.
- A `git config` setting or `-c` value that runs a program or includes more configuration, `git grep -O`,
  `difftool` and `mergetool`.
- Inline Python that imports anything outside the standard library, a standard module shadowed by a file in its
  working directory, or loads code through `runpy`, `importlib` or `ctypes`, and inline JavaScript that loads any
  module that is not built in.
- PowerShell that holds a `System.IO` type as a value, imports a namespace or module with `using`, turns a string into
  a type, uses reflection or compiles code with `Add-Type`.
- WMI or CIM method calls and `wmic ... call create`, and `ssh`, `plink`, `winrs`, `Invoke-Command` and PowerShell
  sessions aimed at this machine or at a session, a VM, a container or a script file, and `psexec`.
- A container that binds a path inside or above the repository, `docker` or `podman` `exec`, `start`, `build`, `cp`
  into a container, and `compose up`, `run` or `build`.
- A job handed to `schtasks /create`, `at`, `batch`, `crontab`, `systemd-run` or `Register-ScheduledTask`.
- A shell command that is not a string, and a tool the gate does not know that still carries a `command`, `cmd` or
  `script` value.

Read-only forms of the same tools still allow: container `ps`, `images`, `inspect`, `logs`, `stats`, `network ls`,
`volume ls`, `compose ls`, `ps`, `logs` and `config`, `schtasks /query`, `crontab -l`, `Get-ScheduledTask`, and WMI or
CIM queries. A top-level command the lexer cannot read still allows on the main thread, an escape past the last
Unicode code point and substitutions or parentheses nested more than 16 deep included, while code nested inside a
readable command that cannot be read denies.

Rule E is something a definition opts into, not a defence against a repository's own configuration. Known limits of
Rule E, accepted rather than open: a listed git command still runs any program the repository's own configuration
names, and Rule E reads the command line, not the configuration it runs under, so a read-only agent is only as
read-only as the repository it reviews. That covers:

- `diff.external`, a `textconv` driver set through `.gitattributes`, and `core.fsmonitor` on `git status`.
- The pager when the command runs on a terminal, which is an interactive shell escape: `less` runs `!command`.
- `--show-signature`, `log.showSignature` and the `%G?` family of format placeholders, which run `gpg.program`.
- A `filter.<driver>.clean` or `filter.<driver>.process` program, which `git diff` and `git status` run on the
  working tree.
- Submodule recursion, which reads each submodule's own configuration.
- A Claude Code plugin loaded for one session with `--plugin-dir` is not under `plugins/cache`, so the gate finds no
  definition for its `<plugin>:<name>` agents and allows them as unknown, a read-only one included. `--plugin-url` is
  assumed to behave the same, not measured.
- On Codex before `rust-v0.166.0`, a call's `workdir` never reaches the gate, and on every Codex version `tty`,
  `shell` and `login` do not either, so a read-only agent there can still run a listed command in another folder,
  under another shell, or on a terminal it then types into through `write_stdin`.
- `git status`, which rewrites `.git/index` to refresh its stat cache, so a read-only agent still writes there.
- `gh pr view --comments` and every other gh or git output, which is text other people wrote and reaches the agent as
  untrusted input.

On OpenCode and Kilo Code the native permission map denies every redirect and `&`, so `2>/dev/null` and `2>&1` deny
there while the gate allows them. A gh `-R` with a host part, a comma-joined option, a leading `^` or `@`, a backslash
and a `workdir` key have no native rule: the map cannot tell a host from a branch name and sees command text only, so
the gate alone holds them.

Known limits of the write rule, accepted rather than open: a write form the gate does not know passes, a top-level
command it cannot parse allows on the main thread, MCP tools are not gated, code run by an allowlisted tool is trusted rather than read,
Copilot's main thread is not gated, the risky variable and option lists come from knowledge rather than vendor
documentation, and a loopback share whose folder cannot be determined denies. Re-audit only when the rule changes, and
record a new limit here rather than chasing it.

#### MCP tools are not gated

Claude Code names an MCP tool `mcp__<server>__<tool>` and compares a `PreToolUse` matcher against that name
([hooks](https://code.claude.com/docs/en/hooks), "MCP tools follow the naming pattern `mcp__<server>__<tool>`"), and
the matcher in [.claude/settings.json](../.claude/settings.json) names built-in tools only. The OpenCode and Kilo Code
runner hands every tool to the gate, but `EDIT_TOOLS` names built-in edit tools only, so an MCP call is allowed there
too. Two servers in [.mcp.json](../.mcp.json) write local files that way. `playwright` does it through
`browser_take_screenshot` and `browser_pdf_save`, whose `filename` "Relative file names are resolved against the
workspace root" ([playwright-mcp README](https://github.com/microsoft/playwright-mcp/blob/main/README.md)).
`chrome-devtools` does it through `take_screenshot`, `take_snapshot`, `take_heapsnapshot`, `performance_stop_trace`,
`screencast_start`, `evaluate_script` and `get_network_request`, each with a path parameter "to save" into
([tool reference](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/tool-reference.md), fetched
2026-09-25).

The one exception is a read-only subagent. Rule E denies it every tool outside its fixed read set, so an MCP call
that reaches the gate, as every call does through the OpenCode and Kilo Code runner, denies. On Claude Code the
matcher never hands the gate an MCP call, and the agent's `tools` allowlist grants it none in the first place.

The canonical wording of the gate itself lives in the `## Required opening move` section of `AGENTS.md`. Every adapter
repeats it verbatim. Change one, change all of them.

---

### Wiring details per surface

Read these before you touch any hook wiring. They moved here from `AGENTS.md`, which links to this section.

- Claude Code's `SessionStart` also injects the subagent supervision text, plain context with no script behind it.
  [GLOBAL_SETUP.md](GLOBAL_SETUP.md) and [sandbox-agent/setup-global.sh](../sandbox-agent/setup-global.sh) carry it
  word for word.
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
  the Claude matcher to Copilot's tool names. The measurements are in [hooks-contract.md](hooks-contract.md).
- The formatting checker fixes what it can on every surface that can rewrite the display, and blocks only on what is
  left. Detail is in [hooks-contract.md](hooks-contract.md).
- OpenCode and Kilo Code run every hook directly in [.agents/hooks/](../.agents/hooks/) on every
  `tool.execute.before`, through the plugin runner. Adding a hook file is the whole registration step. The contract is
  in [hooks-contract.md](hooks-contract.md).
- Every wiring that can reach a subagent injects the subagent text and never the reminder. The per-agent evidence is
  in [hooks-contract.md](hooks-contract.md).
- Copilot gets the reminder on every prompt from `userPromptTransformed` through
  [.agents/hooks/copilot/prompt_reminder.py](../.agents/hooks/copilot/prompt_reminder.py), which sits in a
  subdirectory so the OpenCode and Kilo Code runner skips it.
- [sandbox-agent/live/](../sandbox-agent/live/) proves the wiring against a real model, run by the manual live
  workflow under Repo conventions in `AGENTS.md`. On Copilot, tests 1 and 2 can report `KNOWN-GAP`, as the
  Maintenance follow-ups in `AGENTS.md` record. Test detail is in [sandbox-agent/README.md](../sandbox-agent/README.md).

---

### MCP configuration

One row per file. Several agents ship more than one client, and the clients disagree, so read this table by file
rather than by agent.

| File | Schema key | Serves | Environment-variable syntax |
| --- | --- | --- | --- |
| [.mcp.json](../.mcp.json) | `mcpServers` | Claude Code and the GitHub Copilot CLI | `${VAR}`, `${VAR:-default}`, and for the Copilot CLI also `$VAR`, measured on Copilot CLI 1.0.103 on 2026-10-25 |
| [opencode.json](../opencode.json) at the project root | `mcp` | OpenCode and Kilo Code | none, a token here voids the file for Kilo. Same flat `mcp` plus `enabled` shape loads on OpenCode 1.x and on 2.0.26, measured 2026-10-15, where `debug config` shows it as `mcp.servers` plus `disabled` |
| [.codex/config.toml](../.codex/config.toml) | `[mcp_servers.*]` tables | Codex | none, values are literal |
| [.vscode/mcp.json](../.vscode/mcp.json) | `servers` | GitHub Copilot in VS Code | `${env:VAR}`, `${input:NAME}` |
| [.github/mcp.json](../.github/mcp.json) | `mcpServers` | the GitHub Copilot CLI, only in a folder that has no `.mcp.json` | `$VAR`, `${VAR}`, `${VAR:-default}`, measured on 1.0.103 on 2026-10-25, though the shipped file uses none |
| `~/.config/github-copilot/intellij/mcp.json` | `servers` | GitHub Copilot in JetBrains, global only | none documented |
| repository settings page | pasted JSON | GitHub Copilot cloud agent | none, values are literal |

The project files mirror one server set, with the exceptions listed under "What ships" in [MCP_SETUP.md](MCP_SETUP.md#what-ships): [opencode.json](../opencode.json) also carries `atlassian`, and only [.mcp.json](../.mcp.json) and [.vscode/mcp.json](../.vscode/mcp.json) carry `home-assistant`. Only the file name, the schema key, the `type`
value, and the environment-variable syntax differ. The last two rows are not project files at all, which is why they
carry no template.

Two rows ship no template and cannot. The JetBrains Copilot plugin reads MCP only from the global path above, with no
per-project file, so a shipped file would never be read. The cloud agent takes JSON pasted into a page in the
repository settings, so there is nothing to commit. Of the four Copilot surfaces, VS Code reads
[.vscode/mcp.json](../.vscode/mcp.json) and the CLI reads [.mcp.json](../.mcp.json). Both manual blocks
are written out in [MCP_SETUP.md](MCP_SETUP.md).

The Copilot CLI reads the project `.mcp.json`, the same file and schema Claude Code uses, and expands its
`${VAR:-default}` entries. When `.mcp.json` and `.github/mcp.json` are in the same folder, it reads `.mcp.json` and
not `.github/mcp.json` at all, per file and not per server name, measured on 1.0.103 on 2026-10-25. So
`.github/mcp.json` is kept only as a fallback for a folder that has no `.mcp.json`. See
[MCP_SETUP.md](MCP_SETUP.md#the-cli-mcpjson-and-why-a-fifth-file-exists) for the measurement and the vendor text.

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

- Claude Code is the only agent that does not read `.agents/skills/` natively, so the `.claude/skills` symlink must
  survive every update. It reads `AGENTS.md` natively only while no `CLAUDE.md` exists in the working directory or
  above it, so a single `CLAUDE.md` added anywhere on that path silently stops the nested files from loading.
- Kilo Code moved its configuration root from `.kilocode/` to `.kilo/`. Nothing in this repo writes to `.kilocode/`
  any more. OpenSpec 1.10.0 still hardcodes `.kilocode` for its Kilo target, which is one of the reasons consumers
  should initialise it with the vendor-neutral target instead (see [AGENTS-UPDATE.md](AGENTS-UPDATE.md)).
- Codex loads the whole `.codex/` project layer, custom agents, MCP servers, and hooks alike, only after the project
  is trusted. On a fresh clone the gate does not run until the user approves the project once.
- The JetBrains Copilot plugin scans `.claude/agents`, but it only understands its own `*.agent.md` format, so
  subagent definitions cannot be shared between Copilot and Claude Code or OpenCode.
- GitHub Copilot ships four surfaces (VS Code, JetBrains, CLI, cloud agent) that differ on hooks, on MCP, and on
  documentation quality. Never answer a Copilot question without naming the surface.
- On Windows the two agent symlinks and the skills symlink need `git config core.symlinks true` and Developer Mode
  enabled before the checkout, otherwise git writes plain text files containing the target path and every agent that
  depends on them sees nothing.
