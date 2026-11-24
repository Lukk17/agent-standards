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
- [ ] 3. `markdown-writer` deleted from `~/.config/agents/skills`
- [ ] 4. `e2e-own-skill` added to `~/.config/agents/skills`
- [ ] 5. `~/.config/agents/hooks/preflight-gate/preflight_gate.py` damaged
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
- [ ] `~/.config/agents/.upstream-commit` holds the commit under test
- [ ] The update restored the damaged hook script
- [ ] The update did not bring back the deleted skill
- [ ] The update left the own skill alone
- [ ] The update did not touch `~/.claude/settings.json`
- [ ] `/work/bare` holds none of the per-project files
- [ ] The shared skills tree holds every canonical skill
- [ ] Claude Code got no `~/.claude/skills` and no `~/.claude/agents`
- [ ] `~/.config/codex/skills` is a real directory, not a link
- [ ] The same skill count is reachable through its per-skill links
- [ ] The gate script landed in the shared tree with its rules file
- [ ] Codex TOML subagent count matches canonical
- [ ] `~/.config/opencode/agents` and `~/.config/kilo/agents` are links to `~/.config/agents/agents`
- [ ] OpenCode and Kilo Code subagent counts through those links match canonical
- [ ] Copilot subagent count matches canonical
- [ ] The second install nested no tree inside another
- [ ] `~/.config/agents/AGENTS.md` is the one instruction file, started from `global/AGENTS.md.example`
- [ ] `~/.claude/CLAUDE.md` is a real file holding only the import
- [ ] Codex, OpenCode and Kilo Code point at it with a link each, and Copilot has no link of its own
- [ ] Kilo Code names the shared skills in `skills.paths` and carries no `instructions` key
- [ ] Claude Code's user settings name the marketplace and wire no hook themselves
- [ ] They switch on exactly the plugins `core`, `review-and-security` and `hooks-all` install
- [ ] No plugin with the user scope carries an MCP server
- [ ] A skill, a subagent, the gate script and its rules file sit in the plugin cache
- [ ] Every hook of the switched-on hook plugins starts in the project, runs from its plugin folder and forces a zero exit
- [ ] The markdown lint and the standards advisory are among them
- [ ] Codex's user hooks equal the guide's block
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
