# Global agent discovery: run tasks template

Spec: [7-global-agent-discovery-test.md](../7-global-agent-discovery-test.md)

Copy this file to `../runs/<UTC-timestamp>_7-global-agent-discovery-tasks.md` before starting a run. Tick boxes as you
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
- [ ] `pwd` reports `/work/bare`

#### Run

- [ ] 1. `opencode agent list` captured, exit status read immediately
- [ ] 2. `kilocode agent list` captured, exit status read immediately
- [ ] 3. `kilocode config check` captured, exit status read immediately
- [ ] 4. `copilot skill list` captured, exit status read immediately

#### Expected

- [ ] `/work/bare` still holds none of the per-project files
- [ ] OpenCode exited 0
- [ ] OpenCode named every canonical subagent
- [ ] Kilo Code exited 0
- [ ] Kilo Code named every canonical subagent
- [ ] Kilo Code's configuration check exited 0
- [ ] Kilo Code did not reject the global configuration file
- [ ] Copilot exited 0
- [ ] Copilot loaded every canonical skill from the home directory
- [ ] Copilot reported no parse or load failure

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
