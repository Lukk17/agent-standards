# Global install shape: run tasks template

Spec: [6-global-install-shape-test.md](../6-global-install-shape-test.md)

Copy this file to `../runs/<UTC-timestamp>_6-global-install-shape-tasks.md` before starting a run. Tick boxes as you
go. Add anything you did beyond the spec under Additional tasks I did.

---

### Tasks

#### Prerequisites

- [ ] `docker compose version` exits 0 on the host
- [ ] `docker image inspect agent-standards-sandbox:local` exits 0
- [ ] `git rev-parse --short HEAD` exits 0, hash recorded below

#### Reset state

- [ ] Container shell started, version table copied into Additional tasks I did
- [ ] Every global directory the install writes to cleared, plus `~/.claude.json`
- [ ] `/work/bare` cleared and recreated
- [ ] `/repo` and `/repo/.git` added as git safe directories

#### Run

- [ ] 1. Installer run for all five agents, exit status read
- [ ] 2. Installer run a second time, unchanged, exit status read
- [ ] 3. Moved into `/work/bare`

#### Expected

- [ ] The first install exited 0
- [ ] The second install exited 0
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
- [ ] The second install nested no subagent tree inside another
- [ ] There is one shared instruction file
- [ ] Claude Code points at it with exactly one import line
- [ ] Codex points at it with a resolving symlink
- [ ] OpenCode points at it with a resolving symlink
- [ ] Copilot points at it with a resolving symlink
- [ ] Kilo Code points at it through its `instructions` key
- [ ] Kilo Code is told where the shared skills tree is
- [ ] Claude Code's user settings call the gate by absolute path, with the flag matched separately
- [ ] Claude Code's gate call runs the gate script directly, with no wrapper, and carries no `subprocess.DEVNULL`
- [ ] Claude Code's gate call forces a zero exit
- [ ] Codex's user hooks call the gate by absolute path
- [ ] Codex's gate call is scoped to the tools that can write
- [ ] Codex's gate call forces a zero exit on both the POSIX and the Windows command
- [ ] Codex injects the canonical wording on `UserPromptSubmit` and on `SubagentStart`
- [ ] Every Codex command has a Windows sibling
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
