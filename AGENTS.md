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

Every agent carries the same reminder into each main-thread prompt, word for word, from its own wiring. No wiring
hands it to a subagent: it tells the reader to delegate, and a subagent told that turns its own task away. A subagent
gets the second text below instead, also word for word, from every wiring that can reach one.

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

The line breaks and blank lines are part of the wording, so every wiring delivers real newlines to the model. Claude
Code prints plain text through `echo` with the newlines inside the single-quoted literal, which `sh`, Git Bash and
PowerShell all print unchanged. Codex and Copilot read JSON, so they carry `\n` escapes inside `additionalContext`,
printed by `printf '%s\n'` in a POSIX shell, because `dash` turns an `echo` argument's `\n` into a raw newline that
breaks the JSON, and by `echo` in PowerShell, which prints a single-quoted literal as written. The plugin and
[.agents/hooks/copilot/prompt_reminder.py](.agents/hooks/copilot/prompt_reminder.py) hold the text as a string
constant.

Investigation, review, and bounded implementation are delegated by default. Doing a specialist's work inline from the
main session is the failure mode this gate prevents. Re-run the check at the start of every task. Most work in this
repo is documentation and the Python tooling, so `markdown-writer` and `python-patterns` are the
usual owners, with `code-reviewer` before any merge.

The gate is enforcing, not advisory. One shared rule in
[.agents/hooks/preflight_gate.py](.agents/hooks/preflight_gate.py) decides every tool call, on every agent:

- It denies a main-thread write of any file resolving inside the repository, with no exemption for markdown,
  configuration, or documentation, and tells the caller to delegate the change instead. "Inside the repository" is the
  gate's own roots rather than a git query: the process working directory, the project root the hook payload names in
  its `cwd` field, and the gate script's own on-disk location two parents up, that last one only while it is a real
  project and not the user's home directory or a directory above it, so the user-level install in
  [docs/GLOBAL_SETUP.md](docs/GLOBAL_SETUP.md) protects the open project instead of everything the user owns. A
  relative path resolves against whichever directory a leading `cd` in the command moved to,
  and against every root when the command never changed directory. Deleting, moving, or renaming the repository root or
  any directory above it counts as a write inside it, so `rm -rf ..`, `rm -rf ~`, `Remove-Item -Recurse` or
  `rmdir /s` on a parent, and `mv` or `Move-Item` of a parent are denied too, while the same command on a sibling folder
  that holds no root is allowed. A wildcard operand counts when any path it could match, compared one component at a
  time and case-insensitively on Windows, is the root, a directory above it, or a path inside it, so
  `rm -rf ../agent-*` and `Remove-Item ..\*` are denied. Each shell's own quoting applies: a backslash escapes only in
  a POSIX shell, PowerShell escapes with a backtick and splits an unquoted `a,..` into two paths, and cmd escapes with
  a caret, so `Remove-Item "D:\parent\"` is read as the path it names. The same checks reach inside a wrapper:
  `cmd /c` and `cmd /k`, `bash -c`, `sh -c`, `zsh -c`, and `powershell` or `pwsh` with `-Command`, `-c` or a decoded
  `-EncodedCommand`, nested up to three deep. They also reach code a shell or interpreter takes some other way: a
  heredoc or here-string, a piped `echo`, `printf` or `cat`, `xargs`, `eval`, `Invoke-Expression`, and a file run
  with `source` or `.`. An encoded value that does not decode is an unlexable command and allows, since PowerShell
  refuses to run it. Inline Python is parsed and inline JavaScript read for the path each actually writes, through
  import aliases and renamed bindings, rather than for every string it holds. The writers the gate knows include
  `find -delete` and `find -exec`, `git clean`, `git rm`, `git mv`, `git reset --hard`, `git stash`, `git checkout -f`
  and `git checkout` or `git restore` of a path, `curl -o` and `-O`, `wget`, `touch`, `mkdir`, `install -d`, `tar`
  and `unzip` extraction, the `[System.IO.File]` and `[System.IO.Directory]` methods, and the PowerShell item and
  content cmdlets, bound the way PowerShell binds their parameters. The .NET methods are read whatever shell the tool
  name claims, because Codex on Windows names its shell tool `Bash` and runs the command in PowerShell, so
  `[System.IO.File]::WriteAllText($target, ...)` under `Bash` denies the same way it does under `PowerShell`.
  A write outside the repository, a write to the
  null device or to a PowerShell drive that holds no files such as `Env:` or `Function:`, a write to `tasks.md` at the
  project root, and git branch switching stay allowed, so the main thread keeps full use of git and keeps ownership
  of its own task list.
- It denies any tool call, not only an edit, from a subagent whose own definition declares no skills, because that
  agent is not a specialist. The rule reads `agent_type` out of the payload and looks the definition up in the six
  agent trees, so an unknown or unreadable `agent_type` allows rather than denies.
- It denies the main thread from running a web fetch or web search tool directly, on the one format where that
  tool's name is confirmed (Claude Code today; Codex has no confirmed equivalent name yet, see Maintenance
  follow-ups below). It spawns a subagent to do the research and report back instead.
- It denies the main thread from running a script or a module, because the gate cannot see what a script writes:
  an interpreter handed a file or `-m` (`python x.py`, `node x.js`, `bash x.sh`, `pwsh -File x.ps1`), a package or
  task runner handed any subcommand (`npm`, `npx`, `pnpm`, `yarn`, `uv`, `pip` and their kin), a git subcommand that
  runs a command of its own (`bisect run`, `rebase --exec`, `submodule foreach`, `filter-branch`), a build runner or
  compiler asked for more than its version or help (`make`, `cargo`, `go run`, `go generate`, `go test`, `dotnet`,
  `mvn`, `gradle`, `gradlew`, `just`, `rake` and their kin), a program called by a script file name, any program
  whose path lands inside the repository, and a native program named by any other path unless it is a known
  read-only tool such as `/usr/bin/grep`. The exception is a command that passes an entry of
  `MAIN_THREAD_ALLOWLIST` in the gate, or matches, in full, an entry of the project's own `main-thread-allowlist.txt`
  at its root. The built-in list holds three checks, `python -m pytest`, `node --check` and `bash -n`, and each one
  names the only options it takes: pytest options that load a plugin, a configuration file, a root directory or a
  conftest from elsewhere, set the temporary base, write a report, or import a warning category deny, and so does a
  test path outside the repository. `node --check` takes no preload or require option, and `bash -n` takes nothing
  that turns execution back on. A program spelled with a path never matches a built-in entry, so
  `.venv/Scripts/python.exe -m pytest` needs a project entry, and a project entry whose first word holds a slash
  matches only the file it names. git has no built-in entry: git reads are judged by what they write like any other
  command, which is why read-only git is not listed. A shell handed a script file that an entry allows still has the
  script read as shell code, so what it writes stays the write rule's to judge. This repository's three checks (`python tools/check-markdown.py`, `python tools/check-badges.py`,
  `python tools/gen_subagents.py --check`) live in its own [main-thread-allowlist.txt](main-thread-allowlist.txt),
  because a built-in entry would also allow a same-named script in a consumer project, and that script could write
  files. The file sits at the root rather than under `.agents/`, because the Quickstart imports `.agents` whole and
  would ship it, and no import pathspec names it. Inline code (`python -c`, `node -e`) is not a script run and stays
  with the inline-code reader under the write rule. How entries match and how a consumer extends the list is in
  [docs/GLOBAL_SETUP.md](docs/GLOBAL_SETUP.md).
- Every rule above fires only once the caller is positively identified as the main thread. A format whose payload
  carries nothing that could identify the caller, currently GitHub Copilot, is left ungated rather than guessed at,
  because denying blind risks blocking a legitimate subagent as often as it blocks the main thread. The same holds for
  an OpenCode or Kilo Code call whose session the plugin could not read: the envelope then carries no `is_subagent`,
  and the gate allows.
- It fails open almost everywhere. Any parse error, missing key, unexpected payload, unknown `--format`, or
  unlexable shell command allows the call, because a broken gate must never break a session. The deliberate exception
  is the three repository-boundary helpers, `_resolves_inside_repo`, `_path_exists_in_repo` and `_contains_repo`: a
  path none of them can resolve fails toward True, which denies. Deciding what Rule A protects is the whole job of
  those three, so a path the gate cannot place is treated as inside rather than waved through. On Windows that
  includes a loopback UNC path to a share that is not an administrative drive share, such as `\\localhost\share` or
  `\\127.0.0.1\share`, because only the share definition knows which folder it maps to, an administrative drive share
  such as `\\fileserver\C$` on any host, because the gate cannot prove that host is another machine, and a volume
  GUID or `GLOBALROOT` path. This machine is recognised by its loopback and unspecified addresses in every spelling,
  IPv4-mapped IPv6 included, by its own name with or without a domain or a trailing dot, and by any name or LAN
  address that resolves to one of its own addresses. The loopback mapping runs again on the resolved path, so a link
  that resolves to an administrative share of the project is still inside. A write the gate
  recognises but cannot place denies the same way. A write target the shell has not expanded yet, such as the `$f` in
  `rm $f`, is the common case, and the others are a command nested or wrapped deeper than the gate reads, code piped
  into a shell or interpreter from a program whose output the gate cannot know, as in `curl ... | bash`, a sourced
  file it cannot read, `eval` or `Invoke-Expression` of a variable, and inline code that starts a process or reaches a
  file call through a computed name. Only the running program knows where such a write lands, so the main thread's
  call is denied and the write goes to a subagent or is spelled with a literal path. On Windows, a Git Bash drive path such as
  `/c/Users/x` is read as `C:/Users/x` before it is placed, for a `cd` operand and a write target alike.
- What the write rule reads, beyond the plain writers: a hard link whose source is a project file (`ln` without `-s`,
  `cp -l`, `fsutil hardlink create`, `New-Item -ItemType HardLink`, `mklink /H`), a Windows device, extended-length
  or loopback administrative-share spelling of a project path, command substitution inside double quotes and
  backquotes, a line continuation before CR LF, a PowerShell cmdlet fed its path through the pipeline, `pushd`,
  `popd`, `Push-Location`, `Pop-Location`, `env --chdir`, `sudo --chdir` and `pwsh -WorkingDirectory`, parentheses
  that are a subshell only in a POSIX shell, `xcopy`, `robocopy`, `replace`, `expand`, `esentutl`, `certutil`,
  `bitsadmin`, `mklink`, `Start-Transcript`, every `Export-*` cmdlet, `Start-Process` with its redirects and argument
  list, `Set-ItemProperty`, any other `System.IO` use, in-place editors and formatters, writes and processes inside an
  `awk` or `sed` program, Lua, R, Julia, `sqlite3`, PHP, Perl and Ruby code, and the runners `busybox`, `toybox`,
  `su -c`, `setsid`, `flock`, `watch`, `script`, `wsl` and `git -c alias.x=!...`. It also reads the file a git
  output option names (`--output` and its abbreviations on the diff family, `format-patch`, which writes into the
  working directory unless `--stdout`, `archive -o`, `bundle create`), a `git config` write, which lands in
  `.git/config` or the `-f` file, and hard links made from Python and JavaScript, where the source counts as written
  too. Each of the following cannot be placed and denies on the main thread: a leading assignment, an `env`,
  `export`, cmd `set`, `setx`, `$env:`, `Env:` or `SetEnvironmentVariable` setting of a variable that changes which
  program or file a command uses (git's configuration, directory, work tree, pager, editor and external diff, a
  library preload, `NODE_OPTIONS`, `PYTHONPATH`, `PYTHONSTARTUP`, `PERL5OPT`, `RUBYOPT`, `BASH_ENV`, `ENV`, `PATH`,
  `PYTEST_ADDOPTS`, the temporary directory, and the rest of `_UNPLACEABLE_ENVIRONMENT`), a `git config` setting or
  `-c` value that runs a program or includes more configuration, `git grep -O`, `difftool` and `mergetool`, inline
  Python that imports anything outside the standard library, a standard module shadowed by a file in its working
  directory, or loads code through `runpy`, `importlib` or `ctypes`, inline JavaScript that loads any module that is
  not built in, PowerShell that holds a `System.IO` type as a value, imports a namespace or module with `using`,
  turns a string into a type, uses reflection or compiles code with `Add-Type`, WMI or CIM method calls and
  `wmic ... call create`, `ssh`, `plink`, `winrs`, `Invoke-Command` and PowerShell sessions aimed at this machine or
  at a session, a VM, a container or a script file, `psexec`, a container that binds a path inside or above the
  repository, `docker` or `podman` `exec`, `start`, `build`, `cp` into a container, and `compose up`, `run` or
  `build`, and a job handed to `schtasks /create`, `at`, `batch`, `crontab`, `systemd-run` or
  `Register-ScheduledTask`. Read-only forms of the same tools still allow: container `ps`, `images`, `inspect`,
  `logs`, `stats`, `network ls`, `volume ls`, `compose ls`, `ps`, `logs` and `config`, `schtasks /query`, `crontab -l`,
  `Get-ScheduledTask`, and WMI or CIM queries. The standard-library writers the inline Python
  reader places include archive extraction, URL download to a file, database files, logging file handlers, and
  temporary files created in a named directory. A target holding an unexpanded
  `$VAR`, `{a,b}`, `%VAR%` or `!VAR!` cannot be placed and denies. A shell command that is not a string denies, and so
  does a tool the gate does not know that still carries a `command`, `cmd` or `script` value. A top-level command the
  lexer cannot read still allows, while code nested inside a readable command that cannot be read denies.
- No MCP tool is matched. Claude Code names an MCP tool `mcp__<server>__<tool>` and compares a `PreToolUse` matcher
  against that name (`https://code.claude.com/docs/en/hooks`, "MCP tools follow the naming pattern
  `mcp__<server>__<tool>`"), and the matcher in [.claude/settings.json](.claude/settings.json) names built-in tools
  only. The OpenCode and Kilo Code runner hands every tool to the gate, but `EDIT_TOOLS` names built-in edit tools
  only, so an MCP call is allowed there too. Two servers in [.mcp.json](.mcp.json) write local files that way:
  `playwright` through `browser_take_screenshot` and `browser_pdf_save`, whose `filename` "Relative file names are
  resolved against the workspace root"
  (`https://github.com/microsoft/playwright-mcp/blob/main/README.md`), and `chrome-devtools` through
  `take_screenshot`, `take_snapshot`, `take_heapsnapshot`, `performance_stop_trace`, `screencast_start`,
  `evaluate_script` and `get_network_request`, each with a path parameter "to save" into
  (`https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/tool-reference.md`, fetched 2026-09-25).
- Known limits of the main-thread write rule. These are accepted, not open defects:
  - The rule is a list of forbidden write forms, so a write form it does not know passes.
  - A top-level shell command the gate cannot parse is allowed by design, because the gate fails open.
  - MCP tools that write files are not covered by the matchers, as the bullet above records.
  - A compiled program or native binary run by an allowlisted tool, and code run by an allowlisted test runner, are
    trusted rather than read.
  - GitHub Copilot's hook carries no caller identity, so its main thread is not gated. The live test reports this as
    a known gap.
  - The lists of risky environment variables and options were written from knowledge, not from checked vendor
    documentation.
  - A loopback share whose target folder cannot be determined is denied rather than mapped.

  Re-audit the rule only when the rule itself changes. Record a newly found limit in this list rather than chasing it.

Each agent wires that one script, and the hooks beside it, to its own hook surface:

| Agent | Wiring | Events |
| --- | --- | --- |
| Claude Code | [.claude/settings.json](.claude/settings.json) | `SessionStart` and `UserPromptSubmit` for the gate text, `SessionStart` for the subagent supervision text, `SubagentStart` for the subagent text, `PreToolUse` (matcher `^(Edit\|Write\|MultiEdit\|NotebookEdit\|Bash\|PowerShell\|WebFetch\|WebSearch)$`) for the gate, `PostToolUse` (matcher `^(Edit\|Write\|MultiEdit)$`) for the markdown lint in `markdown_lint_check.py`, `MessageDisplay` for the display fix, `Stop` (with `--display-fixed`) and `SubagentStop` for the formatting checker, `TaskCreated`, `TaskCompleted`, `SessionStart`, `PreCompact` and `Stop` for the task list |
| Codex | inline `[[hooks.*]]` tables in [.codex/config.toml](.codex/config.toml) | `UserPromptSubmit` for the gate text, `SubagentStart` for the subagent text, `PreToolUse` (matcher `^(Bash\|shell\|apply_patch\|Edit\|Write\|NotebookEdit)$`) for the gate, `Stop` for the formatting checker, `SessionStart` for the task list |
| OpenCode and Kilo Code | [.agents/plugin/hooks.js](.agents/plugin/hooks.js), declared once by path in the `plugin` array of [opencode.json](opencode.json), which both tools read | `chat.message` for the gate text in a root session and the subagent text in a child session, `tool.execute.before` for every hook directly in [.agents/hooks/](.agents/hooks/), `experimental.text.complete` for the display fix |
| GitHub Copilot | [.github/hooks/preflight.json](.github/hooks/preflight.json) | `sessionStart` for the gate text and the task list, `subagentStart` for the subagent text, `userPromptTransformed` for the gate text on every prompt through `copilot/prompt_reminder.py`, `preToolUse` (matcher `bash\|powershell\|create\|edit`) for the gate, `agentStop` for the formatting checker |

Per-surface details worth knowing before you touch any of them:

- Claude Code detects a subagent by the presence of `agent_id` in the hook payload, which it documents as present only
  inside a subagent. The same `PreToolUse` payload also carries `agent_type`, the subagent's own name, and that is the
  field Rule B depends on: `agent_id` decides whether a subagent is acting at all, `agent_type` names which definition
  to read the declared skills out of. Codex spells both the same way.
- Claude Code's `SessionStart` also echoes a second, fixed text beside the gate text: the subagent supervision rule.
  It tells the main thread to note how long each background subagent should take, check every running one every 10
  minutes against that estimate, and step in only when one is far over or clearly looping. It is plain context with
  no script behind it, so it cannot deny anything, and no other wiring carries it. The global install in
  [docs/GLOBAL_SETUP.md](docs/GLOBAL_SETUP.md) and [sandbox-agent/setup-global.sh](sandbox-agent/setup-global.sh)
  carry the same entry, word for word.
- Every hook runs on `-S -E`, under an interpreter each wiring resolves for itself: `python3` first, then
  `python`, which is the name the python.org installer puts on a Windows path and usually the only one it puts
  there. Debian 11 and Ubuntu 20.04 onward ship no `/usr/bin/python` unless `python-is-python3` is installed, so a
  wiring that hardcoded either name alone was inert on one platform or the other. Both flags are safe because every
  hook is standard library only, and they take a slice off an interpreter start that the gate pays on every single
  tool call. The plugin tries `python3`, then `python`, and keeps the first one that answers a one-line probe, so a
  Windows Store alias that exists under either name but runs nothing is skipped rather than chosen.
- No hook uses `argparse`, which exits 2 on a usage error. Two is the deny code in the plain format, so a stray flag
  would read as a block. Each hook scans `sys.argv` by hand instead and treats an unknown flag as an allow.
- Only Claude Code has task events, and none of the three agents has a task-updated event, so
  [.agents/hooks/task_list_sync.py](.agents/hooks/task_list_sync.py) writes only `open` and `done`. The model sets
  `in progress` and `blocked` by editing `tasks.md`, which is why Rule A exempts that one path.
- No agent delivers `additionalContext` out of a pre-compact event today. The `PreCompact` wiring above is against a
  future, and what actually carries the task list through a compaction is `SessionStart` firing again with `source`
  set to `compact`. Per-surface detail is in [docs/hooks-contract.md](docs/hooks-contract.md).
- Every wiring anchors the gate at the project root, and a missing gate script allows. A session started in a
  subdirectory resolved the relative script path to nothing, and Python exits 2 when it cannot open the file it was
  handed, which is the deny code on Claude Code and Codex and denies on Copilot too. Each wiring therefore moves to the
  project root first: `${CLAUDE_PROJECT_DIR}` on Claude Code, `git rev-parse --show-toplevel` on Codex, `"cwd": "."` on
  Copilot, the runtime's `worktree` in the plugin. The claude, codex and copilot formats deny with exit 0 and JSON on
  stdout and never use a non-zero exit, so forcing a zero exit on those three turns any error back into an allow. Codex
  and Copilot each carry a separate command field per shell, so they spell it per shell: `|| exit 0` wherever a POSIX
  shell runs the line, `; exit 0` in Codex's `commandWindows` and in Copilot's `powershell` field. Codex 0.156.1 runs
  `commandWindows` under `pwsh`, then `powershell.exe`, then `cmd`, whichever it finds first, a PowerShell with
  `-NoProfile -Command` and `cmd` with `/c` (`get_powershell_shell` in `codex-rs/shell-command/src/shell_detect.rs`
  and `derive_exec_args` in `codex-rs/core/src/shell.rs`, tag `rust-v0.156.1`). Windows PowerShell 5.1 has no `||`
  operator at all, so a `|| exit 0` there is a parse error rather than a fallback. Claude Code has one command field,
  written as POSIX shell and ended with `; exit 0` (see the next point for which shell runs it). The plugin cannot
  force a zero exit at all, because its plain format does use exit 2 as the denial, so it reads each hook file before spawning it and drops
  the ones it cannot open.
- Claude Code runs every command hook in shell form: "The `command` string is passed to a shell: `sh -c` on macOS and
  Linux, Git Bash on Windows, or PowerShell when Git Bash isn't installed"
  (`https://code.claude.com/docs/en/hooks#exec-form-and-shell-form`). Measured on Claude Code 2.1.281, Windows 11 with
  Git Bash installed: a probe hook ran under bash 5.3.9. Every Claude command here is POSIX shell (`PY=$(...)`,
  `"${CLAUDE_PROJECT_DIR}"`), and `pwsh -Command` rejects it with a parse error and exit 1, which Claude Code treats
  as a non-blocking error. On Windows without Git Bash every Claude hook therefore allows and nothing is gated, so the
  setup docs require Git for Windows there. Exec form (`args`) would avoid the shell, but it cannot fall back from
  `python3` to `python` or force a zero exit, and a missing script would then exit 2 and deny.
- Claude Code's `PreToolUse` command calls the gate directly, with no wrapper and no redirect:
  `preflight_gate.py` swaps `sys.stderr` for a null sink for the call and restores it in a `finally`. The `plain`
  format that OpenCode and Kilo Code use still writes its deny message to standard error, so that deny channel is
  unaffected. Codex and Copilot keep the per-shell redirects their variant fields let them write.
- The Claude Code matcher names `PowerShell` beside `Bash`. The hooks reference says of the PowerShell tool: "On
  Windows, wherever the PowerShell tool is enabled, Claude treats PowerShell as the primary shell and routes shell
  commands through it" and "A hook that matches only `Bash` never fires there"
  (`https://code.claude.com/docs/en/hooks#powershell`). Its payload is `tool_name: "PowerShell"` with the command in
  `tool_input.command`, measured on 2.1.281, and the gate already reads that as a PowerShell command. `MultiEdit` is
  matched as well, because the gate treats it as an edit tool, though the current tools reference no longer lists it.
- Codex supports both inline `[[hooks.*]]` tables and a separate `hooks.json`, and warns when a single configuration
  layer carries both. The tables therefore live in `.codex/config.toml` and `.codex/hooks.json` no longer exists.
  Every Windows command in those tables is PowerShell: the gate text is `echo '<json>'; exit 0`, and each script hook
  moves to `git rev-parse --show-toplevel` with `Set-Location -LiteralPath` before it runs, then ends in
  `2>$null; exit 0`. Before that fix every `commandWindows` value failed to parse in PowerShell, so no Codex hook ran
  on Windows at all.
- Copilot hooks are no longer CLI-only. They run in VS Code and in JetBrains as well, from the same `.github/hooks/`
  path. Event names are camelCase, and a hook entry carries `bash` and `powershell` as sibling string fields next to
  `type`, not a nested `command` object. A nested one is silently ignored, which leaves that surface ungated.
- The Copilot CLI additionally reads hooks from `.claude/settings.json`. The JetBrains plugin does not: its bundled
  agent hardcodes `.github/hooks/**/*.json` and rejects PascalCase event names. The borrowed Claude gate wiring does fire
  on the CLI. Measured on Copilot CLI 1.0.81 in the sandbox image: it maps its own tool names to Claude's (`create`
  reaches the hook as `Write`), and hands the hook a Claude-shaped payload (`hook_event_name`, `session_id`, an ISO
  `timestamp`, `cwd`, `tool_name`, `tool_input`) that carries no `agent_id` for a subagent and a main thread alike. Read
  as Claude Code's, that absence named every caller the main thread, so live run 36155485254 denied the docs-architect
  subagent's own write under Rule A. The CLI sets `COPILOT_CLI=1` in the hook's environment, and the gate reads a
  claude-format call carrying it as an unknown caller, the same verdict
  [.github/hooks/preflight.json](.github/hooks/preflight.json) gets on that surface. Do not widen the Claude pattern
  to Copilot's tool names: the CLI reads both files, so the gate already runs twice on every mapped tool call. `SubagentStart` takes no matcher either, and the hooks reference accepts a PascalCase event name
  in its "VS Code compatible format", so the CLI may deliver the subagent text twice, once from each file. The text
  is identical and this is not measured, because Copilot is not installed here. `Stop` and `SubagentStop` take no
  matcher, so those two do run on the CLI, with Copilot's
  snake_case payload. `no_ai_markers_check.py` stays silent on a claude-format `Stop` payload in the shape the hooks
  reference documents for it (`stop_reason` present, `timestamp` an ISO 8601 string, no `last_assistant_message`),
  so the reply is checked once, from `agentStop`. A Claude Code `Stop` carries `last_assistant_message` and is always
  checked.
- The JetBrains plugin scans `.claude/agents`, but it only understands its own `*.agent.md` format, so subagent
  definitions cannot be shared between Copilot and Claude Code or OpenCode.
- The formatting checker fixes what it can on every surface that can rewrite the display, and blocks only on what is
  left, so the user is never asked to read a correction of a slip they did not see. Claude Code's `MessageDisplay`
  (2.1.152 or later, verified on 2.1.281) replaces the text on screen only and records, per session and message id,
  every line it changed. Its `Stop` runs with `--display-fixed`, which skips a fixable marker only on a line that
  record names and checks the whole reply when there is no record. OpenCode and Kilo Code store the fixed text part
  through `experimental.text.complete`, which the plugin hands only to hooks that declare `HOOK_TEXT_EVENT = True`.
  Codex and Copilot have no display hook, so their stop events keep the full check. A block forces another turn, so
  the check honours `stop_hook_active` and Copilot's `stopHookActive`, and a per-session counter allows the next stop
  after a block even when neither flag arrives. Copilot's `agentStop` reads the reply
  from the undocumented `transcriptPath` file and allows whatever it cannot parse, and Copilot is not installed here,
  so that path is verified by the hooks reference and the unit tests only. Detail and quotes are in
  [docs/hooks-contract.md](docs/hooks-contract.md).
- OpenCode and Kilo Code have no event that can block a finished reply, so their plugin runs every check at
  `tool.execute.before`. It is a runner rather than a fixed wiring: on every tool call it discovers every hook in
  the project's [.agents/hooks/](.agents/hooks/), or in `~/.agents/hooks/` when the project has no such directory
  and holds no `.agents/no-global-hooks` opt-out file, runs them in the order each hook declares, and hands each one
  a versioned JSON envelope on standard input with `--format plain`. Adding a hook file is the whole registration
  step. The contract, including the envelope fields, the ordering rule, the deny exit code, and the fail-open rules,
  is written up in [docs/hooks-contract.md](docs/hooks-contract.md).
- OpenCode and Kilo Code name no caller on `tool.execute.before`, whose input is only `tool`, `sessionID` and
  `callID`. The plugin reads the session with `client.session.get`: a session with a `parentID` is a subagent's child
  session and sends `is_subagent: true`, one without is the main thread and sends `false`, and a lookup that fails
  leaves the field out so the gate allows. The answer is cached per session. `agent_type` is the agent named on the
  newest session message (`build` or `code` on the main thread, `general` or the subagent's own name in a child), never
  the session id. Measured on OpenCode 1.18.32 and Kilo Code 7.7.9: a main-thread write was denied, a `general`
  subagent write was allowed, and each lookup took 7 to 57 ms.
- The plugin spawns each hook asynchronously with its own 10 second timer. `spawnSync` under the Bun runtime both tools
  ship returned `ETIMEDOUT` within 100 ms on most tool calls after the first on Windows, which skipped the gate on those
  calls and let main-thread writes through.
- OpenCode and Kilo Code get the gate text on every main-thread prompt from the plugin's `chat.message` handler, a
  stable hook in both tools. It appends the reminder to the user message as a synthetic text part, which the runtime
  saves and sends to the model with the prompt. The handler also fires for the task prompt a subagent receives in its
  child session, so it places the session first, with the same cached `client.session.get` lookup the gate uses: a
  session with no `parentID` gets the reminder, a child session gets the subagent text, and a session the lookup
  cannot read gets nothing. Before that, OpenCode 1.18.32 with `opencode-go/gpt-6-luna` handed the reminder to a
  `docs-architect` subagent, which then refused to write because the main agent must delegate, three runs out of
  three. Removing the reminder from the child session alone was not enough: the subagent still called itself the main
  session and refused. With the subagent text, three isolated runs out of three had the subagent write the file with
  `apply_patch` and the main thread write nothing.
- Every wiring that can reach a subagent injects the subagent text and never the reminder: Claude Code and Codex on
  `SubagentStart`, Copilot on `subagentStart`, the plugin in a child session. Claude Code documents `additionalContext`
  on `SubagentStart` as "String added to the subagent's context at the start of its conversation, before its first
  prompt" (`https://code.claude.com/docs/en/hooks#subagentstart`), and Copilot documents that on `subagentStart`
  "`additionalContext` is prepended to the subagent's prompt"
  (`https://docs.github.com/en/copilot/reference/hooks-reference`). Copilot's built-in `general-purpose` agent emits no
  `subagentStart`, per the same page. Claude Code's hooks reference names tool events as the ones that fire inside a
  subagent, so its `UserPromptSubmit` and `SessionStart` reminder is not expected to reach one, which is read from the
  reference and not measured. Copilot's `userPromptTransformed` fires for a "submitted prompt", and the reference does
  not say whether a subagent's prompt counts, so whether the reminder also reaches a Copilot subagent that way is
  unverified.
- Copilot gets the gate text on every prompt from `userPromptTransformed`, which runs
  [.agents/hooks/copilot/prompt_reminder.py](.agents/hooks/copilot/prompt_reminder.py). The hook appends the reminder
  to the `transformedPrompt` field and returns it as `modifiedTransformedPrompt`, per
  `https://docs.github.com/en/copilot/reference/hooks-reference`. It sits in a subdirectory because the OpenCode and
  Kilo Code runner discovers only the files directly in `.agents/hooks/`, so a helper one agent wires by path never
  costs the other two an interpreter start per tool call. That is the documented opt-out in
  [docs/hooks-contract.md](docs/hooks-contract.md), and it keeps a new top-level file the whole registration step.
- The unit tests and the containerised sandbox prove what each agent discovers. What proves the wiring against a real
  model is [sandbox-agent/live/](sandbox-agent/live/), one script per agent over a shared
  [sandbox-agent/live/lib.sh](sandbox-agent/live/lib.sh), run by the manual live workflow described under Repo
  conventions. Test 1 counts any gate denial as the block, whichever rule gave it: the harness reads the fixed text
  of every `RULE_*_REASON` out of the gate itself, so a new rule needs no harness change, and a probe file that
  landed is a failure whatever the transcript says. Test 2 also reads the subagent's own transcript, through the
  `agent_subagent_context` function each agent script supplies, and fails unless it carries the subagent text
  (`PREFLIGHT for a subagent:`) and not the main-thread reminder. On GitHub Copilot, test 1 reports `KNOWN-GAP`
  rather than `FAIL`, because the Copilot payload carries no agent identifier and the gate cannot tell its main
  thread from a subagent (see Maintenance follow-ups). That expectation is `GATE_KNOWN_GAP=1` in
  [sandbox-agent/live/copilot.sh](sandbox-agent/live/copilot.sh). Remove that expectation, by setting it to `0` as
  every other agent script does, in the same change that removes the matching Maintenance follow-up, once the payload
  carries an agent identifier.

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
- [.agents/hooks/](.agents/hooks/) and [.agents/plugin/](.agents/plugin/) are invoked by every adapter. The Python
  scripts hold the only copy of the gate logic, of the response formatting check, of the markdown lint pass that runs
  after an edit, of the task-list mirror, and of Copilot's per-prompt reminder. The plugin is a thin runner with no
  rules of its own that hands every OpenCode and Kilo Code tool call to every hook directly in that directory, and it carries
  the reminder wording for its own `chat.message` handler.

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
- **Never hand-edit generated subagent files.** Edit `subagents/<name>.md`, then run the generator. CI fails if the
  generated trees drift from canonical.
- **Markdown lint.** `README.md`, `AGENTS.md.example`, `docs/*.md`, `.agents/skills/**/*.md`, and the canonical
  `subagents/*.md` must contain no em-dashes or en-dashes, no prose line over 120 characters, and no level-2 heading.
  The four generated subagent trees are out of scope, because linting them would report the same violation five
  times. This real `AGENTS.md` is not in the lint scope either, but match the style anyway. The same pass also
  validates front matter on every `.agents/skills/<name>/SKILL.md` and every `subagents/<name>.md`: the block has to
  parse as YAML, carry a `name` matching the folder name or the file stem, carry a non-empty string `description` of
  at most 1024 characters that is quoted whenever it holds a colon, and, on a skill, carry no key beyond the five the
  Agent Skills specification defines.
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
  injected wording identical in every wiring file that injects it, including the `REMINDER` constant in
  [.agents/plugin/hooks.js](.agents/plugin/hooks.js), which
  [tools/tests/test_prompt_reminder.py](tools/tests/test_prompt_reminder.py) compares, line breaks included, against
  the canonical block above.
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
- **[.github/workflows/agent-live-tests.yml](.github/workflows/agent-live-tests.yml) is a separate workflow and never
  part of CI.** Its only trigger is `workflow_dispatch`, so no push and no pull request ever starts it. It needs the
  `REQUESTY_API_KEY` repository secret, because it drives each agent against a real model through Requesty, and
  every run spends money on that key. Start it only with the user's explicit approval for that one run.

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
  The front matter carries `name` and `description` and nothing else beyond an optional `license` or `compatibility`,
  per the open Agent Skills specification (`https://agentskills.io/specification`). Write the description in trigger
  form: what the skill covers, then the phrases a user would actually say, then what it is not for and which skill
  owns that instead. Keep the manifest short and push depth into `references/`, and prefer one hub with a reference
  file per topic over a family of sibling skills. Bump the skill-count badge in [README.md](README.md).
- **A subagent:** add or edit `subagents/<name>.md`, run the generator, and commit the canonical source and the four
  generated trees together. Every name in the `skills` list has to have a folder under `.agents/skills/`, or the
  generator exits naming the dangling entries, and the same check rejects an unknown tool name or an unknown model.
  A `tools` list of exactly `read`, `grep` and `glob` also earns `permissionMode: plan` on Claude Code, and
  `model: inherit` leaves the agent on whatever the session already runs. `subagents/*.md` is inside the markdown
  lint scope, so the file has to pass `python tools/check-markdown.py` too. Bump the subagent-count badge.
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

- **Kilo Code is settled, no action outstanding.** Kilo reads `.agents/skills/` natively, so it needs no skill symlink.
  Its subagent tree is the `.kilo/agents` symlink to `../.agents/agents`, which the generator creates and repairs, so
  there is nothing per-Kilo to generate. It accepts the root `opencode.json` for MCP servers and for the plugin
  declaration, and `.kilocode/` is deleted. No `.kilo/kilo.jsonc` ships, because Kilo needs no per-tool copy of
  anything once the shared file carries no substitution tokens. The one live constraint, that a `{env:VAR}` anywhere
  in project config makes Kilo reject the whole file, is recorded under Repo conventions rather than here.
- **GitHub Copilot per-prompt injection is wired, and documented only for the CLI and the cloud agent.**
  [.github/hooks/preflight.json](.github/hooks/preflight.json) runs `copilot/prompt_reminder.py` on
  `userPromptTransformed`.
  The hooks reference (`https://docs.github.com/en/copilot/reference/hooks-reference`) documents that event for the
  Copilot CLI and the cloud agent and says nothing about VS Code or JetBrains. Confirm that both IDEs fire it, or at
  least tolerate the entry, and record the result here.
- **The Copilot `preToolUse` payload carries no agent identifier, and its wiring never passes `--subagent` either.**
  There is no `agent_id` or equivalent field in Copilot's own payload, and
  [.github/hooks/preflight.json](.github/hooks/preflight.json) never sets `--subagent` on the `preToolUse` call, so
  [.agents/hooks/preflight_gate.py](.agents/hooks/preflight_gate.py) cannot tell a Copilot subagent from the Copilot
  main thread. Caller identity resolves to unknown on every call, so neither Rule A, Rule B, nor Rule C ever fires on
  this surface: the whole surface is unenforced, which fails in the unsafe direction rather than the safe one.
  Recheck the hooks reference for an agent identifier and pass it through with `--subagent` when one lands, and in
  the same change set `GATE_KNOWN_GAP=0` in [sandbox-agent/live/copilot.sh](sandbox-agent/live/copilot.sh) so live
  test 1 has to pass there.
- **Codex now runs the formatting check, and the markdown lint has nowhere to go there.** `.codex/config.toml` wires
  `no_ai_markers_check.py` on `Stop`, so Codex is no longer a surface where the reply goes unchecked. Whether Codex's
  `Stop` can actually reject a reply the way Claude Code's can is not verified, so nothing in the docs claims it: they
  say the check runs. Confirm it against the Codex hooks reference and say so plainly once it is measured. The
  markdown lint in `markdown_lint_check.py` stays Claude-only in the meantime, because Codex exposes no post-tool
  event to hang it on. OpenCode and Kilo Code get both hooks for free, since their plugin runs every file in
  [.agents/hooks/](.agents/hooks/) on every tool call.
- **JetBrains Copilot MCP is global-only and officially undocumented.** The plugin reads MCP from
  `~/.config/github-copilot/intellij/mcp.json`. There is no per-project MCP file, and GitHub documents only the in-IDE
  UI rather than the path, so no JetBrains MCP file ships here. Recheck whether GitHub adds a documented per-project
  path (`https://docs.github.com/en/copilot/how-tos/provide-context/use-mcp/extend-copilot-chat-with-mcp`) and ship one
  if it lands.
