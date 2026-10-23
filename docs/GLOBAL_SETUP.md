# Global setup

Install the shared agent configuration once into your home directory so every project on the machine gets it, even the
ones that never ran the per-project import.

This is the counterpart to the per-project import in [AGENT_TOOLING.md](AGENT_TOOLING.md). The two are additive rather
than exclusive: an agent reads both scopes and merges them, so a project that also ran the per-project import keeps
winning on the paths where both scopes define the same thing.

One folder in your home directory, `~/.config/agents`, holds everything the agents can share: the instruction file `AGENTS.md`, the skills, the OpenCode-format subagents, the hook scripts, the OpenCode and Kilo Code plugin, and the updater. Each agent then reaches that folder through its own configuration directory, by a link, by one config line, or by an environment variable. No copy of this repository stays in your home directory: the install and every update fetch a temporary copy, take what they need out of it, and delete it.

Every command below comes in a PowerShell version and a Unix-shell version. Take only the sections for the agents you actually run. On Windows, `~` and `$HOME` both mean `%USERPROFILE%`, so `~/.config/agents` is `C:\Users\<you>\.config\agents`.

An install made before this layout lives in `~/.agents` instead. [Migrating from ~/.agents](#migrating-from-agents) moves it, and the updater refuses to run until it has moved.

---

### What each agent shares and what stays per tool

| What | Claude Code | Codex | OpenCode 1.x and 2.x | Kilo Code | GitHub Copilot |
| --- | --- | --- | --- | --- | --- |
| Configuration directory | `~/.claude`, left where it is | `~/.config/codex`, through `CODEX_HOME` | `~/.config/opencode` | `~/.config/kilo` | `~/.config/copilot`, through `COPILOT_HOME` |
| Always-on instructions | `~/.claude/CLAUDE.md`, a real file whose one line imports `~/.config/agents/AGENTS.md` | `~/.config/codex/AGENTS.md`, a link | `~/.config/opencode/AGENTS.md`, a link | `~/.config/kilo/AGENTS.md`, a link | `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` names `~/.config/agents` |
| Skills | `~/.claude/skills`, a real folder of per-skill links kept by a hook | `~/.config/codex/skills`, a real folder of per-skill links kept by the same hook | `skills.paths` in `opencode.json` | `skills.paths` in `kilo.jsonc` | `COPILOT_SKILLS_DIRS` names `~/.config/agents/skills` |
| Subagents | own format in `~/.claude/agents` | own TOML format in `~/.config/codex/agents` | `~/.config/opencode/agents`, a link to `~/.config/agents/agents` | `~/.config/kilo/agents`, a link to `~/.config/agents/agents` | own `*.agent.md` format in `~/.config/copilot/agents` |
| Hook scripts | shared, `~/.config/agents/hooks` | shared | shared | shared | shared |
| Hook wiring | `hooks` in `~/.claude/settings.json` | `~/.config/codex/hooks.json` | the shared plugin, declared by its directory in `opencode.json` | the same plugin, declared by its directory in `kilo.jsonc` | `~/.config/copilot/hooks/preflight.json` |
| MCP servers | `~/.claude.json`, written by `claude mcp add` | `[mcp_servers.*]` in `~/.config/codex/config.toml` | `mcp` in `~/.config/opencode/opencode.json`, or one shared file | `mcp` in `~/.config/kilo/kilo.jsonc`, or the same shared file | `~/.config/copilot/mcp-config.json`, VS Code user `mcp.json`, JetBrains `mcp.json` |

Claude Code keeps its own directory because `CLAUDE_CONFIG_DIR`, the variable that would move it, still leaks state back into `~/.claude` or loses it: issues [#80580](https://github.com/anthropics/claude-code/issues/80580), [#30538](https://github.com/anthropics/claude-code/issues/30538), [#98789](https://github.com/anthropics/claude-code/issues/98789), [#97680](https://github.com/anthropics/claude-code/issues/97680), [#90868](https://github.com/anthropics/claude-code/issues/90868), [#88603](https://github.com/anthropics/claude-code/issues/88603), [#100138](https://github.com/anthropics/claude-code/issues/100138) and [#80791](https://github.com/anthropics/claude-code/issues/80791) were all open when this layout was chosen. Re-check them before you move it.

So there are four subagent trees rather than six. OpenCode and Kilo Code read the same OpenCode-format files, so both
link to `~/.config/agents/agents`. Claude Code, Codex and Copilot each need their own format, for these reasons:

- Claude Code skips a subagent file with no `name` key, and the OpenCode format has none. Its documentation says a
  file with "No `name`" is treated "as documentation kept beside your agents"
  ([sub-agents docs](https://code.claude.com/docs/en/sub-agents)). The OpenCode format also writes `tools` as a map
  where Claude Code expects a list, and carries no `skills` list, so the skills a subagent preloads would be lost even
  if the file loaded. Measured with Claude Code 2.1.281 in a throwaway configuration directory: an `agents` junction to
  the OpenCode tree loaded none of the 25 subagents, and the same junction to the Claude tree loaded all 25.
- The reverse does not work either. OpenCode 1.18.32 rejected its whole configuration on the first Claude-format file
  ("Configuration is invalid"), and Kilo Code 7.7.9 skipped all 25 of them.
- Codex reads subagents only as "standalone TOML files under `~/.codex/agents/`"
  ([subagents docs](https://learn.chatgpt.com/codex/agent-configuration/subagents)), which is `$CODEX_HOME/agents` once `CODEX_HOME` is set.
- Copilot takes `tools` as a "list of strings, string" and stores personal agents in `~/.copilot/agents` "as
  `.agent.md` files"
  ([custom agents reference](https://docs.github.com/en/copilot/reference/custom-agents-configuration),
  [CLI config dir reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference)).
  The OpenCode `tools` map does not fit that. The Copilot CLI was not installed on the machine this was checked on, so
  this row rests on the documentation alone.

Two agents cannot take the shared skills folder as one directory link, because each writes into its own skills folder as well. Claude Code puts the skills it syncs from claude.ai in `~/.claude/skills/synced/` ([skills docs](https://code.claude.com/docs/en/skills): "Claude Code uses `~/.claude/skills/synced/` for skills downloaded from claude.ai"), and Codex puts its bundled skills in `$CODEX_HOME/skills/.system/`, measured with Codex 0.162.1. Through a whole-directory link both landed in the shared tree that every other agent scans. That is why both folders are real directories holding one link per shared skill, which [sync_skill_links.py](#the-skill-link-hook) keeps current.

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

You need `git`, and Python 3 for the hooks. Every script under `~/.config/agents/hooks/` is Python, and every wiring throws a
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
such as `~/.config/codex/AGENTS.md`, has to be a symbolic link instead, and on Windows that needs Developer Mode, in Settings,
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

Create `~/.config/agents`. PowerShell:

```powershell
New-Item -ItemType Directory -Force $HOME\.config\agents
```

Unix shell:

```bash
mkdir -p ~/.config/agents
```

Copy the five shared trees into it: `skills/`, the OpenCode-format `agents/`, the `hooks/` scripts, the `plugin/`
runner, and the `instructions/` folder holding the reply rules. PowerShell:

```powershell
foreach ($d in 'skills', 'agents', 'hooks', 'plugin', 'instructions') { Copy-Item -Recurse -Force "$src\.agents\$d" "$HOME\.config\agents\" }
```

Unix shell:

```bash
for d in skills agents hooks plugin instructions; do cp -R "$src/.agents/$d" ~/.config/agents/; done
```

Copy the updater into `~/.config/agents/bin`. It is the one command
[Updating the global installation](#updating-the-global-installation) runs, and every update keeps it current.
PowerShell:

```powershell
Copy-Item -Recurse -Force "$src\global\bin" "$HOME\.config\agents\"
```

Unix shell:

```bash
cp -R "$src/global/bin" ~/.config/agents/
```

Delete what you do not want before you go on. A skill folder or a subagent file you remove now stays removed, because
the update below refreshes only what you already have and never adds anything.

Record which commit you installed, so the update can tell which files upstream removed since and what changed in the
hook wiring. PowerShell:

```powershell
git -C $src rev-parse HEAD | Set-Content $HOME\.config\agents\.upstream-commit
```

Unix shell:

```bash
git -C "$src" rev-parse HEAD > ~/.config/agents/.upstream-commit
```

`preflight_gate.py` guards only the project a session is open in and never your home directory at large: it takes the
project root from the hook payload's own `cwd` field and from the working directory, and it treats its own location in
`~/.config/agents/hooks` as the user-level install rather than as a project.

Three of the hook scripts get wired per agent below, and the skill link hook in `hooks/claude/` a fourth, for Claude Code only. `markdown_lint_check.py` is not wired: it lints only files inside a project that imported `.agents/hooks`, where the project wiring already runs it, so a global wiring would start a second interpreter on every edit for nothing. It is copied anyway, together with the `_check_markdown.py` rules beside it, because the copy is one directory rather than a file list.

`task_list_sync.py` mirrors the agent's own task list into a file named `tasks.md` so a compaction cannot lose it, and writes the `tasks.widget.json` snapshot beside it. Both land at the project root when the working directory has an imported `.agents/hooks/` beside it. Your home directory never counts as a project, even when a linked `~/.agents` gives it a `.agents/hooks`, and the hook never writes either file there. A session that is in no project keeps both in the directory it started in, for example `~/.local/state/agents/workspace`, and a session started in your home directory keeps them in `$XDG_STATE_HOME/agents`, which is `~/.local/state/agents` when `XDG_STATE_HOME` is unset or not an absolute path. Add `tasks.md` and `tasks.widget.json` to your global gitignore if you start sessions inside repositories that do not import the hooks, so neither shows up as an untracked file.

Git reads the global ignore file named by `core.excludesFile`, and without one it reads `$XDG_CONFIG_HOME/git/ignore`, which is `~/.config/git/ignore` when `XDG_CONFIG_HOME` is not set ([gitignore docs](https://git-scm.com/docs/gitignore): "If $XDG_CONFIG_HOME is either not set or empty, $HOME/.config/git/ignore is used instead"). See whether you named a file of your own. It prints nothing when you did not, in either shell:

```bash
git config --global core.excludesFile
```

When it prints nothing, add both names to `~/.config/git/ignore`, each only once. When it prints a path, use that path in the command instead. Unix shell:

```bash
mkdir -p ~/.config/git && for p in tasks.md tasks.widget.json; do grep -qxF "$p" ~/.config/git/ignore 2>/dev/null || printf '\n%s\n' "$p" >> ~/.config/git/ignore; done
```

PowerShell:

```powershell
New-Item -ItemType Directory -Force $HOME\.config\git | Out-Null; foreach ($p in 'tasks.md', 'tasks.widget.json') { if (-not ((Test-Path $HOME\.config\git\ignore) -and (Get-Content $HOME\.config\git\ignore) -contains $p)) { Add-Content $HOME\.config\git\ignore "`n$p" } }
```

Check from inside any repository. Each name prints with the file and line that ignores it:

```bash
git check-ignore -v tasks.md tasks.widget.json
```

---

### Step 3, the always-on instructions

`~/.config/agents/AGENTS.md` is the one instruction file. Every agent reaches it from its own directory, as its section below shows. On a new machine it comes from `global/AGENTS.md.example` in the temporary copy, a template of rules about how you work in every project, with nothing project-specific in it. The root `AGENTS.md.example` is the per-project template and is not the one to use here. Copy the global template, only when you have no instruction file there yet. PowerShell:

```powershell
if (-not (Test-Path $HOME\.config\agents\AGENTS.md)) { Copy-Item "$src\global\AGENTS.md.example" $HOME\.config\agents\AGENTS.md }
```

Unix shell:

```bash
[ -e ~/.config/agents/AGENTS.md ] || cp "$src/global/AGENTS.md.example" ~/.config/agents/AGENTS.md
```

Then make the copy yours. Neither the install nor `update-global.sh` or `update-global.ps1` ever writes this file once it exists: the updaters refresh only the `hooks`, `plugin`, `instructions`, `bin`, `skills` and `agents` folders under `~/.config/agents`, so your changes survive every update, and a later change to the template reaches you only when you take it in yourself with the commands below.

Delete the template's own note at the top, the paragraph that starts with "This is a template". Unix shell, which keeps the previous version as `AGENTS.md.bak` beside it:

```bash
sed -i.bak '/^This is a template\. /{N;d;}' ~/.config/agents/AGENTS.md
```

PowerShell:

```powershell
(Get-Content -Raw $HOME\.config\agents\AGENTS.md) -replace '(?m)^This is a template\. .*\r?\n\r?\n', '' | Set-Content -NoNewline $HOME\.config\agents\AGENTS.md
```

Check that the note is gone. It prints nothing. Unix shell:

```bash
grep -n '^This is a template' ~/.config/agents/AGENTS.md
```

PowerShell:

```powershell
Select-String -Path $HOME\.config\agents\AGENTS.md -Pattern '^This is a template'
```

Every rule in the template is one line, so a rule you do not want goes with one command that names the words its line starts with. Put the start of your rule in place of `4\. When two rules still pull`, with a backslash before every dot. Unix shell:

```bash
sed -i.bak '/^4\. When two rules still pull/d' ~/.config/agents/AGENTS.md
```

PowerShell:

```powershell
(Get-Content $HOME\.config\agents\AGENTS.md) | Where-Object { $_ -notmatch '^4\. When two rules still pull' } | Set-Content $HOME\.config\agents\AGENTS.md
```

To change words inside a rule instead, replace them in place. Put your own words in place of `old words` and `new words`. Unix shell:

```bash
sed -i.bak 's/old words/new words/' ~/.config/agents/AGENTS.md
```

PowerShell:

```powershell
(Get-Content -Raw $HOME\.config\agents\AGENTS.md).Replace('old words', 'new words') | Set-Content -NoNewline $HOME\.config\agents\AGENTS.md
```

Check the result by searching for the words you removed or wrote. Unix shell:

```bash
grep -n 'new words' ~/.config/agents/AGENTS.md
```

PowerShell:

```powershell
Select-String -Path $HOME\.config\agents\AGENTS.md -Pattern 'new words'
```

The reply rules stay a separate file, `~/.config/agents/instructions/reply-rules.md`, and are never merged into `AGENTS.md`. A project loads its own copy through the `instructions` key of `opencode.json` on OpenCode 1.x and Kilo Code. OpenCode 2.x ignores that key, expands neither an `@path` line nor a markdown link in `AGENTS.md`, and replaces the whole base prompt when an agent's `system` names a file, so the plugin adds the rules itself there: on every model request it pushes the project's `.agents/instructions/reply-rules.md`, or this global copy when the project has none, as one more system part, which keeps the built-in prompt. It skips a session whose `parentID` marks it as a subagent, because only the main thread's reply reaches the user, and a session it cannot place still gets the rules. Measured with OpenCode 2.0.26. On OpenCode 1.x and Kilo Code the `instructions` key loads the rules into every agent, subagents included, and that stays as it is. On Claude Code, a subagent loads the same CLAUDE.md hierarchy as the main conversation, `~/.claude/CLAUDE.md` and the `AGENTS.md` it imports included, unless its definition sets `omitClaudeMd: true` ([sub-agents](https://code.claude.com/docs/en/sub-agents), "What loads at startup"), so any rule placed there reaches subagents too. On Claude Code, Codex and Copilot, whether a global install should load them is still open. TODO: decide and document the route for those three.

---

### Step 4, the environment variables

Codex and Copilot find their configuration directory, and Copilot finds the shared skills and instructions, through environment variables. Set them for your user account rather than one shell, so an agent started from a desktop launcher sees them too.

| Variable | Value | Read by |
| --- | --- | --- |
| `CODEX_HOME` | `~/.config/codex` | Codex |
| `COPILOT_HOME` | `~/.config/copilot` | GitHub Copilot CLI |
| `COPILOT_SKILLS_DIRS` | `~/.config/agents/skills` | GitHub Copilot CLI |
| `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` | `~/.config/agents` | GitHub Copilot CLI |

Copilot documents `COPILOT_SKILLS_DIRS` as "Comma-separated list of additional directories for skills" and `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` as "Comma-separated list of additional directories for custom instructions", read for "Additional `AGENTS.md` and `*.instructions.md` files" ([CLI command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference), [custom instructions](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions)). Setting `COPILOT_HOME` was observed to stop the CLI scanning `~/.agents/skills`, which is one more reason to name the skills folder explicitly.

#### Linux

A systemd user session reads `~/.config/environment.d/*.conf`, lines of `KEY=VALUE` whose right side may use `${OTHER_KEY}` ([environment.d](https://www.freedesktop.org/software/systemd/man/latest/environment.d.html)). Write `${HOME}`, never `~`, because the file is not read by a shell. Create the directory:

```bash
mkdir -p ~/.config/environment.d
```

Write the file:

```bash
printf '%s\n' 'CODEX_HOME=${HOME}/.config/codex' 'COPILOT_HOME=${HOME}/.config/copilot' 'COPILOT_SKILLS_DIRS=${HOME}/.config/agents/skills' 'COPILOT_CUSTOM_INSTRUCTIONS_DIRS=${HOME}/.config/agents' > ~/.config/environment.d/60-agents.conf
```

Check it. It prints the four lines:

```bash
cat ~/.config/environment.d/60-agents.conf
```

That reaches everything the user manager starts, a terminal opened from the desktop included. It does not reach an SSH login or a text console: "For other instances of the shell, not launched by the user service manager, the environment they inherit is defined by the program that starts them" (same page). Source the same file from your shell's start-up file so those get it too.

Skip the two lines below when your shell already imports every file in `~/.config/environment.d/`, because `60-agents.conf` then arrives with the rest and a second line only loads it twice. Check for an import first:

```bash
grep -n 'environment.d' ~/.zshenv ~/.config/zsh/.zshenv ~/.profile ~/.bash_profile ~/.bashrc 2>/dev/null
```

A loop over `environment.d/*.conf` in that output means this step is already done. That is the recommended zsh layout, where `~/.zshenv` only points zsh at `~/.config/zsh` and the `.zshenv` there does the import for every shell, login or not, interactive or not. `~/.zshenv` holds:

```zsh
export ZDOTDIR="$HOME/.config/zsh"
[ -r "$ZDOTDIR/.zshenv" ] && . "$ZDOTDIR/.zshenv"
```

`~/.config/zsh/.zshenv` removes duplicate PATH entries, imports every `.conf` file, then drops PATH entries that are not a directory:

```zsh
typeset -U path PATH
for env_conf in "$HOME"/.config/environment.d/*.conf(N); do set -a; . "$env_conf"; set +a; done
unset env_conf
path=($^path(N-/))
```

Without such an import, add one line for this file. For zsh, which reads `~/.zshenv` for every shell:

```bash
printf '%s\n' 'set -a; . "$HOME/.config/environment.d/60-agents.conf"; set +a' >> ~/.zshenv
```

For bash and other POSIX shells, the same line goes in `~/.profile`, or in `~/.bash_profile` if you have one, because bash then skips `~/.profile`. One command writes it to whichever of the two applies:

```bash
f=~/.profile; [ -e ~/.bash_profile ] && f=~/.bash_profile; printf '%s\n' 'set -a; . "$HOME/.config/environment.d/60-agents.conf"; set +a' >> "$f"
```

Check that the line is there, in whichever of the files you wrote. It prints the line with its number:

```bash
grep -n '60-agents.conf' ~/.zshenv ~/.profile ~/.bash_profile 2>/dev/null
```

Sign out and back in once, so the desktop session picks the file up.

#### macOS

A terminal shell reads `~/.zshenv`. Add the four exports there:

```bash
printf '%s\n' 'export CODEX_HOME="$HOME/.config/codex"' 'export COPILOT_HOME="$HOME/.config/copilot"' 'export COPILOT_SKILLS_DIRS="$HOME/.config/agents/skills"' 'export COPILOT_CUSTOM_INSTRUCTIONS_DIRS="$HOME/.config/agents"' >> ~/.zshenv
```

Check it. It prints the four lines with their numbers:

```bash
grep -nE 'CODEX_HOME|COPILOT_' ~/.zshenv
```

An application started from the Dock or Finder reads no shell file, so set the same variables for the login session with a LaunchAgent that runs `launchctl setenv` at login. Create its folder:

```bash
mkdir -p ~/Library/LaunchAgents
```

Write the file. The quotes around `EOF` keep the shell from changing anything inside it:

```bash
tee ~/Library/LaunchAgents/local.agents.environment.plist >/dev/null <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>local.agents.environment</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/sh</string>
    <string>-c</string>
    <string>launchctl setenv CODEX_HOME /Users/you/.config/codex; launchctl setenv COPILOT_HOME /Users/you/.config/copilot; launchctl setenv COPILOT_SKILLS_DIRS /Users/you/.config/agents/skills; launchctl setenv COPILOT_CUSTOM_INSTRUCTIONS_DIRS /Users/you/.config/agents</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
</dict>
</plist>
EOF
```

Put your real home directory in place of `/Users/you`. The macOS `sed` needs the empty `''` after `-i`:

```bash
sed -i '' "s#/Users/you#$HOME#g" ~/Library/LaunchAgents/local.agents.environment.plist
```

Check that the file is valid. It prints the path followed by `OK`:

```bash
plutil -lint ~/Library/LaunchAgents/local.agents.environment.plist
```

Check that it names your home directory. It prints the four paths:

```bash
grep -o "$HOME/[^ ;<]*" ~/Library/LaunchAgents/local.agents.environment.plist
```

Load it once now, and launchd loads it at every login after:

```bash
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/local.agents.environment.plist
```

Neither half was run on a Mac for this guide.

#### Windows

Set each variable for your user account. PowerShell:

```powershell
setx CODEX_HOME "$HOME\.config\codex"
```

```powershell
setx COPILOT_HOME "$HOME\.config\copilot"
```

```powershell
setx COPILOT_SKILLS_DIRS "$HOME\.config\agents\skills"
```

```powershell
setx COPILOT_CUSTOM_INSTRUCTIONS_DIRS "$HOME\.config\agents"
```

`setx` writes the user environment and does not change the shell it runs in, so open a new terminal, or sign out and back in for applications started from the Start menu.

Check what the user environment now holds. It prints the four names with their values, in any shell:

```powershell
'CODEX_HOME', 'COPILOT_HOME', 'COPILOT_SKILLS_DIRS', 'COPILOT_CUSTOM_INSTRUCTIONS_DIRS' | ForEach-Object { "$_=$([Environment]::GetEnvironmentVariable($_, 'User'))" }
```

---

### Per-agent setup

Every subsection assumes steps 1 to 4 are done. Adding a second agent later is nothing more than running its
subsection too, because the shared folder is the same files. The commands that write a configuration file read their
block, or the shipped server list, out of the temporary copy from step 1, so run them before the finish step deletes
it, and make a new copy as in step 1 when you come back later.

#### Claude Code

Claude Code stays in `~/.claude`. It reads personal skills from `~/.claude/skills/<skill-name>/SKILL.md`, where a `<skill-name>` entry "can be a symlink to a directory elsewhere on disk" ([skills docs](https://code.claude.com/docs/en/skills)), personal subagents from `~/.claude/agents/` ([sub-agents docs](https://code.claude.com/docs/en/sub-agents)), user hooks from `~/.claude/settings.json`, and personal instructions from `~/.claude/CLAUDE.md` ([memory docs](https://code.claude.com/docs/en/memory)).

Create the directory. PowerShell:

```powershell
New-Item -ItemType Directory -Force $HOME\.claude
```

Unix shell:

```bash
mkdir -p ~/.claude
```

Make `~/.claude/CLAUDE.md` a real file that imports the shared one, rather than a link to it. "CLAUDE.md files can import additional files using `@path/to/import` syntax", and a user-scope file's imports load without a prompt (memory docs). A link would not do, because in a Cowork session Claude Code "skips a `~/.claude/CLAUDE.md` that is itself a symlink or hard link". A real file still loads there, but Cowork also "skips any import in a user-scope file that resolves to a path outside the session's working directory", so anything that must reach a Cowork session has to be written into `~/.claude/CLAUDE.md` itself, below the import. If you already have a `~/.claude/CLAUDE.md`, move its content into `~/.config/agents/AGENTS.md` first. PowerShell:

```powershell
if (-not (Test-Path $HOME\.claude\CLAUDE.md)) { Set-Content -Path $HOME\.claude\CLAUDE.md -Value '@~/.config/agents/AGENTS.md' }
```

Unix shell:

```bash
[ -e ~/.claude/CLAUDE.md ] || printf '%s\n' '@~/.config/agents/AGENTS.md' > ~/.claude/CLAUDE.md
```

Check it. The first line is the import. PowerShell:

```powershell
Get-Content $HOME\.claude\CLAUDE.md -TotalCount 1
```

Unix shell:

```bash
head -n 1 ~/.claude/CLAUDE.md
```

Give Claude Code its skills. On Linux and macOS, `~/.claude/skills` is a real directory and [the skill link hook](#the-skill-link-hook) fills it with one link per shared skill, so create it empty and let the hook run once:

```bash
mkdir -p ~/.claude/skills
```

```bash
python3 -S -E ~/.config/agents/hooks/claude/sync_skill_links.py
```

On Windows the hook does nothing, because per-skill junctions were never tested there. Link the whole directory instead, and accept that the skills Claude Code syncs from claude.ai then land in `~/.config/agents/skills/synced/`, where the updater and the hook both ignore them but other agents may scan them. PowerShell:

```powershell
New-Item -ItemType Junction -Path $HOME\.claude\skills -Target $HOME\.config\agents\skills
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
([hooks docs](https://code.claude.com/docs/en/hooks)). The block names your home directory as `/home/you`, and the
command below it writes your real one in its place, with forward slashes on Windows too, which work there and need no
escaping inside JSON.

This is the same event set the per-project wiring uses, minus the markdown lint pass, plus the skill link hook. Claude Code keeps the long
preflight text with the full status block, while Codex and Copilot below use the short one-line opening.
`SessionStart` and `UserPromptSubmit` inject the gate text, `SessionStart` also injects the rule for checking on
background subagents
every 10 minutes, and its second group runs the skill link hook when a session starts or resumes: the `startup` and `resume` matcher values are the ones Claude Code documents for "New session" and resumed sessions (hooks docs), so a `/clear` or a compaction never runs it again. `SubagentStart` tells a subagent to do its delegated task itself rather than hand it on,
`PreToolUse` is the blocking half, `MessageDisplay` fixes dashes, bold and italic on
screen (Claude Code 2.1.152 or later), `Stop` checks what that fix leaves, nothing checks a subagent's reply style because only the main thread's reply reaches the user,
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
            "command": "echo 'PREFLIGHT: before code work, name the skills and subagents that own this task and invoke them, or say none apply and why. Delegate investigation, review and bounded implementation by default. If the prompt asks anything, answer every question first, then start the work. End every reply to the user with this block, exactly as shown: no heading, no bullets, no numbered list, plain lines only, keeping every blank line:\n\nRunning: `running task name` (or: nothing)\n\n~~DONE: older finished task~~\n~~DONE: most recent finished task~~\n\nNOW: what is being done right now\n\nNext: the next task\nThen: the task after that\n\nWaiting on: what you wait for (or: nothing)\n\nWhen several tasks run, list each name in backticks on the Running line, separated by commas.'"
          },
          {
            "type": "command",
            "command": "echo 'When you launch a background subagent, note how long its task should take and schedule a recurring check every 10 minutes while any subagent runs. At each check compare its running time and latest output with that expectation. Leave it alone unless it is far over (for example 30 minutes on a task that should take 1) or clearly looping, then ask it for status or stop it and tell the user why.'"
          },
          {
            "type": "command",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.config/agents/hooks/task_list_sync.py --event sessionstart --format claude ; exit 0"
          }
        ]
      },
      {
        "matcher": "startup|resume",
        "hooks": [
          {
            "type": "command",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.config/agents/hooks/claude/sync_skill_links.py ; exit 0"
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo 'PREFLIGHT: before code work, name the skills and subagents that own this task and invoke them, or say none apply and why. Delegate investigation, review and bounded implementation by default. If the prompt asks anything, answer every question first, then start the work. End every reply to the user with this block, exactly as shown: no heading, no bullets, no numbered list, plain lines only, keeping every blank line:\n\nRunning: `running task name` (or: nothing)\n\n~~DONE: older finished task~~\n~~DONE: most recent finished task~~\n\nNOW: what is being done right now\n\nNext: the next task\nThen: the task after that\n\nWaiting on: what you wait for (or: nothing)\n\nWhen several tasks run, list each name in backticks on the Running line, separated by commas.'"
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
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.config/agents/hooks/preflight_gate.py --format claude ; exit 0"
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
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.config/agents/hooks/task_list_sync.py --event precompact --format claude ; exit 0"
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
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.config/agents/hooks/task_list_sync.py --event taskcreated --format claude ; exit 0"
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
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.config/agents/hooks/task_list_sync.py --event taskcompleted --format claude ; exit 0"
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
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.config/agents/hooks/no_ai_markers_check.py --format claude --display-fixed ; exit 0"
          },
          {
            "type": "command",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.config/agents/hooks/task_list_sync.py --event stop --format claude ; exit 0"
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
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.config/agents/hooks/no_ai_markers_check.py --format claude --display ; exit 0"
          }
        ]
      }
    ]
  }
}
```

Write it with one command. The command reads the block above out of the temporary copy from step 1, so run it before you delete the copy. It puts your home directory in place of `/home/you` and merges the block into `~/.claude/settings.json`, or creates the file when there is none. Every other key in the file stays as it is. In each event, a hook group this install wrote earlier, recognised by a path into `agents/hooks/` or by the wording of the reminder, is replaced, and every other group of yours is kept, so running the command again changes nothing. A file that is not plain JSON stops it with an error before anything is written. The file is written back with two-space indentation. Unix shell:

```bash
python3 -c 'import json,re,sys,pathlib;h=pathlib.Path.home();g=pathlib.Path(sys.argv[1]).read_text(encoding="utf-8");b=json.loads([x for x in re.findall(r"^\x60{3}json\n(.*?)^\x60{3}$",g,re.M|re.S) if sys.argv[2] in x][0].replace("/home/you/",h.as_posix()+"/"));p=h.joinpath(sys.argv[3]);s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};o=lambda x:any(m in json.dumps(x) for m in ("agents/hooks/","PREFLIGHT","Before code work","background subagent"));e=s.setdefault("hooks",{});[e.update({k:[x for x in e.get(k,[]) if not o(x)]+v}) for k,v in b["hooks"].items()];[s.setdefault(k,v) for k,v in b.items()];p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")' "$src/docs/GLOBAL_SETUP.md" MessageDisplay .claude/settings.json
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,re,sys,pathlib;h=pathlib.Path.home();g=pathlib.Path(sys.argv[1]).read_text(encoding="utf-8");b=json.loads([x for x in re.findall(r"^\x60{3}json\n(.*?)^\x60{3}$",g,re.M|re.S) if sys.argv[2] in x][0].replace("/home/you/",h.as_posix()+"/"));p=h.joinpath(sys.argv[3]);s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};o=lambda x:any(m in json.dumps(x) for m in ("agents/hooks/","PREFLIGHT","Before code work","background subagent"));e=s.setdefault("hooks",{});[e.update({k:[x for x in e.get(k,[]) if not o(x)]+v}) for k,v in b["hooks"].items()];[s.setdefault(k,v) for k,v in b.items()];p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")' "$src\docs\GLOBAL_SETUP.md" MessageDisplay .claude/settings.json
```

Check it. It prints every hook script the file now runs, each under your own home directory. Unix shell:

```bash
grep -o '[^ "]*/\.config/agents/hooks/[^ "]*' ~/.claude/settings.json
```

PowerShell:

```powershell
Select-String -Path $HOME\.claude\settings.json -Pattern '[^ "]*/\.config/agents/hooks/[^ "]*' -AllMatches | ForEach-Object { $_.Matches.Value }
```

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

Check it, in either shell. "To check that Claude Code connected, run `claude mcp get <name>`" (MCP docs):

```bash
claude mcp get context7
```

#### Codex

Codex keeps its configuration in `CODEX_HOME`, which step 4 points at `~/.config/codex`. Everything below lands there. Create it. PowerShell:

```powershell
New-Item -ItemType Directory -Force $HOME\.config\codex
```

Unix shell:

```bash
mkdir -p ~/.config/codex
```

Point Codex at the instruction file. It reads `AGENTS.md` from its home directory
([AGENTS.md docs](https://learn.chatgpt.com/codex/agent-configuration/agents-md)), so make that a link. PowerShell:

```powershell
New-Item -ItemType SymbolicLink -Path $HOME\.config\codex\AGENTS.md -Target $HOME\.config\agents\AGENTS.md
```

Unix shell:

```bash
ln -s ../agents/AGENTS.md ~/.config/codex/AGENTS.md
```

Give Codex the skills. Codex scans `$HOME/.agents/skills` and, as a "Deprecated user skills location (`$CODEX_HOME/skills`), kept for backward compatibility", the `skills` folder in its home (`host_roots.rs` in [openai/codex](https://github.com/openai/codex)), and it "supports symlinked skill folders and follows the symlink target" ([build skills](https://learn.chatgpt.com/codex/build-skills)). It also writes its own bundled skills into `$CODEX_HOME/skills/.system/`, so the folder stays real and [the skill link hook](#the-skill-link-hook) fills it with one link per shared skill. On Linux and macOS:

```bash
mkdir -p ~/.config/codex/skills
```

```bash
python3 -S -E ~/.config/agents/hooks/claude/sync_skill_links.py
```

On Windows, where the hook does nothing, link each skill folder with a junction instead, and repeat that for a skill added later. PowerShell:

```powershell
Get-ChildItem -Directory $HOME\.config\agents\skills | ForEach-Object { New-Item -ItemType Junction -Path "$HOME\.config\codex\skills\$($_.Name)" -Target $_.FullName }
```

When upstream removes the deprecated location, the skills move to `~/.agents/skills` or a `skills` setting Codex documents by then, and this step changes with it.

Copy the TOML subagents into `~/.config/codex/agents/`
([subagents](https://learn.chatgpt.com/codex/agent-configuration/subagents)). PowerShell:

```powershell
Copy-Item -Recurse -Force "$src\.codex\agents" $HOME\.config\codex\
```

Unix shell:

```bash
cp -R "$src/.codex/agents" ~/.config/codex/
```

Wire the hooks in `~/.config/codex/hooks.json`, which is the user-level hooks file
([hooks docs](https://learn.chatgpt.com/codex/hooks)). The same tables can go inline in `~/.config/codex/config.toml` instead,
and Codex asks you to pick one form per configuration layer rather than using both. The command below the block puts
your home directory in place of `/home/you`. All
five events matter: `UserPromptSubmit` injects the reminder on the main thread, `SubagentStart` injects the subagent
text inside a subagent, `PreToolUse` is the blocking half, `Stop` checks the reply formatting, and `SessionStart` puts
the task list back. The two texts differ on purpose: the reminder tells its reader to delegate, and a subagent told
that turns its own task away, so a subagent is told to do the work itself instead. The `|| exit 0` on every script
`command` and the
`; exit 0` on every `commandWindows` are what make a missing or broken script allow the call instead of denying every
one of them. Each command needs its `commandWindows` sibling, because Codex picks one of the two per platform and a
command with no sibling is simply absent on the other. Codex runs `commandWindows` in PowerShell, `pwsh` when it is
installed and Windows PowerShell otherwise, and Windows PowerShell has no `||`, which is why the Windows lines end in
`; exit 0` and send errors to `$null` rather than `nul`. Codex 0.156.1 tries `pwsh`, then `powershell.exe`, then
`cmd`, and runs a PowerShell with `-NoProfile -Command` and `cmd` with `/c` (`get_powershell_shell` in
`codex-rs/shell-command/src/shell_detect.rs` and `derive_exec_args` in `codex-rs/core/src/shell.rs`, tag
`rust-v0.156.1` of [openai/codex](https://github.com/openai/codex)).

Codex tracks every hook by a hash of its definition: "new or changed hooks are marked for review and skipped until
trusted" ([hooks docs](https://learn.chatgpt.com/docs/hooks)). After you write or refresh these entries, open an
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
            "command": "grep -F '\"agent_id\"' >/dev/null || printf '%s\\n' '{\"hookSpecificOutput\": {\"hookEventName\": \"UserPromptSubmit\", \"additionalContext\": \"Before code work, name the skills and subagents that own this task and invoke them, or say none apply and why, in one line. End every reply with the status block the skill describes, plain text only.\"}}'",
            "commandWindows": "if (-not [Console]::In.ReadToEnd().Contains(\"`\"agent_id`\"\")) { echo '{\"hookSpecificOutput\": {\"hookEventName\": \"UserPromptSubmit\", \"additionalContext\": \"Before code work, name the skills and subagents that own this task and invoke them, or say none apply and why, in one line. End every reply with the status block the skill describes, plain text only.\"}}' }; exit 0"
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
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.config/agents/hooks/task_list_sync.py --event sessionstart --format codex 2>/dev/null || exit 0",
            "commandWindows": "$root = git rev-parse --show-toplevel 2>$null; if ($root) { Set-Location -LiteralPath $root }; python -S -E /home/you/.config/agents/hooks/task_list_sync.py --event sessionstart --format codex 2>$null; exit 0"
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
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.config/agents/hooks/no_ai_markers_check.py --format codex 2>/dev/null || exit 0",
            "commandWindows": "$root = git rev-parse --show-toplevel 2>$null; if ($root) { Set-Location -LiteralPath $root }; python -S -E /home/you/.config/agents/hooks/no_ai_markers_check.py --format codex 2>$null; exit 0"
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
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.config/agents/hooks/preflight_gate.py --format codex 2>/dev/null || exit 0",
            "commandWindows": "$root = git rev-parse --show-toplevel 2>$null; if ($root) { Set-Location -LiteralPath $root }; python -S -E /home/you/.config/agents/hooks/preflight_gate.py --format codex 2>$null; exit 0"
          }
        ]
      }
    ]
  }
}
```

Write it with the same command as under [Claude Code](#claude-code), with the Codex marker and file. It reads the block above from the temporary copy, replaces only the hook groups this install wrote, and keeps the rest of your file. Unix shell:

```bash
python3 -c 'import json,re,sys,pathlib;h=pathlib.Path.home();g=pathlib.Path(sys.argv[1]).read_text(encoding="utf-8");b=json.loads([x for x in re.findall(r"^\x60{3}json\n(.*?)^\x60{3}$",g,re.M|re.S) if sys.argv[2] in x][0].replace("/home/you/",h.as_posix()+"/"));p=h.joinpath(sys.argv[3]);s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};o=lambda x:any(m in json.dumps(x) for m in ("agents/hooks/","PREFLIGHT","Before code work","background subagent"));e=s.setdefault("hooks",{});[e.update({k:[x for x in e.get(k,[]) if not o(x)]+v}) for k,v in b["hooks"].items()];[s.setdefault(k,v) for k,v in b.items()];p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")' "$src/docs/GLOBAL_SETUP.md" commandWindows .config/codex/hooks.json
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,re,sys,pathlib;h=pathlib.Path.home();g=pathlib.Path(sys.argv[1]).read_text(encoding="utf-8");b=json.loads([x for x in re.findall(r"^\x60{3}json\n(.*?)^\x60{3}$",g,re.M|re.S) if sys.argv[2] in x][0].replace("/home/you/",h.as_posix()+"/"));p=h.joinpath(sys.argv[3]);s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};o=lambda x:any(m in json.dumps(x) for m in ("agents/hooks/","PREFLIGHT","Before code work","background subagent"));e=s.setdefault("hooks",{});[e.update({k:[x for x in e.get(k,[]) if not o(x)]+v}) for k,v in b["hooks"].items()];[s.setdefault(k,v) for k,v in b.items()];p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")' "$src\docs\GLOBAL_SETUP.md" commandWindows .config/codex/hooks.json
```

Check it. It prints every hook script the file now runs. Unix shell:

```bash
grep -o '[^ "]*/\.config/agents/hooks/[^ "]*' ~/.config/codex/hooks.json
```

PowerShell:

```powershell
Select-String -Path $HOME\.config\codex\hooks.json -Pattern '[^ "]*/\.config/agents/hooks/[^ "]*' -AllMatches | ForEach-Object { $_.Matches.Value }
```

MCP servers go in `[mcp_servers.<name>]` tables in `~/.config/codex/config.toml`, which is shared by the Codex CLI, the IDE extension, and the ChatGPT desktop app ([MCP docs](https://learn.chatgpt.com/codex/extend/mcp)). Add each machine-wide server with `codex mcp add`, which writes the table for you. The MCP page gives this very example: "to add Context7 (a free MCP server for developer documentation), you can run the following command: `codex mcp add context7 -- npx -y @upstash/context7-mcp`" ([MCP docs](https://learn.chatgpt.com/docs/extend/mcp), read 2026-10-23). The command below pins the same `@latest` tag the shipped table uses. In either shell:

```bash
codex mcp add context7 -- npx -y @upstash/context7-mcp@latest
```

Check it. "Run `codex mcp list` to see configured servers" (same page):

```bash
codex mcp list
```

Add another server from [MCP_SETUP.md](MCP_SETUP.md) the same way, with its command and arguments after the `--`. Never pass a token on that command line with `--env`, because it then lands in your shell history. Codex has no substitution for a token, as [Codex and Copilot CLI globals](MCP_SETUP.md#codex-and-copilot-cli-globals) explains.

#### OpenCode

Everything here applies to OpenCode 1.x and 2.x alike, except where a 2.x difference is named. Measured with OpenCode 1.19.0 and 2.0.26, each in a throwaway home.

Create the configuration directory. PowerShell:

```powershell
New-Item -ItemType Directory -Force $HOME\.config\opencode
```

Unix shell:

```bash
mkdir -p ~/.config/opencode
```

Point OpenCode at the instruction file. Its global rules file is `~/.config/opencode/AGENTS.md` ([rules docs](https://opencode.ai/docs/rules/)), so make that a link. Do not rely on the fallback the 1.x rules page describes, "Global rules: ~/.claude/CLAUDE.md (used if no ~/.config/opencode/AGENTS.md exists)": OpenCode 2.x does not fall back to `~/.claude/CLAUDE.md`, and it ignores the `instructions` key, so the link is the one route both read. PowerShell:

```powershell
New-Item -ItemType SymbolicLink -Path $HOME\.config\opencode\AGENTS.md -Target $HOME\.config\agents\AGENTS.md
```

Unix shell:

```bash
ln -s ../agents/AGENTS.md ~/.config/opencode/AGENTS.md
```

Link the subagents to the shared tree. The global location is `~/.config/opencode/agents/`
([agents docs](https://opencode.ai/docs/agents/)). If the directory already exists, move it aside first, because the link needs its name.
PowerShell:

```powershell
New-Item -ItemType Junction -Path $HOME\.config\opencode\agents -Target $HOME\.config\agents\agents
```

Unix shell:

```bash
ln -s ../agents/agents ~/.config/opencode/agents
```

Name the skills folder and declare the plugin in `~/.config/opencode/opencode.json`, as the block below shows for a home directory of `/home/you`. The plugin entry is the `plugin` directory rather than `hooks.js`: every loader resolves a directory to its `index.js`, which re-exports the one default export `{ id, server, setup }` that 1.x and Kilo Code call through `server` and 2.x through `setup`. Declaring it by path rather than copying it means an update reaches OpenCode with nothing else to do.

```jsonc
{
  "skills": { "paths": ["/home/you/.config/agents/skills"] },
  "plugin": ["/home/you/.config/agents/plugin"]
}
```

Write it with one command, which puts your own home directory in. It merges into the file you have, or creates it, and keeps every other key. It also removes what an install made before the `~/.config/agents` layout left there: a `plugin` entry into an old `agents/plugin` folder, and an `instructions` entry that names `~/.claude/CLAUDE.md`. Running it again changes nothing. A file that is not plain JSON, for example one with comments, stops it with an error before anything is written. Unix shell:

```bash
python3 -c 'import json,pathlib;h=pathlib.Path.home();p=h/".config/opencode/opencode.json";s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};a=h.as_posix()+"/.config/agents/";k=s.setdefault("skills",{});k["paths"]=[x for x in k.get("paths",[]) if x!=a+"skills"]+[a+"skills"];s["plugin"]=[x for x in s.get("plugin",[]) if "agents/plugin" not in str(x)]+[a+"plugin"];i=[x for x in s.pop("instructions",[]) if ".claude/CLAUDE.md" not in str(x)];s.update({"instructions":i} if i else {});p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")'
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,pathlib;h=pathlib.Path.home();p=h/".config/opencode/opencode.json";s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};a=h.as_posix()+"/.config/agents/";k=s.setdefault("skills",{});k["paths"]=[x for x in k.get("paths",[]) if x!=a+"skills"]+[a+"skills"];s["plugin"]=[x for x in s.get("plugin",[]) if "agents/plugin" not in str(x)]+[a+"plugin"];i=[x for x in s.pop("instructions",[]) if ".claude/CLAUDE.md" not in str(x)];s.update({"instructions":i} if i else {});p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")'
```

Check it. It prints the file. Unix shell:

```bash
cat ~/.config/opencode/opencode.json
```

PowerShell:

```powershell
Get-Content $HOME\.config\opencode\opencode.json
```

Leave `~/.config/opencode/plugins/` without a copy of the plugin. Files in that directory load automatically at
startup ([plugins docs](https://opencode.ai/docs/plugins/)), so a copy there would load the runner a second time.

The plugin prefers the project's own `.agents/hooks/` and falls back to `~/.config/agents/hooks/`, so it gates every project,
including one that never ran the per-project import.
[How the OpenCode and Kilo Code plugin finds its hooks](#how-the-opencode-and-kilo-code-plugin-finds-its-hooks) has
the order and the per-project opt-out.

On 2.x the plugin also adds the reply rules through the session `context` hook, as [step 3](#step-3-the-always-on-instructions) describes.

OpenCode 2.x has no hook that runs after a finished reply. Its only hook that can refuse anything is the tool hook: "Only tool execute.before may fail" (`packages/core/src/plugin/hooks.ts`, OpenCode 2.0.26). So on 2.x the reply formatting check sees a reply only when the next tool call starts, and blocks that call rather than the reply, and a reply with no tool call after it is never checked. 1.x and Kilo Code keep `experimental.text.complete`, which stores a fixed copy of each text part the main session writes. On every runtime a subagent's prose is left as written and never refused, while the gate still checks its tool calls.

OpenCode 1.x and 2.x both keep their data in `~/.local/share/opencode` and do not share one database format, so running both on one machine lets each corrupt the other's sessions. Give 1.x a data directory of its own by starting it with `XDG_DATA_HOME` set, for example through an alias for whichever command starts your 1.x build:

```bash
alias opencode1='XDG_DATA_HOME="$HOME/.local/share/opencode-v1" opencode1'
```

`XDG_DATA_HOME` reaches every process 1.x starts, so a local MCP server that stores data by that variable moves with it.

MCP servers go under the `mcp` key of `~/.config/opencode/opencode.json` ([config docs](https://opencode.ai/docs/config/)), or in the shared file from [Share one MCP list between OpenCode and Kilo Code](#share-one-mcp-list-between-opencode-and-kilo-code). Copy the machine-wide servers out of the shipped [opencode.json](../opencode.json) in the temporary copy with one command, naming each server you want at the end, here `context7`. It adds or replaces only the servers you name and keeps the rest of the file. Unix shell:

```bash
python3 -c 'import json,sys,pathlib;u=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["mcp"];p=pathlib.Path.home().joinpath(sys.argv[2]);s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};s.setdefault("mcp",{}).update({n:u[n] for n in sys.argv[3:]});p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")' "$src/opencode.json" .config/opencode/opencode.json context7
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,sys,pathlib;u=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["mcp"];p=pathlib.Path.home().joinpath(sys.argv[2]);s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};s.setdefault("mcp",{}).update({n:u[n] for n in sys.argv[3:]});p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")' "$src\opencode.json" .config/opencode/opencode.json context7
```

Check it. It prints the server names in the file. Unix shell:

```bash
python3 -c 'import json,pathlib;print(sorted(json.loads((pathlib.Path.home()/".config/opencode/opencode.json").read_text(encoding="utf-8")).get("mcp",{})))'
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,pathlib;print(sorted(json.loads((pathlib.Path.home()/".config/opencode/opencode.json").read_text(encoding="utf-8")).get("mcp",{})))'
```

#### Kilo Code

Create the configuration directory. PowerShell:

```powershell
New-Item -ItemType Directory -Force $HOME\.config\kilo
```

Unix shell:

```bash
mkdir -p ~/.config/kilo
```

Point Kilo Code at the instruction file. Kilo Code 7.8.9 reads `~/.config/kilo/AGENTS.md`, the `AGENTS.md` in its global configuration directory (`globalFiles` in `packages/opencode/src/session/instruction.ts` of [Kilo-Org/kilocode](https://github.com/Kilo-Org/kilocode)), so make that a link. PowerShell:

```powershell
New-Item -ItemType SymbolicLink -Path $HOME\.config\kilo\AGENTS.md -Target $HOME\.config\agents\AGENTS.md
```

Unix shell:

```bash
ln -s ../agents/AGENTS.md ~/.config/kilo/AGENTS.md
```

Link the subagents to the same shared tree OpenCode uses. The global location is `~/.config/kilo/agents/`
([custom subagents](https://kilo.ai/docs/customize/custom-subagents)). Kilo Code 7.7.9 loaded all 25 subagents through
a junction there, in a throwaway home, both with and without a `markdown_source` rule. The documentation asks for that
rule when a project's `.kilo/agents/` links outside the project, and the global directory did not need it. PowerShell:

```powershell
New-Item -ItemType Junction -Path $HOME\.config\kilo\agents -Target $HOME\.config\agents\agents
```

Unix shell:

```bash
ln -s ../agents/agents ~/.config/kilo/agents
```

Name the skills folder and the plugin in `~/.config/kilo/kilo.jsonc`. "The `skills.paths` key accepts absolute paths, `~/` home-relative paths, or paths relative to the project root" ([skills docs](https://kilo.ai/docs/customize/skills)), and Kilo loads a local plugin named as an absolute `file:` URL ([plugins docs](https://kilo.ai/docs/automate/extending/plugins)), here the plugin directory. The block below shows the result for a Windows home directory of `C:\Users\you`:

```jsonc
{
  "skills": { "paths": ["~/.config/agents/skills"] },
  "plugin": ["file:///C:/Users/you/.config/agents/plugin"]
}
```

Write it with one command. It works like the OpenCode command above: it merges into the file you have or creates it, writes the `file:` URL of your own plugin folder, which is `file:///home/you/.config/agents/plugin` for a Linux home of `/home/you`, removes an old `plugin` entry and an `instructions` entry naming `~/.claude/CLAUDE.md`, and stops before writing anything when the file is not plain JSON. Unix shell:

```bash
python3 -c 'import json,pathlib;h=pathlib.Path.home();p=h/".config/kilo/kilo.jsonc";s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};d="~/.config/agents/skills";k=s.setdefault("skills",{});k["paths"]=[x for x in k.get("paths",[]) if x!=d]+[d];s["plugin"]=[x for x in s.get("plugin",[]) if "agents/plugin" not in str(x)]+[(h/".config/agents/plugin").as_uri()];i=[x for x in s.pop("instructions",[]) if ".claude/CLAUDE.md" not in str(x)];s.update({"instructions":i} if i else {});p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")'
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,pathlib;h=pathlib.Path.home();p=h/".config/kilo/kilo.jsonc";s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};d="~/.config/agents/skills";k=s.setdefault("skills",{});k["paths"]=[x for x in k.get("paths",[]) if x!=d]+[d];s["plugin"]=[x for x in s.get("plugin",[]) if "agents/plugin" not in str(x)]+[(h/".config/agents/plugin").as_uri()];i=[x for x in s.pop("instructions",[]) if ".claude/CLAUDE.md" not in str(x)];s.update({"instructions":i} if i else {});p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")'
```

Check it. It prints the file. Unix shell:

```bash
cat ~/.config/kilo/kilo.jsonc
```

PowerShell:

```powershell
Get-Content $HOME\.config\kilo\kilo.jsonc
```

Leave `~/.config/kilo/plugin/` without a copy of the plugin, for the same reason as under OpenCode: every file in that
directory is "auto-registered at startup", so a copy there would load the runner a second time.

MCP servers go under the `mcp` key of `~/.config/kilo/kilo.jsonc`, in the same shape as `opencode.json`
([CLI docs](https://kilo.ai/docs/code-with-ai/platforms/cli)), or in the shared file below. `{env:VAR}` works here:
Kilo refuses it in a project config file, but resolves it in "your global config (~/.config/kilo), a config passed via
KILO_CONFIG / KILO_CONFIG_CONTENT, or organization/MDM-managed config".

Copy machine-wide servers out of the shipped [opencode.json](../opencode.json) in the temporary copy the same way as for OpenCode, naming each server at the end. Unix shell:

```bash
python3 -c 'import json,sys,pathlib;u=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["mcp"];p=pathlib.Path.home().joinpath(sys.argv[2]);s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};s.setdefault("mcp",{}).update({n:u[n] for n in sys.argv[3:]});p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")' "$src/opencode.json" .config/kilo/kilo.jsonc context7
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,sys,pathlib;u=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["mcp"];p=pathlib.Path.home().joinpath(sys.argv[2]);s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};s.setdefault("mcp",{}).update({n:u[n] for n in sys.argv[3:]});p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")' "$src\opencode.json" .config/kilo/kilo.jsonc context7
```

The global file is also the place for the Context7 API key header, if you want Kilo to use your key rather than the free tier. The entry looks like this:

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

Write it with one command. It writes the reference `{env:CONTEXT7_API_KEY}` and never the key itself, which Kilo reads from the variable you set in [Step 3 of MCP_SETUP.md](MCP_SETUP.md#step-3-set-environment-variables-system-wide). It replaces any `context7` entry already there and keeps the rest of the file. The last word names the file. For Kilo Code, Unix shell:

```bash
python3 -c 'import json,sys,pathlib;p=pathlib.Path.home().joinpath(sys.argv[1]);s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};s.setdefault("mcp",{})["context7"]={"type":"remote","url":"https://mcp.context7.com/mcp","headers":{"CONTEXT7_API_KEY":"{env:CONTEXT7_API_KEY}"},"enabled":True};p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")' .config/kilo/kilo.jsonc
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,sys,pathlib;p=pathlib.Path.home().joinpath(sys.argv[1]);s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};s.setdefault("mcp",{})["context7"]={"type":"remote","url":"https://mcp.context7.com/mcp","headers":{"CONTEXT7_API_KEY":"{env:CONTEXT7_API_KEY}"},"enabled":True};p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")' .config/kilo/kilo.jsonc
```

For OpenCode, Unix shell:

```bash
python3 -c 'import json,sys,pathlib;p=pathlib.Path.home().joinpath(sys.argv[1]);s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};s.setdefault("mcp",{})["context7"]={"type":"remote","url":"https://mcp.context7.com/mcp","headers":{"CONTEXT7_API_KEY":"{env:CONTEXT7_API_KEY}"},"enabled":True};p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")' .config/opencode/opencode.json
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,sys,pathlib;p=pathlib.Path.home().joinpath(sys.argv[1]);s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};s.setdefault("mcp",{})["context7"]={"type":"remote","url":"https://mcp.context7.com/mcp","headers":{"CONTEXT7_API_KEY":"{env:CONTEXT7_API_KEY}"},"enabled":True};p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")' .config/opencode/opencode.json
```

Check the Kilo Code file. It prints the server names in it, and the OpenCode check above does the same for `opencode.json`. Unix shell:

```bash
python3 -c 'import json,pathlib;print(sorted(json.loads((pathlib.Path.home()/".config/kilo/kilo.jsonc").read_text(encoding="utf-8")).get("mcp",{})))'
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,pathlib;print(sorted(json.loads((pathlib.Path.home()/".config/kilo/kilo.jsonc").read_text(encoding="utf-8")).get("mcp",{})))'
```

#### Share one MCP list between OpenCode and Kilo Code

Optional. Put the machine-wide servers in one file that holds nothing but an `mcp` block, for example `~/.config/agents/mcp.json`, in the `opencode.json` shape from [MCP_SETUP.md](MCP_SETUP.md). The same command as under [OpenCode](#opencode) copies the servers you name out of the shipped [opencode.json](../opencode.json) in the temporary copy into that file. Unix shell:

```bash
python3 -c 'import json,sys,pathlib;u=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["mcp"];p=pathlib.Path.home().joinpath(sys.argv[2]);s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};s.setdefault("mcp",{}).update({n:u[n] for n in sys.argv[3:]});p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")' "$src/opencode.json" .config/agents/mcp.json context7
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,sys,pathlib;u=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["mcp"];p=pathlib.Path.home().joinpath(sys.argv[2]);s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};s.setdefault("mcp",{}).update({n:u[n] for n in sys.argv[3:]});p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")' "$src\opencode.json" .config/agents/mcp.json context7
```

Then name it in both variables, for your user account rather than one shell. PowerShell:

```powershell
[Environment]::SetEnvironmentVariable('OPENCODE_CONFIG', "$HOME\.config\agents\mcp.json", 'User')
```

```powershell
[Environment]::SetEnvironmentVariable('KILO_CONFIG', "$HOME\.config\agents\mcp.json", 'User')
```

Check both. It prints the two names with their values:

```powershell
'OPENCODE_CONFIG', 'KILO_CONFIG' | ForEach-Object { "$_=$([Environment]::GetEnvironmentVariable($_, 'User'))" }
```

Linux, in the environment file from step 4:

```bash
printf '%s\n' 'OPENCODE_CONFIG=${HOME}/.config/agents/mcp.json' 'KILO_CONFIG=${HOME}/.config/agents/mcp.json' >> ~/.config/environment.d/60-agents.conf
```

Check it. It prints the two lines:

```bash
grep -n '_CONFIG=' ~/.config/environment.d/60-agents.conf
```

Both tools merge that file over their own global config, so keep the `mcp` block out of `opencode.json` and `kilo.jsonc` to have one list. This command removes it from both and keeps every other key. Unix shell:

```bash
python3 -c 'import json,pathlib;h=pathlib.Path.home();[p.write_text(json.dumps({k:v for k,v in json.loads(p.read_text(encoding="utf-8")).items() if k!="mcp"},indent=2)+"\n",encoding="utf-8") for p in (h/".config/opencode/opencode.json",h/".config/kilo/kilo.jsonc") if p.exists()]'
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,pathlib;h=pathlib.Path.home();[p.write_text(json.dumps({k:v for k,v in json.loads(p.read_text(encoding="utf-8")).items() if k!="mcp"},indent=2)+"\n",encoding="utf-8") for p in (h/".config/opencode/opencode.json",h/".config/kilo/kilo.jsonc") if p.exists()]'
```

Check all three files. It prints each file with the server names it holds, and only the shared file should name any. Unix shell:

```bash
python3 -c 'import json,pathlib;h=pathlib.Path.home();[print(p,sorted(json.loads(p.read_text(encoding="utf-8")).get("mcp",{}))) for p in (h/".config/agents/mcp.json",h/".config/opencode/opencode.json",h/".config/kilo/kilo.jsonc") if p.exists()]'
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,pathlib;h=pathlib.Path.home();[print(p,sorted(json.loads(p.read_text(encoding="utf-8")).get("mcp",{}))) for p in (h/".config/agents/mcp.json",h/".config/opencode/opencode.json",h/".config/kilo/kilo.jsonc") if p.exists()]'
```

Restart the agents, or sign out and in again, so they see the variables. Whether Kilo Code ever writes back into a file named by `KILO_CONFIG` was not tested.

#### GitHub Copilot

The CLI configuration directory is `COPILOT_HOME`, which step 4 points at `~/.config/copilot`, and "`COPILOT_HOME` replaces the entire `~/.copilot` path" ([CLI config dir reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference)). The same step names the shared skills in `COPILOT_SKILLS_DIRS` and the shared instruction folder in `COPILOT_CUSTOM_INSTRUCTIONS_DIRS`, so the skills and the instructions need nothing here.

VS Code reads its own fixed paths: its Local agent loads user hooks from `~/.copilot/hooks/*.json` and user custom agents from `~/.copilot/agents` or `~/.claude/agents` ([VS Code hooks](https://code.visualstudio.com/docs/copilot/customization/hooks), [VS Code custom agents](https://code.visualstudio.com/docs/copilot/customization/custom-agents)). Whether it honours `COPILOT_HOME` is not documented and was not tested, so a VS Code user who wants the hooks there keeps a copy in `~/.copilot` as well. Because VS Code reads both agent folders, a subagent installed for Claude Code and for Copilot shows up there twice.

Create the two directories the copies land in. PowerShell:

```powershell
New-Item -ItemType Directory -Force $HOME\.config\copilot\agents, $HOME\.config\copilot\hooks
```

Unix shell:

```bash
mkdir -p ~/.config/copilot/agents ~/.config/copilot/hooks
```

Copy the `*.agent.md` subagents into `~/.config/copilot/agents/`. PowerShell:

```powershell
Copy-Item -Recurse -Force "$src\.github\agents\*" $HOME\.config\copilot\agents\
```

Unix shell:

```bash
cp -R "$src/.github/agents/." ~/.config/copilot/agents/
```

Wire the hooks in `~/.config/copilot/hooks/preflight.json`, the user-level hooks directory
([hooks reference](https://docs.github.com/en/copilot/reference/hooks-reference)). The block is
the checkout's `.github/hooks/preflight.json` with every script path made absolute, and the command below the block
puts your home directory in place of `/home/you`. Five events matter: `sessionStart` injects the reminder and puts the task list back,
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
        "bash": "printf '%s\\n' '{\"additionalContext\": \"Before code work, name the skills and subagents that own this task and invoke them, or say none apply and why, in one line. End every reply with the status block the skill describes, plain text only.\"}'",
        "powershell": "echo '{\"additionalContext\": \"Before code work, name the skills and subagents that own this task and invoke them, or say none apply and why, in one line. End every reply with the status block the skill describes, plain text only.\"}'"
      },
      {
        "type": "command",
        "cwd": ".",
        "bash": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.config/agents/hooks/task_list_sync.py --event sessionstart --format copilot 2>/dev/null || exit 0",
        "powershell": "python -S -E /home/you/.config/agents/hooks/task_list_sync.py --event sessionstart --format copilot 2>$null; exit 0"
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
        "bash": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.config/agents/hooks/copilot/prompt_reminder.py 2>/dev/null || exit 0",
        "powershell": "python -S -E /home/you/.config/agents/hooks/copilot/prompt_reminder.py 2>$null; exit 0"
      }
    ],
    "preToolUse": [
      {
        "type": "command",
        "matcher": "bash|powershell|create|edit|apply_patch",
        "cwd": ".",
        "bash": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.config/agents/hooks/preflight_gate.py --format copilot 2>/dev/null || exit 0",
        "powershell": "python -S -E /home/you/.config/agents/hooks/preflight_gate.py --format copilot 2>$null; exit 0"
      }
    ],
    "agentStop": [
      {
        "type": "command",
        "cwd": ".",
        "bash": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.config/agents/hooks/no_ai_markers_check.py --format copilot 2>/dev/null || exit 0",
        "powershell": "python -S -E /home/you/.config/agents/hooks/no_ai_markers_check.py --format copilot 2>$null; exit 0"
      }
    ]
  }
}
```

Write it with the same command as under [Claude Code](#claude-code), with the Copilot marker and file. It reads the block above from the temporary copy, replaces only the hook entries this install wrote, and keeps the rest of your file. Unix shell:

```bash
python3 -c 'import json,re,sys,pathlib;h=pathlib.Path.home();g=pathlib.Path(sys.argv[1]).read_text(encoding="utf-8");b=json.loads([x for x in re.findall(r"^\x60{3}json\n(.*?)^\x60{3}$",g,re.M|re.S) if sys.argv[2] in x][0].replace("/home/you/",h.as_posix()+"/"));p=h.joinpath(sys.argv[3]);s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};o=lambda x:any(m in json.dumps(x) for m in ("agents/hooks/","PREFLIGHT","Before code work","background subagent"));e=s.setdefault("hooks",{});[e.update({k:[x for x in e.get(k,[]) if not o(x)]+v}) for k,v in b["hooks"].items()];[s.setdefault(k,v) for k,v in b.items()];p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")' "$src/docs/GLOBAL_SETUP.md" userPromptTransformed .config/copilot/hooks/preflight.json
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,re,sys,pathlib;h=pathlib.Path.home();g=pathlib.Path(sys.argv[1]).read_text(encoding="utf-8");b=json.loads([x for x in re.findall(r"^\x60{3}json\n(.*?)^\x60{3}$",g,re.M|re.S) if sys.argv[2] in x][0].replace("/home/you/",h.as_posix()+"/"));p=h.joinpath(sys.argv[3]);s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};o=lambda x:any(m in json.dumps(x) for m in ("agents/hooks/","PREFLIGHT","Before code work","background subagent"));e=s.setdefault("hooks",{});[e.update({k:[x for x in e.get(k,[]) if not o(x)]+v}) for k,v in b["hooks"].items()];[s.setdefault(k,v) for k,v in b.items()];p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")' "$src\docs\GLOBAL_SETUP.md" userPromptTransformed .config/copilot/hooks/preflight.json
```

Check it. It prints every hook script the file now runs. Unix shell:

```bash
grep -o '[^ "]*/\.config/agents/hooks/[^ "]*' ~/.config/copilot/hooks/preflight.json
```

PowerShell:

```powershell
Select-String -Path $HOME\.config\copilot\hooks\preflight.json -Pattern '[^ "]*/\.config/agents/hooks/[^ "]*' -AllMatches | ForEach-Object { $_.Matches.Value }
```

Do not turn on `chat.useClaudeHooks` in VS Code on top of this. With it on, the Local agent also runs the hooks in
`~/.claude/settings.json`, next to the ones in `~/.copilot/hooks/`, and the documentation adds that "Local ignores
matcher values". The gate is wired in both files, so every tool call in a VS Code chat would run it twice.

MCP for the CLI is `~/.config/copilot/mcp-config.json`. In VS Code, run the `MCP: Open User Configuration` command to open
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

### The skill link hook

`~/.config/agents/hooks/claude/sync_skill_links.py` keeps two folders in step with `~/.config/agents/skills`: `~/.claude/skills` when `~/.claude` exists, and `$CODEX_HOME/skills`, or `~/.config/codex/skills` when `CODEX_HOME` is unset, when that Codex home exists. In each it links every shared folder that holds a `SKILL.md` and has no entry of that name yet, and removes a link that points into the shared folder at a skill that is gone. It never touches `synced`, `.trash`, a dot entry such as Codex's `.system`, a real directory, or a link that points anywhere else, and it leaves a folder that is itself a link alone. It always exits 0 and reports to standard error, because Claude Code adds a `SessionStart` hook's standard output to the model's context.

Claude Code runs it when a session starts or resumes, and both updaters run it after an update, so a Codex-only machine picks up a new skill at the next update or when you run it by hand. The updaters run it with `HOME` set to the home they update and `CODEX_HOME` set to `.config/codex` inside that home, whatever your own `CODEX_HOME` says, so an update of another home with `--home-dir` or `-HomeDir` links nothing into your own Codex home. By hand:

```bash
python3 -S -E ~/.config/agents/hooks/claude/sync_skill_links.py
```

On Windows it does nothing, by design, because per-skill junctions were never tested there. The Windows steps above use junctions made by hand instead.

---

### Migrating from ~/.agents

An install made before this layout keeps everything in `~/.agents`, links `~/.claude/skills` to `~/.agents/skills` as a whole, and reads its instructions from `~/.claude/CLAUDE.md`. The updater stops with "migrate it first" until the steps below are done. Run them in order, on Linux and macOS:

1. Move the shared folder:

   ```bash
   mkdir -p ~/.config && mv ~/.agents ~/.config/agents
   ```

2. Drop the skills that Claude Code synced through the old whole-directory link, which are its own and not part of the install:

   ```bash
   rm -rf ~/.config/agents/skills/synced ~/.config/agents/skills/.trash
   ```

3. Replace the whole-directory link with a real folder, which removes only the link:

   ```bash
   rm ~/.claude/skills && mkdir ~/.claude/skills
   ```

4. Move your instructions into the shared file, then make `~/.claude/CLAUDE.md` the one-line import. When `~/.claude/CLAUDE.md` is a real file holding your instructions:

   ```bash
   mv ~/.claude/CLAUDE.md ~/.config/agents/AGENTS.md && printf '%s\n' '@~/.config/agents/AGENTS.md' > ~/.claude/CLAUDE.md
   ```

5. Do step 4 of the install, the environment variables, then sign out and back in.

6. Move the Codex and Copilot directories under `~/.config`, so their sessions, settings and credentials move with them:

   ```bash
   mv ~/.codex ~/.config/codex && mv ~/.copilot ~/.config/copilot
   ```

7. Replace the old instruction links. `~/.config/codex/AGENTS.md` pointed at `~/.claude/CLAUDE.md`, and Copilot now reads `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` instead of its own link:

   ```bash
   ln -sfn ../agents/AGENTS.md ~/.config/codex/AGENTS.md && rm -f ~/.config/copilot/copilot-instructions.md
   ```

8. Repoint the OpenCode and Kilo Code subagent links, and add their `AGENTS.md` links:

   ```bash
   for d in opencode kilo; do ln -sfn ../agents/agents ~/.config/$d/agents; ln -sfn ../agents/AGENTS.md ~/.config/$d/AGENTS.md; done
   ```

9. Rewrite the wiring in the configuration files with the commands from each agent's section, which keep every setting of yours. Make a temporary copy as in [step 1](#step-1-a-temporary-copy-of-the-repository), run the command that writes the configuration file in the section of each agent you use, [Claude Code](#claude-code), [Codex](#codex), [OpenCode](#opencode), [Kilo Code](#kilo-code) and [GitHub Copilot](#github-copilot), each followed by its check, then delete the copy as in [the finish step](#finish-delete-the-temporary-copy). In `~/.claude/settings.json`, `~/.config/codex/hooks.json` and `~/.config/copilot/hooks/preflight.json` the command replaces every hook group the old install wrote, the ones naming `/.agents/hooks/` included, with the current block, so the Claude Code `SessionStart` gains the skill link group. In `opencode.json` and `kilo.jsonc` it replaces the old `plugin` entry with the `plugin` directory, adds `skills.paths`, and removes the `instructions` entry that named `~/.claude/CLAUDE.md`. Then trust the changed hooks in an interactive Codex session.

10. Run the updater from its new place, which also fills `~/.claude/skills` and `~/.config/codex/skills`:

    ```bash
    sh ~/.config/agents/bin/update-global.sh
    ```

On Windows the same steps apply with `Move-Item` for `mv`, `(Get-Item $HOME\.claude\skills).Delete()` to remove the old junction, and `New-Item -ItemType Junction` and `-ItemType SymbolicLink` for the new links as shown in each agent's section. That sequence was not run on Windows for this guide.

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
3. The global `.config/agents/hooks/` in your home directory, the one step 2 filled. On Windows that is
   `C:\Users\<you>\.config\agents\hooks`, elsewhere `~/.config/agents/hooks`. The old `~/.agents/hooks` is no longer read.

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
project root instead, one per line, in the form described above. Blank lines and lines starting with `#` are skipped.
The file sits at the root rather than under `.agents/`, so importing or updating `.agents` never overwrites it. For
example:

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
2. The content of `~/.config/agents/AGENTS.md`. Editing the template down to the parts that are about you is a job only you
   can do.
3. Reading the merged configuration files. No command above overwrites a configuration file you already have: each
   merges into it, keeps your own keys, and is followed by a check that prints what it wrote. Read that output, because
   only you know which of the other entries are yours.

---

### Global path map

Every global location this document touches, per agent. The project-level equivalents are the paths the import
writes into your repository, and they are unaffected by anything here.

| Agent | Skills | Subagents | Hooks or plugin | MCP config | Global instructions | Config-dir env var |
| --- | --- | --- | --- | --- | --- | --- |
| Claude Code | `~/.claude/skills/`, per-skill links into `~/.config/agents/skills` | `~/.claude/agents/` | `hooks` in `~/.claude/settings.json` | `~/.claude.json`, written by `claude mcp add --scope user` | `~/.claude/CLAUDE.md`, importing `~/.config/agents/AGENTS.md`, plus `~/.claude/rules/` | `CLAUDE_CONFIG_DIR`, left unset |
| Codex | `~/.config/codex/skills/`, per-skill links, also `$HOME/.agents/skills` and `/etc/codex/skills` | `~/.config/codex/agents/` as TOML | `~/.config/codex/hooks.json`, or inline `[[hooks.*]]` in `~/.config/codex/config.toml` | `[mcp_servers.*]` in `~/.config/codex/config.toml` | `~/.config/codex/AGENTS.md`, a link | `CODEX_HOME` |
| OpenCode | `skills.paths`, plus `~/.agents/skills/`, `~/.claude/skills/` and `~/.config/opencode/skills/` natively | `~/.config/opencode/agents/`, a link to `~/.config/agents/agents` | `plugin` in `~/.config/opencode/opencode.json`, naming `~/.config/agents/plugin` | `mcp` in `~/.config/opencode/opencode.json`, or the file in `OPENCODE_CONFIG` | `~/.config/opencode/AGENTS.md`, a link | `OPENCODE_CONFIG_DIR`, and `OPENCODE_CONFIG` for a file |
| Kilo Code | `skills.paths`, plus `~/.agents/skills/` and `~/.kilo/skills/` natively, `~/.claude/skills/` behind a compatibility setting | `~/.config/kilo/agents/`, a link to `~/.config/agents/agents` | `plugin` in `~/.config/kilo/kilo.jsonc`, naming `~/.config/agents/plugin` | `mcp` in `~/.config/kilo/kilo.jsonc`, or the file in `KILO_CONFIG` | `~/.config/kilo/AGENTS.md`, a link | `KILO_CONFIG` for a file |
| GitHub Copilot | `COPILOT_SKILLS_DIRS`, plus `~/.config/copilot/skills/` | `~/.config/copilot/agents/` for the CLI, `~/.copilot/agents/` for VS Code | `~/.config/copilot/hooks/` for the CLI, `~/.copilot/hooks/` for VS Code | `~/.config/copilot/mcp-config.json` for the CLI, user-profile `mcp.json` for VS Code, `C:\Users\<you>\AppData\Local\github-copilot\intellij\mcp.json` for JetBrains on Windows | `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` naming `~/.config/agents` | `COPILOT_HOME` |

---

### Updating the global installation

One command updates everything the install put in your home directory. It clones a temporary copy of this repository,
reads the files of its newest commit, updates your install from them, prints what it did, and deletes the copy.
PowerShell:

```powershell
pwsh -NoProfile -File $HOME\.config\agents\bin\update-global.ps1
```

Unix shell:

```bash
sh ~/.config/agents/bin/update-global.sh
```

The PowerShell version needs PowerShell 7.4 or later, which is `pwsh`, not the Windows PowerShell 5.1 that Windows
ships. The Unix version runs in any POSIX `sh`, including Git Bash. Both do exactly the same thing.

What it changes:

- The hook scripts in `~/.config/agents/hooks`, the plugin in `~/.config/agents/plugin`, the reply rules in `~/.config/agents/instructions`, and the updater itself in `~/.config/agents/bin`
  are refreshed in full, including a file upstream added since your last update. OpenCode and Kilo Code name the
  plugin by path, so this reaches both.
- Every skill folder you already have in `~/.config/agents/skills` is refreshed file by file, when upstream still ships a
  skill of that name. A skill you do not have is never added, so one you deleted stays deleted. `synced`, `.trash` and any dot folder are never treated as skills, so the folders Claude Code and Codex own are neither reported nor touched.
- Every subagent file you already have is refreshed, in the four trees: `~/.config/agents/agents`, which OpenCode and Kilo
  Code reach through their links, `~/.claude/agents`, `~/.config/codex/agents`, and `~/.config/copilot/agents`. A subagent you do
  not have is never added.
- A file is removed only when the commit recorded in `~/.config/agents/.upstream-commit` shipped it and the new commit no
  longer does. A file of your own, such as a note you keep inside a skill folder, was never shipped, so it is never
  removed. When the recorded commit is missing or unknown, nothing is removed and the summary says so.
- A skill folder or a subagent file that upstream stopped shipping altogether stays in place and is reported as
  `keep`. One that never came from upstream is reported as `skip` and left alone.
- The new commit is written to `~/.config/agents/.upstream-commit`.
- [The skill link hook](#the-skill-link-hook) runs last, so a skill removed upstream loses its links now rather than at the next session. A dry run skips it.

It never touches the files listed under [Files no update touches](#files-no-update-touches). When upstream changed the
hook wiring since the recorded commit, the summary names the changed files and prints the `git diff` command that
shows the change. Take each change in by running the command that writes that file, in the agent's section above,
against a new temporary copy made as in [step 1](#step-1-a-temporary-copy-of-the-repository), then delete the copy. The
command replaces only the hook groups the install wrote and keeps your own. After any change to `~/.config/codex/hooks.json`, open an interactive Codex session and
trust the hooks again, because "changed hooks are marked for review and skipped until trusted"
([hooks docs](https://learn.chatgpt.com/codex/hooks)).

An install still in `~/.agents` stops the updater with an error that points at [Migrating from ~/.agents](#migrating-from-agents).

To see what an update would do first, run it as a dry run. It prints the same list and writes nothing. PowerShell:

```powershell
pwsh -NoProfile -File $HOME\.config\agents\bin\update-global.ps1 -DryRun
```

Unix shell:

```bash
sh ~/.config/agents/bin/update-global.sh --dry-run
```

The summary lists one line per file it changed or skill and subagent it left alone, then the wiring report and the
totals, for example:

```text
update  ~/.config/agents/hooks/preflight_gate.py
add     ~/.config/agents/skills/research/references/source-order.md
skip    ~/.config/agents/skills/my-own-skill (not an upstream skill)
Hook wiring: unchanged upstream since 1006f0084bd24080dcfbadb5c4bd33aaa616950d.
Recorded 3f2abe7a3afd255c4220154474a1c4700ca37273 in ~/.config/agents/.upstream-commit.
Skill links: the Claude Code and Codex skills folders checked against ~/.config/agents/skills.
Updated 1, added 1, removed 0. Unchanged 371. Left alone: 0 removed upstream, 1 not from upstream.
```

To update from a clone of this repository you already have rather than from GitHub, name it as the source. The
updater reads that clone's last commit and never its working tree, so uncommitted work in it cannot reach your home
directory. Replace the path with your clone. PowerShell:

```powershell
pwsh -NoProfile -File $HOME\.config\agents\bin\update-global.ps1 -Source D:\src\agent-standards
```

Unix shell:

```bash
sh ~/.config/agents/bin/update-global.sh --source ~/src/agent-standards
```

#### Installed before the updater existed

An install older than the updater has no `bin` folder yet. Migrate it first as in [Migrating from ~/.agents](#migrating-from-agents), then run the updater once out of a temporary copy, and that first run
puts it in `~/.config/agents/bin` for every later update. PowerShell:

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
folder name under `.agents/skills/`. Every agent then finds it the way it finds the others, once the skill link hook has run for Claude Code and Codex, and from then on the
update keeps it current. PowerShell:

```powershell
Copy-Item -Recurse "$src\.agents\skills\research" $HOME\.config\agents\skills\research
```

Unix shell:

```bash
cp -R "$src/.agents/skills/research" ~/.config/agents/skills/research
```

#### Files no update touches

Never refreshed, on purpose, because they become yours the moment you install them: `~/.config/agents/AGENTS.md`, `~/.claude/settings.json`,
`~/.claude/CLAUDE.md`, `~/.claude.json`, `~/.config/codex/hooks.json`, `~/.config/codex/config.toml`,
`~/.config/opencode/opencode.json`, `~/.config/kilo/kilo.jsonc`, `~/.config/copilot/hooks/preflight.json`,
`~/.config/copilot/mcp-config.json`, the environment file from step 4, and `~/.config/agents/mcp.json` if you made one. When upstream changes the gate wording or the
hook wiring, run the command that writes the file again, from the agent's section above and against a new temporary copy. When it adds an MCP server you want, add it with the MCP command in the same section.

---

### Undoing the global installation

Remove it by hand, checking each directory before you delete it. Every directory the install writes into is one an
agent also lets you put your own files in, so deleting a whole tree takes anything you wrote yourself along with it.

Remove the links first, so deleting a link never reaches the shared folder behind it. A junction or a symlink is
removed as the link itself, and the per-skill links inside `~/.claude/skills` and `~/.config/codex/skills` go with a find that deletes links only. PowerShell:

```powershell
foreach ($l in "$HOME\.claude\skills", "$HOME\.config\opencode\agents", "$HOME\.config\kilo\agents") { if ((Test-Path $l) -and (Get-Item $l).LinkType) { (Get-Item $l).Delete() } }
```

Unix shell:

```bash
find ~/.claude/skills ~/.config/codex/skills -maxdepth 1 -type l -delete
```

```bash
rm -f ~/.config/opencode/agents ~/.config/kilo/agents ~/.config/codex/AGENTS.md ~/.config/opencode/AGENTS.md ~/.config/kilo/AGENTS.md
```

Before the shared folder goes, put your instructions back into `~/.claude/CLAUDE.md`, whose import line would otherwise name a file that no longer exists. This command replaces that one line with the content of `~/.config/agents/AGENTS.md` and keeps every other line of the file. Unix shell:

```bash
python3 -c 'import pathlib,re;h=pathlib.Path.home();p=h/".claude/CLAUDE.md";a=(h/".config/agents/AGENTS.md").read_text(encoding="utf-8").rstrip("\n");p.write_text(re.sub(r"(?m)^@~/\.config/agents/AGENTS\.md$",lambda m:a,p.read_text(encoding="utf-8")),encoding="utf-8")'
```

PowerShell 7.4 or later:

```powershell
python -c 'import pathlib,re;h=pathlib.Path.home();p=h/".claude/CLAUDE.md";a=(h/".config/agents/AGENTS.md").read_text(encoding="utf-8").rstrip("\n");p.write_text(re.sub(r"(?m)^@~/\.config/agents/AGENTS\.md$",lambda m:a,p.read_text(encoding="utf-8")),encoding="utf-8")'
```

Check that the import line is gone. It prints nothing. Unix shell:

```bash
grep -n '^@~/.config/agents/AGENTS.md' ~/.claude/CLAUDE.md
```

PowerShell:

```powershell
Select-String -Path $HOME\.claude\CLAUDE.md -Pattern '^@~/.config/agents/AGENTS.md'
```

Then delete the shared folder. PowerShell:

```powershell
Remove-Item -Recurse -Force $HOME\.config\agents
```

Unix shell:

```bash
rm -rf ~/.config/agents
```

Then, per agent, remove only what you recognise in the `agents/` directories of Claude Code, Codex and Copilot.

Take the gate out of `~/.claude/settings.json`, `~/.config/codex/hooks.json` and `~/.config/copilot/hooks/preflight.json`. Each may hold configuration of yours as well, so this command removes only the hook groups the install wrote, recognised the same way the install command recognises them, and keeps everything else. Unix shell:

```bash
python3 -c 'import json,pathlib;h=pathlib.Path.home();o=lambda x:any(m in json.dumps(x) for m in ("agents/hooks/","PREFLIGHT","Before code work","background subagent"));[p.write_text(json.dumps((lambda s:{**s,"hooks":{k:[x for x in v if not o(x)] for k,v in s.get("hooks",{}).items() if any(not o(x) for x in v)}})(json.loads(p.read_text(encoding="utf-8"))),indent=2)+"\n",encoding="utf-8") for p in (h/".claude/settings.json",h/".config/codex/hooks.json",h/".config/copilot/hooks/preflight.json") if p.exists()]'
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,pathlib;h=pathlib.Path.home();o=lambda x:any(m in json.dumps(x) for m in ("agents/hooks/","PREFLIGHT","Before code work","background subagent"));[p.write_text(json.dumps((lambda s:{**s,"hooks":{k:[x for x in v if not o(x)] for k,v in s.get("hooks",{}).items() if any(not o(x) for x in v)}})(json.loads(p.read_text(encoding="utf-8"))),indent=2)+"\n",encoding="utf-8") for p in (h/".claude/settings.json",h/".config/codex/hooks.json",h/".config/copilot/hooks/preflight.json") if p.exists()]'
```

Take the `plugin` and `skills` entries out of `opencode.json` and `kilo.jsonc` the same way, which removes only the entries that name `~/.config/agents`. Unix shell:

```bash
python3 -c 'import json,pathlib;h=pathlib.Path.home();f=lambda s:{**s,"plugin":[x for x in s.get("plugin",[]) if "agents/plugin" not in str(x)],"skills":{**s.get("skills",{}),"paths":[x for x in s.get("skills",{}).get("paths",[]) if ".config/agents/skills" not in x]}};[p.write_text(json.dumps(f(json.loads(p.read_text(encoding="utf-8"))),indent=2)+"\n",encoding="utf-8") for p in (h/".config/opencode/opencode.json",h/".config/kilo/kilo.jsonc") if p.exists()]'
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,pathlib;h=pathlib.Path.home();f=lambda s:{**s,"plugin":[x for x in s.get("plugin",[]) if "agents/plugin" not in str(x)],"skills":{**s.get("skills",{}),"paths":[x for x in s.get("skills",{}).get("paths",[]) if ".config/agents/skills" not in x]}};[p.write_text(json.dumps(f(json.loads(p.read_text(encoding="utf-8"))),indent=2)+"\n",encoding="utf-8") for p in (h/".config/opencode/opencode.json",h/".config/kilo/kilo.jsonc") if p.exists()]'
```

Check all five files. It prints the name of each file that still names `~/.config/agents`, so it prints nothing when the gate and the plugin are out. Unix shell:

```bash
grep -l 'config/agents/' ~/.claude/settings.json ~/.config/codex/hooks.json ~/.config/copilot/hooks/preflight.json ~/.config/opencode/opencode.json ~/.config/kilo/kilo.jsonc 2>/dev/null
```

PowerShell:

```powershell
Select-String -List -Path $HOME\.claude\settings.json, $HOME\.config\codex\hooks.json, $HOME\.config\copilot\hooks\preflight.json, $HOME\.config\opencode\opencode.json, $HOME\.config\kilo\kilo.jsonc -Pattern 'config/agents/' -ErrorAction SilentlyContinue | ForEach-Object { $_.Path }
```

Remove the environment variables from step 4. On Linux, delete the environment file, then the line that loads it from your shell start-up files. The `sed` keeps each previous file as a `.bak` beside it:

```bash
rm -f ~/.config/environment.d/60-agents.conf
```

```bash
for f in ~/.zshenv ~/.profile ~/.bash_profile; do [ -f "$f" ] && sed -i.bak '/60-agents\.conf/d' "$f"; done
```

Check. It prints nothing:

```bash
grep -n '60-agents.conf' ~/.zshenv ~/.profile ~/.bash_profile 2>/dev/null
```

On macOS, remove the four exports from `~/.zshenv`, keeping the previous file as `~/.zshenv.bak`:

```bash
sed -i.bak -E '/^export (CODEX_HOME|COPILOT_HOME|COPILOT_SKILLS_DIRS|COPILOT_CUSTOM_INSTRUCTIONS_DIRS)=/d' ~/.zshenv
```

Stop the LaunchAgent and delete it:

```bash
launchctl bootout "gui/$(id -u)" ~/Library/LaunchAgents/local.agents.environment.plist
```

```bash
rm -f ~/Library/LaunchAgents/local.agents.environment.plist
```

Clear the values it set in the running session:

```bash
for v in CODEX_HOME COPILOT_HOME COPILOT_SKILLS_DIRS COPILOT_CUSTOM_INSTRUCTIONS_DIRS; do launchctl unsetenv "$v"; done
```

Check. It prints nothing:

```bash
grep -nE 'CODEX_HOME|COPILOT_' ~/.zshenv
```

On Windows, clear each variable from your user environment, the two for the shared MCP list included:

```powershell
'CODEX_HOME', 'COPILOT_HOME', 'COPILOT_SKILLS_DIRS', 'COPILOT_CUSTOM_INSTRUCTIONS_DIRS', 'OPENCODE_CONFIG', 'KILO_CONFIG' | ForEach-Object { [Environment]::SetEnvironmentVariable($_, $null, 'User') }
```

Check. It prints each name with an empty value:

```powershell
'CODEX_HOME', 'COPILOT_HOME', 'COPILOT_SKILLS_DIRS', 'COPILOT_CUSTOM_INSTRUCTIONS_DIRS', 'OPENCODE_CONFIG', 'KILO_CONFIG' | ForEach-Object { "$_=$([Environment]::GetEnvironmentVariable($_, 'User'))" }
```

Sign out and back in, so no running application keeps the old values.

---

### Limitations

Honest list of what a global install cannot do.

1. The blocking half of the preflight gate is project-shaped. Every shipped hook wiring calls
   `.agents/hooks/preflight_gate.py`, resolved against the session's working directory. At user level you have to
   rewrite that to an absolute path, which the Claude Code, Codex, and Copilot sections above tell you to do, and the
   same is true of `task_list_sync.py` and `no_ai_markers_check.py`. The gate script recognises its own place in
   `~/.config/agents/hooks` and then looks for subagent definitions in the trees this install writes, `~/.claude/agents`,
   `~/.config/agents/agents`, `~/.config/codex/agents` and `~/.config/copilot/agents`. The text-injection half,
   the `echo` that reminds the model to name its skills, has no file dependency and works globally as it ships.

2. The OpenCode and Kilo Code plugin needs no path rewriting. It uses the project's own `.agents/hooks/` when the
   project has one and your home directory's `.config/agents/hooks/` otherwise, so the global entry gates a project that
   never ran the per-project import. The one project that stays ungated is one holding the opt-out file described in
   [How the OpenCode and Kilo Code plugin finds its hooks](#how-the-opencode-and-kilo-code-plugin-finds-its-hooks). On OpenCode 2.x the reply checks only ever block the next tool call, as its section says.

3. Copilot hooks reach the CLI, the cloud agent and the Local agent in VS Code. The cloud agent reads hooks only from
   `.github/hooks/*.json` in the cloned repository, so nothing in your home directory reaches it. Whether the
   JetBrains plugin reads the user hooks directory was not verified, and neither was whether VS Code follows `COPILOT_HOME`. Copilot code review has no hook surface.

4. Claude Code Cowork sessions and cloud sessions do not read `~/.claude/skills` on your machine at all. Cowork loads
   the skills enabled for your claude.ai account, and cloud sessions additionally load project skills from the cloned
   repository. Cowork also skips the import in `~/.claude/CLAUDE.md`, so only what is written into that file itself reaches it. The global install covers your local sessions and not those two.

5. Kilo Code documents no environment variable that relocates its whole configuration directory. `KILO_CONFIG` and
   `KILO_CONFIG_CONTENT` pass configuration rather than moving the directory. Claude Code has `CLAUDE_CONFIG_DIR`, which this layout leaves unset for the reasons at the top.

6. On Windows the skill link hook does nothing, so `~/.claude/skills` is one junction to the shared folder and the skills Claude Code syncs from claude.ai land inside it, and Codex needs a junction per skill made by hand. None of the Windows steps of this layout, the migration included, was run for this guide.

7. Codex reads the shared skills through `$CODEX_HOME/skills`, a location its own source calls deprecated. When it goes, this guide changes with it.

8. Project settings win. A project that ran the per-project import brings its own `.claude/settings.json`,
   `opencode.json`, `.codex/config.toml`, and skills, and those take precedence over the global ones. Hooks are the
   exception: Claude Code and Codex run the global and the project hooks side by side. The formatting check handles
   that itself. The copy under `~/.config/agents/hooks/` stays silent in a project whose `.claude/settings.json`,
   `.claude/settings.local.json`, `.codex/config.toml`, `.codex/hooks.json` or `.github/hooks/*.json` already runs
   `no_ai_markers_check.py` on the same event, so one reply is never blocked twice and one batch never fixed twice.
   When it cannot read those files it checks anyway.

---

### Where these paths come from

Every path in this document was taken from the current published documentation, fetched on 2026-09-25 and for the `~/.config/agents` layout on 2026-10-13, or measured
where the documentation says nothing. The first measurements ran on Windows 11 against Claude Code 2.1.281, Codex 0.156.1,
OpenCode 1.18.32 and Kilo Code 7.7.9, each in a throwaway home. The layout measurements ran on Linux against Claude Code 2.1.296, Codex 0.162.1, OpenCode 1.19.0 and 2.0.26, and Kilo Code 7.8.9, each in a throwaway home. The container sandbox in this repository then ran the whole install against Claude Code 2.1.250, Codex 0.150.1, OpenCode 1.18.25, Kilo Code 7.5.5 and GitHub Copilot CLI 1.0.81, where Copilot listed every shared skill through `COPILOT_SKILLS_DIRS` with `COPILOT_HOME` set.

| Agent | Pages used |
| --- | --- |
| Claude Code | [settings](https://code.claude.com/docs/en/settings), [skills](https://code.claude.com/docs/en/skills), [sub-agents](https://code.claude.com/docs/en/sub-agents), [memory](https://code.claude.com/docs/en/memory), [hooks](https://code.claude.com/docs/en/hooks), [MCP](https://code.claude.com/docs/en/mcp) |
| Codex | [build skills](https://learn.chatgpt.com/codex/build-skills), [subagents](https://learn.chatgpt.com/codex/agent-configuration/subagents), [hooks](https://learn.chatgpt.com/codex/hooks), [config basics](https://learn.chatgpt.com/codex/config-file/config-basic), [AGENTS.md](https://learn.chatgpt.com/codex/agent-configuration/agents-md), [MCP](https://learn.chatgpt.com/codex/extend/mcp) |
| OpenCode | [config](https://opencode.ai/docs/config/), [skills](https://opencode.ai/docs/skills/), [agents](https://opencode.ai/docs/agents/), [plugins](https://opencode.ai/docs/plugins/), [rules](https://opencode.ai/docs/rules/), [2.x plugins](https://opencode.ai/v2/docs/plugins/) |
| Kilo Code | [skills](https://kilo.ai/docs/customize/skills), [custom subagents](https://kilo.ai/docs/customize/custom-subagents), [plugins](https://kilo.ai/docs/automate/extending/plugins), [CLI](https://kilo.ai/docs/code-with-ai/platforms/cli), [custom rules](https://kilo.ai/docs/customize/custom-rules) |
| GitHub Copilot | [CLI config dir](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference), [CLI command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference), [agent skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills), [custom agents](https://docs.github.com/en/copilot/reference/custom-agents-configuration), [hooks](https://docs.github.com/en/copilot/reference/hooks-reference), [CLI custom instructions](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions), [VS Code hooks](https://code.visualstudio.com/docs/copilot/customization/hooks), [VS Code custom agents](https://code.visualstudio.com/docs/copilot/customization/custom-agents) |
| Linux and the layout | [environment.d](https://www.freedesktop.org/software/systemd/man/latest/environment.d.html), and the Claude Code issues named at the top |
