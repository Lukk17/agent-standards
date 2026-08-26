# Project import shape: run tasks template

Spec: [2-project-import-shape-test.md](../2-project-import-shape-test.md)

Copy this file to `../runs/<UTC-timestamp>_2-project-import-shape-tasks.md` before starting a run. Tick boxes as you
go. Add anything you did beyond the spec under Additional tasks I did.

---

### Tasks

#### Prerequisites

- [ ] `docker compose version` exits 0 on the host
- [ ] `docker image inspect agent-standards-sandbox:local` exits 0
- [ ] `git rev-parse --short HEAD` exits 0, hash recorded below

#### Reset state

None beyond the fresh container. `setup-project.sh` rebuilds `/work/project` itself.

#### Run

- [ ] 1. Container shell started, version table copied into Additional tasks I did
- [ ] 2. `setup-project.sh` ran to completion
- [ ] 3. Moved into `/work/project`

#### Expected

- [ ] Run step 2 exited 0
- [ ] `AGENTS.md` was activated
- [ ] `AGENTS.md.example` is gone, so the template was renamed rather than copied
- [ ] `subagents/` stayed upstream
- [ ] `tools/` stayed upstream
- [ ] The shared gate script landed
- [ ] The plugin shim landed
- [ ] Every canonical skill landed, counted against the mounted repository
- [ ] `.claude/skills` is a symlink that resolves to a directory
- [ ] The same skill count is reachable through that symlink
- [ ] `python-patterns` resolves through the symlink
- [ ] `.opencode/agents` is a symlink that resolves to a directory
- [ ] `.kilo/agents` is a symlink that resolves to a directory
- [ ] Claude Code subagent count matches canonical
- [ ] Codex TOML subagent count matches canonical
- [ ] Copilot `*.agent.md` subagent count matches canonical
- [ ] Claude Code calls the gate on `PreToolUse` in its own format
- [ ] Claude Code injects the gate text on every prompt
- [ ] Codex calls the gate on `PreToolUse` in its own format
- [ ] Codex injects the gate text on every prompt
- [ ] Copilot calls the gate on `preToolUse` in its own format
- [ ] Copilot injects the gate text on session start
- [ ] OpenCode declares the shared plugin by path
- [ ] OpenCode is pointed at `AGENTS.md`
- [ ] The plugin is declared in a file Kilo Code reads

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
