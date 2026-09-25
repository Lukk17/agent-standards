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
- [ ] 3. `markdown-writer` deleted from `~/.agents/skills`
- [ ] 4. `e2e-own-skill` added to `~/.agents/skills`
- [ ] 5. `~/.agents/hooks/preflight_gate.py` damaged
- [ ] 6. Digest of `~/.claude/settings.json` recorded
- [ ] 7. Update run with `--update`, exit status read
- [ ] 8. Skills left by the update recorded
- [ ] 9. `markdown-writer` copied back, `e2e-own-skill` removed
- [ ] 10. Moved into `/work/bare`

#### Expected

- [ ] The first install exited 0
- [ ] The second install exited 0
- [ ] The update exited 0
- [ ] No temporary clone and no `~/.agent-standards` left behind
- [ ] `~/.agents/.upstream-commit` holds the commit under test
- [ ] The update restored the damaged hook script
- [ ] The update did not bring back the deleted skill
- [ ] The update left the own skill alone
- [ ] The update did not touch `~/.claude/settings.json`
- [ ] `/work/bare` holds none of the per-project files
- [ ] The shared skills tree holds every canonical skill
- [ ] `~/.claude/skills` is a link to `~/.agents/skills`
- [ ] The same skill count is reachable through that link
- [ ] The gate script landed in the shared tree
- [ ] Claude Code subagent count matches canonical
- [ ] Codex TOML subagent count matches canonical
- [ ] `~/.config/opencode/agents` and `~/.config/kilo/agents` are links to `~/.agents/agents`
- [ ] OpenCode and Kilo Code subagent counts through those links match canonical
- [ ] Copilot subagent count matches canonical
- [ ] The second install nested no tree inside another
- [ ] `~/.claude/CLAUDE.md` is the template, and `~/.agents` holds no instruction file
- [ ] Codex and Copilot point at it with a link each
- [ ] OpenCode has no global rules file of its own
- [ ] Kilo Code points at it through its `instructions` key, by absolute path
- [ ] Kilo Code carries no `skills.paths` entry
- [ ] Claude Code's user settings equal the guide's block
- [ ] Codex's user hooks equal the guide's block
- [ ] Claude Code's user settings call the gate by absolute path, with the flag matched separately
- [ ] Claude Code's gate call runs the gate script directly, with no wrapper, and carries no `subprocess.DEVNULL`
- [ ] Claude Code's gate call forces a zero exit
- [ ] Claude Code injects the subagent supervision text at session start
- [ ] Claude Code tells a subagent to do its task itself on `SubagentStart`, never with the delegating reminder
- [ ] Claude Code fixes the reply on `MessageDisplay` and checks what is left on `Stop` with `--display-fixed`
- [ ] Codex's user hooks call the gate by absolute path
- [ ] Codex's gate call is scoped to the tools that can write
- [ ] Codex's gate call forces a zero exit with `|| exit 0` on the POSIX command
- [ ] Every Codex Windows command ends in the PowerShell `; exit 0`, and its script calls move to the project root first
- [ ] Codex injects the canonical wording on `UserPromptSubmit` and the subagent text on `SubagentStart`
- [ ] Every Codex command has a Windows sibling
- [ ] Copilot's user hooks call the gate by absolute path
- [ ] Copilot's user hooks call the prompt reminder by absolute path
- [ ] Copilot's user hooks check the reply formatting on `agentStop` by absolute path
- [ ] No project-relative gate call survived the rewrite
- [ ] OpenCode names the shared plugin by absolute path
- [ ] Kilo Code names the shared plugin by absolute `file://` URL
- [ ] Neither holds a copy of the plugin in its own plugin directory

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
