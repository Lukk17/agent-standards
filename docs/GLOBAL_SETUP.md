# Global setup

Install the shared agent configuration once into your home directory so every project on the machine gets it, even the
ones that never ran the per-project import.

This is the counterpart to the per-project import in [AGENT_TOOLING.md](https://github.com/Lukk17/agent-standards/blob/master/docs/AGENT_TOOLING.md). The two are additive rather
than exclusive: an agent reads both scopes and merges them, so a project that also ran the per-project import keeps
winning on the paths where both scopes define the same thing.

One folder in your home directory, `~/.config/agents`, holds everything the agents can share: the instruction file `AGENTS.md`, the skills, the OpenCode-format subagents, the hook scripts, the OpenCode and Kilo Code plugin, and the updater. Codex, OpenCode, Kilo Code and GitHub Copilot each reach that folder through their own configuration directory, by a link, by one config line, or by an environment variable. No copy of this repository stays in your home directory: the install and every update fetch a temporary copy, take what they need out of it, and delete it.

Claude Code is the exception. It reads one shared file, `~/.config/agents/AGENTS.md`, through a one-line import in `~/.claude/CLAUDE.md`, and takes its skills, subagents and hooks as plugins from the marketplace of this repository, installed with the user scope. Nothing of the shared folder is linked or copied into `~/.claude` for it, as [its section](#claude-code) describes.

Every command below comes in a PowerShell version and a Unix-shell version. Take only the sections for the agents you actually run. On Windows, `~` and `$HOME` both mean `%USERPROFILE%`, so `~/.config/agents` is `C:\Users\<you>\.config\agents`.

An install made before this layout lives in `~/.agents` instead. [Migrating from ~/.agents](#migrating-from-agents) moves it, and the updater refuses to run until it has moved. An install that gave Claude Code skill links, subagent copies and a `hooks` block in its own directory moves once as well, as [Moving Claude Code to the plugins](#moving-claude-code-to-the-plugins) describes.

---

### What each agent shares and what stays per tool

| What | Claude Code | Codex | OpenCode 1.x and 2.x | Kilo Code | GitHub Copilot |
| --- | --- | --- | --- | --- | --- |
| Configuration directory | `~/.claude`, left where it is | `~/.config/codex`, through `CODEX_HOME` | `~/.config/opencode` | `~/.config/kilo` | `~/.config/copilot`, through `COPILOT_HOME` |
| Always-on instructions | `~/.claude/CLAUDE.md`, a real file whose one line imports `~/.config/agents/AGENTS.md` | `~/.config/codex/AGENTS.md`, a link | `~/.config/opencode/AGENTS.md`, a link | `~/.config/kilo/AGENTS.md`, a link | `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` names `~/.config/agents` |
| Skills | plugins from the marketplace, installed with the user scope, never the shared folder | `~/.config/codex/skills`, a real folder of per-skill links kept by the skill link hook | `skills.paths` in `opencode.json` | `skills.paths` in `kilo.jsonc` | `COPILOT_SKILLS_DIRS` names `~/.config/agents/skills` |
| Subagents | plugins, one `agent-<name>` each | own TOML format in `~/.config/codex/agents` | `~/.config/opencode/agents`, a link to `~/.config/agents/agents` | `~/.config/kilo/agents`, a link to `~/.config/agents/agents` | own `*.agent.md` format in `~/.config/copilot/agents` |
| Hook scripts | inside each `hook-<name>` plugin | shared, `~/.config/agents/hooks` | shared | shared | shared |
| Hook wiring | inside each `hook-<name>` plugin, switched on by `enabledPlugins` in `~/.claude/settings.json` | `~/.config/codex/hooks.json` | the shared plugin, declared by its directory in `opencode.json` | the same plugin, declared by its directory in `kilo.jsonc` | `~/.config/copilot/hooks/preflight.json` |
| MCP servers | none at user scope and no `mcp-<server>` plugin with the user scope, each project's `.mcp.json` or a plugin at project scope | none at user scope, each project's `.codex/config.toml`, in a trusted project | none at user scope, each project's `opencode.json` | none at user scope, the same project `opencode.json` | none at user scope for the CLI and VS Code, each project's `.mcp.json` and `.vscode/mcp.json`, and JetBrains `mcp.json`, which has no project file |

Claude Code keeps its own directory because `CLAUDE_CONFIG_DIR`, the variable that would move it, still leaks state back into `~/.claude` or loses it: issues [#80580](https://github.com/anthropics/claude-code/issues/80580), [#30538](https://github.com/anthropics/claude-code/issues/30538), [#98789](https://github.com/anthropics/claude-code/issues/98789), [#97680](https://github.com/anthropics/claude-code/issues/97680), [#90868](https://github.com/anthropics/claude-code/issues/90868), [#88603](https://github.com/anthropics/claude-code/issues/88603), [#100138](https://github.com/anthropics/claude-code/issues/100138) and [#80791](https://github.com/anthropics/claude-code/issues/80791) were all open when this layout was chosen. Re-check them before you move it.

So the install places three subagent trees. OpenCode and Kilo Code read the same OpenCode-format files, so both
link to `~/.config/agents/agents`. Codex and Copilot each need their own format, and Claude Code takes every subagent as its own plugin, in a format of its own as well, for these reasons:

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

Codex cannot take the shared skills folder as one directory link, because it writes into its own skills folder as well: it puts its bundled skills in `$CODEX_HOME/skills/.system/`, measured with Codex 0.162.1. Through a whole-directory link they landed in the shared tree that every other agent scans. That is why the Codex folder is a real directory holding one link per shared skill, which [sync_skill_links.py](#the-skill-link-hook) keeps current. Claude Code writes into its own folder too, the skills it syncs from claude.ai go to `~/.claude/skills/synced/` ([skills docs](https://code.claude.com/docs/en/skills): "Claude Code uses `~/.claude/skills/synced/` for skills downloaded from claude.ai"), and it needs no link at all, because its skills are plugins.

No agent gets an MCP server at user or global scope, and Claude Code gets no `mcp-<server>` plugin with the user scope either. Each project declares the servers it uses in its own files, because every chat starts its own copy of every server it loads, so a server at user scope runs in every chat of every project. The rule, the measurement behind it, the commands and the Codex trust note are under [Where a server is declared](https://github.com/Lukk17/agent-standards/blob/master/docs/MCP_SETUP.md#where-a-server-is-declared). OpenCode and Kilo Code share each project's list without any setup, because both read the project's `opencode.json`.

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
shell, and every agent in this document that reads a link followed one when it was measured: OpenCode 1.18.32 and Kilo Code 7.7.9 loaded subagents through a junction. A file link,
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

If you never use a bare repository yourself, also tell git to ignore one it finds on its own. A bare repository is a git folder with no working tree, and one hidden inside a project you open, such as a branch you were asked to review, brings its own `config`. When an agent runs git in or below that folder, git reads that `config`, and a setting there can name a program git then runs, as `core.fsmonitor` does for `git status`. With `safe.bareRepository` set to `explicit`, Git "only works with bare repositories specified via the top-level `--git-dir` command-line option, or the `GIT_DIR` environment variable", which git suggests to anyone who does not use bare repositories, because it "will protect you from attacks that involve cloning a repository that contains a bare repository and running a Git command within that directory" ([safe.bareRepository at v2.43.0](https://raw.githubusercontent.com/git/git/v2.43.0/Documentation/config/safe.txt)). Git honours the setting only from your system, global and command-line configuration, never from a repository's own, so a repository cannot switch it back off. Before git 2.44 the setting also refuses a command run inside a normal repository's own `.git` folder, and before git 2.45 one run inside a linked worktree's folder under `.git/worktrees` ([2.44.0 release notes](https://raw.githubusercontent.com/git/git/v2.44.0/Documentation/RelNotes/2.44.0.txt), [2.45.0 release notes](https://raw.githubusercontent.com/git/git/v2.45.0/Documentation/RelNotes/2.45.0.txt)), so set it on git 2.45 or newer, or accept that git refuses those folders. In either shell:

```bash
git config --global safe.bareRepository explicit
```

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

Three of the hook scripts get wired per agent below, for Codex and Copilot, and the OpenCode and Kilo Code plugin runs them itself. Claude Code reads none of the five trees: it runs its own copy of every hook from the hook plugins. The skill link hook in `hooks/claude/` is wired nowhere, the updater and you run it for Codex. `markdown_lint_check.py`, with the `_check_markdown.py` rules beside it, and every other script under `hooks/claude/` are copied and left unwired, because each of them reports through a Claude Code event only. They are copied anyway, because the copy is one directory rather than a file list.

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

The reply rules stay a separate file, `~/.config/agents/instructions/reply-rules.md`, and are never merged into `AGENTS.md`. A project loads its own copy through the `instructions` key of `opencode.json` on OpenCode 1.x and Kilo Code. OpenCode 2.x ignores that key, expands neither an `@path` line nor a markdown link in `AGENTS.md`, and replaces the whole base prompt when an agent's `system` names a file, so the plugin adds the rules itself there: on every model request it pushes the project's `.agents/instructions/reply-rules.md`, or this global copy when the project has none, as one more system part, which keeps the built-in prompt. It skips a session whose `parentID` marks it as a subagent, because only the main thread's reply reaches the user, and a session it cannot place still gets the rules. Measured with OpenCode 2.0.26. On OpenCode 1.x and Kilo Code the `instructions` key loads the rules into every agent, subagents included, and that stays as it is. On Claude Code no plugin and no hook loads the reply rules. They come from your own output style, a file in `~/.claude/output-styles` whose body is the text of `reply-rules.md`, which reaches the main conversation only, as [the Claude Code section](#claude-code) shows with the commands. They stay out of `AGENTS.md` there too, because a Claude Code subagent loads the same CLAUDE.md hierarchy as the main conversation, `~/.claude/CLAUDE.md` and the `AGENTS.md` it imports included, unless its definition sets `omitClaudeMd: true` ([sub-agents](https://code.claude.com/docs/en/sub-agents), "What loads at startup"), so any rule placed there reaches subagents too. On Codex and Copilot nothing loads the reply rules: the reminder each of them prints on every prompt carries the status block, the one part of the rules every reply needs.

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

Every subsection but the Claude Code one assumes steps 1 to 4 are done. Adding a second agent later is nothing more than running its
subsection too, because the shared folder is the same files. The commands that write a configuration file read their
block, or the shipped server list, out of the temporary copy from step 1, so run them before the finish step deletes
it, and make a new copy as in step 1 when you come back later.

#### Claude Code

Claude Code stays in `~/.claude` and reads one shared file from `~/.config/agents`, the instruction file `AGENTS.md`, through the import below. It takes nothing else from the shared folder. Its skills, subagents and hooks are plugins from the marketplace of this repository, the [marketplace.json](https://github.com/Lukk17/agent-standards/blob/master/.claude-plugin/marketplace.json) on the upstream `master`, added once and installed with the user scope, where "the plugin is enabled for you in every project on this machine" ([Install plugins](https://code.claude.com/docs/en/plugins/install), "Choose an install scope", read 2026-11-24). So this install puts no link into `~/.claude/skills`, no copy into `~/.claude/agents` and no `hooks` block into `~/.claude/settings.json`.

Of steps 1 to 4, Claude Code needs step 3, the instruction file, and from step 2 only the `instructions` folder, which holds the text of the reply rules. No plugin command below reads the temporary copy. An install made before the plugins holds those links, copies and hooks, and [Moving Claude Code to the plugins](#moving-claude-code-to-the-plugins) removes them first. [Claude Code plugins](https://github.com/Lukk17/agent-standards/blob/master/docs/AGENT_TOOLING.md#claude-code-plugins) lists every plugin and bundle, and gives the same commands with `--scope project` for a single project. The commands below were run with Claude Code 2.1.325 on 2026-11-24 in a throwaway home.

Create the directory. PowerShell:

```powershell
New-Item -ItemType Directory -Force $HOME\.claude
```

Unix shell:

```bash
mkdir -p ~/.claude
```

Make `~/.claude/CLAUDE.md` a real file that imports the shared one, rather than a link to it. This import is the one thing Claude Code still reads from `~/.config/agents`. "CLAUDE.md files can import additional files using `@path/to/import` syntax", and a user-scope file's imports load without a prompt ([memory docs](https://code.claude.com/docs/en/memory)). A link would not do, because in a Cowork session Claude Code "skips a `~/.claude/CLAUDE.md` that is itself a symlink or hard link". A real file still loads there, but Cowork also "skips any import in a user-scope file that resolves to a path outside the session's working directory", so anything that must reach a Cowork session has to be written into `~/.claude/CLAUDE.md` itself, below the import. If you already have a `~/.claude/CLAUDE.md`, move its content into `~/.config/agents/AGENTS.md` first. PowerShell:

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

`~/.config/agents/MACHINE.md`, when you keep one, is not imported. It stays a plain file that one rule in `AGENTS.md` names by its path, so an agent reads it only when a task touches the machine itself.

Add the marketplace once. The command is the same in PowerShell and a Unix shell, as is every `claude plugin` command below:

```bash
claude plugin marketplace add Lukk17/agent-standards --scope user
```

It ends with `Successfully added marketplace: agent-standards (declared in user settings)` and records the marketplace under `extraKnownMarketplaces` in `~/.claude/settings.json`.

Install `core`, the skills that subagents in two or more domains preload:

```bash
claude plugin install core@agent-standards --scope user
```

It ends with `Successfully installed plugin: core@agent-standards (scope: user)` and names the plugins the bundle brought. Each one is recorded under `enabledPlugins` in `~/.claude/settings.json`.

Then install each bundle you use in every project, such as `review-and-security`, which brings the `code-reviewer` and `security-auditor` subagents with two more and their skills:

```bash
claude plugin install review-and-security@agent-standards --scope user
```

Install every other bundle, subagent or skill in the project that needs it, with `--scope project`, as [Claude Code plugins](https://github.com/Lukk17/agent-standards/blob/master/docs/AGENT_TOOLING.md#claude-code-plugins) shows. A domain bundle installed in a project brings `core` again, at project scope. The two do not add up, because `enabledPlugins` entries "merge key by key. For each plugin id, the value that applies is the one from the highest-precedence source that mentions the id" ([plugin loading](https://code.claude.com/docs/en/plugins/loading), "Find where a plugin is enabled", read 2026-11-24), so a plugin switched on at both scopes is still one plugin.

Choose the user-wide set by the size of the skill listing. Claude Code loads the name and the description of every enabled skill into every session, and "The budget scales at 1% of the model's context window. When the listing overflows, Claude Code drops descriptions starting with the skills you invoke least" ([skills docs](https://code.claude.com/docs/en/skills), "Skill descriptions are cut short", read 2026-11-24). A skill whose description was dropped can no longer be matched to a request by its keywords. These are the description characters of what this repository shipped on 2026-11-24:

| Installed with the user scope | Description characters |
| --- | --- |
| `core` | 2,992 |
| `core` and one domain bundle | 3,199 to 4,275 |
| `core`, `agent-tooling`, `linux`, `personal-tools` and `homelab` | 7,059 |
| the bundle `all` | 11,281 |
| all 72 skills | 15,374 |

So install `core` and the bundles you use in every project with the user scope, install the rest in the project that needs them, and never install `all` with the user scope. A plugin at project scope adds its descriptions only in that project.

Install the hooks. `hooks-all` brings every hook plugin: the preflight gate, the three reminders, the reply formatting check, the task list, the markdown lint and the standards advisory.

```bash
claude plugin install hooks-all@agent-standards --scope user
```

With the user scope every one of them runs in every project on the machine, the markdown lint and the standards advisory included. The markdown lint then reports on `README.md` and on the files under `docs/`, `.agents/skills/` and `subagents/` of any project you edit, by the rules of this repository, and the standards advisory warns after an edit in any project. To leave those two out, install the hook plugins one by one instead, such as `hook-preflight-gate`, and install `hook-markdown-lint-check` and `hook-standards-advisory-check` with `--scope project` only where you want them:

```bash
claude plugin install hook-preflight-gate@agent-standards --scope user
```

Each hook plugin runs its script from the plugin's own folder in the Claude Code plugin cache, started in the project directory, so no command names a path under `~/.config/agents`. Every command is POSIX shell, because Claude Code passes a command hook "to a shell: `sh -c` on macOS and Linux, Git Bash on Windows, or PowerShell when Git Bash isn't installed" ([hooks docs](https://code.claude.com/docs/en/hooks)). On a Windows machine without Git Bash, PowerShell rejects these commands with a parse error and exits 1, which Claude Code treats as a non-blocking error, so every hook allows and nothing is gated. Install Git for Windows before relying on the gate there.

Check the install. It lists every plugin with its version, `Scope: user` and its status:

```bash
claude plugin list
```

Check that nothing was written the old way. Both commands print nothing on a machine that never had the older install. Unix shell:

```bash
find ~/.claude/skills -maxdepth 1 -type l -lname '*.config/agents/skills/*' 2>/dev/null
```

```bash
grep -n 'config/agents/hooks/' ~/.claude/settings.json
```

PowerShell:

```powershell
Get-ChildItem $HOME\.claude\skills -Force -ErrorAction SilentlyContinue | Where-Object { $_.LinkType }
```

```powershell
Select-String -Path $HOME\.claude\settings.json -Pattern 'config/agents/hooks/' -List
```

Keep no MCP server at user scope. MCP at user scope is stored in `~/.claude.json`, and a plugin installed with the user scope is on in every project, so install no `mcp-<server>` plugin and no `mcp-all` with the user scope either. None of the bundles above carries a server. Declare each server in the project that uses it, in its `.mcp.json`, with `claude mcp add --scope project`, or as its plugin with `--scope project`, and approve it on the first start of `claude` in that folder, as [Where a server is declared](https://github.com/Lukk17/agent-standards/blob/master/docs/MCP_SETUP.md#where-a-server-is-declared) describes with the commands.

Give Claude Code the reply rules through an output style of your own. No plugin and no hook loads them. An output style is a markdown file in `~/.claude/output-styles`, whose instructions Claude Code sends "with every request", and it reaches the main conversation only: "Other subagents run their own system prompt, so styles don't change how they respond" ([output styles](https://code.claude.com/docs/en/output-styles), "How output styles work", read 2026-11-24). That is where the rules belong, because only the main thread's reply reaches you. The text to copy is `.agents/instructions/reply-rules.md` of this repository, which the shared folder holds as `~/.config/agents/instructions/reply-rules.md`. Write the style file with its front matter above that text. `keep-coding-instructions: true` keeps Claude Code's own software engineering instructions beside the style. Unix shell:

```bash
mkdir -p ~/.claude/output-styles && { printf '%s\n' '---' 'name: Reply rules' 'description: The agent-standards reply rules' 'keep-coding-instructions: true' '---' ''; cat ~/.config/agents/instructions/reply-rules.md; } > ~/.claude/output-styles/reply-rules.md
```

PowerShell:

```powershell
New-Item -ItemType Directory -Force $HOME\.claude\output-styles | Out-Null; Set-Content -Path $HOME\.claude\output-styles\reply-rules.md -Value (@('---', 'name: Reply rules', 'description: The agent-standards reply rules', 'keep-coding-instructions: true', '---', '') + (Get-Content $HOME\.config\agents\instructions\reply-rules.md))
```

Make it the style of every project by setting `outputStyle` in `~/.claude/settings.json`, where "A project's own settings files take precedence over that value" (same page, "Change your output style"). The command keeps every other key of the file. Unix shell:

```bash
python3 -c 'import json,pathlib;p=pathlib.Path.home()/".claude/settings.json";s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};s["outputStyle"]="Reply rules";p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")'
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,pathlib;p=pathlib.Path.home()/".claude/settings.json";s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};s["outputStyle"]="Reply rules";p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")'
```

Check it in a new session with `/output-style`, which lists `Reply rules (current)`, measured with Claude Code 2.1.325. To use it in one session only, run `/output-style Reply rules` there instead. The style file is your own copy: no update refreshes it, so write it again when the reply rules change upstream.

A project's own skills live in that project's `.claude/skills/<skill-name>/SKILL.md`, in a real folder that you commit, and a personal skill of yours in `~/.claude/skills/<skill-name>/`. Never make `.claude/skills` a link to `.agents/skills`. That folder holds the agent-standards skills for the other agents, and Claude Code loads a skill in a skills folder and a plugin skill of the same name side by side, "because plugin skills are namespaced as `/plugin-name:skill-name`" (skills docs, "Resolve skills that share a name"), so the link would list every agent-standards skill twice.

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
python3 -S -E ~/.config/agents/hooks/claude/sync-skill-links/sync_skill_links.py
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
            "command": "grep -F '\"agent_id\"' >/dev/null || printf '%s\\n' '{\"hookSpecificOutput\": {\"hookEventName\": \"UserPromptSubmit\", \"additionalContext\": \"Before code work, name the skills and subagents that own this task and invoke them, or say none apply and why, in one line. End every reply to the user with this block, exactly as shown: no heading, no bullets, no numbered list, plain lines only, keeping every blank line:\\n\\nRunning: `running task name` (or: nothing)\\n\\n~~DONE: older finished task~~\\n~~DONE: most recent finished task~~\\n\\nNOW: what is being done right now\\n\\nNext: the next task\\nThen: the task after that\\n\\nWaiting on: what you wait for (or: nothing)\\n\\nWhen several tasks run, list each name in backticks on the Running line, separated by commas.\"}}'",
            "commandWindows": "if (-not [Console]::In.ReadToEnd().Contains(\"`\"agent_id`\"\")) { echo '{\"hookSpecificOutput\": {\"hookEventName\": \"UserPromptSubmit\", \"additionalContext\": \"Before code work, name the skills and subagents that own this task and invoke them, or say none apply and why, in one line. End every reply to the user with this block, exactly as shown: no heading, no bullets, no numbered list, plain lines only, keeping every blank line:\\n\\nRunning: `running task name` (or: nothing)\\n\\n~~DONE: older finished task~~\\n~~DONE: most recent finished task~~\\n\\nNOW: what is being done right now\\n\\nNext: the next task\\nThen: the task after that\\n\\nWaiting on: what you wait for (or: nothing)\\n\\nWhen several tasks run, list each name in backticks on the Running line, separated by commas.\"}}' }; exit 0"
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
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.config/agents/hooks/task-list-sync/task_list_sync.py --event sessionstart --format codex 2>/dev/null || exit 0",
            "commandWindows": "$root = git rev-parse --show-toplevel 2>$null; if ($root) { Set-Location -LiteralPath $root }; python -S -E /home/you/.config/agents/hooks/task-list-sync/task_list_sync.py --event sessionstart --format codex 2>$null; exit 0"
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
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.config/agents/hooks/no-ai-markers-check/no_ai_markers_check.py --format codex 2>/dev/null || exit 0",
            "commandWindows": "$root = git rev-parse --show-toplevel 2>$null; if ($root) { Set-Location -LiteralPath $root }; python -S -E /home/you/.config/agents/hooks/no-ai-markers-check/no_ai_markers_check.py --format codex 2>$null; exit 0"
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
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.config/agents/hooks/preflight-gate/preflight_gate.py --format codex 2>/dev/null || exit 0",
            "commandWindows": "$root = git rev-parse --show-toplevel 2>$null; if ($root) { Set-Location -LiteralPath $root }; python -S -E /home/you/.config/agents/hooks/preflight-gate/preflight_gate.py --format codex 2>$null; exit 0"
          }
        ]
      }
    ]
  }
}
```

Write it with one command. The command reads the block above out of the temporary copy from step 1, so run it before you delete the copy. It puts your home directory in place of `/home/you`, with forward slashes on Windows too, which work there and need no escaping inside JSON, and merges the block into `~/.config/codex/hooks.json`, or creates the file when there is none. Every other key in the file stays as it is. In each event, a hook group this install wrote earlier, recognised by a path into `agents/hooks/` or by the wording of the reminder, is replaced, and every other group of yours is kept, so running the command again changes nothing. A file that is not plain JSON stops it with an error before anything is written. The file is written back with two-space indentation. Unix shell:

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

MCP servers could go in `[mcp_servers.<name>]` tables in `~/.config/codex/config.toml`, which is shared by the Codex CLI, the IDE extension, and the ChatGPT desktop app ([MCP docs](https://learn.chatgpt.com/codex/extend/mcp)), but keep no server there, and leave `codex mcp add` unused, because it writes only that file. Each project declares its servers in its own `.codex/config.toml`, which Codex loads only in a trusted project: "you can also scope MCP servers to a project with `.codex/config.toml` (trusted projects only)" ([MCP docs](https://learn.chatgpt.com/docs/extend/mcp), read 2026-11-20). The trust is a `[projects."<path>"]` table with `trust_level = "trusted"` in `~/.config/codex/config.toml`. It is not a server, so it stays there. The commands and the trust entry are under [Where a server is declared](https://github.com/Lukk17/agent-standards/blob/master/docs/MCP_SETUP.md#where-a-server-is-declared).

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

MCP servers could go under the `mcp` key of `~/.config/opencode/opencode.json` ([config docs](https://opencode.ai/docs/config/)), but keep no server there. Each project declares its servers in the `mcp` block of its own `opencode.json`, as [Where a server is declared](https://github.com/Lukk17/agent-standards/blob/master/docs/MCP_SETUP.md#where-a-server-is-declared) describes with the commands.

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

MCP servers could go under the `mcp` key of `~/.config/kilo/kilo.jsonc`, in the same shape as `opencode.json` ([CLI docs](https://kilo.ai/docs/code-with-ai/platforms/cli)), but keep no server there. Kilo Code reads the project's `opencode.json`, so each project declares its servers there for OpenCode and Kilo Code at once, as [Where a server is declared](https://github.com/Lukk17/agent-standards/blob/master/docs/MCP_SETUP.md#where-a-server-is-declared) describes with the commands. That file can hold no `{env:VAR}` token, so Kilo Code uses Context7 on the free tier, as [What ships](https://github.com/Lukk17/agent-standards/blob/master/docs/MCP_SETUP.md#what-ships) explains.

#### Share one MCP list between OpenCode and Kilo Code

Not needed any more. No server sits in a global file, so there is no global list to share, and both agents already share each project's `opencode.json`. If an older setup made `~/.config/agents/mcp.json` and named it in `OPENCODE_CONFIG` and `KILO_CONFIG`, first declare each server it holds in the projects that use it, as [Where a server is declared](https://github.com/Lukk17/agent-standards/blob/master/docs/MCP_SETUP.md#where-a-server-is-declared) describes, then delete the file and clear both variables. Linux, in the environment file from step 4:

```bash
sed -i '/^OPENCODE_CONFIG=/d;/^KILO_CONFIG=/d' ~/.config/environment.d/60-agents.conf
```

Check it. It prints nothing once both lines are gone:

```bash
grep -n '_CONFIG=' ~/.config/environment.d/60-agents.conf
```

PowerShell:

```powershell
'OPENCODE_CONFIG', 'KILO_CONFIG' | ForEach-Object { [Environment]::SetEnvironmentVariable($_, $null, 'User') }
```

Delete the file, in either shell:

```bash
rm ~/.config/agents/mcp.json
```

Restart the agents, or sign out and in again, so they stop reading the variables.

#### GitHub Copilot

The CLI configuration directory is `COPILOT_HOME`, which step 4 points at `~/.config/copilot`, and "`COPILOT_HOME` replaces the entire `~/.copilot` path" ([CLI config dir reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference)). The same step names the shared skills in `COPILOT_SKILLS_DIRS` and the shared instruction folder in `COPILOT_CUSTOM_INSTRUCTIONS_DIRS`, so the skills and the instructions need nothing here.

VS Code reads its own fixed paths: its Local agent loads user hooks from `~/.copilot/hooks/*.json` and user custom agents from `~/.copilot/agents` or `~/.claude/agents` ([VS Code hooks](https://code.visualstudio.com/docs/copilot/customization/hooks), [VS Code custom agents](https://code.visualstudio.com/docs/copilot/customization/custom-agents)). Whether it honours `COPILOT_HOME` is not documented and was not tested, so a VS Code user who wants the hooks there keeps a copy in `~/.copilot` as well. Because VS Code reads both agent folders, a subagent copy that an older install left in `~/.claude/agents` shows up there twice, until [Moving Claude Code to the plugins](#moving-claude-code-to-the-plugins) has removed it.

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
        "bash": "printf '%s\\n' '{\"additionalContext\": \"Before code work, name the skills and subagents that own this task and invoke them, or say none apply and why, in one line. End every reply to the user with this block, exactly as shown: no heading, no bullets, no numbered list, plain lines only, keeping every blank line:\\n\\nRunning: `running task name` (or: nothing)\\n\\n~~DONE: older finished task~~\\n~~DONE: most recent finished task~~\\n\\nNOW: what is being done right now\\n\\nNext: the next task\\nThen: the task after that\\n\\nWaiting on: what you wait for (or: nothing)\\n\\nWhen several tasks run, list each name in backticks on the Running line, separated by commas.\"}'",
        "powershell": "echo '{\"additionalContext\": \"Before code work, name the skills and subagents that own this task and invoke them, or say none apply and why, in one line. End every reply to the user with this block, exactly as shown: no heading, no bullets, no numbered list, plain lines only, keeping every blank line:\\n\\nRunning: `running task name` (or: nothing)\\n\\n~~DONE: older finished task~~\\n~~DONE: most recent finished task~~\\n\\nNOW: what is being done right now\\n\\nNext: the next task\\nThen: the task after that\\n\\nWaiting on: what you wait for (or: nothing)\\n\\nWhen several tasks run, list each name in backticks on the Running line, separated by commas.\"}'"
      },
      {
        "type": "command",
        "cwd": ".",
        "bash": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.config/agents/hooks/task-list-sync/task_list_sync.py --event sessionstart --format copilot 2>/dev/null || exit 0",
        "powershell": "python -S -E /home/you/.config/agents/hooks/task-list-sync/task_list_sync.py --event sessionstart --format copilot 2>$null; exit 0"
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
        "bash": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.config/agents/hooks/copilot/prompt-reminder/prompt_reminder.py 2>/dev/null || exit 0",
        "powershell": "python -S -E /home/you/.config/agents/hooks/copilot/prompt-reminder/prompt_reminder.py 2>$null; exit 0"
      }
    ],
    "preToolUse": [
      {
        "type": "command",
        "matcher": "bash|powershell|create|edit|apply_patch",
        "cwd": ".",
        "bash": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.config/agents/hooks/preflight-gate/preflight_gate.py --format copilot 2>/dev/null || exit 0",
        "powershell": "python -S -E /home/you/.config/agents/hooks/preflight-gate/preflight_gate.py --format copilot 2>$null; exit 0"
      }
    ],
    "agentStop": [
      {
        "type": "command",
        "cwd": ".",
        "bash": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E /home/you/.config/agents/hooks/no-ai-markers-check/no_ai_markers_check.py --format copilot 2>/dev/null || exit 0",
        "powershell": "python -S -E /home/you/.config/agents/hooks/no-ai-markers-check/no_ai_markers_check.py --format copilot 2>$null; exit 0"
      }
    ]
  }
}
```

Write it with the same command as under [Codex](#codex), with the Copilot marker and file. It reads the block above from the temporary copy, replaces only the hook entries this install wrote, and keeps the rest of your file. Unix shell:

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
matcher values". This install writes no hook into that file any more, but a `hooks` block an older install left there would run the gate a second time on every tool call in a VS Code chat, until [Moving Claude Code to the plugins](#moving-claude-code-to-the-plugins) has removed it.

MCP for the CLI could go in `~/.config/copilot/mcp-config.json`, and for VS Code in the `mcp.json` in your user profile folder, which the `MCP: Open User Configuration` command opens and which applies across every workspace. Keep no server in either. The CLI reads the project's `.mcp.json` and VS Code the project's `.vscode/mcp.json`, as [Where a server is declared](https://github.com/Lukk17/agent-standards/blob/master/docs/MCP_SETUP.md#where-a-server-is-declared) describes. The JetBrains plugin reads one global file and no project file: `C:\Users\<you>\AppData\Local\github-copilot\intellij\mcp.json` on Windows and `~/.config/github-copilot/intellij/mcp.json` elsewhere, so its servers can only go there. GitHub documents only the in-IDE interface, not the path, so treat that path as observed rather than documented. The manual block for JetBrains is in [MCP_SETUP.md](https://github.com/Lukk17/agent-standards/blob/master/docs/MCP_SETUP.md).

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

`~/.config/agents/hooks/claude/sync-skill-links/sync_skill_links.py` keeps one folder in step with `~/.config/agents/skills`: `$CODEX_HOME/skills`, or `~/.config/codex/skills` when `CODEX_HOME` is unset, when that Codex home exists. In it the script links every shared folder that holds a `SKILL.md` and has no entry of that name yet, and removes a link that points into the shared folder at a skill that is gone. It never touches `synced`, `.trash`, a dot entry such as Codex's `.system`, a real directory, or a link that points anywhere else, and it leaves a folder that is itself a link alone. It always exits 0 and reports to standard error.

It no longer has a Claude Code job. Claude Code takes its skills as plugins, so the script never creates, fills or cleans `~/.claude/skills`, and no Claude Code event runs it. The links an older install left there go with [Moving Claude Code to the plugins](#moving-claude-code-to-the-plugins). The script keeps its place under `hooks/claude/`, two folders below the hooks folder, where the OpenCode and Kilo Code plugin never runs it on a tool call.

Both updaters run it after an update, so a Codex machine picks up a new skill at the next update or when you run it by hand. The updaters run it with `HOME` set to the home they update and `CODEX_HOME` set to `.config/codex` inside that home, whatever your own `CODEX_HOME` says, so an update of another home with `--home-dir` or `-HomeDir` links nothing into your own Codex home. By hand:

```bash
python3 -S -E ~/.config/agents/hooks/claude/sync-skill-links/sync_skill_links.py
```

On Windows it does nothing, by design, because per-skill junctions were never tested there. The Windows steps above use junctions made by hand instead.

---

### Migrating from ~/.agents

An install made before this layout keeps everything in `~/.agents`, links `~/.claude/skills` to `~/.agents/skills` as a whole, and reads its instructions from `~/.claude/CLAUDE.md`. The updater stops with "migrate it first" until the steps below are done. Run them in order, on Linux and macOS, then give Claude Code its plugins as [Moving Claude Code to the plugins](#moving-claude-code-to-the-plugins) describes:

1. Move the shared folder:

   ```bash
   mkdir -p ~/.config && mv ~/.agents ~/.config/agents
   ```

2. Drop the skills that Claude Code synced through the old whole-directory link, which are its own and not part of the install:

   ```bash
   rm -rf ~/.config/agents/skills/synced ~/.config/agents/skills/.trash
   ```

3. Remove the whole-directory link, which removes only the link. Claude Code takes its skills as plugins now, so nothing replaces it:

   ```bash
   rm ~/.claude/skills
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

9. Rewrite the wiring in the configuration files with the commands from each agent's section, which keep every setting of yours. Make a temporary copy as in [step 1](#step-1-a-temporary-copy-of-the-repository), run the command that writes the configuration file in the section of each agent you use, [Codex](#codex), [OpenCode](#opencode), [Kilo Code](#kilo-code) and [GitHub Copilot](#github-copilot), each followed by its check, then delete the copy as in [the finish step](#finish-delete-the-temporary-copy). In `~/.config/codex/hooks.json` and `~/.config/copilot/hooks/preflight.json` the command replaces every hook group the old install wrote, the ones naming `/.agents/hooks/` included, with the current block. In `opencode.json` and `kilo.jsonc` it replaces the old `plugin` entry with the `plugin` directory, adds `skills.paths`, and removes the `instructions` entry that named `~/.claude/CLAUDE.md`. Then trust the changed hooks in an interactive Codex session. The `hooks` block in `~/.claude/settings.json` gets no new copy: step 3 of [Moving Claude Code to the plugins](#moving-claude-code-to-the-plugins) removes it.

10. Run the updater from its new place, which also fills `~/.config/codex/skills`:

    ```bash
    sh ~/.config/agents/bin/update-global.sh
    ```

On Windows the same steps apply with `Move-Item` for `mv`, `(Get-Item $HOME\.claude\skills).Delete()` to remove the old junction, and `New-Item -ItemType Junction` and `-ItemType SymbolicLink` for the new links as shown in each agent's section. That sequence was not run on Windows for this guide.

---

### Moving Claude Code to the plugins

An install made before Claude Code moved to the plugins gave it three things in its own directory: one link per shared skill in `~/.claude/skills`, or on Windows one junction for the whole folder, a copy of every subagent in `~/.claude/agents`, and a `hooks` block in `~/.claude/settings.json` that runs the scripts in `~/.config/agents/hooks`. No update refreshes any of them any more, and the updater ends with a line starting `Claude Code:` that names each one it still finds.

Remove all three before you install the plugins. Claude Code loads a personal skill and a plugin skill of the same name side by side, "because plugin skills are namespaced as `/plugin-name:skill-name`" ([skills docs](https://code.claude.com/docs/en/skills), "Resolve skills that share a name"), so the links would list every skill twice, and a hook that the settings file and a plugin both carry runs twice. Nothing under `~/.config/agents` changes: Codex, OpenCode, Kilo Code and Copilot keep reading it, and `~/.claude/CLAUDE.md` keeps its import. Close every Claude Code session first. The Unix shell commands below were run on Linux with Claude Code 2.1.325 against such an install in a throwaway home. The PowerShell commands were not run.

1. Remove the skill links. A skill folder of your own, the `synced` folder and a link that points anywhere else stay. Unix shell:

   ```bash
   find ~/.claude/skills -maxdepth 1 -type l -lname '*.config/agents/skills/*' -delete
   ```

   PowerShell, where the older install made `~/.claude/skills` one junction to the shared folder. This removes the junction and never the folder behind it:

   ```powershell
   if ((Test-Path $HOME\.claude\skills) -and (Get-Item $HOME\.claude\skills).LinkType) { (Get-Item $HOME\.claude\skills).Delete() }
   ```

   Through that junction Claude Code wrote the skills it synced from claude.ai into the shared folder. Remove them on Windows, so no other agent scans them:

   ```powershell
   Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $HOME\.config\agents\skills\synced, $HOME\.config\agents\skills\.trash
   ```

2. Remove the subagent copies. The command takes the names from `~/.config/agents/agents`, so a subagent of your own stays, and so does any other file you keep in an agent's folder. A copy you changed by hand goes with the rest, so move it out first, and delete by hand a copy whose file you already removed from the shared folder. Unix shell:

   ```bash
   for f in ~/.config/agents/agents/*.md; do n=$(basename "$f" .md); rm -f ~/.claude/agents/"$n"/"$n".md ~/.claude/agents/"$n".md; rmdir ~/.claude/agents/"$n" 2>/dev/null || true; done
   ```

   PowerShell:

   ```powershell
   Get-ChildItem $HOME\.config\agents\agents -Filter *.md | ForEach-Object { $n = $_.BaseName; Remove-Item -Force -ErrorAction SilentlyContinue "$HOME\.claude\agents\$n\$n.md", "$HOME\.claude\agents\$n.md"; if ((Test-Path "$HOME\.claude\agents\$n") -and -not (Get-ChildItem -Force "$HOME\.claude\agents\$n")) { Remove-Item "$HOME\.claude\agents\$n" } }
   ```

3. Remove the `hooks` block the install wrote into `~/.claude/settings.json`. The command removes only the hook groups the install wrote, recognised by a path into `agents/hooks/` or by the wording of a reminder, keeps every hook of your own and every other key, and drops the `hooks` key when nothing is left in it. Unix shell:

   ```bash
   python3 -c 'import json,pathlib;p=pathlib.Path.home()/".claude/settings.json";s=json.loads(p.read_text(encoding="utf-8"));o=lambda x:any(m in json.dumps(x) for m in ("agents/hooks/","PREFLIGHT","Before code work","background subagent"));h={k:[x for x in v if not o(x)] for k,v in s.get("hooks",{}).items()};h={k:v for k,v in h.items() if v};s={k:(h if k=="hooks" else v) for k,v in s.items() if k!="hooks" or h};p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")'
   ```

   PowerShell 7.4 or later:

   ```powershell
   python -c 'import json,pathlib;p=pathlib.Path.home()/".claude/settings.json";s=json.loads(p.read_text(encoding="utf-8"));o=lambda x:any(m in json.dumps(x) for m in ("agents/hooks/","PREFLIGHT","Before code work","background subagent"));h={k:[x for x in v if not o(x)] for k,v in s.get("hooks",{}).items()};h={k:v for k,v in h.items() if v};s={k:(h if k=="hooks" else v) for k,v in s.items() if k!="hooks" or h};p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")'
   ```

4. Check that all three are gone. Each command prints nothing. Unix shell:

   ```bash
   find ~/.claude/skills -maxdepth 1 -type l -lname '*.config/agents/skills/*'
   ```

   ```bash
   for f in ~/.config/agents/agents/*.md; do n=$(basename "$f" .md); ls ~/.claude/agents/"$n"/"$n".md ~/.claude/agents/"$n".md 2>/dev/null; done
   ```

   ```bash
   grep -n 'config/agents/hooks/' ~/.claude/settings.json
   ```

   PowerShell:

   ```powershell
   Get-ChildItem $HOME\.claude\skills -Force -ErrorAction SilentlyContinue | Where-Object { $_.LinkType }
   ```

   ```powershell
   Get-ChildItem $HOME\.config\agents\agents -Filter *.md | ForEach-Object { Get-Item -ErrorAction SilentlyContinue "$HOME\.claude\agents\$($_.BaseName)\$($_.BaseName).md", "$HOME\.claude\agents\$($_.BaseName).md" }
   ```

   ```powershell
   Select-String -Path $HOME\.claude\settings.json -Pattern 'config/agents/hooks/' -List
   ```

5. Add the marketplace. The command is the same in either shell, as are the two below it:

   ```bash
   claude plugin marketplace add Lukk17/agent-standards --scope user
   ```

6. Install `core`, then each bundle you use in every project, chosen as [the Claude Code section](#claude-code) describes:

   ```bash
   claude plugin install core@agent-standards --scope user
   ```

7. Install the hooks, which now run in every project, the markdown lint and the standards advisory included:

   ```bash
   claude plugin install hooks-all@agent-standards --scope user
   ```

8. Check the result. It lists every plugin with `Scope: user`:

   ```bash
   claude plugin list
   ```

The install merges into `~/.claude/settings.json` and keeps the hooks and keys of your own. Give Claude Code the reply rules through an output style next, as [the Claude Code section](#claude-code) shows. A project that still holds a `.claude/skills` link, a `.claude/agents` tree or a `hooks` block from an older import moves the same way, with the commands under [Moving Claude Code to the plugins](https://github.com/Lukk17/agent-standards/blob/master/docs/AGENTS-UPDATE.md#moving-claude-code-to-the-plugins) in the update guide.

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
hooks the project ships in its own `.agents/hooks/`, and it does nothing on Codex or GitHub Copilot,
which call the gate from their own settings files, or on Claude Code, which calls it from its hook plugin.

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
outside the standard library, or a JavaScript module that is not built in, and in a command that changes directory
any standard Python module not built into the interpreter, because the gate no longer knows which folder could hold a
file of the same name. Writing `tasks.md` at the project root,
sending output to the null device, and switching branches all stay allowed.

Starting a shell, an interpreter, an editor or any other program that waits for typed input denies too, such as a bare
`bash`, `python3`, `python3 -i`, `vim`, `less`, `tmux`, `psql` or `gdb`, or a `git commit` that would open the editor,
because the gate never sees what is typed into it. Pass the code with `-c` or `-e`, the query with `psql -c` or
`sqlite3 db "SQL"`, the message with `git commit -m`, run a debugger in batch mode, pipe the input in, feed a database
shell or a debugger a file with `< file`, as in `psql app < schema.sql`, or hand the work to a subagent. An `xargs`
with nothing piped in reads names from the terminal and denies too, `xargs rm < list.txt` included, so pipe the names
in, as in `cat list.txt | xargs rm`, or name the file with `xargs -a list.txt`. A shell or an
interpreter fed a file with `< file` still denies, because that file is a script the gate cannot read.

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
  entry `python scripts/verify.py` allows that command and denies `python scripts/verify.py --fix`. The further
  arguments include the tool's own options, such as `-C`, `-f`, `--prefix` or `--manifest-path`, which can point the
  run at another folder or file, so end an entry with `...` only where every option the tool takes is safe.
- A word with a slash in it is a file path, and it matches the file it names from the folder the command starts in.
  When the gate cannot tell which of two folders that is, it has to name that file from both.
- An allowlisted command must run without changing directory. An entry, the built-in ones included, applies only to a
  command that changes no directory anywhere and starts inside the project. A `cd`, `pushd`, `popd`, `Set-Location`,
  `env --chdir` or any other directory change in the command, even one into a project folder as in
  `cd docs && python -m pytest -q`, turns every entry off for the whole command, and so does a Codex `workdir` outside
  the project, because pytest loads the `conftest.py` and make the `Makefile` of the folder they run in, and the gate
  does not follow where a directory change lands. Run the check from the project root and name the path instead, as in
  `python -m pytest -q docs`.
- The gate reads the words of the command, not what they do. A word counts as a directory change when a piece of it
  between blanks or shell punctuation is `cd`, `chdir`, `pushd`, `popd`, `sl`, `Set-Location`, `Push-Location` or
  `Pop-Location`, or when it holds `chdir`, `setwd`, `currentdirectory`, `workingdirectory`, `set-location`,
  `push-location`, `pop-location`, `setlocation`, `pushcurrentlocation`, `poplocation`, `execdir` or `okdir`
  anywhere, in any case. Only the text `echo`, `printf`, `Write-Output` or `Write-Host` prints is left out. So
  `python -m pytest -k chdir` turns every entry off and denies. Pick another `-k` expression, or hand the run to a
  subagent.
- An entry that hands a script to a shell, such as `bash scripts/check.sh`, only lifts the script-run rule. The gate
  still reads the script as shell code and denies it when it writes a file in the project or changes directory.
- The built-in list names no project's own scripts, because an entry such as `python tools/check.py` would also allow a
  same-named script in every other project, and that script could write files.

The built-in list lives in `MAIN_THREAD_ALLOWLIST` near the top of `.agents/hooks/preflight-gate/gate_rules.py`, the rules file the gate script `preflight_gate.py` imports. Do not edit it
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
subagent to add an entry. The project root here is the folder the gate runs in, never the working directory a single
call names: Codex fills that from the call's `workdir`, which the main thread picks, so an allowlist in a folder
outside the project adds nothing. Commit the file so the whole team gets the same list.

---

### What this document deliberately leaves to you

1. MCP servers, in each project. No server is machine-wide: each project declares the servers it uses in its own files, and no agent gets one at user scope. Which servers a project needs is a judgement about that project. [Where a server is declared](https://github.com/Lukk17/agent-standards/blob/master/docs/MCP_SETUP.md#where-a-server-is-declared) has the rule and the commands.
2. The content of `~/.config/agents/AGENTS.md`. Editing the template down to the parts that are about you is a job only you
   can do.
3. Reading the merged configuration files. No command above overwrites a configuration file you already have: each
   merges into it, keeps your own keys, and is followed by a check that prints what it wrote. Read that output, because
   only you know which of the other entries are yours.
4. Which Claude Code bundles go on the whole machine. [The Claude Code section](#claude-code) gives the sizes, and only you know which bundles every one of your projects uses.

---

### Global path map

Every global location this document touches, per agent. The project-level equivalents are the paths the import
writes into your repository, and they are unaffected by anything here.

| Agent | Skills | Subagents | Hooks or plugin | MCP config | Global instructions | Config-dir env var |
| --- | --- | --- | --- | --- | --- | --- |
| Claude Code | skill plugins in `~/.claude/plugins/cache/agent-standards/`, switched on by `enabledPlugins` in `~/.claude/settings.json`. `~/.claude/skills/` holds only skills of your own | `agent-<name>` plugins in the same cache. `~/.claude/agents/` holds only subagents of your own | `hook-<name>` plugins in the same cache, and no `hooks` block of this install in `~/.claude/settings.json` | none, `~/.claude.json` holds no server and no `mcp-<server>` plugin has the user scope, each project's `.mcp.json` does | `~/.claude/CLAUDE.md`, importing `~/.config/agents/AGENTS.md`, plus `~/.claude/rules/`, and the reply rules as your own style in `~/.claude/output-styles/` | `CLAUDE_CONFIG_DIR`, left unset |
| Codex | `~/.config/codex/skills/`, per-skill links, also `$HOME/.agents/skills` and `/etc/codex/skills` | `~/.config/codex/agents/` as TOML | `~/.config/codex/hooks.json`, or inline `[[hooks.*]]` in `~/.config/codex/config.toml` | none, each project's `.codex/config.toml`, trusted through `projects.<path>.trust_level` in `~/.config/codex/config.toml` | `~/.config/codex/AGENTS.md`, a link | `CODEX_HOME` |
| OpenCode | `skills.paths`, plus `~/.agents/skills/`, `~/.claude/skills/` and `~/.config/opencode/skills/` natively | `~/.config/opencode/agents/`, a link to `~/.config/agents/agents` | `plugin` in `~/.config/opencode/opencode.json`, naming `~/.config/agents/plugin` | none, each project's `opencode.json` | `~/.config/opencode/AGENTS.md`, a link | `OPENCODE_CONFIG_DIR`, and `OPENCODE_CONFIG` for a file |
| Kilo Code | `skills.paths`, plus `~/.agents/skills/` and `~/.kilo/skills/` natively, `~/.claude/skills/` behind a compatibility setting | `~/.config/kilo/agents/`, a link to `~/.config/agents/agents` | `plugin` in `~/.config/kilo/kilo.jsonc`, naming `~/.config/agents/plugin` | none, each project's `opencode.json` | `~/.config/kilo/AGENTS.md`, a link | `KILO_CONFIG` for a file |
| GitHub Copilot | `COPILOT_SKILLS_DIRS`, plus `~/.config/copilot/skills/` | `~/.config/copilot/agents/` for the CLI, `~/.copilot/agents/` for VS Code | `~/.config/copilot/hooks/` for the CLI, `~/.copilot/hooks/` for VS Code | none for the CLI and VS Code, each project's `.mcp.json` and `.vscode/mcp.json`, and `C:\Users\<you>\AppData\Local\github-copilot\intellij\mcp.json` for JetBrains on Windows, which has no project file | `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` naming `~/.config/agents` | `COPILOT_HOME` |

---

### Updating the global installation

One command updates everything the install put into the shared folder and the directories of Codex and Copilot. It clones a temporary copy of this repository,
reads the files of its newest commit, updates your install from them, prints what it did, and deletes the copy. It writes nothing under `~/.claude`: the Claude Code plugins update through the marketplace, as [Updating the Claude Code plugins](#updating-the-claude-code-plugins) below shows.
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
- Every subagent file you already have is refreshed, in the three trees: `~/.config/agents/agents`, which OpenCode and Kilo
  Code reach through their links, `~/.config/codex/agents`, and `~/.config/copilot/agents`. A subagent you do
  not have is never added.
- A file is removed only when the commit recorded in `~/.config/agents/.upstream-commit` shipped it and the new commit no
  longer does. A file of your own, such as a note you keep inside a skill folder, was never shipped, so it is never
  removed. When the recorded commit is missing or unknown, nothing is removed and the summary says so.
- A skill folder or a subagent file that upstream stopped shipping altogether stays in place and is reported as
  `keep`. One that never came from upstream is reported as `skip` and left alone.
- A hook file upstream moved or removed stays in place when your own wiring, `~/.config/codex/hooks.json`, `~/.config/codex/config.toml`, a hook file in `~/.config/copilot/hooks` or `~/.copilot/hooks`, or a `hooks` block an older install left in `~/.claude/settings.json`, still names it. It is reported as `keep (still wired)`, and a `WARNING` line at the end says that hook stays on the old copy until you take the new wiring in.
- A skill upstream renamed, such as `security-review`, now `application-security-review`, moves to its new name.
- The new commit is written to `~/.config/agents/.upstream-commit`.
- [The skill link hook](#the-skill-link-hook) runs last, so a skill removed upstream loses its link in the Codex skills folder now. A dry run skips it.
- Nothing under `~/.claude` is written. `~/.claude/settings.json` is only read. When the home still holds the skill links, the subagent copies or the `hooks` block of an install made before the plugins, a line starting `Claude Code:` names them and points at [Moving Claude Code to the plugins](#moving-claude-code-to-the-plugins).

It never touches the files listed under [Files no update touches](#files-no-update-touches). When upstream changed the
hook wiring of Codex or Copilot since the recorded commit, the summary names the changed files and prints the `git diff` command that
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
update  ~/.config/agents/hooks/preflight-gate/preflight_gate.py
add     ~/.config/agents/skills/research/references/source-order.md
skip    ~/.config/agents/skills/my-own-skill (not an upstream skill)
Hook wiring: unchanged upstream since 1006f0084bd24080dcfbadb5c4bd33aaa616950d.
Recorded 3f2abe7a3afd255c4220154474a1c4700ca37273 in ~/.config/agents/.upstream-commit.
Skill links: the Codex skills folder checked against ~/.config/agents/skills.
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
folder name under `.agents/skills/`. Codex, OpenCode, Kilo Code and Copilot then find it the way they find the others, once the skill link hook has run for Codex, and from then on the
update keeps it current. Claude Code gets a skill it does not have as that skill's plugin instead, such as `claude plugin install research@agent-standards --scope user`. PowerShell:

```powershell
Copy-Item -Recurse "$src\.agents\skills\research" $HOME\.config\agents\skills\research
```

Unix shell:

```bash
cp -R "$src/.agents/skills/research" ~/.config/agents/skills/research
```

#### Updating the Claude Code plugins

Claude Code does not refresh this marketplace in the background, because auto-update is off by default for every marketplace but the official ones ([Install plugins](https://code.claude.com/docs/en/plugins/install), "Keep plugins updated", read 2026-11-24). Refresh it first. The command is the same in either shell:

```bash
claude plugin marketplace update agent-standards
```

Then update the plugins. "There's no command that updates every plugin at once" (same page, "Update plugins now"), and a plugin updates only when its version rises, which every change upstream makes it do. In a session, `/plugin`, the Marketplaces tab and Update marketplace do both steps for every plugin you installed from it. From a shell, update one plugin:

```bash
claude plugin update core@agent-standards --scope user
```

Or update every plugin you installed with the user scope in one go. Unix shell:

```bash
claude plugin list --json | python3 -c 'import json,sys;[print(p["id"]) for p in json.load(sys.stdin) if p["scope"]=="user" and p["id"].endswith("@agent-standards")]' | while read -r p; do claude plugin update "$p" --scope user </dev/null; done
```

PowerShell:

```powershell
claude plugin list --json | ConvertFrom-Json | Where-Object { $_.scope -eq 'user' -and $_.id -like '*@agent-standards' } | ForEach-Object { claude plugin update $_.id --scope user }
```

An updated plugin loads in the next session. The Unix shell loop was run with Claude Code 2.1.325 against a home holding `core`, `agent-tooling` and `hooks-all`, and the PowerShell loop was not run.

A session opened inside a clone of the agent-standards repository itself changes which copy the whole machine uses. That repository's own `.claude/settings.json` declares the marketplace `agent-standards` as its local folder, and a session there replaces a registration of the same marketplace from GitHub for the whole machine, measured in the container sandbox with Claude Code 2.1.314. This reaches only a machine that works on agent-standards itself. See which source is registered. It prints `Source: GitHub (Lukk17/agent-standards)` for the upstream one and a directory for a clone, in either shell:

```bash
claude plugin marketplace list
```

When it names a directory, the plugins you installed are read from that clone, uncommitted work included, and `claude plugin list` shows a `Read from:` line with the folder for each. Go back by adding the upstream marketplace again with the first command of [the Claude Code section](#claude-code). Claude Code 2.1.325 refused that command with "its source doesn't match its extraKnownMarketplaces entry" after the folder had been added by hand with the user scope, and accepted it once the `agent-standards` entry was removed from `extraKnownMarketplaces` in `~/.claude/settings.json`. The way back after a session replaced the registration was not measured.

#### Files no update touches

Never refreshed, on purpose, because they become yours the moment you install them: `~/.config/agents/AGENTS.md`, `~/.claude/settings.json`,
`~/.claude/CLAUDE.md`, `~/.claude.json`, your reply rules style in `~/.claude/output-styles`, `~/.config/codex/hooks.json`, `~/.config/codex/config.toml`,
`~/.config/opencode/opencode.json`, `~/.config/kilo/kilo.jsonc`, `~/.config/copilot/hooks/preflight.json`,
`~/.config/copilot/mcp-config.json`, the environment file from step 4, and `~/.config/agents/mcp.json` if you made one. When upstream changes the gate wording or the
hook wiring of Codex or Copilot, run the command that writes the file again, from the agent's section above and against a new temporary copy. The Claude Code wiring arrives with its hook plugins. When it adds an MCP server you want, declare it in the project that uses it, as [Where a server is declared](https://github.com/Lukk17/agent-standards/blob/master/docs/MCP_SETUP.md#where-a-server-is-declared) describes.

---

### Undoing the global installation

Remove it by hand, checking each directory before you delete it. Every directory the install writes into is one an
agent also lets you put your own files in, so deleting a whole tree takes anything you wrote yourself along with it.

Take the plugins out of Claude Code first. Removing the marketplace uninstalls every plugin installed from it: "When you remove a marketplace, Claude Code uninstalls every plugin you installed from it and removes their `enabledPlugins` entries from your settings files" ([Install plugins](https://code.claude.com/docs/en/plugins/install), "Manage marketplaces", read 2026-11-24). Run it from your home directory, so no project settings are in reach. Claude Code 2.1.325 then left every other key of `~/.claude/settings.json` in place, with `enabledPlugins` and `extraKnownMarketplaces` empty. The command is the same in either shell:

```bash
claude plugin marketplace remove agent-standards --scope user
```

Delete the reply rules style when you made one, and take the `outputStyle` key out of `~/.claude/settings.json` by hand. PowerShell:

```powershell
Remove-Item -Force -ErrorAction SilentlyContinue $HOME\.claude\output-styles\reply-rules.md
```

Unix shell:

```bash
rm -f ~/.claude/output-styles/reply-rules.md
```

An install made before the plugins also holds skill links, subagent copies and a `hooks` block for Claude Code. Remove them with steps 1 to 4 of [Moving Claude Code to the plugins](#moving-claude-code-to-the-plugins).

Then remove the links of the other agents, so deleting a link never reaches the shared folder behind it. A junction or a symlink is
removed as the link itself, and the per-skill links inside `~/.config/codex/skills` go with a find that deletes links only. PowerShell:

```powershell
foreach ($l in "$HOME\.config\opencode\agents", "$HOME\.config\kilo\agents") { if ((Test-Path $l) -and (Get-Item $l).LinkType) { (Get-Item $l).Delete() } }
```

Unix shell:

```bash
find ~/.config/codex/skills -maxdepth 1 -type l -delete
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

Then, per agent, remove only what you recognise in the `agents/` directories of Codex and Copilot.

Take the gate out of `~/.config/codex/hooks.json` and `~/.config/copilot/hooks/preflight.json`. Each may hold configuration of yours as well, so this command removes only the hook groups the install wrote, recognised the same way the install command recognises them, and keeps everything else. Unix shell:

```bash
python3 -c 'import json,pathlib;h=pathlib.Path.home();o=lambda x:any(m in json.dumps(x) for m in ("agents/hooks/","PREFLIGHT","Before code work","background subagent"));[p.write_text(json.dumps((lambda s:{**s,"hooks":{k:[x for x in v if not o(x)] for k,v in s.get("hooks",{}).items() if any(not o(x) for x in v)}})(json.loads(p.read_text(encoding="utf-8"))),indent=2)+"\n",encoding="utf-8") for p in (h/".config/codex/hooks.json",h/".config/copilot/hooks/preflight.json") if p.exists()]'
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,pathlib;h=pathlib.Path.home();o=lambda x:any(m in json.dumps(x) for m in ("agents/hooks/","PREFLIGHT","Before code work","background subagent"));[p.write_text(json.dumps((lambda s:{**s,"hooks":{k:[x for x in v if not o(x)] for k,v in s.get("hooks",{}).items() if any(not o(x) for x in v)}})(json.loads(p.read_text(encoding="utf-8"))),indent=2)+"\n",encoding="utf-8") for p in (h/".config/codex/hooks.json",h/".config/copilot/hooks/preflight.json") if p.exists()]'
```

Take the `plugin` and `skills` entries out of `opencode.json` and `kilo.jsonc` the same way, which removes only the entries that name `~/.config/agents`. Unix shell:

```bash
python3 -c 'import json,pathlib;h=pathlib.Path.home();f=lambda s:{**s,"plugin":[x for x in s.get("plugin",[]) if "agents/plugin" not in str(x)],"skills":{**s.get("skills",{}),"paths":[x for x in s.get("skills",{}).get("paths",[]) if ".config/agents/skills" not in x]}};[p.write_text(json.dumps(f(json.loads(p.read_text(encoding="utf-8"))),indent=2)+"\n",encoding="utf-8") for p in (h/".config/opencode/opencode.json",h/".config/kilo/kilo.jsonc") if p.exists()]'
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,pathlib;h=pathlib.Path.home();f=lambda s:{**s,"plugin":[x for x in s.get("plugin",[]) if "agents/plugin" not in str(x)],"skills":{**s.get("skills",{}),"paths":[x for x in s.get("skills",{}).get("paths",[]) if ".config/agents/skills" not in x]}};[p.write_text(json.dumps(f(json.loads(p.read_text(encoding="utf-8"))),indent=2)+"\n",encoding="utf-8") for p in (h/".config/opencode/opencode.json",h/".config/kilo/kilo.jsonc") if p.exists()]'
```

Check all five files. It prints the name of each file that still names `~/.config/agents`, so it prints nothing when the gate and the plugin are out. `~/.claude/settings.json` is on the list for a `hooks` block an older install left there. Unix shell:

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

1. The blocking half of the preflight gate is project-shaped. The hook wiring Codex and Copilot ship calls
   `.agents/hooks/preflight-gate/preflight_gate.py`, resolved against the session's working directory. At user level you have to
   rewrite that to an absolute path, which the Codex and Copilot sections above tell you to do, and the
   same is true of `task_list_sync.py` and `no_ai_markers_check.py`. The gate script recognises its own place in
   `~/.config/agents/hooks` and then looks for subagent definitions in the trees this install writes,
   `~/.config/agents/agents`, `~/.config/codex/agents` and `~/.config/copilot/agents`. The text-injection half,
   the `echo` that reminds the model to name its skills, has no file dependency and works globally as it ships. On Claude Code the gate is the `hook-preflight-gate` plugin, which needs no path rewriting: it runs from its own folder in the plugin cache, and finds a plugin subagent's definition in that cache and a subagent of your own in `~/.claude/agents`.

2. The OpenCode and Kilo Code plugin needs no path rewriting. It uses the project's own `.agents/hooks/` when the
   project has one and your home directory's `.config/agents/hooks/` otherwise, so the global entry gates a project that
   never ran the per-project import. The one project that stays ungated is one holding the opt-out file described in
   [How the OpenCode and Kilo Code plugin finds its hooks](#how-the-opencode-and-kilo-code-plugin-finds-its-hooks). On OpenCode 2.x the reply checks only ever block the next tool call, as its section says.

3. Copilot hooks reach the CLI, the cloud agent and the Local agent in VS Code. The cloud agent reads hooks only from
   `.github/hooks/*.json` in the cloned repository, so nothing in your home directory reaches it. Whether the
   JetBrains plugin reads the user hooks directory was not verified, and neither was whether VS Code follows `COPILOT_HOME`. Copilot code review has no hook surface.

4. Claude Code Cowork sessions and cloud sessions get none of the plugins you install with the user scope: "Plugins you install on your computer at user or local scope aren't available in cloud sessions" ([Install plugins](https://code.claude.com/docs/en/plugins/install), read 2026-11-24). Neither do they read `~/.claude/skills` on your machine. Cowork loads
   the skills enabled for your claude.ai account, and cloud sessions additionally load project skills from the cloned
   repository. Cowork also skips the import in `~/.claude/CLAUDE.md`, so only what is written into that file itself reaches it. The global install covers your local sessions and not those two.

5. Kilo Code documents no environment variable that relocates its whole configuration directory. `KILO_CONFIG` and
   `KILO_CONFIG_CONTENT` pass configuration rather than moving the directory. Claude Code has `CLAUDE_CONFIG_DIR`, which this layout leaves unset for the reasons at the top.

6. On Windows the skill link hook does nothing, so Codex needs a junction per skill made by hand. None of the Windows steps of this layout, the two migrations included, was run for this guide, and neither was any PowerShell form of a `claude plugin` command, which is the same line as in a Unix shell.

7. Codex reads the shared skills through `$CODEX_HOME/skills`, a location its own source calls deprecated. When it goes, this guide changes with it.

8. Project settings win. A project that ran the per-project import brings its own `.claude/settings.json`,
   `opencode.json`, `.codex/config.toml`, and skills, and those take precedence over the global ones. Hooks are the
   exception: Codex runs the global and the project hooks side by side, and so does Claude Code in a project whose own `.claude/settings.json` still wires a hook that a plugin with the user scope also carries. A plugin switched on at both scopes is still one plugin. The formatting check handles
   that itself. The copy under `~/.config/agents/hooks/` stays silent in a project whose `.claude/settings.json`,
   `.claude/settings.local.json`, `.codex/config.toml`, `.codex/hooks.json` or `.github/hooks/*.json` already runs
   `no_ai_markers_check.py` on the same event, so one reply is never blocked twice and one batch never fixed twice.
   When it cannot read those files it checks anyway.

---

### Where these paths come from

Every path in this document was taken from the current published documentation, fetched on 2026-09-25 and for the `~/.config/agents` layout on 2026-10-13, or measured
where the documentation says nothing. The first measurements ran on Windows 11 against Claude Code 2.1.281, Codex 0.156.1,
OpenCode 1.18.32 and Kilo Code 7.7.9, each in a throwaway home. The layout measurements ran on Linux against Claude Code 2.1.296, Codex 0.162.1, OpenCode 1.19.0 and 2.0.26, and Kilo Code 7.8.9, each in a throwaway home. The container sandbox in this repository then ran the whole install against Claude Code 2.1.250, Codex 0.150.1, OpenCode 1.18.25, Kilo Code 7.5.5 and GitHub Copilot CLI 1.0.81, where Copilot listed every shared skill through `COPILOT_SKILLS_DIRS` with `COPILOT_HOME` set. The Claude Code plugin route was taken from the plugin pages fetched on 2026-11-24 and run on Linux with Claude Code 2.1.325 in a throwaway home: the marketplace add, the installs with the user scope, the update loop, the marketplace removal, the output style and the move of an older install.

| Agent | Pages used |
| --- | --- |
| Claude Code | [settings](https://code.claude.com/docs/en/settings), [skills](https://code.claude.com/docs/en/skills), [sub-agents](https://code.claude.com/docs/en/sub-agents), [memory](https://code.claude.com/docs/en/memory), [hooks](https://code.claude.com/docs/en/hooks), [MCP](https://code.claude.com/docs/en/mcp), [install plugins](https://code.claude.com/docs/en/plugins/install), [plugin loading](https://code.claude.com/docs/en/plugins/loading), [output styles](https://code.claude.com/docs/en/output-styles) |
| Codex | [build skills](https://learn.chatgpt.com/codex/build-skills), [subagents](https://learn.chatgpt.com/codex/agent-configuration/subagents), [hooks](https://learn.chatgpt.com/codex/hooks), [config basics](https://learn.chatgpt.com/codex/config-file/config-basic), [AGENTS.md](https://learn.chatgpt.com/codex/agent-configuration/agents-md), [MCP](https://learn.chatgpt.com/codex/extend/mcp) |
| OpenCode | [config](https://opencode.ai/docs/config/), [skills](https://opencode.ai/docs/skills/), [agents](https://opencode.ai/docs/agents/), [plugins](https://opencode.ai/docs/plugins/), [rules](https://opencode.ai/docs/rules/), [2.x plugins](https://opencode.ai/v2/docs/plugins/) |
| Kilo Code | [skills](https://kilo.ai/docs/customize/skills), [custom subagents](https://kilo.ai/docs/customize/custom-subagents), [plugins](https://kilo.ai/docs/automate/extending/plugins), [CLI](https://kilo.ai/docs/code-with-ai/platforms/cli), [custom rules](https://kilo.ai/docs/customize/custom-rules) |
| GitHub Copilot | [CLI config dir](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference), [CLI command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference), [agent skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills), [custom agents](https://docs.github.com/en/copilot/reference/custom-agents-configuration), [hooks](https://docs.github.com/en/copilot/reference/hooks-reference), [CLI custom instructions](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions), [VS Code hooks](https://code.visualstudio.com/docs/copilot/customization/hooks), [VS Code custom agents](https://code.visualstudio.com/docs/copilot/customization/custom-agents) |
| Linux and the layout | [environment.d](https://www.freedesktop.org/software/systemd/man/latest/environment.d.html), and the Claude Code issues named at the top |
