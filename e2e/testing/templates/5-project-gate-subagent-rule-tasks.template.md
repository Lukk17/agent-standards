# Project gate subagent rule: run tasks template

Spec: [5-project-gate-subagent-rule-test.md](../5-project-gate-subagent-rule-test.md)

Copy this file to `../runs/<UTC-timestamp>_5-project-gate-subagent-rule-tasks.md` before starting a run. Tick boxes as
you go. Add anything you did beyond the spec under Additional tasks I did.

---

### Tasks

#### Prerequisites

- [ ] `docker compose version` exits 0 on the host
- [ ] `docker image inspect agent-standards-sandbox:local` exits 0
- [ ] `git rev-parse --short HEAD` exits 0, hash recorded below

#### Reset state

- [ ] Container shell started, version table copied into Additional tasks I did
- [ ] `setup-project.sh` ran to completion
- [ ] Moved into `/work/project`
- [ ] Any probe left by an earlier run removed

#### Run

- [ ] 1. Main-thread source edit judged with the project's own gate copy
- [ ] 2. Baseline: probe payload judged before the probe definition exists
- [ ] 3. Probe definition copied into `.claude/agents/`
- [ ] 4. Probe payload judged again in `claude` format
- [ ] 5. Probe payload judged in `copilot` format with `--subagent`
- [ ] 6. Probe payload judged in `plain` format with `--subagent`, exit status read immediately
- [ ] 7. Specialist payload judged
- [ ] 8. Probe deleted

#### Expected

- [ ] The project's gate copy denied the main-thread source edit
- [ ] The baseline judgement allowed, output empty
- [ ] The probe definition is where the gate looks for it
- [ ] With the definition on disk, the payload was denied
- [ ] The refusal is rule B and names the probe
- [ ] The `copilot` adapter denied it for the same reason
- [ ] The `plain` adapter exited 2
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
