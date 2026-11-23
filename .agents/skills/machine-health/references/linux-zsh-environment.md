# Linux: Where Variables and zsh Files Belong

Contents:

- [The target layout](#the-target-layout)
- [The checks](#the-checks)

Whether each variable and each zsh file lives where it belongs, and whether graphical applications see what the terminal sees. The rules live in [SKILL.md](../SKILL.md), and the PATH checks that come first are in [linux.md](linux.md). The commands were executed read-only on CachyOS with zsh 5.9.2, systemd 262 and Plasma.

---

### The target layout

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

---

### The checks

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

The comparisons start zsh from an empty environment with `env -i`, because a shell started from the agent inherits the agent's own variables and would hide every difference. Outside Plasma, use the process of the session's shell or panel in place of `plasmashell`, or compare against `systemctl --user show-environment` alone. Report each `warn` with the file that sets the variable, from the trace under "Which file sets what" in [linux.md](linux.md), and hand the move to the owner as the fix.
