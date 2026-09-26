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

The gate is one shared rule in [../.agents/hooks/preflight_gate.py](../.agents/hooks/preflight_gate.py). It reads a hook
payload on standard input and denies four things: a write of any file resolving inside the repository working tree
coming from the main thread, with no exemption left for markdown, configuration, or `docs/` (delegate the change to a
subagent that owns the area instead), any tool call at all from a subagent whose own definition declares no skills
(spawn a specialist instead), a web fetch or web search called straight from the main thread on the one format whose
payload names that tool today, Claude Code, and a script or module run from the main thread, because the gate cannot see
what a script writes. The allowlist that lifts the last rule is in
[What the main thread may run](GLOBAL_SETUP.md#what-the-main-thread-may-run). A relative path is resolved against
whatever a leading `cd` in the command moved to, so changing directory first buys nothing. A write outside the
repository, the null device, `tasks.md` at the project root, and switching a git branch stay allowed, and the main
thread keeps full use of git otherwise. Caller identity is a tri-state, subagent, main thread, or unknown when a payload
carries nothing that could tell the two apart, and none of the four rules fires on an unknown caller. Every failure path
also allows the call, because a broken gate must never break a session, with one deliberate exception: a path none of
the three repository-boundary helpers can resolve is treated as inside, which denies.

Three more hooks live beside it in [../.agents/hooks/](../.agents/hooks/) and ride the same wirings:
`no_ai_markers_check.py` checks the reply, `markdown_lint_check.py` lints a file just after it was edited, and
`task_list_sync.py` mirrors the session task list into `tasks.md`. Every hook is invoked on `-S -E`, under the
first of `python3` and `python` its wiring resolves, and none of them uses `argparse`, because it exits 2 on a
usage error and 2 is the deny code in the plain format.

Each agent wires those scripts through its own hook surface, and the surfaces differ in what they can stop.

| Agent | Hook config | Blocks a tool call | Injects context | Blocks a reply | Tells subagent from main thread |
| --- | --- | --- | --- | --- | --- |
| Claude Code | [.claude/settings.json](../.claude/settings.json) | yes, `PreToolUse` | yes, `SessionStart` and `UserPromptSubmit` on every turn, and the subagent text on `SubagentStart` | yes, `Stop` and `SubagentStop`, after `MessageDisplay` fixes the display | yes, `agent_id` is present only inside a subagent |
| Codex | inline `[[hooks.*]]` in [.codex/config.toml](../.codex/config.toml) | yes, `PreToolUse` | yes, `UserPromptSubmit`, and the subagent text on `SubagentStart` | runs the check on `Stop` | yes, `agent_id` is present only inside a subagent |
| OpenCode | plugin [.agents/plugin/hooks.js](../.agents/plugin/hooks.js), declared by path in [opencode.json](../opencode.json) | yes, throwing from `tool.execute.before` | yes, `chat.message` on every root-session prompt, as a synthetic text part, and the subagent text in a child session | no, but `experimental.text.complete` stores a fixed text part | yes, the session `parentID` read through `client.session.get` |
| Kilo Code | the same plugin, same declaration | yes, throwing from `tool.execute.before` | yes, same mechanism | no | yes, same mechanism |
| GitHub Copilot | [.github/hooks/preflight.json](../.github/hooks/preflight.json), camelCase events | fires on `preToolUse`, but caller identity there always resolves to unknown, so the gate always allows | yes, `sessionStart` and `userPromptTransformed` on every prompt, and the subagent text on `subagentStart` | yes, `agentStop` forces a correction turn | no, the `preToolUse` payload carries no agent identifier |

The full event set per surface, beyond the gate itself:

| Agent | Gate | Formatting check | Markdown lint | Task list |
| --- | --- | --- | --- | --- |
| Claude Code | `SessionStart`, `UserPromptSubmit`, `SubagentStart`, `PreToolUse` | `MessageDisplay`, `Stop`, `SubagentStop` | `PostToolUse`, matcher `^(Edit\|Write\|MultiEdit)$` | `TaskCreated`, `TaskCompleted`, `SessionStart`, `PreCompact`, `Stop` |
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
  fix leaves, a semicolon above all, while `SubagentStop` checks the whole reply. Codex runs the full check on `Stop`.
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
  stored fix of a finished text part.
- GitHub Copilot's `preToolUse` payload carries no agent identifier at all, so caller identity there resolves to
  unknown every time and none of the gate's four rules ever fires. The hook is wired and runs, but it always allows:
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
continuation before CR LF, a PowerShell cmdlet fed its path through the pipeline, `pushd`, `popd`, `Push-Location`,
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
CIM queries. A top-level command the lexer cannot read still allows, while code nested inside a readable command that
cannot be read denies.

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
- The JetBrains Copilot plugin scans `.claude/agents`, but it only understands its own `*.agent.md` format, so
  subagent definitions cannot be shared between Copilot and Claude Code or OpenCode.
- GitHub Copilot ships four surfaces (VS Code, JetBrains, CLI, cloud agent) that differ on hooks, on MCP, and on
  documentation quality. Never answer a Copilot question without naming the surface.
- On Windows the two agent symlinks and the skills symlink need `git config core.symlinks true` and Developer Mode
  enabled before the checkout, otherwise git writes plain text files containing the target path and every agent that
  depends on them sees nothing.
