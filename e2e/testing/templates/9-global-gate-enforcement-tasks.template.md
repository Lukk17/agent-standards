# Global gate enforcement: run tasks template

Spec: [9-global-gate-enforcement-test.md](../9-global-gate-enforcement-test.md)

Copy this file to `../runs/<UTC-timestamp>_9-global-gate-enforcement-tasks.md` before starting a run. Tick boxes as
you go. Add anything you did beyond the spec under Additional tasks I did.

---

### Tasks

#### Prerequisites

- [ ] `docker compose version` exits 0 on the host
- [ ] `docker image inspect agent-standards-sandbox:local` exits 0
- [ ] `git rev-parse --short HEAD` exits 0, hash recorded below

#### Reset state

- [ ] Container shell started, version table copied into Additional tasks I did
- [ ] Full global install from spec 6 performed, every command in order
- [ ] Any probe left by an earlier run removed
- [ ] `pwd` reports `/work/bare`

#### Run

- [ ] 1. Main-thread source edit judged in `claude` format with the home-directory gate copy
- [ ] 2. Same payload judged in `codex` format
- [ ] 3. Same payload judged in `plain` format, exit status read immediately
- [ ] 4. Baseline: probe payload judged before the probe definition exists
- [ ] 5. Probe definition copied into the global subagent directory
- [ ] 6. Probe payload judged again
- [ ] 7. Specialist payload judged
- [ ] 8. Probe deleted

#### Expected

- [ ] `/work/bare` holds none of the per-project files
- [ ] There is no project-relative gate script in the working directory
- [ ] The home-directory gate copy denied the main-thread source edit
- [ ] The refusal is rule A
- [ ] The `codex` adapter denied the same payload
- [ ] The `plain` adapter exited 2
- [ ] The baseline judgement allowed, output empty
- [ ] With the definition in the home directory, the payload was denied
- [ ] The refusal is rule B and names the probe
- [ ] The specialist payload was allowed, output empty
- [ ] The probe is gone again

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
