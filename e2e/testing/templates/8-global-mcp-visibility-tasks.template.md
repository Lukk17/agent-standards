# Global MCP visibility: run tasks template

Spec: [8-global-mcp-visibility-test.md](../8-global-mcp-visibility-test.md)

Copy this file to `../runs/<UTC-timestamp>_8-global-mcp-visibility-tasks.md` before starting a run. Tick boxes as you
go. Add anything you did beyond the spec under Additional tasks I did.

---

### Tasks

#### Prerequisites

- [ ] `docker compose version` exits 0 on the host
- [ ] `docker image inspect agent-standards-sandbox:local` exits 0
- [ ] `git rev-parse --short HEAD` exits 0, hash recorded below

#### Reset state

- [ ] Container shell started, version table copied into Additional tasks I did
- [ ] Full global install from spec 6 performed, every command in order
- [ ] Codex user-scope server tables and trust record placed
- [ ] Copilot user-scope server file placed
- [ ] Context7 added to Claude Code at user scope
- [ ] `pwd` reports `/work/bare`

#### Run

- [ ] 1. `claude mcp list` captured, exit status read immediately
- [ ] 2. `codex mcp list` captured, exit status read immediately
- [ ] 3. `opencode mcp list` captured, exit status read immediately
- [ ] 4. `kilocode mcp list` captured, exit status read immediately
- [ ] 5. `copilot mcp list` captured, exit status read immediately

#### Expected

- [ ] `/work/bare` still holds none of the per-project files
- [ ] Claude Code exited 0
- [ ] Claude Code named the server added at user scope
- [ ] Codex exited 0
- [ ] Codex named every server its user-scope file declares
- [ ] OpenCode exited 0
- [ ] OpenCode named every server its global configuration declares
- [ ] Kilo Code exited 0
- [ ] Kilo Code named every server its global configuration declares
- [ ] Copilot exited 0
- [ ] Copilot named every server its user-scope file declares
- [ ] No project-scope server name leaked into any listing

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
