# Global install shape: run tasks template

Spec: [6-global-install-shape-test.md](../6-global-install-shape-test.md)

Copy this file to `../runs/<UTC-timestamp>_6-global-install-shape-tasks.md` before starting a run. Tick boxes as you
go. Add anything you did beyond the spec under Additional tasks I did.

---

### Tasks

#### Prerequisites

- [ ] `docker compose version` exits 0 on the host
- [ ] `docker image inspect agent-standards-harness:local` exits 0
- [ ] `git rev-parse --short HEAD` exits 0, hash recorded below

#### Reset state

- [ ] Container shell started, version table copied into Additional tasks I did
- [ ] Every global directory the install writes to cleared
- [ ] `/work/bare` cleared and recreated
- [ ] `/repo` added as a git safe directory

#### Run

- [ ] 1. Shared checkout cloned into the home directory
- [ ] 2. Sparse checkout directories selected
- [ ] 3. Push URL set to `no_push`
- [ ] 4. `$HOME/.agents` created
- [ ] 5. Canonical content copied into it
- [ ] 6. Machine-wide instruction file placed
- [ ] 7. `$HOME/.claude` created
- [ ] 8. Claude Code skills symlink created
- [ ] 9. Claude Code subagents copied
- [ ] 10. Claude Code instruction import placed
- [ ] 11. Claude Code user settings placed
- [ ] 12. `$HOME/.codex` created
- [ ] 13. Codex TOML subagents copied
- [ ] 14. Codex instruction symlink created
- [ ] 15. Codex user hooks placed
- [ ] 16. OpenCode configuration directories created
- [ ] 17. OpenCode subagents copied
- [ ] 18. OpenCode plugin installed
- [ ] 19. OpenCode instruction symlink created
- [ ] 20. OpenCode global configuration placed
- [ ] 21. Kilo Code configuration directories created
- [ ] 22. Kilo Code subagents copied
- [ ] 23. Kilo Code plugin installed
- [ ] 24. Kilo Code global configuration placed
- [ ] 25. Copilot configuration directories created
- [ ] 26. Copilot subagents copied
- [ ] 27. Copilot hooks file copied
- [ ] 28. Gate call in that copy rewritten to an absolute path
- [ ] 29. Copilot instruction symlink created
- [ ] 30. Moved into `/work/bare`

#### Expected

- [ ] `/work/bare` holds none of the per-project files
- [ ] The shared skills tree holds every canonical skill
- [ ] `~/.claude/skills` is a symlink that resolves to a directory
- [ ] The same skill count is reachable through that symlink
- [ ] The gate script landed in the shared tree
- [ ] Claude Code subagent count matches canonical
- [ ] Codex TOML subagent count matches canonical
- [ ] OpenCode subagent count matches canonical
- [ ] Kilo Code subagent count matches canonical
- [ ] Copilot subagent count matches canonical
- [ ] There is one shared instruction file
- [ ] Claude Code points at it with an import line
- [ ] Codex points at it with a resolving symlink
- [ ] OpenCode points at it with a resolving symlink
- [ ] Copilot points at it with a resolving symlink
- [ ] Kilo Code points at it through its `instructions` key
- [ ] Kilo Code is told where the shared skills tree is
- [ ] Claude Code's user settings call the gate by absolute path
- [ ] Codex's user hooks call the gate by absolute path
- [ ] Copilot's user hooks call the gate by absolute path
- [ ] No project-relative gate call survived the rewrite
- [ ] The plugin shim landed in both global plugin locations

#### Verdict

- [ ] Verdict: PASS / FAIL (delete the wrong one)

---

### Result summary

Commit under test:

Input tokens:

Output tokens:

Start (UTC):

End (UTC):

Duration:

---

### Additional tasks I did
