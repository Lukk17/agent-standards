# Project MCP visibility: run tasks template

Spec: [4-project-mcp-visibility-test.md](../4-project-mcp-visibility-test.md)

Copy this file to `../runs/<UTC-timestamp>_4-project-mcp-visibility-tasks.md` before starting a run. Tick boxes as you
go. Add anything you did beyond the spec under Additional tasks I did.

---

### Tasks

#### Prerequisites

- [ ] `docker compose version` exits 0 on the host
- [ ] `docker image inspect agent-standards-sandbox:local` exits 0
- [ ] `git rev-parse --short HEAD` exits 0, hash recorded below

#### Reset state

- [ ] Container shell started, version table copied into Additional tasks I did
- [ ] `setup-project.sh` ran to completion
- [ ] `$HOME/.codex` created
- [ ] Trust record written into `$HOME/.codex/config.toml`
- [ ] Moved into `/work/project`

#### Run

- [ ] 1. `claude mcp list` captured, exit status read immediately
- [ ] 2. `codex mcp list` captured, exit status read immediately
- [ ] 3. `opencode mcp list` captured, exit status read immediately
- [ ] 4. `kilocode mcp list` captured, exit status read immediately
- [ ] 5. `copilot mcp list` captured, exit status read immediately

#### Expected

- [ ] `.mcp.json` declares at least one server
- [ ] `.codex/config.toml` declares at least one server
- [ ] `opencode.json` declares at least one server
- [ ] `.vscode/mcp.json` declares at least one server under its own `servers` key
- [ ] Claude Code exited 0
- [ ] Claude Code named every server the templates ship
- [ ] Codex exited 0
- [ ] Codex named every server
- [ ] OpenCode exited 0
- [ ] OpenCode named every server
- [ ] Kilo Code exited 0
- [ ] Kilo Code named every server
- [ ] Copilot exited 0
- [ ] Copilot named every server

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
