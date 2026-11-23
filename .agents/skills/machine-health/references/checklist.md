# Machine Health Checklist

Run it before sending the health report to the owner.

- [ ] `MACHINE.md` read, never-touch devices noted, owner rows left alone
- [ ] Every check run read-only, nothing installed, nothing repaired, nothing elevated
- [ ] Every root or elevated command written to Needs root with the row it fills
- [ ] Every vendor limit quoted with its URL and fetch date
- [ ] Every command not executed in this run marked UNVERIFIED
- [ ] On Linux with a systemd user session and zsh as the login shell: variables and PATH entries both graphical applications and terminals need live in `~/.config/environment.d/*.conf`, `~/.zshenv` only imports them, sets `ZDOTDIR` and deduplicates PATH, interactive-only setup sits in `.zshrc`, `~/.profile` holds nothing while zsh is the login shell, and the graphical session's environment matches the terminal's
- [ ] On Linux with a systemd user session and zsh as the login shell: zsh files live in `$ZDOTDIR`, `~/.config/zsh`, with `~/.zshenv` the only one left in the home directory
- [ ] Baseline written on the first run, drift against it on every later run
- [ ] Findings handed to the owner with evidence, fix and undo, none applied
- [ ] Change log entry added for the run
