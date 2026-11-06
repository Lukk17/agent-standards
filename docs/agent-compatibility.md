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
payload on standard input and denies six things: a write of any file resolving inside the repository working tree
coming from the main thread, with no exemption left for markdown, configuration, or `docs/` (delegate the change to a
subagent that owns the area instead), any tool call at all from a subagent whose own definition declares no skills
(spawn a specialist instead), an edit, any tool outside a fixed read set, or a shell command outside its own list
from a subagent whose definition is marked read-only, a web fetch or web search called straight from the main thread on the one format whose
payload names that tool today, Claude Code, a script or module run from the main thread, because the gate cannot see
what a script writes, and a shell, an interpreter or an editor the main thread starts that waits for typed input,
because the gate never sees what is typed into it. The allowlist that lifts the script rule is in
[What the main thread may run](GLOBAL_SETUP.md#what-the-main-thread-may-run). A relative path is resolved against
whatever a leading `cd` in the command moved to, so changing directory first buys nothing. A write outside the
repository, the null device, `tasks.md` at the project root, and switching a git branch stay allowed, and the main
thread keeps full use of git otherwise. Caller identity is a tri-state, subagent, main thread, or unknown when a payload
carries nothing that could tell the two apart, and none of the six rules fires on an unknown caller. Every failure path
also allows the call, because a broken gate must never break a session, with three deliberate exceptions: a path none of
the three repository-boundary helpers can resolve is treated as inside, which denies, a command a read-only subagent
sends that the lexer cannot read denies, because it matches nothing on that agent's list, and so does a working
directory a read-only subagent's call reports that does not exist or cannot be resolved, because the gate cannot tell
which repository a command run there would read.

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
| OpenCode | plugin [.agents/plugin/hooks.js](../.agents/plugin/hooks.js), declared by its directory under singular `plugin` in [opencode.json](../opencode.json), `server` on 1.x and `setup` on 2.x. Singular `plugin` loads on 1.x and on 2.0.26, measured 2026-10-15: `opencode plugin list` from the repo shows the repo copy beside the global copy | yes, throwing from `tool.execute.before` | yes, per session: a root session gets the main-thread reminder and a child session the subagent text, through `chat.message` as a synthetic text part on every prompt on 1.x, through the session `context` hook as a system part on every request on 2.x | no, but `experimental.text.complete` stores a fixed text part | yes, the session `parentID` read through `client.session.get` |
| Kilo Code | the same plugin, same declaration | yes, throwing from `tool.execute.before` | yes, the main-thread reminder to a root session and the subagent text to a child session, through `chat.message` as on OpenCode 1.x | no | yes, same mechanism |
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
- As a runner-independent backstop the project also ships [.opencode/opencode.json](../.opencode/opencode.json), which denies the main session a native edit of any project file but `tasks.md`. The plugin gate never fires on some runtimes, measured 2026-10-26, so this file blocks main-thread writes through permissions instead. A subagent whose definition allows `write` or `edit` keeps it, because agent rules come after project rules. One file cannot serve every runtime. Measured 2026-11-01 with the sandbox mock model, the plugin removed so the rule alone decided, on OpenCode 1.18.25 and 1.19.5, OpenCode 2.0.28 and 2.2.5, and Kilo Code 7.5.5 and 7.8.18:
  - OpenCode 2.x reads the default, a 2.x `permissions` list: `edit` denied on `*`, then allowed on `/*` and on `tasks.md`, the last match winning. 2.x matches a path inside the project relative to the session directory and a path outside it as an absolute one, so `/*` leaves an outside write to the gate, which allows it. 2.x also lowers a V1 `permission` object in this file to the same list, but the default keeps the 2.x form.
  - OpenCode 1.x refuses to start on that file: "V2 permissions are not supported by OpenCode V1". It refuses the `permissions` key at the top level and under `agent.<name>`, in `opencode.json` and `opencode.jsonc` alike, though not in an agent's markdown front matter. A 1.x user copies [.opencode/opencode.json.v1](../.opencode/opencode.json.v1) over the default. It holds the same rule in the V1 `permission` form with `../*` allowed instead of `/*`, because 1.x matches every path relative to the worktree, so an outside path starts with `../`. `../*` stays out of the default because a 2.x session started in a subfolder sees the rest of the project as `../`, and the allow let such a session edit it. Outside a git repository 1.x takes `/` as the worktree, so there the variant denies every main-thread edit, `tasks.md` and outside paths included. [tools/tests/test_opencode_backstop.py](../tools/tests/test_opencode_backstop.py) holds both shapes.
  - Kilo Code reads neither file, only the root [opencode.json](../opencode.json), so it has no native backstop and the plugin gate is its only guard. The rule cannot move into the root file: Kilo applies its project rules again after a subagent's own, so an `edit` deny there took `write` and `edit` away from `python-pro`, and from every writing subagent with it.
  - Not measured on Windows, where an outside path starts with a drive letter that neither `/*` nor `../*` matches, so the backstop may refuse an outside edit there.
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
  fetched 2026-10-30), so a `cwd` that does not exist, lies outside the project, or sits in or below a folder that
  holds a `.git` or any entry named `HEAD`, denies. The `cwd` is checked exactly as sent, blanks included, so a
  folder named `evil` with a trailing blank is never mistaken for a plain `evil` beside it. Any `HEAD` counts because
  git's `is_git_directory()` needs only a valid `HEAD` in the folder itself, and looks for `objects` and `refs` under
  the folder a `commondir` file names, testing each with `access(path.buf, X_OK)` rather than for a directory
  ([setup.c at v2.43.0](https://raw.githubusercontent.com/git/git/v2.43.0/setup.c), fetched 2026-10-31). A committed
  bare repository therefore needs nothing beside its `HEAD` but a `commondir` file, or `objects` and `refs` as
  executable regular files: git 2.43.0 took both layouts for a bare repository, from the folder itself and from a
  folder below it, and read the planted `config`. A plain folder that happens to hold a file named `HEAD` denies
  too. The one folder with a `.git` that passes is a linked
  worktree of the project's own repository: its `.git` is a regular file, opened without following a symlink and
  checked on the open descriptor, holding exactly `gitdir: <path>`, that path resolves, symlinks and `..` followed, to
  a folder directly under the project's own `.git/worktrees/`, the `commondir` file there resolves back to the
  project's `.git`, and the `gitdir` file there resolves back to this folder's `.git`, which is the layout
  `git worktree add` writes (measured on git 2.43.0). A `.git` directory, a pointer that leads anywhere else, a missing
  target, a missing or foreign `commondir`, and a back-pointer that is missing or names another checkout still deny,
  so a second checkout cannot borrow the project's worktree folder. Before it lexes a command it holds every character to a
  fixed set: letters, digits, a blank, a newline and `._/:=,@^~%+-`, with `2>/dev/null` and `2>&1` as the only
  redirects. A quote of either kind, a backslash, a `$`, a backtick, a glob, a brace, a separator, a pipe, a carriage
  return and any non-ASCII character deny there. No quote is accepted, because each shell an agent may run reads a
  quoted span its own way, so a git format spells a space `%x20` and a newline `%n`, as in
  `git --no-pager log --format=%h%x20%an%x20%s` (measured on git 2.43.0). Every command left has to match the list.
  A git command also has to open with `git --no-pager`, whatever the list says, because git on a terminal pipes its
  output into a pager, and `less` runs any command typed after `!`. `--no-pager` sets `use_pager = 0` in
  `handle_options`, and `commit_pager_choice` then sets `GIT_PAGER` to `cat`, so neither `core.pager` nor
  `pager.<cmd>` can start one ([git.c at v2.43.0](https://raw.githubusercontent.com/git/git/v2.43.0/git.c), fetched
  2026-11-01). Measured on git 2.43.0 under a pseudo-terminal from `script`: `git log`, `git show` and `git diff HEAD`
  each started `GIT_PAGER`, while `git --no-pager` with `log`, `diff`, `show` or `status` did not, `pager.status=true`
  included. Only the long form passes, so `-P`, `--paginate` and a `-c` before the subcommand deny. No word,
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
  `git --no-pager log origin/main..HEAD`. gh may not open a browser (`--web`, `-w`, `-w=true`, `-cw`) or name another host by a
  URL argument, and `-R` or `--repo` must be exactly `OWNER/REPO` of letters, digits, `.`, `_` and `-`, because
  `--repo` takes `[HOST/]OWNER/REPO` ([gh pr view](https://cli.github.com/manual/gh_pr_view)), so a host part and
  an scp-style `git@host:owner/repo` deny alike. Nor may gh run a `--jq` or `-q` expression: go-gh
  compiles it with `gojq.WithEnvironLoader(func() []string { return os.Environ() })`
  ([pkg/jq/jq.go at go-gh v2.13.0](https://raw.githubusercontent.com/cli/go-gh/v2.13.0/pkg/jq/jq.go), the version gh
  2.89.0 pins, fetched 2026-10-30), and gojq's loader "allows to configure the environment variables referenced by
  `env` and `$ENV`" ([gojq README](https://raw.githubusercontent.com/itchyny/gojq/main/README.md)), so `--jq env`
  prints every variable, tokens included. `--template` and `-t` deny with it. A gh template has no environment function, but neither flag then
  carries code. On the `codex` format a read-only agent runs no gh command at all. gh sends its output to a pager
  whenever stdout is a terminal: "`GH_PAGER`, `PAGER` (in order of precedence): a terminal paging program to send
  standard output to, e.g. `less`" (`gh help environment`, gh 2.89.0), `StartPager` returns early only when that
  program is empty or `cat` or stdout is no terminal
  ([pkg/iostreams/iostreams.go at v2.89.0](https://raw.githubusercontent.com/cli/cli/v2.89.0/pkg/iostreams/iostreams.go)),
  and `gh pr view` starts it before it writes `--json` output
  ([pkg/cmd/pr/view/view.go at v2.89.0](https://raw.githubusercontent.com/cli/cli/v2.89.0/pkg/cmd/pr/view/view.go),
  both fetched 2026-11-01). No flag turns it off, and the environment prefix or `gh config set pager` that would are
  refused. Claude Code, OpenCode and Kilo Code hand the gate the call's `tty` key, which Rule E denies, but Codex hands
  its hook the command alone, so there a listed gh command could open a pager that `write_stdin` then types into.
  Codex does set `("GH_PAGER", "cat")` in `UNIFIED_EXEC_ENV` for every command it starts
  ([process_manager.rs at rust-v0.166.0](https://raw.githubusercontent.com/openai/codex/rust-v0.166.0/codex-rs/core/src/unified_exec/process_manager.rs)),
  and gh reads `GH_PAGER` before its own `pager` setting ("Pager precedence 1. GH_PAGER 2. pager from config 3. PAGER",
  [pkg/cmd/factory/default.go at v2.89.0](https://raw.githubusercontent.com/cli/cli/v2.89.0/pkg/cmd/factory/default.go)),
  but its shell snapshot, `shell_snapshot` with `default_enabled: true`
  ([features/src/lib.rs at rust-v0.166.0](https://raw.githubusercontent.com/openai/codex/rust-v0.166.0/codex-rs/features/src/lib.rs)),
  sources every export of the user's login shell before a `-lc` command and re-exports after it only the
  `shell_environment_policy` overrides and Codex's own variables
  ([tools/runtimes/mod.rs at rust-v0.166.0](https://raw.githubusercontent.com/openai/codex/rust-v0.166.0/codex-rs/core/src/tools/runtimes/mod.rs),
  all fetched 2026-11-06). A `GH_PAGER` the user exports therefore reaches gh in place of `cat`. That is read from the
  source, not measured, so gh stays denied there.
  Every `command` and `cmd` value is judged, not only the first. Unlike every other rule, any failure while lexing or matching denies here, a parse error and
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
  ([subagents, "Custom agents"](https://developers.openai.com/codex/subagents), fetched 2026-10-30). Codex does name
  the subagent on `PreToolUse`, although the hooks page lists `agent_id` and `agent_type` only for `SubagentStart` and
  `SubagentStop` ([hooks](https://learn.chatgpt.com/docs/hooks), fetched 2026-10-30) and the generated schema lists
  both as optional: in live run 41348146352 on Codex 0.166.0, the payload of a call the read-only `code-reviewer`
  made from its own rollout carried the keys `agent_id`, `agent_type`, `cwd`, `hook_event_name`, `model`,
  `permission_mode`, `session_id`, `tool_input`, `tool_name`, `tool_use_id`, `transcript_path` and `turn_id`, with
  `agent_type` `code-reviewer`, while the main thread's payloads carried neither field. Rule E therefore finds the
  read-only definition there. That run's reviewer never tried the probe touch, so a Rule E denial on Codex is proven
  by the gate's own tests on that payload shape, not yet by a live run. A payload without the fields is still
  allowed. Even so, Codex's own `PreToolUse` input for a shell call is `serde_json::json!({ "command": args.cmd })`
  (`exec_command.rs` at `rust-v0.156.1` and at `main` on 2026-10-30), so `tty`, `shell` and `login` never reach the
  gate there, and before `rust-v0.166.0` neither does `workdir`. Its `write_stdin` tool, which types into a shell
  started with `tty: true`, "doesn't run `PreToolUse` again when it sends input or polls a command that already
  passed `PreToolUse`" (same hooks page), and the page itself says to "Treat tool hooks as a useful guardrail, not a
  complete enforcement boundary". Rule E denies the `tty: true` start wherever the gate sees it, which is Claude
  Code and the OpenCode and Kilo Code runner. Copilot gets no shell for such an agent, as the next item explains.
- Rule F keeps the main thread, on every format, from starting a program that waits for typed input, because Codex's
  `write_stdin` types into a running terminal and no hook sees it: its handler's `pre_tool_use_payload` returns `None`
  under the comment "`write_stdin` is transport for an existing exec session. Empty writes are background polls, and
  non-empty writes continue a command that already ran PreToolUse as Bash, so do not emit a second pre hook here"
  ([write_stdin.rs at rust-v0.166.0](https://raw.githubusercontent.com/openai/codex/rust-v0.166.0/codex-rs/core/src/tools/handlers/unified_exec/write_stdin.rs),
  the same on `main`, both fetched 2026-11-06). Adding `write_stdin` to the matcher in
  [.codex/config.toml](../.codex/config.toml) would therefore match nothing, so the gate refuses the start instead.
  The programs are the POSIX shells, `fish`, `mksh`, `yash`, `tcsh`, `csh`, `nu`, `pwsh`, `powershell` and `cmd`,
  `su` and `runuser` without `-c`, `--command` or `--session-command`, read clustered as in `su -lc` and by
  prefix, `sudo` or `doas` with `-s` or `-i` and no command, `pkexec` with no program,
  since "If PROGRAM is not specified, the default shell will be run"
  ([pkexec.xml](https://raw.githubusercontent.com/polkit-org/polkit/main/docs/man/pkexec.xml), fetched 2026-11-06),
  `newgrp`, `script` without `-c` or a command operand, which starts `$SHELL`, `expect`, and `socat` with an `EXEC`,
  `SYSTEM`, `SHELL` or `PTY` address, the interpreters `python` in every spelling, `pypy` among them, `ipython`,
  `node`, `deno`, `perl`, `ruby`, `php`, `lua`, `luajit`, `R`, `julia` and `tclsh`, the REPLs `irb`, `pry`,
  `bpython`, `ptpython`, `ghci` and `jshell`, the editors `vi`, `vim`, `nvim`, `view`, `vimdiff`, `nano`, `pico`,
  `emacs`, `mg` and `micro`, the line editors `ed`, `red` and `ex`, the pagers `less`, `more` and `most`, `tmux`
  with any subcommand, because `send-keys` types into a session and `attach` hands one over, and `screen`. The
  database shells `sqlite3`, `psql`, `mysql`, `mariadb`, `mongosh` and `redis-cli` are held without their inline
  query or command (`sqlite3 db "SQL"`, `psql -c`, `mysql -e`, `mongosh --eval`, `redis-cli PING`), piped input or a
  file on standard input (`psql app < schema.sql`),
  the debuggers `gdb` and `lldb` without batch mode (`gdb -batch`, `lldb -b`), and `pdb` always. git is held when
  it opens the editor or a prompt: a `git commit` with no `-m`, `-F`, `-C`, `--fixup` or `--no-edit`, each read by
  its unambiguous prefix as `--mess=x` is, `--amend` and `--fixup amend:` or `reword:` included, since `--no-edit` is how to "Use the selected commit message without launching an editor"
  ([git-commit](https://git-scm.com/docs/git-commit), fetched 2026-11-06), `git commit -e`, `git rebase -i`,
  `git add -p`, `-i` and `-e`, `-p` on `checkout`, `restore`, `reset` and `stash push` or `save`, while
  `git stash show -p` and `git stash list -p` only print a diff, `git clean -i`, `git config -e`, and
  `git notes add`, `append` and `edit` with no `-m`, `-F` or `-C`. A
  `PYTHONINSPECT` setting is refused like the other variables below, because "If this is set to a non-empty string
  it is equivalent to specifying the `-i` option" ([Command line and environment](https://docs.python.org/3/using/cmdline.html),
  fetched 2026-11-06). A shell or an interpreter is held
  when it has no script, no inline code (`-c`, `-e` and their kin) and no input from a pipe, a heredoc or a
  here-string, and also whenever a flag keeps it waiting after that code: `python -i`, which enters interactive mode
  "When the `-c` option is used" ([Command line and environment](https://docs.python.org/3/using/cmdline.html),
  fetched 2026-11-06), `node -i`, `lua -i`, `julia -i`, `perl -d`, `php -a`, `pwsh -NoExit`, which "Doesn't exit
  after running startup commands" ([about_Pwsh](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_pwsh),
  fetched 2026-11-06), and `cmd /k`, which "keeps the command processor running"
  ([cmd](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/cmd), fetched 2026-11-06).
  cmd reads no switch past the first of `/c`, `/k` and `/r`, so only that one decides, and `cmd /c xcopy a b /k` runs
  and exits. Microsoft's page lists only `/c` and `/k`, and `/r` is read as `/c` the way ReactOS's
  `base/shell/cmd/cmd.c` reads it, which stops at the first `C`, `K` or `R` (inferred from that reimplementation,
  not measured on Windows). `pwsh -Command -` reads from the terminal like `pwsh -File -`, because "If the value of
  Command is `-`, the command text is read from standard input" (same about_Pwsh page, fetched 2026-11-06).
  A REPL and a full-screen editor are held whatever they are handed, a file to edit and piped input included,
  because they read the keyboard from the terminal. A line editor fed by a pipe or a heredoc is left to the other
  rules. `--version`, `--help` and each program's own version and help flags pass while they come before the first
  operand or `--`, so `sh -s -- --help` is still held, except for the database shells, the debuggers, `su`, `runuser`
  and `script`, whose options are read wherever they sit, as getopt permutes them, so `psql app --version` passes, and `command -v` and `command -V`, which only describe a
  name, pass whatever they name. The program is read the way the
  script rule reads it: `env`, `exec`, `command`, `sudo`, `nohup`, `timeout` and the other wrappers are peeled, each
  with its own value flags so `env -i bash` and `exec -a name bash` still name `bash`, a path such as
  `/usr/bin/python3` names the program its file name gives, and a versioned name such as `python3.12` counts as
  `python`. A shell, an interpreter, `su`, `runuser` and `script` fed a file with `< x.sh` run a script the gate
  cannot read, so `bash < x.sh` is held as a bare `bash` is. A subagent is
  never held by Rule F, and a read-only one is already held to its list by Rule E.
- GitHub Copilot's `preToolUse` payload carries no agent identifier at all, so caller identity there resolves to
  unknown every time and none of the gate's six rules ever fires. The hook is wired and runs, but it always allows:
  that surface is entirely unenforced by the gate, not merely weaker, and the `AGENTS.md` text plus the
  `sessionStart` and `userPromptTransformed` injections carry the whole weight instead.
- Copilot in JetBrains fires only six events, has no subagent event at all, and reads hook configuration only from
  `.github/hooks/`. A hook file anywhere else is ignored by that client.

#### Where the write rule draws the repository boundary

"Inside the repository" is the gate's own roots rather than a git query: the process working directory, the project
root the hook payload names in its `cwd` field, and the gate script's own on-disk location two parents up, that last
one only while it is a real project and not the user's home directory or a directory above it. The `cwd` root is kept
exactly as sent, so a folder named with a trailing blank is never read as the folder without it. That is what lets the
user-level install in [GLOBAL_SETUP.md](GLOBAL_SETUP.md) protect the open project instead of everything the user owns.
A relative path resolves against whichever directory a leading `cd` in the command moved to, and against every root
when the command never changed directory. A `cd` the shell refuses, into a folder that does not exist or a link that
loops, leaves it where it was, so `cd docs; cd /nonexistent; echo x > ../AGENTS.md` is placed from `docs`. A `cd`
whose landing the text does not name can stand in any folder the command has visited or in any root, and a relative
path is placed from all of them, with no allowlist entry applying afterwards. That covers `cd -`, `cd ~-`, `cd ~+`,
`cd "$OLDPWD"`, `cd $DIR`, `cd "$(...)"`, a bare `cd` or `pushd`, `pushd +1`, `pushd -0` and `pushd -n`, `popd` with
any argument, `Set-Location -` and `+`, a `-StackName`, and a plain name such as `cd docs` while `CDPATH` is set in the
environment the shell inherits. A command that sets `CDPATH` itself cannot be placed, like `PATH`. On Windows, a Git Bash drive path such as `/c/Users/x` is read as
`C:/Users/x` before it is placed, for a `cd` operand and a write target alike. An edit tool's path and a path a
PowerShell pipeline feeds a cmdlet are placed both exactly as sent and trimmed, and either reading inside denies,
because a host that keeps a blank at either end writes through `/tmp/l ` or joins ` /../AGENTS.md` to the project.
A main-thread shell call that carries its own `workdir`, as the OpenCode and Kilo Code bash tool does while the plugin
sends the project root as `cwd`, is read a second time from that folder, resolved against every root when relative,
so `echo x > ../AGENTS.md` with `workdir` set to `docs` denies.

The payload `cwd` widens the write rule and never an allow decision, because Codex fills it from the `workdir` the
main thread chose. It is a root a write may not land in and a folder the command may start in, but the allowlist, the
built-in pytest check's test paths and an allowlisted path entry are trusted only from the gate's working directory and
its install root, every folder the command can start in has to sit inside one of those, an allowlisted path has to
name the same file from each of them, and a file run with `source` or `.` is read from each of them and is
unplaceable when two copies differ.

Deleting, moving, or renaming the repository root or any directory above it counts as a write inside it, so
`rm -rf ..`, `rm -rf ~`, `Remove-Item -Recurse` or `rmdir /s` on a parent, and `mv` or `Move-Item` of a parent are
denied, while the same command on a sibling folder that holds no root is allowed. A wildcard operand counts when any
path it could match, compared one component at a time and case-insensitively on Windows, is the root, a directory
above it, or a path inside it, so `rm -rf ../agent-*` and `Remove-Item ..\*` are denied.

A write outside the repository, a write to the null device or to a PowerShell drive that holds no files such as `Env:`
or `Function:`, each spelled with no blank around it, a write to `tasks.md` at the project root, and git branch switching stay allowed, so the main thread
keeps full use of git and keeps ownership of its own task list.

#### How the write rule reads a command

Each shell's own quoting applies: a backslash escapes only in a POSIX shell, PowerShell escapes with a backtick and
splits an unquoted `a,..` into two paths, and cmd escapes with a caret, so `Remove-Item "D:\parent\"` is read as the
path it names. The same checks reach inside a wrapper: `cmd /c`, `cmd /k` and `cmd /r`, `bash -c`, `sh -c`, `zsh -c`, and
`powershell` or `pwsh` with `-Command`, `-c` or a decoded `-EncodedCommand`, nested up to three deep. They also reach
code a shell or interpreter takes some other way: a heredoc or here-string, a piped `echo`, `printf` or `cat`,
`xargs`, `eval`, `Invoke-Expression`, and a file run with `source` or `.`. An encoded value that does not decode is an
unlexable command and allows, since PowerShell refuses to run it. Inline Python is parsed and inline JavaScript read
for the path each actually writes, through import aliases and renamed bindings, rather than for every string it holds.

Codex's `apply_patch` call carries a patch body rather than a file path, and the key that holds that body in the
payload is not confirmed. The gate therefore reads the file headers out of every string value in the call rather than
out of one named key, and denies the call when it finds no path key and no file header, because an edit whose target
it cannot resolve is not trusted. A header may be indented: Codex's parser runs `let trimmed = line.trim();` and then
`trimmed.strip_prefix(UPDATE_FILE_MARKER)`, and the same for the add and delete markers
([streaming_parser.rs at rust-v0.166.0](https://raw.githubusercontent.com/openai/codex/rust-v0.166.0/codex-rs/apply-patch/src/streaming_parser.rs),
fetched 2026-11-06), so `  *** Update File: AGENTS.md` names a file, while the markers compare case for case. The
headers are read beside any path key the call carries, and an edit tool's every path key is placed, not only the
first, so a call with `file_path` outside and `filePath` inside denies.

The writers the gate knows include `find -delete` and `find -exec`, `git clean`, `git rm`, `git mv`,
`git reset --hard`, `git stash`, `git checkout -f` and `git checkout` or `git restore` of a path, `curl -o` and `-O`,
`wget`, `touch`, `mkdir`, `install -d`, `tar` and `unzip` extraction, the `[System.IO.File]` and
`[System.IO.Directory]` methods, and the PowerShell item and content cmdlets, bound the way PowerShell binds their
parameters. The .NET methods are read whatever shell the tool name claims, because Codex on Windows names its shell
tool `Bash` and runs the command in PowerShell, so `[System.IO.File]::WriteAllText($target, ...)` under `Bash` denies
the same way it does under `PowerShell`.

Every wrapper is peeled by its own options, as getopt reads them: a value attached (`sudo -D/tmp`, `ionice -c3`), after
`=` (`--chdir=/tmp`) or in the next word, and a long option by any unambiguous prefix (`env --chd=/tmp`,
`xargs --max-pr 1`). The wrappers are `env`, `sudo`, `doas`, `exec`, `command`, `nohup`, `setsid`, `stdbuf`, `nice`,
`ionice`, `time`, `timeout`, `gtimeout`, `pkexec`, `runuser -u`, `taskset`, `chrt`, `prlimit`, `unbuffer`, `rlwrap`, `strace`,
`ltrace`, `fakeroot`, `firejail`, `numactl`, `valgrind`, `caffeinate`, `busybox`, `toybox` and `xargs`. `env -S`
splits its string the way a shell would, a file a wrapper writes itself (`time -o`, `strace -o`, `ltrace -o`,
`rlwrap -l`, `fakeroot -s`, `valgrind --log-file`) is a write target, and `mksh` and `yash` are read as POSIX shells.
Commands piped into `ed` or `red` are read for the files `w` writes. sed is read the way GNU sed's getopt_long reads
it, options anywhere before `--` and long options by prefix, so `-i` takes the rest of its cluster as a backup suffix
(`sed -ie`, `-ibak`, `-i~`, `--in-pl`), and `-nf script`, `--fi script` and `--expr=...` are found wherever they sit.
A sed script file the gate cannot read is unplaceable. perl and ruby read `-i` the same way inside a switch cluster
(`perl -pi~`).

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
resolve, which denies, because deciding what Rule A protects is their whole job. A symlink loop is such a path:
Python 3.11 and 3.12 raise `RuntimeError` from `Path.resolve` on one where 3.13 returns the path, and every resolving
helper reads that error as unplaceable, so a `cd` into a loop leaves the shell where it was, as a `cd` into a missing
folder does, and a root that loops is dropped. On Windows that includes a loopback
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
- A shell command that is not a string, an edit path key that holds neither a string nor null, and a tool the gate
  does not know that still carries a `command`, `cmd` or `script` value.
- A shell call whose `workdir` resolves to no directory from any root, loops, or names a share the gate cannot map.
- A command run under `chroot`, `sudo -R` or a firejail option that remaps the file system such as `--private`, an
  `env -S` string holding an escape, a `$` or a `#`, and `strace -o` into a pipe.
- Inline or piped code for `fish`, `csh`, `tcsh`, `nu` or `tclsh`, whose languages the gate does not read, commands
  piped into `ex`, and commands piped into `ed` that run a shell command, use a global command or come from a program
  whose output the gate cannot know. A script any of them runs is a script run.
- Words `xargs` reads from the terminal or from a program whose output the gate cannot know, when they become code or
  the program itself, as in `xargs -I{} sh -c {}`, and any such word handed to `sed`, `awk` or `find`, which read a
  script, a program or a write from any argument. `git` takes code only at or before its subcommand, so
  `cat x | xargs git` denies while `git ls-files -m | xargs git add` allows.

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
- `--show-signature`, `log.showSignature` and the `%G?` family of format placeholders, which run `gpg.program`.
- A `filter.<driver>.clean` or `filter.<driver>.process` program, which `git diff` and `git status` run on the
  working tree.
- Submodule recursion, which reads each submodule's own configuration.
- A Claude Code plugin loaded for one session with `--plugin-dir` is not under `plugins/cache`, so the gate finds no
  definition for its `<plugin>:<name>` agents and allows them as unknown, a read-only one included. `--plugin-url` is
  assumed to behave the same, not measured.
- On Codex before `rust-v0.166.0`, a call's `workdir` never reaches the gate, and on every Codex version `tty`,
  `shell` and `login` do not either, so a read-only agent there can still run a listed command in another folder,
  under another shell, or on a terminal it then types into through `write_stdin`. No listed command opens a pager
  there, because git runs only as `git --no-pager` and gh not at all, so the terminal holds no pager to escape from.
- `git status`, which rewrites `.git/index` to refresh its stat cache, so a read-only agent still writes there.
- `gh pr view --comments` and every other gh or git output, which is text other people wrote and reaches the agent as
  untrusted input.

Rule E's working-directory check, which keeps a read-only agent out of a repository planted inside the project, has
known limits of its own, accepted rather than open:

- The gate checks the folder before the command runs, so a `HEAD`, `.git` or pointer file planted between the check
  and the run is not seen. A read-only agent cannot write, so that needs another process writing at the same moment.
- Windows has no `O_NOFOLLOW`, so the only symlink guard on a `.git`, `commondir` or `gitdir` pointer there is the
  link check before the open, which a swap between the two can pass. `fstat` on the opened descriptor still refuses a
  pipe, a device and a directory.
- A hard link is read as the regular file it is. A checkout cannot create one, so a pull request cannot plant one.
- Configuration the user wrote that reaches into the working tree is trusted, at the project root as much as in a
  subfolder. A relative `include.path` "is considered to be relative to the configuration file in which the include
  directive was found" ([git-config at v2.43.0](https://raw.githubusercontent.com/git/git/v2.43.0/Documentation/config.txt),
  "Includes", fetched 2026-10-31), so one in `.git/config` can name a tracked file a pull request edits, and an
  `includeIf "onbranch:..."` include is met by whatever branch name the pull request picks.
- A committed `.gitattributes` can route any file through a `diff`, `filter` or `merge` driver the user configured
  for their own use, so a listed command runs that driver on content the pull request chose. The gate reads no
  attributes.
- A submodule's configuration lives under `.git/modules`, which no pull request can write, so it is the user's own and
  not checked.

As defence in depth, a consumer who uses no bare repository can set `safe.bareRepository` to `explicit`, as
[Prerequisites in GLOBAL_SETUP.md](GLOBAL_SETUP.md#prerequisites) explains. On git 2.43.0 the planted `commondir`
layout then fails with `cannot use bare repository ... (safe.bareRepository is 'explicit')`.

On OpenCode and Kilo Code the native permission map denies every redirect and `&`, so `2>/dev/null` and `2>&1` deny
there while the gate allows them. A gh `-R` with a host part, a comma-joined option, a leading `^` or `@`, a backslash
and a `workdir` key have no native rule: the map cannot tell a host from a branch name and sees command text only, so
the gate alone holds them.

Known limits of the write rule, accepted rather than open: a write form the gate does not know passes, a top-level
command it cannot parse allows on the main thread, MCP tools are not gated, code run by an allowlisted tool is trusted rather than read,
Copilot's main thread is not gated, the risky variable and option lists come from knowledge rather than vendor
documentation, a loopback share whose folder cannot be determined denies, Rule F knows only the programs and the git
forms on its list, so a program that waits for typed input without being on it, or a git command that opens the
editor only on a terminal, such as `git merge`, `git revert`, `git tag -a` or `git rebase --continue` with no message,
can still be typed into through Codex's `write_stdin`, and so can inline code that opens a prompt of its own, such as
`python3 -c 'import code; code.interact()'`, a `breakpoint()` call, `node -e 'require("repl").start()'` or
`perl -ne eval`, because the gate reads inline code for the files it writes and cannot list every way code reads the
terminal (Codex starts every such process with `PAGER`, `GIT_PAGER` and `GH_PAGER` set to `cat`,
[process_manager.rs at rust-v0.166.0](https://raw.githubusercontent.com/openai/codex/rust-v0.166.0/codex-rs/core/src/unified_exec/process_manager.rs),
fetched 2026-11-06, so git and gh open no pager there unless the user's own login shell exports one, which Codex's
shell snapshot restores over `cat`, as Rule E above explains), `xargs` handing a write command names from a file or
from the terminal passes, as in `xargs rm < list.txt`, `xargs -a list.txt rm` or a bare `xargs rm`, because the lexer
drops an input redirect and the gate reads neither the file nor what is typed, so it sees `rm` with no operand (the
same names piped in, as in `cat list.txt | xargs rm`, and a replace string read from either, as in
`xargs -I{} rm {} < list.txt`, still deny), a `CDPATH` set only by the user's shell profile, which the gate never sees, sends `cd docs` to the first `docs`
under it while the gate places the command from `./docs`, and the `tasks.md` exemption holds at every root, so a call whose `cwd`
names a project subfolder, as a Codex `workdir` does from `rust-v0.166.0`, may write `tasks.md` in that subfolder. Re-audit only when the rule changes, and record a new limit here rather than chasing it.

Rule F also reads these forms as handed their input, each an accepted limit:

- `vim -V`, `vi -V1` and `nvim -V` read as a version flag, though there `-V` sets the verbosity and the editor starts.
- A version or help flag is read without knowing which options of `tmux`, `screen`, the pagers and the editors take a
  value, so `tmux -LV`, `tmux -f -V`, `screen -S -v` and `less -o -V README.md` pass, though the flag is that option's
  value and the program starts.
- `pwsh -File - -?` and `pwsh -Command - -v` pass, though the flag after `-` goes to the script pwsh reads from the
  terminal.
- `psql -f -` with nothing piped in passes, because `-f` reads as a script file, though `-` is the terminal.

The write rule reads `gawk -i inplace` and `--include=inplace` as an in-place edit, but not the attached
`gawk -iinplace`, which passes.

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
