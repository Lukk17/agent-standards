# Project gate decisions: run tasks template

Spec: [1-project-gate-decisions-test.md](../1-project-gate-decisions-test.md)

Copy this file to `../runs/<UTC-timestamp>_1-project-gate-decisions-tasks.md` before starting a run. Tick boxes as you
go. Add anything you did beyond the spec under Additional tasks I did.

---

### Tasks

#### Prerequisites

- [ ] `docker compose version` exits 0 on the host
- [ ] `docker image inspect agent-standards-sandbox:local` exits 0
- [ ] `git rev-parse --short HEAD` exits 0, hash recorded below

#### Reset state

None. This test writes no persisted state.

#### Run

- [ ] 1. Container shell started, version table copied into Additional tasks I did
- [ ] 2. Moved to `/repo`
- [ ] 3. Main-thread source edit judged in `claude` format
- [ ] 4. Main-thread source edit judged in `codex` format
- [ ] 5. Main-thread source edit judged in `copilot` format
- [ ] 6. Main-thread source edit judged in `plain` format, exit status read immediately
- [ ] 7. Shell redirect into a source file judged
- [ ] 8. Documentation edit judged
- [ ] 9. Malformed payload judged

#### Expected

- [ ] `claude` format decided deny
- [ ] The `claude` refusal is rule A, naming the source-file rule
- [ ] `codex` format decided deny
- [ ] `copilot` format decided deny
- [ ] `plain` format exited 2
- [ ] The shell redirect was denied
- [ ] The refusal named the redirect target, not the shell binary
- [ ] The documentation edit was allowed, output empty
- [ ] The malformed payload failed open, output empty

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
