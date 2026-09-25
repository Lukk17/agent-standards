# Global setup

Install the shared agent configuration once into your home directory so every project on the machine gets it, even the
ones that never ran the per-project import.

This is the counterpart to the per-project import in [AGENT_TOOLING.md](AGENT_TOOLING.md). The two are additive rather
than exclusive: an agent reads both scopes and merges them, so a project that also ran the per-project import keeps
winning on the paths where both scopes define the same thing.

One folder in your home directory, `~/.agents`, holds everything the agents can share: the skills, the OpenCode-format
subagents, the hook scripts and the OpenCode and Kilo Code plugin. Each agent then either reads that folder on its own
or reaches it through one link or one config line. No copy of this repository stays in your home directory: the install
and every update fetch a temporary copy, take what they need out of it, and delete it.

Every command below comes in a PowerShell version and a Unix-shell version. Take only the sections for the agents you
actually run. On Windows, `~` and `$HOME` both mean `%USERPROFILE%`, so `~/.agents` is `C:\Users\<you>\.agents`.

---

### What each agent shares and what stays per tool

| What | Claude Code | Codex | OpenCode | Kilo Code | GitHub Copilot |
| --- | --- | --- | --- | --- | --- |
| Always-on instructions | `~/.claude/CLAUDE.md`, the one main file | `~/.codex/AGENTS.md`, a link to `~/.claude/CLAUDE.md` | falls back to `~/.claude/CLAUDE.md` on its own | `instructions` in `~/.config/kilo/kilo.jsonc` points at `~/.claude/CLAUDE.md` | `~/.copilot/copilot-instructions.md`, a link of its own to `~/.claude/CLAUDE.md` |
| Skills | `~/.claude/skills`, a link to `~/.agents/skills` | reads `~/.agents/skills` natively | reads `~/.agents/skills` natively | reads `~/.agents/skills` natively | reads `~/.agents/skills` natively |
| Subagents | own format in `~/.claude/agents` | own TOML format in `~/.codex/agents` | `~/.config/opencode/agents`, a junction or link to `~/.agents/agents` | `~/.config/kilo/agents`, a junction or link to `~/.agents/agents` | own `*.agent.md` format in `~/.copilot/agents` |
| Hook scripts | shared, `~/.agents/hooks` | shared, `~/.agents/hooks` | shared, `~/.agents/hooks` | shared, `~/.agents/hooks` | shared, `~/.agents/hooks` |
| Hook wiring | `hooks` in `~/.claude/settings.json` | `~/.codex/hooks.json` | the shared plugin, declared by path in `~/.config/opencode/opencode.json` | the same shared plugin, declared by path in `~/.config/kilo/kilo.jsonc` | `~/.copilot/hooks/preflight.json` |
| MCP servers | `~/.claude.json`, written by `claude mcp add` | `[mcp_servers.*]` in `~/.codex/config.toml` | `mcp` in `~/.config/opencode/opencode.json`, or one shared file | `mcp` in `~/.config/kilo/kilo.jsonc`, or the same shared file | `~/.copilot/mcp-config.json`, VS Code user `mcp.json`, JetBrains `mcp.json` |

So there are four subagent trees rather than six. OpenCode and Kilo Code read the same OpenCode-format files, so both
link to `~/.agents/agents`. Claude Code, Codex and Copilot each need their own format, for these reasons:

- Claude Code skips a subagent file with no `name` key, and the OpenCode format has none. Its documentation says a
  file with "No `name`" is treated "as documentation kept beside your agents"
  ([sub-agents docs](https://code.claude.com/docs/en/sub-agents)). The OpenCode format also writes `tools` as a map
  where Claude Code expects a list, and carries no `skills` list, so the skills a subagent preloads would be lost even
  if the file loaded. Measured with Claude Code 2.1.281 in a throwaway configuration directory: an `agents` junction to
  the OpenCode tree loaded none of the 25 subagents, and the same junction to the Claude tree loaded all 25.
- The reverse does not work either. OpenCode 1.18.32 rejected its whole configuration on the first Claude-format file
  ("Configuration is invalid"), and Kilo Code 7.7.9 skipped all 25 of them.
- Codex reads subagents only as "standalone TOML files under `~/.codex/agents/`"
  ([subagents docs](https://learn.chatgpt.com/codex/agent-configuration/subagents)).
- Copilot takes `tools` as a "list of strings, string" and stores personal agents in `~/.copilot/agents` "as
  `.agent.md` files"
  ([custom agents reference](https://docs.github.com/en/copilot/reference/custom-agents-configuration),
  [CLI config dir reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference)).
  The OpenCode `tools` map does not fit that. The Copilot CLI was not installed on the machine this was checked on, so
  this row rests on the documentation alone.

None of the five documents a setting that moves its global subagent directory. OpenCode has `OPENCODE_CONFIG_DIR`, but
that is an environment variable that also loads plugins, skills and commands from the directory it names, so a link is
the smaller change.

OpenCode and Kilo Code can share one MCP server list, but not by reading each other's file. Kilo Code "no longer falls
back to opencode configuration stored in .opencode directories (such as ~/.config/opencode ...)"
([Kilo CLI docs](https://kilo.ai/docs/code-with-ai/platforms/cli)). What both do support is a custom config file named
by an environment variable, `OPENCODE_CONFIG` for OpenCode ([config docs](https://opencode.ai/docs/config/)) and
`KILO_CONFIG` for Kilo Code, which Kilo lists as trusted config where `{env:VAR}` resolves. A file holding only an
`mcp` block, named by both variables, is the one list both read. OpenCode 1.18.32 and Kilo Code 7.7.9 both showed a
server from such a file in `debug config`, each run in a throwaway home.
[Share one MCP list between OpenCode and Kilo Code](#share-one-mcp-list-between-opencode-and-kilo-code) has the
commands.

---

### Prerequisites

You need `git`, and Python 3 for the hooks. Every script under `~/.agents/hooks/` is Python, and every wiring throws a
failed call away so a broken hook can never break a session, so a missing interpreter does not error: it allows every
call the gate was meant to block. Confirm one answers before you rely on any of it. PowerShell:

```powershell
python --version
```

Unix shell:

```bash
python3 --version
```

On Windows, link a directory with a junction. `New-Item -ItemType Junction` needs no Developer Mode and no elevated
shell, and every agent in this document followed one when it was measured: Claude Code 2.1.281 loaded skills and
subagents through a junction, and OpenCode 1.18.32 and Kilo Code 7.7.9 loaded subagents through one. A file link,
such as `~/.codex/AGENTS.md`, has to be a symbolic link instead, and on Windows that needs Developer Mode, in Settings,
System, For developers. Claude Code's own documentation says the same about symlinking `CLAUDE.md`
([memory docs](https://code.claude.com/docs/en/memory)).

If you run the Unix-shell blocks under Git Bash on Windows, tell the MSYS runtime to make real symlinks first, because
that is not its default. Put this in the session before you start, or in your `~/.bashrc`:

```bash
export MSYS=winsymlinks:nativestrict
```

Without that setting `ln -s` silently copies the target, so a link becomes a stale snapshot and an update stops
reaching it.

WSL works too, but inside WSL `$HOME` is the Linux home, so the install lands there and a Windows-side agent never sees
it. Use WSL only if the agents you run are the ones inside it.

---

### Step 1, a temporary copy of the repository

Clone into your temporary directory, not your home directory. The copy lives only as long as the install. PowerShell:

```powershell
$src = Join-Path ([IO.Path]::GetTempPath()) 'agent-standards'
```

```powershell
git clone --filter=blob:none https://github.com/Lukk17/agent-standards.git $src
```

Unix shell:

```bash
src="$(mktemp -d)/agent-standards"
```

```bash
git clone --filter=blob:none https://github.com/Lukk17/agent-standards.git "$src"
```

The clone is blobless, so file contents come down only for the commit you check out. Keep the same shell open until
the install is finished, because every later block reads `$src`.

---

### Step 2, the one shared folder

Create `~/.agents`. PowerShell:

```powershell
New-Item -ItemType Directory -Force $HOME\.agents
```

Unix shell:

```bash
mkdir -p ~/.agents
```

Copy the four shared trees into it: `skills/`, the OpenCode-format `agents/`, the `hooks/` scripts, and the `plugin/`
runner. PowerShell:

```powershell
foreach ($d in 'skills', 'agents', 'hooks', 'plugin') { Copy-Item -Recurse -Force "$src\.agents\$d" "$HOME\.agents\" }
```

Unix shell:

```bash
for d in skills agents hooks plugin; do cp -R "$src/.agents/$d" ~/.agents/; done
```

Copy the updater into `~/.agents/bin`. It is the one command
[Updating the global installation](#updating-the-global-installation) runs, and every update keeps it current.
PowerShell:

```powershell
Copy-Item -Recurse -Force "$src\global\bin" "$HOME\.agents\"
```

Unix shell:

```bash
cp -R "$src/global/bin" ~/.agents/
```

Delete what you do not want before you go on. A skill folder or a subagent file you remove now stays removed, because
the update below refreshes only what you already have and never adds anything.

Record which commit you installed, so the update can tell which files upstream removed since and what changed in the
hook wiring. PowerShell:

```powershell
git -C $src rev-parse HEAD | Set-Content $HOME\.agents\.upstream-commit
```

Unix shell:

```bash
git -C "$src" rev-parse HEAD > ~/.agents/.upstream-commit
```

`preflight_gate.py` guards only the project a session is open in and never your home directory at large: it takes the
project root from the hook payload's own `cwd` field and from the working directory, and it ignores its own on-disk
location once that location is your home directory rather than a project.

Three of the hook scripts get wired per agent below. `markdown_lint_check.py` does not: it shells out to
`tools/check-markdown.py`, which stays in the upstream repository, so a global wiring would start an interpreter that
returns 0 every time. It is copied anyway, because the copy is one directory rather than a file list.

`task_list_sync.py` mirrors the agent's own task list into a file named `tasks.md` so a compaction cannot lose it. It
writes that file at the project root when the working directory has an imported `.agents/hooks/` beside it, and in
your home directory when it does not. Add `tasks.md` to your global gitignore if you would rather it never showed up as
an untracked file.

---

### Step 3, the always-on instructions

`~/.claude/CLAUDE.md` is the one instruction file. Claude Code reads it natively, OpenCode falls back to it, and the
other three are pointed at it in their sections below. If you have none yet, start from `AGENTS.md.example` in the
temporary copy and cut the project-specific sections, keeping the parts about how you work everywhere. PowerShell:

```powershell
New-Item -ItemType Directory -Force $HOME\.claude
```

Unix shell:

```bash
mkdir -p ~/.claude
```

Copy the template, only when you have no `CLAUDE.md` yet. PowerShell:

```powershell
if (-not (Test-Path $HOME\.claude\CLAUDE.md)) { Copy-Item "$src\AGENTS.md.example" $HOME\.claude\CLAUDE.md }
```

Unix shell:

```bash
[ -e ~/.claude/CLAUDE.md ] || cp "$src/AGENTS.md.example" ~/.claude/CLAUDE.md
```

---

### Per-agent setup

Every subsection assumes steps 1 to 3 are done. Adding a second agent later is nothing more than running its
subsection too, because the shared folder is the same files.

#### Claude Code

Claude Code reads its personal skills from `~/.claude/skills/<skill-name>/SKILL.md`
([skills docs](https://code.claude.com/docs/en/skills)), so the shared skills reach it through one directory link.
Personal subagents live in `~/.claude/agents/` ([sub-agents docs](https://code.claude.com/docs/en/sub-agents)), user
hooks in `~/.claude/settings.json`, and personal instructions in `~/.claude/CLAUDE.md`
([memory docs](https://code.claude.com/docs/en/memory)).

Link the skills. PowerShell:

```powershell
New-Item -ItemType Junction -Path $HOME\.claude\skills -Target $HOME\.agents\skills
```

Unix shell:

```bash
ln -s ~/.agents/skills ~/.claude/skills
```

Copy the Claude-format subagents. This is one of the three trees that cannot be shared, see the table at the top.
PowerShell:

```powershell
Copy-Item -Recurse -Force "$src\.claude\agents" $HOME\.claude\
```

Unix shell:

```bash
cp -R "$src/.claude/agents" ~/.claude/
```

Wire the hooks into `~/.claude/settings.json`. Hooks in that file apply to every project on the machine
([hooks docs](https://code.claude.com/docs/en/hooks)). Replace every absolute path with your real home directory.
Forward slashes work on Windows too and save you escaping backslashes inside JSON.

This is the same event set the per-project wiring uses, minus the markdown lint pass. `SessionStart` and
`UserPromptSubmit` inject the gate text, `SessionStart` also injects the rule for checking on background subagents
every 10 minutes, `SubagentStart` tells a subagent to do its delegated task itself rather than hand it on,
`PreToolUse` is the blocking half, `MessageDisplay` fixes dashes, bold and italic on
screen (Claude Code 2.1.152 or later), `Stop` checks what that fix leaves and `SubagentStop` checks the whole reply,
and the five task events keep `tasks.md` in step. Each command resolves its own interpreter, `python3`
first and `python` second, because Debian and Ubuntu ship no `python` and the python.org Windows installer ships
no `python3`. `-S -E` skips site initialisation and ignores the
`PYTHON*` environment variables, which is safe because every hook is standard library only and saves a slice of
interpreter start on every single tool call. The trailing `; exit 0` is what turns a missing or broken hook back into
an allow. Every command is POSIX shell, because Claude Code passes a command hook "to a shell: `sh -c` on macOS and
Linux, Git Bash on Windows, or PowerShell when Git Bash isn't installed"
([hooks docs](https://code.claude.com/docs/en/hooks)). Claude Code 2.1.281 on Windows 11 with Git Bash installed ran a
probe hook under bash 5.3.9. On a Windows machine without Git Bash, PowerShell rejects these commands with a parse error
and exits 1, which Claude Code treats as a non-blocking error, so every hook allows and nothing is gated. Install Git
for Windows before relying on the gate there.

The `PreToolUse` matcher names `PowerShell` beside `Bash` because Claude Code on Windows routes shell commands through
its PowerShell tool whenever that tool is on, and the docs say "a hook that matches only `Bash` never fires there"
([hooks docs](https://code.claude.com/docs/en/hooks#powershell)).

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo 'PREFLIGHT: before code work, name the skills and subagents that own this task and invoke them, or say none apply and why. Delegate investigation, review and bounded implementation by default. Follow the user-communication skill when writing to the user. If the prompt asks anything, answer every question first, then start the work. End every reply to the user with this block, exactly as shown: no heading, no bullets, no numbered list, plain lines only, keeping every blank line:\n\nRunning: `running task name` (or: nothing)\n\n~~DONE: older finished task~~\n~~DONE: most recent finished task~~\n\n**NOW: what is being done right now**\n\nNext: the next task\nThen: the task after that\n\nWaiting on: what you wait for (or: nothing)\n\nWhen several tasks run, list each name in backticks on the Running line, separated by commas.'"
          },
          {
            "type": "command",
            "command": "echo 'When you launch a background subagent, note how long its task should take and schedule a recurring check every 10 minutes while any subagent runs. At each check compare its running time and latest output with that expectation. Leave it alone unless it is far over (for example 30 minutes on a task that should take 1) or clearly looping, then ask it for status or stop it and tell the user why.'"
          },
          {
            "type": "command",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.agents/hooks/task_list_sync.py --event sessionstart --format claude ; exit 0"
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo 'PREFLIGHT: before code work, name the skills and subagents that own this task and invoke them, or say none apply and why. Delegate investigation, review and bounded implementation by default. Follow the user-communication skill when writing to the user. If the prompt asks anything, answer every question first, then start the work. End every reply to the user with this block, exactly as shown: no heading, no bullets, no numbered list, plain lines only, keeping every blank line:\n\nRunning: `running task name` (or: nothing)\n\n~~DONE: older finished task~~\n~~DONE: most recent finished task~~\n\n**NOW: what is being done right now**\n\nNext: the next task\nThen: the task after that\n\nWaiting on: what you wait for (or: nothing)\n\nWhen several tasks run, list each name in backticks on the Running line, separated by commas.'"
          }
        ]
      }
    ],
    "SubagentStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo '{\"hookSpecificOutput\": {\"hookEventName\": \"SubagentStart\", \"additionalContext\": \"PREFLIGHT for a subagent: you are a subagent, and the main thread delegated this task to you. Do the work yourself with your own tools and load the skills your definition names. The rules that the main thread must delegate and may not write files apply to the main thread only, so do not hand this task on and do not refuse it for that reason. The preflight gate still checks every tool call you make. Report back what you changed and how you verified it.\"}}'"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "^(Edit|Write|MultiEdit|NotebookEdit|Bash|PowerShell|WebFetch|WebSearch)$",
        "hooks": [
          {
            "type": "command",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.agents/hooks/preflight_gate.py --format claude ; exit 0"
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.agents/hooks/task_list_sync.py --event precompact --format claude ; exit 0"
          }
        ]
      }
    ],
    "TaskCreated": [
      {
        "hooks": [
          {
            "type": "command",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.agents/hooks/task_list_sync.py --event taskcreated --format claude ; exit 0"
          }
        ]
      }
    ],
    "TaskCompleted": [
      {
        "hooks": [
          {
            "type": "command",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.agents/hooks/task_list_sync.py --event taskcompleted --format claude ; exit 0"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.agents/hooks/no_ai_markers_check.py --format claude --display-fixed ; exit 0"
          },
          {
            "type": "command",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.agents/hooks/task_list_sync.py --event stop --format claude ; exit 0"
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          {
            "type": "command",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.agents/hooks/no_ai_markers_check.py --format claude ; exit 0"
          }
        ]
      }
    ],
    "MessageDisplay": [
      {
        "hooks": [
          {
            "type": "command",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.agents/hooks/no_ai_markers_check.py --format claude --display ; exit 0"
          }
        ]
      }
    ]
  }
}
```

If you already have a `~/.claude/settings.json`, merge the `hooks` block into it rather than overwriting the file.

MCP at user scope is stored in `~/.claude.json`, and the supported way to write it is the CLI rather than hand-editing
([MCP docs](https://code.claude.com/docs/en/mcp)). One server per command, so add only the ones that genuinely are
machine-wide. PowerShell:

```powershell
claude mcp add --transport http context7 --scope user https://mcp.context7.com/mcp
```

Unix shell:

```bash
claude mcp add --transport http context7 --scope user https://mcp.context7.com/mcp
```

#### Codex

Codex scans `$HOME/.agents/skills` for skills natively and follows symlinked skill folders while scanning
([build skills](https://learn.chatgpt.com/codex/build-skills)), so step 2 finished the skills job.

Create the configuration directory. PowerShell:

```powershell
New-Item -ItemType Directory -Force $HOME\.codex
```

Unix shell:

```bash
mkdir -p ~/.codex
```

Copy the TOML subagents into `~/.codex/agents/`
([subagents](https://learn.chatgpt.com/codex/agent-configuration/subagents)). PowerShell:

```powershell
Copy-Item -Recurse -Force "$src\.codex\agents" $HOME\.codex\
```

Unix shell:

```bash
cp -R "$src/.codex/agents" ~/.codex/
```

Point Codex at the instruction file. It reads `~/.codex/AGENTS.md`
([AGENTS.md docs](https://learn.chatgpt.com/codex/agent-configuration/agents-md)), so make that a link to
`~/.claude/CLAUDE.md`. PowerShell:

```powershell
New-Item -ItemType SymbolicLink -Path $HOME\.codex\AGENTS.md -Target $HOME\.claude\CLAUDE.md
```

Unix shell:

```bash
ln -s ~/.claude/CLAUDE.md ~/.codex/AGENTS.md
```

Wire the hooks in `~/.codex/hooks.json`, which is the user-level hooks file
([hooks docs](https://learn.chatgpt.com/codex/hooks)). The same tables can go inline in `~/.codex/config.toml` instead,
and Codex asks you to pick one form per configuration layer rather than using both. Replace every absolute path. All
five events matter: `UserPromptSubmit` injects the reminder on the main thread, `SubagentStart` injects the subagent
text inside a subagent, `PreToolUse` is the blocking half, `Stop` checks the reply formatting, and `SessionStart` puts
the task list back. The two texts differ on purpose: the reminder tells its reader to delegate, and a subagent told
that turns its own task away, so a subagent is told to do the work itself instead. The `|| exit 0` on every script
`command` and the
`; exit 0` on every `commandWindows` are what make a missing or broken script allow the call instead of denying every
one of them. Each command needs its `commandWindows` sibling, because Codex picks one of the two per platform and a
command with no sibling is simply absent on the other. Codex runs `commandWindows` in PowerShell, `pwsh` when it is
installed and Windows PowerShell otherwise, and Windows PowerShell has no `||`, which is why the Windows lines end in
`; exit 0` and send errors to `$null` rather than `nul`.

Codex tracks every hook by a hash of its definition: "new or changed hooks are marked for review and skipped until
trusted" ([hooks docs](https://learn.chatgpt.com/docs/hooks)). After you paste or refresh these entries, open an
interactive Codex session and trust them, or every changed hook, the reminder included, is silently skipped. Codex
0.156.1 ran the unchanged `Stop` hook, skipped the edited reminder hook, and ran it only with
`--dangerously-bypass-hook-trust`.

The two reminder commands print JSON whose `additionalContext` carries the line breaks as `\n` escapes. The POSIX
`command` prints it with `printf '%s\n'` rather than `echo`, because `dash`, the `sh` on Debian and Ubuntu, turns
`\n` inside an `echo` argument into a raw newline and breaks the JSON. Codex also runs `UserPromptSubmit` for the
message that starts a subagent, and only then puts an `agent_id` key in the payload, so both reminder commands first
look for `"agent_id"` on standard input and print nothing when they find it.

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "statusMessage": "Preflight gate",
            "command": "grep -F '\"agent_id\"' >/dev/null || printf '%s\\n' '{\"hookSpecificOutput\": {\"hookEventName\": \"UserPromptSubmit\", \"additionalContext\": \"PREFLIGHT: before code work, name the skills and subagents that own this task and invoke them, or say none apply and why. Delegate investigation, review and bounded implementation by default. Follow the user-communication skill when writing to the user. If the prompt asks anything, answer every question first, then start the work. End every reply to the user with this block, exactly as shown: no heading, no bullets, no numbered list, plain lines only, keeping every blank line:\\n\\nRunning: `running task name` (or: nothing)\\n\\n~~DONE: older finished task~~\\n~~DONE: most recent finished task~~\\n\\n**NOW: what is being done right now**\\n\\nNext: the next task\\nThen: the task after that\\n\\nWaiting on: what you wait for (or: nothing)\\n\\nWhen several tasks run, list each name in backticks on the Running line, separated by commas.\"}}'",
            "commandWindows": "if (-not [Console]::In.ReadToEnd().Contains(\"`\"agent_id`\"\")) { echo '{\"hookSpecificOutput\": {\"hookEventName\": \"UserPromptSubmit\", \"additionalContext\": \"PREFLIGHT: before code work, name the skills and subagents that own this task and invoke them, or say none apply and why. Delegate investigation, review and bounded implementation by default. Follow the user-communication skill when writing to the user. If the prompt asks anything, answer every question first, then start the work. End every reply to the user with this block, exactly as shown: no heading, no bullets, no numbered list, plain lines only, keeping every blank line:\\n\\nRunning: `running task name` (or: nothing)\\n\\n~~DONE: older finished task~~\\n~~DONE: most recent finished task~~\\n\\n**NOW: what is being done right now**\\n\\nNext: the next task\\nThen: the task after that\\n\\nWaiting on: what you wait for (or: nothing)\\n\\nWhen several tasks run, list each name in backticks on the Running line, separated by commas.\"}}' }; exit 0"
          }
        ]
      }
    ],
    "SubagentStart": [
      {
        "hooks": [
          {
            "type": "command",
            "statusMessage": "Preflight gate",
            "command": "printf '%s\\n' '{\"hookSpecificOutput\": {\"hookEventName\": \"SubagentStart\", \"additionalContext\": \"PREFLIGHT for a subagent: you are a subagent, and the main thread delegated this task to you. Do the work yourself with your own tools and load the skills your definition names. The rules that the main thread must delegate and may not write files apply to the main thread only, so do not hand this task on and do not refuse it for that reason. The preflight gate still checks every tool call you make. Report back what you changed and how you verified it.\"}}'",
            "commandWindows": "echo '{\"hookSpecificOutput\": {\"hookEventName\": \"SubagentStart\", \"additionalContext\": \"PREFLIGHT for a subagent: you are a subagent, and the main thread delegated this task to you. Do the work yourself with your own tools and load the skills your definition names. The rules that the main thread must delegate and may not write files apply to the main thread only, so do not hand this task on and do not refuse it for that reason. The preflight gate still checks every tool call you make. Report back what you changed and how you verified it.\"}}'; exit 0"
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "statusMessage": "Task list",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.agents/hooks/task_list_sync.py --event sessionstart --format codex 2>/dev/null || exit 0",
            "commandWindows": "$root = git rev-parse --show-toplevel 2>$null; if ($root) { Set-Location -LiteralPath $root }; python -S -E /home/you/.agents/hooks/task_list_sync.py --event sessionstart --format codex 2>$null; exit 0"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "statusMessage": "Formatting check",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.agents/hooks/no_ai_markers_check.py --format codex 2>/dev/null || exit 0",
            "commandWindows": "$root = git rev-parse --show-toplevel 2>$null; if ($root) { Set-Location -LiteralPath $root }; python -S -E /home/you/.agents/hooks/no_ai_markers_check.py --format codex 2>$null; exit 0"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "^(Bash|shell|apply_patch|Edit|Write|NotebookEdit)$",
        "hooks": [
          {
            "type": "command",
            "statusMessage": "Preflight gate",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.agents/hooks/preflight_gate.py --format codex 2>/dev/null || exit 0",
            "commandWindows": "$root = git rev-parse --show-toplevel 2>$null; if ($root) { Set-Location -LiteralPath $root }; python -S -E /home/you/.agents/hooks/preflight_gate.py --format codex 2>$null; exit 0"
          }
        ]
      }
    ]
  }
}
```

MCP servers go in `[mcp_servers.<name>]` tables in `~/.codex/config.toml`, which is shared by the Codex CLI, the IDE
extension, and the ChatGPT desktop app ([MCP docs](https://learn.chatgpt.com/codex/extend/mcp)). Copy the tables you
want from [MCP_SETUP.md](MCP_SETUP.md).

#### OpenCode

OpenCode reads `~/.agents/skills/<name>/SKILL.md` natively ([skills docs](https://opencode.ai/docs/skills/)). It also
reads `~/.claude/skills`, which the Claude Code link points at the same folder, and loads a skill from whichever
location it finds it in, so there is nothing to undo.

It reads the instruction file on its own. Its global rules file is `~/.config/opencode/AGENTS.md`, and "Global rules:
~/.claude/CLAUDE.md (used if no ~/.config/opencode/AGENTS.md exists)" ([rules docs](https://opencode.ai/docs/rules/)).
Create no `~/.config/opencode/AGENTS.md` and it reads `~/.claude/CLAUDE.md`.

Create the configuration directory. PowerShell:

```powershell
New-Item -ItemType Directory -Force $HOME\.config\opencode
```

Unix shell:

```bash
mkdir -p ~/.config/opencode
```

Link the subagents to the shared tree. The global location is `~/.config/opencode/agents/`
([agents docs](https://opencode.ai/docs/agents/)), and OpenCode 1.18.32 loaded all 25 subagents through a junction
there in a throwaway home. If the directory already exists, move it aside first, because the link needs its name.
PowerShell:

```powershell
New-Item -ItemType Junction -Path $HOME\.config\opencode\agents -Target $HOME\.agents\agents
```

Unix shell:

```bash
ln -s ~/.agents/agents ~/.config/opencode/agents
```

Declare the plugin by path rather than copying it, so an update to `~/.agents/plugin/hooks.js` reaches OpenCode with
nothing else to do. Add this to `~/.config/opencode/opencode.json`, with your real home directory:

```jsonc
{
  "plugin": ["C:/Users/you/.agents/plugin/hooks.js"]
}
```

Leave `~/.config/opencode/plugins/` without a copy of `hooks.js`. Files in that directory load automatically at
startup ([plugins docs](https://opencode.ai/docs/plugins/)), so a copy there would load the runner a second time.

The plugin prefers the project's own `.agents/hooks/` and falls back to `~/.agents/hooks/`, so it gates every project,
including one that never ran the per-project import.
[How the OpenCode and Kilo Code plugin finds its hooks](#how-the-opencode-and-kilo-code-plugin-finds-its-hooks) has
the order and the per-project opt-out.

MCP servers go under the `mcp` key of `~/.config/opencode/opencode.json`
([config docs](https://opencode.ai/docs/config/)), or in the shared file from
[Share one MCP list between OpenCode and Kilo Code](#share-one-mcp-list-between-opencode-and-kilo-code). Take the
block from [MCP_SETUP.md](MCP_SETUP.md) and keep the machine-wide servers only.

#### Kilo Code

Kilo Code reads the shared skills with no configuration: "install them at `~/.agents/skills/<name>/SKILL.md`. Kilo
discovers this user-level directory by default, without a skills.paths entry"
([skills docs](https://kilo.ai/docs/customize/skills)). A `skills.paths` entry naming `~/.agents/skills` is therefore
not needed.

Create the configuration directory. PowerShell:

```powershell
New-Item -ItemType Directory -Force $HOME\.config\kilo
```

Unix shell:

```bash
mkdir -p ~/.config/kilo
```

Link the subagents to the same shared tree OpenCode uses. The global location is `~/.config/kilo/agents/`
([custom subagents](https://kilo.ai/docs/customize/custom-subagents)). Kilo Code 7.7.9 loaded all 25 subagents through
a junction there, in a throwaway home, both with and without a `markdown_source` rule. The documentation asks for that
rule when a project's `.kilo/agents/` links outside the project, and the global directory did not need it. PowerShell:

```powershell
New-Item -ItemType Junction -Path $HOME\.config\kilo\agents -Target $HOME\.agents\agents
```

Unix shell:

```bash
ln -s ~/.agents/agents ~/.config/kilo/agents
```

Kilo Code reads no global `AGENTS.md`. Global rules come from the `instructions` key of `~/.config/kilo/kilo.jsonc`
([custom rules](https://kilo.ai/docs/customize/custom-rules)), and the same file takes the plugin. Kilo loads a local
plugin named as an absolute `file:` URL ([plugins docs](https://kilo.ai/docs/automate/extending/plugins)). Merge this
into `~/.config/kilo/kilo.jsonc`, with your real home directory:

```jsonc
{
  "instructions": ["C:/Users/you/.claude/CLAUDE.md"],
  "plugin": ["file:///C:/Users/you/.agents/plugin/hooks.js"]
}
```

Leave `~/.config/kilo/plugin/` without a copy of `hooks.js`, for the same reason as under OpenCode: every file in that
directory is "auto-registered at startup", so a copy there would load the runner a second time.

MCP servers go under the `mcp` key of `~/.config/kilo/kilo.jsonc`, in the same shape as `opencode.json`
([CLI docs](https://kilo.ai/docs/code-with-ai/platforms/cli)), or in the shared file below. `{env:VAR}` works here:
Kilo refuses it in a project config file, but resolves it in "your global config (~/.config/kilo), a config passed via
KILO_CONFIG / KILO_CONFIG_CONTENT, or organization/MDM-managed config". This is the place for the Context7 API key
header if you want Kilo to use your key rather than the free tier:

```jsonc
{
  "mcp": {
    "context7": {
      "type": "remote",
      "url": "https://mcp.context7.com/mcp",
      "headers": { "CONTEXT7_API_KEY": "{env:CONTEXT7_API_KEY}" },
      "enabled": true
    }
  }
}
```

#### Share one MCP list between OpenCode and Kilo Code

Optional. Put the machine-wide servers in one file that holds nothing but an `mcp` block, for example
`~/.agents/mcp.json`, in the `opencode.json` shape from [MCP_SETUP.md](MCP_SETUP.md). Then name it in both variables,
for your user account rather than one shell. PowerShell:

```powershell
[Environment]::SetEnvironmentVariable('OPENCODE_CONFIG', "$HOME\.agents\mcp.json", 'User')
```

```powershell
[Environment]::SetEnvironmentVariable('KILO_CONFIG', "$HOME\.agents\mcp.json", 'User')
```

Unix shell, added to your shell profile:

```bash
printf 'export OPENCODE_CONFIG="$HOME/.agents/mcp.json"\nexport KILO_CONFIG="$HOME/.agents/mcp.json"\n' >> ~/.profile
```

Both tools merge that file over their own global config, so keep the `mcp` block out of `opencode.json` and
`kilo.jsonc` to have one list. Restart the agents, or sign out and in again on Windows, so they see the variables.
Whether Kilo Code ever writes back into a file named by `KILO_CONFIG` was not tested.

#### GitHub Copilot

Copilot reads `~/.agents/skills` as a personal skills location alongside `~/.copilot/skills`
([about agent skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)), so step 2 finished the
skills job, across the cloud agent, code review, the CLI, and agent mode in VS Code and JetBrains.

The CLI configuration directory is `~/.copilot`, relocatable with `COPILOT_HOME`
([CLI config dir reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference)).
VS Code reads from it too: its Local agent loads user hooks from `~/.copilot/hooks/*.json` and user custom agents from
`~/.copilot/agents` or `~/.claude/agents`
([VS Code hooks](https://code.visualstudio.com/docs/copilot/customization/hooks),
[VS Code custom agents](https://code.visualstudio.com/docs/copilot/customization/custom-agents)). Because VS Code reads
both agent folders, a subagent installed for Claude Code and for Copilot shows up there twice.

Create the two directories the copies land in. PowerShell:

```powershell
New-Item -ItemType Directory -Force $HOME\.copilot\agents, $HOME\.copilot\hooks
```

Unix shell:

```bash
mkdir -p ~/.copilot/agents ~/.copilot/hooks
```

Copy the `*.agent.md` subagents into `~/.copilot/agents/`. PowerShell:

```powershell
Copy-Item -Recurse -Force "$src\.github\agents\*" $HOME\.copilot\agents\
```

Unix shell:

```bash
cp -R "$src/.github/agents/." ~/.copilot/agents/
```

Wire the hooks in `~/.copilot/hooks/preflight.json`, the user-level hooks directory
([hooks reference](https://docs.github.com/en/copilot/reference/hooks-reference)). The block is
the checkout's `.github/hooks/preflight.json` with every script path made absolute. Replace every absolute
path. Five events matter: `sessionStart` injects the reminder and puts the task list back,
`subagentStart` injects the subagent text inside a subagent, `userPromptTransformed` appends the reminder to every
prompt, `preToolUse` is the blocking half, and `agentStop` checks the reply formatting. Each entry carries `bash`
and `powershell` as sibling string fields, because Copilot picks one per shell. The `|| exit 0` on every `bash`
script call and the `; exit 0` on every `powershell` one are what make a missing or broken script allow the call.

```json
{
  "version": 1,
  "hooks": {
    "sessionStart": [
      {
        "type": "command",
        "bash": "printf '%s\\n' '{\"additionalContext\": \"PREFLIGHT: before code work, name the skills and subagents that own this task and invoke them, or say none apply and why. Delegate investigation, review and bounded implementation by default. Follow the user-communication skill when writing to the user. If the prompt asks anything, answer every question first, then start the work. End every reply to the user with this block, exactly as shown: no heading, no bullets, no numbered list, plain lines only, keeping every blank line:\\n\\nRunning: `running task name` (or: nothing)\\n\\n~~DONE: older finished task~~\\n~~DONE: most recent finished task~~\\n\\n**NOW: what is being done right now**\\n\\nNext: the next task\\nThen: the task after that\\n\\nWaiting on: what you wait for (or: nothing)\\n\\nWhen several tasks run, list each name in backticks on the Running line, separated by commas.\"}'",
        "powershell": "echo '{\"additionalContext\": \"PREFLIGHT: before code work, name the skills and subagents that own this task and invoke them, or say none apply and why. Delegate investigation, review and bounded implementation by default. Follow the user-communication skill when writing to the user. If the prompt asks anything, answer every question first, then start the work. End every reply to the user with this block, exactly as shown: no heading, no bullets, no numbered list, plain lines only, keeping every blank line:\\n\\nRunning: `running task name` (or: nothing)\\n\\n~~DONE: older finished task~~\\n~~DONE: most recent finished task~~\\n\\n**NOW: what is being done right now**\\n\\nNext: the next task\\nThen: the task after that\\n\\nWaiting on: what you wait for (or: nothing)\\n\\nWhen several tasks run, list each name in backticks on the Running line, separated by commas.\"}'"
      },
      {
        "type": "command",
        "cwd": ".",
        "bash": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.agents/hooks/task_list_sync.py --event sessionstart --format copilot 2>/dev/null || exit 0",
        "powershell": "python -S -E /home/you/.agents/hooks/task_list_sync.py --event sessionstart --format copilot 2>$null; exit 0"
      }
    ],
    "subagentStart": [
      {
        "type": "command",
        "bash": "printf '%s\\n' '{\"additionalContext\": \"PREFLIGHT for a subagent: you are a subagent, and the main thread delegated this task to you. Do the work yourself with your own tools and load the skills your definition names. The rules that the main thread must delegate and may not write files apply to the main thread only, so do not hand this task on and do not refuse it for that reason. The preflight gate still checks every tool call you make. Report back what you changed and how you verified it.\"}'",
        "powershell": "echo '{\"additionalContext\": \"PREFLIGHT for a subagent: you are a subagent, and the main thread delegated this task to you. Do the work yourself with your own tools and load the skills your definition names. The rules that the main thread must delegate and may not write files apply to the main thread only, so do not hand this task on and do not refuse it for that reason. The preflight gate still checks every tool call you make. Report back what you changed and how you verified it.\"}'"
      }
    ],
    "userPromptTransformed": [
      {
        "type": "command",
        "cwd": ".",
        "bash": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.agents/hooks/copilot/prompt_reminder.py 2>/dev/null || exit 0",
        "powershell": "python -S -E /home/you/.agents/hooks/copilot/prompt_reminder.py 2>$null; exit 0"
      }
    ],
    "preToolUse": [
      {
        "type": "command",
        "matcher": "bash|powershell|create|edit|apply_patch",
        "cwd": ".",
        "bash": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.agents/hooks/preflight_gate.py --format copilot 2>/dev/null || exit 0",
        "powershell": "python -S -E /home/you/.agents/hooks/preflight_gate.py --format copilot 2>$null; exit 0"
      }
    ],
    "agentStop": [
      {
        "type": "command",
        "cwd": ".",
        "bash": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.agents/hooks/no_ai_markers_check.py --format copilot 2>/dev/null || exit 0",
        "powershell": "python -S -E /home/you/.agents/hooks/no_ai_markers_check.py --format copilot 2>$null; exit 0"
      }
    ]
  }
}
```

Do not turn on `chat.useClaudeHooks` in VS Code on top of this. With it on, the Local agent also runs the hooks in
`~/.claude/settings.json`, next to the ones in `~/.copilot/hooks/`, and the documentation adds that "Local ignores
matcher values". The gate is wired in both files, so every tool call in a VS Code chat would run it twice.

Point Copilot at the instruction file. Its personal instructions live in `~/.copilot/copilot-instructions.md`, and it
reads none of the other agents' files, so it needs a link of its own. Run it in PowerShell 7 (`pwsh`): Windows
PowerShell 5.1 refuses the symbolic link with "Administrator privilege required" even with Developer Mode on.
PowerShell:

```powershell
New-Item -ItemType SymbolicLink -Path $HOME\.copilot\copilot-instructions.md -Target $HOME\.claude\CLAUDE.md
```

Unix shell:

```bash
ln -s ~/.claude/CLAUDE.md ~/.copilot/copilot-instructions.md
```

MCP for the CLI is `~/.copilot/mcp-config.json`. In VS Code, run the `MCP: Open User Configuration` command to open
the `mcp.json` in your user profile folder, which applies across every workspace. The JetBrains plugin reads one global
file and no project file: `C:\Users\<you>\AppData\Local\github-copilot\intellij\mcp.json` on Windows and
`~/.config/github-copilot/intellij/mcp.json` elsewhere. GitHub documents only the in-IDE interface, not the path, so
treat that path as observed rather than documented. The manual blocks for all three are in [MCP_SETUP.md](MCP_SETUP.md).

---

### Finish, delete the temporary copy

PowerShell:

```powershell
Remove-Item -Recurse -Force $src
```

Unix shell:

```bash
rm -rf "$src"
```

---

### How the OpenCode and Kilo Code plugin finds its hooks

The plugin runs the hook scripts, it holds no rules of its own. On every tool call it picks one directory of hooks and
runs every script in it.

It looks in this order and stops at the first match:

1. The project's own `.agents/hooks/`. If that directory exists, the plugin uses it and nothing else, even when it is
   empty. A project that ran the per-project import therefore keeps its own copy of the gate, pinned to the version it
   imported.
2. The opt-out file `.agents/no-global-hooks` in the project. If it exists, the plugin runs no hooks at all for that
   project. Only its presence counts, so an empty file is enough.
3. The global `.agents/hooks/` in your home directory, the one step 2 filled. On Windows that is
   `C:\Users\<you>\.agents\hooks`, elsewhere `~/.agents/hooks`.

If none of those exists, no hook runs and every tool call is allowed.

A global hook still guards the project, not your home directory. The plugin starts it in the project root and names
that root in the `cwd` field of the payload, so the gate protects the files of the project you have open, the same way
the per-project copy does.

The choice is made again on every tool call, so adding or removing the opt-out file, or importing hooks into the
project, takes effect on the next call without a restart.

To run one project without the gate on OpenCode and Kilo Code, create the opt-out file from the project root.
PowerShell:

```powershell
New-Item -ItemType File -Force .agents\no-global-hooks
```

Unix shell:

```bash
mkdir -p .agents && touch .agents/no-global-hooks
```

To turn the gate back on, delete that file. The opt-out only switches the global fallback off. It never switches off
hooks the project ships in its own `.agents/hooks/`, and it does nothing on Claude Code, Codex, or GitHub Copilot,
which call the gate from their own settings files.

---

### What the main thread may run

The gate stops the main thread from running a script or a module, because it cannot see what a script writes. The main
thread hands that work to a subagent instead, and subagents are not affected by this rule.

What counts as running a script:

- An interpreter handed a file or a module, such as `python x.py`, `python -m pip`, `node x.js`, `bash x.sh`, or
  `pwsh -File x.ps1`.
- A package or task runner handed any subcommand, such as `npm run build`, `npx prettier`, `pnpm lint`, `yarn test`,
  `uv run`, or `pip install`.
- A git subcommand that runs a command of its own: `git bisect run`, `git rebase --exec`, `git submodule foreach`, and
  `git filter-branch`.
- A build runner or compiler asked for anything beyond its version or help, such as `make`, `make build`,
  `cargo build`, `go run .`, `go generate`, `go test`, `dotnet build`, `mvn test`, `gradle build`, `just test`, or
  `rake`. `make --version`, `go version` and `dotnet --info` stay allowed.
- A program called by a script file name, such as `.\deploy.ps1`, and any program whose path lands inside the
  project, such as `./gradlew build` or `./bin/tool`.
- A native program named by any other path, such as `/usr/local/bin/terraform apply`, unless it is a known read-only
  tool such as `/usr/bin/grep`.

Inline code, such as `python -c "print(1)"` or `node -e "..."`, is not a script run. The gate reads that code itself
and denies it when it writes a file in the project, or when it loads code the gate cannot read: a Python import from
outside the standard library, or a JavaScript module that is not built in. Writing `tasks.md` at the project root,
sending output to the null device, and switching branches all stay allowed.

A command also denies when it sets an environment variable that changes which program or file it uses, such as
`GIT_DIR`, `GIT_CONFIG_PARAMETERS`, `LD_PRELOAD`, `NODE_OPTIONS`, `PYTHONPATH`, `BASH_ENV`, `PATH`, or
`PYTEST_ADDOPTS`, whether the assignment leads the command, goes through `env` or `export`, or is a PowerShell
`$env:` assignment. `LANG=C ls` and `PYTHONUTF8=1 python -m pytest` stay allowed.

Three read-only checks are always allowed, each with only the options listed:

| Check | Options it may carry |
| --- | --- |
| `python -m pytest` | `-q`, `-v`, `-x`, `-s`, `-l`, `-k`, `-m`, `-r`, `--tb`, `--maxfail`, `--durations`, `--capture`, `--color`, `--deselect`, `--ignore`, `--lf`, `--ff`, `--nf`, `--sw`, `--co`, `--no-header`, `--no-summary`, `--strict-markers`, `--runxfail`, and the long forms of those, plus test paths inside the project |
| `node --check` | file names only |
| `bash -n` | file names only |

Any other option denies. For pytest that covers every option that loads a plugin (`-p`), a configuration file (`-c`,
`--config-file`, `-o`), a root directory or a conftest from elsewhere (`--rootdir`, `--confcutdir`, a test path outside
the project), sets the temporary base (`--basetemp`), writes a report (`--junitxml`, `--debug`), or imports a warning
category (`-W`). For `node --check` it covers `-r`, `--require` and `--import`, and for `bash -n` it covers `-i` and
`+n`, which would run the script after all.

git has no entry. A git read such as `git status` or `git log` is not a script run in the first place, so the gate
judges it by what it writes, like any other command. `git diff --output=file`, `git format-patch` without `--stdout`,
and `git config` writes deny when their file lands in the project.

How a project entry is matched:

- The first word is the program. `python3`, `python3.13` and `py` all count as `python`. A first word with a slash in
  it names a file instead, and matches only that file, so `.venv/Scripts/python.exe -m pytest` needs its own entry,
  and an entry `scripts/verify.sh` does not allow `other/verify.sh`.
- A trailing `...` accepts any further arguments. Without it the command has to end where the entry ends, so an
  entry `python scripts/verify.py` allows that command and denies `python scripts/verify.py --fix`.
- A word with a slash in it is a file path, and it matches the file it names from where the command runs. After
  `cd scripts`, `python verify.py` still matches, and after `cd docs`, `python scripts/verify.py` does not.
- An entry that hands a script to a shell, such as `bash scripts/check.sh`, only lifts the script-run rule. The gate
  still reads the script as shell code and denies it when it writes a file in the project.
- The built-in list names no project's own scripts, because an entry such as `python tools/check.py` would also allow a
  same-named script in every other project, and that script could write files.

The built-in list lives in `MAIN_THREAD_ALLOWLIST` near the top of `.agents/hooks/preflight_gate.py`. Do not edit it
in a project, because the next update overwrites that file. Add your own entries to `main-thread-allowlist.txt` at the
project root instead, one per line, in the form described above. Blank lines and lines starting with `#` are
skipped. The file
sits at the root rather than under `.agents/`, so importing or updating `.agents` never overwrites it. For example:

```text
# read-only checks this project allows its main thread
npm run lint ...
make check
python scripts/verify.py
```

The gate reads that file from the project root on every call, so a new entry works on the next command. The main
thread cannot write the file itself, because the gate protects it like every other file in the project, so ask a
subagent to add an entry. Commit the file so the whole team gets the same list.

---

### What this document deliberately leaves to you

1. MCP servers, everywhere. Which servers are machine-wide is a judgement about your machine, and most servers should
   not be global at all. Each agent's subsection above says where its user-scope MCP configuration lives, and
   [MCP_SETUP.md](MCP_SETUP.md) has the blocks.
2. The content of `~/.claude/CLAUDE.md`. Editing the template down to the parts that are about you is a job only you
   can do.
3. Merging into a configuration file you already have. Nothing above tells you to overwrite one. Where a file already
   exists, merge the block rather than replacing the file.

---

### Global path map

Every global location this document touches, per agent. The project-level equivalents are the paths the import
writes into your repository, and they are unaffected by anything here.

| Agent | Skills | Subagents | Hooks or plugin | MCP config | Global instructions | Config-dir env var |
| --- | --- | --- | --- | --- | --- | --- |
| Claude Code | `~/.claude/skills/`, a link to `~/.agents/skills` | `~/.claude/agents/` | `hooks` in `~/.claude/settings.json` | `~/.claude.json`, written by `claude mcp add --scope user` | `~/.claude/CLAUDE.md`, plus `~/.claude/rules/` | `CLAUDE_CONFIG_DIR` |
| Codex | `$HOME/.agents/skills` native, also `/etc/codex/skills` | `~/.codex/agents/` as TOML | `~/.codex/hooks.json`, or inline `[[hooks.*]]` in `~/.codex/config.toml` | `[mcp_servers.*]` in `~/.codex/config.toml` | `~/.codex/AGENTS.md`, a link to `~/.claude/CLAUDE.md` | `CODEX_HOME` |
| OpenCode | `~/.agents/skills/`, `~/.claude/skills/`, `~/.config/opencode/skills/`, all native | `~/.config/opencode/agents/`, a link to `~/.agents/agents` | `plugin` in `~/.config/opencode/opencode.json`, naming `~/.agents/plugin/hooks.js` | `mcp` in `~/.config/opencode/opencode.json`, or the file in `OPENCODE_CONFIG` | falls back to `~/.claude/CLAUDE.md` | `OPENCODE_CONFIG_DIR`, and `OPENCODE_CONFIG` for a file |
| Kilo Code | `~/.agents/skills/` and `~/.kilo/skills/` native, `~/.claude/skills/` behind a compatibility setting | `~/.config/kilo/agents/`, a link to `~/.agents/agents` | `plugin` in `~/.config/kilo/kilo.jsonc`, naming `~/.agents/plugin/hooks.js` | `mcp` in `~/.config/kilo/kilo.jsonc`, or the file in `KILO_CONFIG` | `instructions` in `~/.config/kilo/kilo.jsonc` | `KILO_CONFIG` for a file |
| GitHub Copilot | `~/.copilot/skills/` and `~/.agents/skills/`, both native | `~/.copilot/agents/`, read by the CLI and VS Code | `~/.copilot/hooks/`, read by the CLI and VS Code | `~/.copilot/mcp-config.json` for the CLI, user-profile `mcp.json` for VS Code, `C:\Users\<you>\AppData\Local\github-copilot\intellij\mcp.json` for JetBrains on Windows | `~/.copilot/copilot-instructions.md`, a link to `~/.claude/CLAUDE.md` | `COPILOT_HOME` |

---

### Updating the global installation

One command updates everything the install put in your home directory. It clones a temporary copy of this repository,
reads the files of its newest commit, updates your install from them, prints what it did, and deletes the copy.
PowerShell:

```powershell
pwsh -NoProfile -File $HOME\.agents\bin\update-global.ps1
```

Unix shell:

```bash
sh ~/.agents/bin/update-global.sh
```

The PowerShell version needs PowerShell 7.4 or later, which is `pwsh`, not the Windows PowerShell 5.1 that Windows
ships. The Unix version runs in any POSIX `sh`, including Git Bash. Both do exactly the same thing.

What it changes:

- The hook scripts in `~/.agents/hooks`, the plugin in `~/.agents/plugin`, and the updater itself in `~/.agents/bin`
  are refreshed in full, including a file upstream added since your last update. OpenCode and Kilo Code name the
  plugin by path, so this reaches both.
- Every skill folder you already have in `~/.agents/skills` is refreshed file by file, when upstream still ships a
  skill of that name. A skill you do not have is never added, so one you deleted stays deleted.
- Every subagent file you already have is refreshed, in the four trees: `~/.agents/agents`, which OpenCode and Kilo
  Code reach through their links, `~/.claude/agents`, `~/.codex/agents`, and `~/.copilot/agents`. A subagent you do
  not have is never added.
- A file is removed only when the commit recorded in `~/.agents/.upstream-commit` shipped it and the new commit no
  longer does. A file of your own, such as a note you keep inside a skill folder, was never shipped, so it is never
  removed. When the recorded commit is missing or unknown, nothing is removed and the summary says so.
- A skill folder or a subagent file that upstream stopped shipping altogether stays in place and is reported as
  `keep`. One that never came from upstream is reported as `skip` and left alone.
- The new commit is written to `~/.agents/.upstream-commit`.

It never touches the files listed under [Files no update touches](#files-no-update-touches). When upstream changed the
hook wiring since the recorded commit, the summary names the changed files and prints the `git diff` command that
shows the change. Merge each changed entry into your own file by hand, taking it from the per-agent block above and
writing your absolute paths into it. After any change to `~/.codex/hooks.json`, open an interactive Codex session and
trust the hooks again, because "changed hooks are marked for review and skipped until trusted"
([hooks docs](https://learn.chatgpt.com/codex/hooks)).

To see what an update would do first, run it as a dry run. It prints the same list and writes nothing. PowerShell:

```powershell
pwsh -NoProfile -File $HOME\.agents\bin\update-global.ps1 -DryRun
```

Unix shell:

```bash
sh ~/.agents/bin/update-global.sh --dry-run
```

The summary lists one line per file it changed or skill and subagent it left alone, then the wiring report and the
totals, for example:

```text
update  ~/.agents/hooks/preflight_gate.py
add     ~/.agents/skills/research/references/source-order.md
skip    ~/.agents/skills/my-own-skill (not an upstream skill)
Hook wiring: unchanged upstream since 1006f0084bd24080dcfbadb5c4bd33aaa616950d.
Recorded 3f2abe7a3afd255c4220154474a1c4700ca37273 in ~/.agents/.upstream-commit.
Updated 1, added 1, removed 0. Unchanged 371. Left alone: 0 removed upstream, 1 not from upstream.
```

To update from a clone of this repository you already have rather than from GitHub, name it as the source. The
updater reads that clone's last commit and never its working tree, so uncommitted work in it cannot reach your home
directory. Replace the path with your clone. PowerShell:

```powershell
pwsh -NoProfile -File $HOME\.agents\bin\update-global.ps1 -Source D:\src\agent-standards
```

Unix shell:

```bash
sh ~/.agents/bin/update-global.sh --source ~/src/agent-standards
```

#### Installed before the updater existed

An install older than `~/.agents/bin` has no updater yet. Run it once out of a temporary copy, and that first run
puts it in `~/.agents/bin` for every later update. PowerShell:

```powershell
$src = Join-Path ([IO.Path]::GetTempPath()) 'agent-standards'
```

```powershell
git clone --filter=blob:none https://github.com/Lukk17/agent-standards.git $src
```

```powershell
pwsh -NoProfile -File "$src\global\bin\update-global.ps1" -Source $src
```

```powershell
Remove-Item -Recurse -Force $src
```

Unix shell:

```bash
src="$(mktemp -d)/agent-standards"
```

```bash
git clone --filter=blob:none https://github.com/Lukk17/agent-standards.git "$src"
```

```bash
sh "$src/global/bin/update-global.sh" --source "$src"
```

```bash
rm -rf "$src"
```

#### Adding a skill you do not have yet

The update never adds a skill, so copy the one folder out of a temporary copy made as in
[step 1](#step-1-a-temporary-copy-of-the-repository), and delete the copy afterwards. Replace `research` with the
folder name under `.agents/skills/`. Every agent then finds it the way it finds the others, and from then on the
update keeps it current. PowerShell:

```powershell
Copy-Item -Recurse "$src\.agents\skills\research" $HOME\.agents\skills\research
```

Unix shell:

```bash
cp -R "$src/.agents/skills/research" ~/.agents/skills/research
```

#### Files no update touches

Never refreshed, on purpose, because they become yours the moment you install them: `~/.claude/settings.json`,
`~/.claude/CLAUDE.md`, `~/.claude.json`, `~/.codex/hooks.json`, `~/.codex/config.toml`,
`~/.config/opencode/opencode.json`, `~/.config/kilo/kilo.jsonc`, `~/.copilot/hooks/preflight.json`,
`~/.copilot/mcp-config.json`, and `~/.agents/mcp.json` if you made one. When upstream changes the gate wording, the
hook wiring, or adds an MCP server, merge it into those by hand.

---

### Undoing the global installation

Remove it by hand, checking each directory before you delete it. Every directory the install writes into is one an
agent also lets you put your own files in, so deleting a whole tree takes anything you wrote yourself along with it.

Remove the links first, so deleting a link never reaches the shared folder behind it. A junction or a symlink is
removed as the link itself. PowerShell:

```powershell
foreach ($l in "$HOME\.claude\skills", "$HOME\.config\opencode\agents", "$HOME\.config\kilo\agents") { if (Test-Path $l) { (Get-Item $l).Delete() } }
```

Unix shell:

```bash
rm -f ~/.claude/skills ~/.config/opencode/agents ~/.config/kilo/agents
```

Then delete the shared folder. PowerShell:

```powershell
Remove-Item -Recurse -Force $HOME\.agents
```

Unix shell:

```bash
rm -rf ~/.agents
```

Then, per agent, remove only what you recognise: the `agents/` directories of Claude Code, Codex and Copilot, and the
two instruction links, `~/.codex/AGENTS.md` and `~/.copilot/copilot-instructions.md`. Take the gate out of
`~/.claude/settings.json`, `~/.codex/hooks.json`, and `~/.copilot/hooks/preflight.json`, and the `plugin` and
`instructions` entries out of `opencode.json` and `kilo.jsonc`, by editing those files, since each may hold
configuration of yours as well. `~/.claude/CLAUDE.md` is yours and stays.

---

### Limitations

Honest list of what a global install cannot do.

1. The blocking half of the preflight gate is project-shaped. Every shipped hook wiring calls
   `.agents/hooks/preflight_gate.py`, resolved against the session's working directory. At user level you have to
   rewrite that to an absolute path, which the Claude Code, Codex, and Copilot sections above tell you to do, and the
   same is true of `task_list_sync.py` and `no_ai_markers_check.py`. The gate script then looks for subagent
   definitions in both the current directory and its own grandparent, so a copy at
   `~/.agents/hooks/preflight_gate.py` does find `~/.claude/agents` and `~/.agents/agents`. The text-injection half,
   the `echo` that reminds the model to name its skills, has no file dependency and works globally as it ships.

2. The OpenCode and Kilo Code plugin needs no path rewriting. It uses the project's own `.agents/hooks/` when the
   project has one and your home directory's `.agents/hooks/` otherwise, so the global entry gates a project that
   never ran the per-project import. The one project that stays ungated is one holding the opt-out file described in
   [How the OpenCode and Kilo Code plugin finds its hooks](#how-the-opencode-and-kilo-code-plugin-finds-its-hooks).

3. Copilot hooks reach the CLI, the cloud agent and the Local agent in VS Code. The cloud agent reads hooks only from
   `.github/hooks/*.json` in the cloned repository, so nothing in your home directory reaches it. Whether the
   JetBrains plugin reads `~/.copilot/hooks/` was not verified. Copilot code review has no hook surface.

4. Claude Code Cowork sessions and cloud sessions do not read `~/.claude/skills` on your machine at all. Cowork loads
   the skills enabled for your claude.ai account, and cloud sessions additionally load project skills from the cloned
   repository. So the global install covers your local sessions and not those two.

5. Kilo Code documents no environment variable that relocates its whole configuration directory. `KILO_CONFIG` and
   `KILO_CONFIG_CONTENT` pass configuration rather than moving the directory. The other four agents all have one:
   `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `OPENCODE_CONFIG_DIR`, and `COPILOT_HOME`.

6. Linked directories are documented for three agents and measured for the rest. Claude Code documents that a
   `<skill-name>` entry may be a symlink, Codex documents that it follows symlinked skill folders, and Kilo Code
   documents a linked `.kilo/agents/` with its `markdown_source` rule. The subagent and skills links in this document
   were measured on Windows 11 with junctions: Claude Code 2.1.281, OpenCode 1.18.32 and Kilo Code 7.7.9 each loaded
   the linked tree in a throwaway home. A Unix symlink in the same place was not measured.

7. Project settings win. A project that ran the per-project import brings its own `.claude/settings.json`,
   `opencode.json`, `.codex/config.toml`, and skills, and those take precedence over the global ones. Hooks are the
   exception: Claude Code and Codex run the global and the project hooks side by side. The formatting check handles
   that itself. The copy under `~/.agents/hooks/` stays silent in a project whose `.claude/settings.json`,
   `.claude/settings.local.json`, `.codex/config.toml`, `.codex/hooks.json` or `.github/hooks/*.json` already runs
   `no_ai_markers_check.py` on the same event, so one reply is never blocked twice and one batch never fixed twice.
   When it cannot read those files it checks anyway.

---

### Where these paths come from

Every path in this document was taken from the current published documentation, fetched on 2026-09-25, or measured
where the documentation says nothing. The measurements ran on Windows 11 against Claude Code 2.1.281, Codex 0.156.1,
OpenCode 1.18.32 and Kilo Code 7.7.9, each in a throwaway home.

| Agent | Pages used |
| --- | --- |
| Claude Code | [settings](https://code.claude.com/docs/en/settings), [skills](https://code.claude.com/docs/en/skills), [sub-agents](https://code.claude.com/docs/en/sub-agents), [memory](https://code.claude.com/docs/en/memory), [hooks](https://code.claude.com/docs/en/hooks), [MCP](https://code.claude.com/docs/en/mcp) |
| Codex | [build skills](https://learn.chatgpt.com/codex/build-skills), [subagents](https://learn.chatgpt.com/codex/agent-configuration/subagents), [hooks](https://learn.chatgpt.com/codex/hooks), [config basics](https://learn.chatgpt.com/codex/config-file/config-basic), [AGENTS.md](https://learn.chatgpt.com/codex/agent-configuration/agents-md), [MCP](https://learn.chatgpt.com/codex/extend/mcp) |
| OpenCode | [config](https://opencode.ai/docs/config/), [skills](https://opencode.ai/docs/skills/), [agents](https://opencode.ai/docs/agents/), [plugins](https://opencode.ai/docs/plugins/), [rules](https://opencode.ai/docs/rules/) |
| Kilo Code | [skills](https://kilo.ai/docs/customize/skills), [custom subagents](https://kilo.ai/docs/customize/custom-subagents), [plugins](https://kilo.ai/docs/automate/extending/plugins), [CLI](https://kilo.ai/docs/code-with-ai/platforms/cli), [custom rules](https://kilo.ai/docs/customize/custom-rules) |
| GitHub Copilot | [CLI config dir](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference), [agent skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills), [custom agents](https://docs.github.com/en/copilot/reference/custom-agents-configuration), [hooks](https://docs.github.com/en/copilot/reference/hooks-reference), [CLI custom instructions](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions), [VS Code hooks](https://code.visualstudio.com/docs/copilot/customization/hooks), [VS Code custom agents](https://code.visualstudio.com/docs/copilot/customization/custom-agents) |
