# Paths and Environment

PATH duplicates, entries that do not exist, shadowed binaries, which startup file sets what, and whether each variable and each zsh file lives where it belongs. The rules live in [SKILL.md](../SKILL.md). Linux commands below were executed read-only on CachyOS with zsh and bash, and the placement checks with zsh 5.9.2, systemd 262 and Plasma, macOS and Windows commands are UNVERIFIED. List variable names and paths only, never the value of a variable that might hold a secret.

---

### Measure the shell the owner uses

A non-interactive agent shell does not read the same startup files as the owner's terminal, so its PATH is not the owner's PATH. On the test machine the agent's own PATH had no duplicates, while `zsh -ic` had ten. Always measure through the owner's login shell from `MACHINE.md`, interactive and login separately, because they read different files.

| Shell | Interactive | Login |
|---|---|---|
| zsh | `zsh -ic 'print -l $path'` | `zsh -lc 'print -l $path'` |
| bash | `bash -ic 'echo "$PATH"' \| tr ':' '\n'` | `bash -lc 'echo "$PATH"' \| tr ':' '\n'` |
| PowerShell 7 | `$env:Path -split ';'` | the same, the process inherits machine plus user |

The zsh and bash forms were executed. On the test machine the interactive zsh PATH had 34 entries and the login one 24, which is expected when the PATH work lives in `.zshrc`.

---

### Duplicates and missing entries

| OS | Command | Wrong looks like | Status |
|---|---|---|---|
| Linux, macOS, zsh | `zsh -ic 'print -l $path' \| sort \| uniq -cd` | Any line, `warn`. Usually a file sourced twice | verified, ten duplicates |
| Linux, macOS, bash | `bash -ic 'echo "$PATH"' \| tr ':' '\n' \| sort \| uniq -cd` | Any line | verified, eight duplicates |
| Linux, macOS, zsh | `zsh -ic 'for d in $path; do [[ -d $d ]] \|\| print "not a directory: $d"; done'` | Any line. A directory that is gone, or an entry that names a file, which PATH ignores | verified, four, two of them files such as `/usr/bin/brave-browser-stable` |
| Windows | `$env:Path -split ';' \| Where-Object { $_ } \| Group-Object \| Where-Object Count -gt 1 \| Select-Object Count, Name` | Any line | UNVERIFIED |
| Windows | `$env:Path -split ';' \| Where-Object { $_ -and -not (Test-Path -LiteralPath $_ -PathType Container) }` | Any line | UNVERIFIED |
| Windows | `[Environment]::GetEnvironmentVariable('Path', 'Machine') -split ';'` and the same with `'User'` | The same directory in both scopes, or a user entry that belongs in the machine scope | UNVERIFIED |

---

### Shadowed binaries

The first match on PATH wins, so a version manager's shim or a second install can stand in front of the system binary without anyone deciding it.

| OS | Command | Wrong looks like | Status |
|---|---|---|---|
| Linux, macOS | `zsh -ic 'for b in python python3 pip java node npm git ssh gpg docker; do whence -a $b; done'` | A tool resolving somewhere the owner did not choose. On the test machine `python3` resolved to `~/.pyenv/shims/python3` ahead of `/usr/bin/python3`, and `java` to SDKMAN ahead of `/usr/bin/java`. That is `ok` when `MACHINE.md` records it as the owner's choice and `warn` when it does not | verified |
| Linux, bash | `bash -ic 'type -a python3'` | Same | verified |
| macOS | the zsh form above | Homebrew's `/opt/homebrew/bin` behind `/usr/bin` for a tool the owner installed through Homebrew, or the reverse | UNVERIFIED |
| Windows | `Get-Command python, python3, pip, java, node, git, ssh -All -ErrorAction SilentlyContinue \| Select-Object Name, Source` | `python.exe` resolving to the App Execution Alias under `WindowsApps` ahead of a real install, a stub that opens the Store instead of running Python | UNVERIFIED |

---

### Which file sets what

| OS | Command | What it shows | Status |
|---|---|---|---|
| zsh | `zsh -x -ic exit 2>&1 \| grep -E 'PATH='` | Every PATH assignment, prefixed with the file and line, for example `+/home/lukk/apps_config/env.sh:41> export PATH=...` | verified |
| bash | `PS4='+${BASH_SOURCE}:${LINENO}: ' bash -x -ic exit 2>&1 \| grep -E 'PATH='` | Same, with the file and line from `PS4` | verified |
| Linux, systemd user session | `systemctl --user show-environment \| grep -c '^PATH='` | Whether the graphical session carries a PATH of its own, set through `environment.d`. Print the count or the names, not the value, in the report | verified |
| Linux | `ls /etc/profile.d/ ~/.config/environment.d/ 2>/dev/null` | Files every login shell or the session reads | verified |
| macOS | `cat /etc/paths; ls /etc/paths.d` | What `path_helper` prepends in a login shell | UNVERIFIED |
| Windows | the two `GetEnvironmentVariable` scopes above | Machine and user PATH, set through System Properties or the registry | UNVERIFIED |

A trace with `-x` runs the startup files, which is what an interactive shell does anyway, and changes nothing. Report the file and line for each duplicate, so the owner can remove the second source rather than the symptom. Never edit a startup file during the check.

---

### Where variables and zsh files belong

This is a Linux check with a systemd user session and zsh as the login shell. On bash, or with no systemd user session, report it as not applicable rather than as a finding. The target layout, with the source each part rests on:

| What | Where it belongs | Source |
|---|---|---|
| A variable or PATH entry that graphical applications and terminals both need, such as `JAVA_HOME`, `ANDROID_HOME` or a tool's `bin` | `~/.config/environment.d/*.conf`, two-digit prefix, `KEY=VALUE` lines | `environment.d(5)`, systemd 262: "contain lists of environment variable assignments passed to services started by the systemd user instance", and some session managers "query the systemd user instance for the exported environment and inject this configuration into programs they start" |
| Loading those files into every zsh, and removing duplicate PATH entries | `~/.zshenv`, which imports the `environment.d` files and runs `typeset -U path`, and nothing else besides `ZDOTDIR` | zsh manual, Startup/Shutdown Files: every zsh reads `$ZDOTDIR/.zshenv`, and the files read by every shell should be "kept as small as possible" |
| Interactive-only setup: `nvm.sh`, `pyenv init`, `sdkman-init.sh`, completions, the prompt | `$ZDOTDIR/.zshrc` | zsh manual: "if the shell is interactive, commands are read from /etc/zshrc and then $ZDOTDIR/.zshrc" |
| Anything at all, when zsh is the login shell | not `~/.profile` | zsh manual, Invocation, section Compatibility: `$HOME/.profile` is read only when zsh emulates sh or ksh, so a native zsh never reads it |
| `.zshrc`, `.zprofile`, `.zlogin`, `.zlogout`, history and the completion dump | `$ZDOTDIR`, set to `~/.config/zsh` | zsh manual: "If ZDOTDIR is unset, HOME is used instead" |
| The only zsh file in the home directory | `~/.zshenv`, whose one job there is to set `ZDOTDIR` before zsh looks for the rest | the same page: `.zshenv` is read before every other user file |

Sources: <https://zsh.sourceforge.io/Doc/Release/Files.html>, <https://zsh.sourceforge.io/Doc/Release/Invocation.html> and `man 5 environment.d` from systemd 262. Commands below print names and paths only, never a value.

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Login shell | `getent passwd "$USER" \| cut -d: -f7` | Not zsh, which makes the rest of this table not applicable | verified |
| `ZDOTDIR` | `zsh -c 'print -r -- ${ZDOTDIR:-unset}'` | `unset`, or anything other than `~/.config/zsh`, `warn` | verified, `unset` on the test machine |
| zsh files left in home | `ls -a ~ \| grep -E '^\.(zshrc\|zprofile\|zlogin\|zlogout\|zsh_history\|zcompdump.*)$'` | Any line. Only `.zshenv` belongs in home | verified, five on the test machine |
| `~/.profile` with zsh as login shell | `grep -cE '^\s*export ' ~/.profile` | Any count above zero, `warn`: no zsh reads the file, so those variables reach neither the terminal nor the session | verified, one export on the test machine |
| What `~/.zshenv` does | `grep -nE '^\s*(export\s+)?[A-Za-z_]+=\|typeset -U\|environment\.d' ~/.zshenv \| cut -d= -f1` | An assignment other than `ZDOTDIR`, a missing `typeset -U path`, or no import of the `environment.d` files | verified, the import present and `typeset -U path` missing on the test machine |
| The `environment.d` files | `ls ~/.config/environment.d/` | Empty while the terminal sets tool homes that graphical applications need | verified |
| Interactive-only setup in the wrong file | `grep -nE 'nvm\.sh\|pyenv init\|sdkman-init' ~/.zshenv ~/.profile ~/.zprofile ~/.config/environment.d/*.conf 2>/dev/null \| cut -d: -f1,2` | Any line, `warn`. These belong in `.zshrc` only | verified, none on the test machine |
| Names the shell sets that the graphical session lacks | `comm -13 <(tr '\0' '\n' < /proc/$(pgrep -x plasmashell)/environ \| cut -d= -f1 \| sort -u) <(env -i HOME="$HOME" USER="$USER" LOGNAME="$LOGNAME" TERM=dumb zsh -lic env 2>/dev/null \| cut -d= -f1 \| sort -u)` | A tool home such as `JAVA_HOME` or `ANDROID_HOME`, `warn`, because an IDE started from the menu will not see it. Shell-only names (`_`, `SHLVL`, `TERM`, prompt and plugin variables) and what interactive-only setup exports (`NVM_*`, `PYENV_SHELL`) are expected | verified, `JAVA_HOME`, `ANDROID_HOME`, `GRADLE_USER_HOME` and others on the test machine |
| PATH entries the graphical session lacks | `comm -13 <(tr '\0' '\n' < /proc/$(pgrep -x plasmashell)/environ \| sed -n 's/^PATH=//p' \| tr ':' '\n' \| sort -u) <(env -i HOME="$HOME" USER="$USER" LOGNAME="$LOGNAME" TERM=dumb zsh -lic 'print -l $path' 2>/dev/null \| sort -u)` | Any entry a graphical application needs, `warn`. Version manager shims are expected only in the terminal | verified, fourteen on the test machine |
| The systemd user environment against the session | `comm -13 <(tr '\0' '\n' < /proc/$(pgrep -x plasmashell)/environ \| cut -d= -f1 \| sort -u) <(systemctl --user show-environment \| cut -d= -f1 \| sort -u)` | Any line: the user manager exports a name the session never received, so a new login is needed or the session does not import it | verified, none on the test machine |

The comparisons start zsh from an empty environment with `env -i`, because a shell started from the agent inherits the agent's own variables and would hide every difference. Outside Plasma, use the process of the session's shell or panel in place of `plasmashell`, or compare against `systemctl --user show-environment` alone. Report each `warn` with the file that sets the variable, from the trace in "Which file sets what" above, and hand the move to the owner as the fix.
