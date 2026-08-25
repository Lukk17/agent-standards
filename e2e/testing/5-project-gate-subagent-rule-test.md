# Project gate subagent rule: e2e test

Suite A, per-project setup. Setup cost class 4: the full project import, plus a probe subagent definition written
into the imported project and deleted again inside the same run.

---

### What this verifies

- The gate copy the import delivered, `.agents/hooks/preflight_gate.py` inside the project, is the one exercised
  here. [1-project-gate-decisions-test.md](1-project-gate-decisions-test.md) drives the upstream copy in isolation.
  This spec drives the copy the hook wirings asserted in
  [2-project-import-shape-test.md](2-project-import-shape-test.md) actually point at.
- That copy denies a main-thread edit of a source file from inside the imported project.
- Rule B reaches the imported subagent tree: a subagent whose definition declares no skills is refused, and the
  refusal names that subagent rather than falling through to the main-thread rule.
- Rule B is driven by the definition on disk and nothing else. The same payload is allowed before the probe
  definition exists and denied after it is written, which is what makes the deny attributable.
- A subagent that does declare skills is allowed, so the rule is targeted rather than a blanket block on delegation.
- Out of scope, because the container is given no provider credentials: no agent runtime fires the hook and no model
  is asked anything. This spec proves the gate refuses the payload. It does not prove an agent runtime sends that
  payload, and it does not prove a model respects the refusal it gets back.

---

### Prerequisites

Check that Docker answers on the host. PowerShell:

```powershell
docker compose version
```

Unix shell:

```bash
docker compose version
```

Expect exit 0.

Check the harness image exists. PowerShell:

```powershell
docker image inspect agent-standards-harness:local
```

Unix shell:

```bash
docker image inspect agent-standards-harness:local
```

Expect exit 0.

Record the commit under test. PowerShell:

```powershell
git rev-parse --short HEAD
```

Unix shell:

```bash
git rev-parse --short HEAD
```

Expect exit 0. Copy the short hash into the run record.

---

### Reset state

Start the container shell from the repository root. Everything after this block is typed into that shell.
PowerShell:

```powershell
docker compose -f test-harness\docker-compose.yml run --rm harness /bin/bash
```

Unix shell:

```bash
docker compose -f test-harness/docker-compose.yml run --rm harness /bin/bash
```

Build the clean project and run the documented import into it.

```bash
/harness/setup-project.sh
```

Move into the imported project, which fixes the gate's first search root at the project.

```bash
cd /work/project
```

Remove any probe left behind by an interrupted earlier run, so the baseline step below means something.

```bash
rm -f /work/project/.claude/agents/e2e-no-skills-probe.md
```

---

### Run

1. Judge a main-thread source edit with the project's own gate copy.

```bash
python3 .agents/hooks/preflight_gate.py --format claude < /repo/e2e/fixtures/gate-payloads/main-thread-source-edit.json > /tmp/project-gate-source.json
```

2. Establish the baseline: judge the probe subagent's payload before the probe definition exists.

```bash
python3 .agents/hooks/preflight_gate.py --format claude < /repo/e2e/fixtures/gate-payloads/subagent-without-skills.json > /tmp/project-gate-probe-before.json
```

3. Write the probe definition into the subagent directory the gate reads.

```bash
cp /repo/e2e/fixtures/e2e-no-skills-probe.md /work/project/.claude/agents/e2e-no-skills-probe.md
```

4. Judge the same payload again, now that the definition is on disk.

```bash
python3 .agents/hooks/preflight_gate.py --format claude < /repo/e2e/fixtures/gate-payloads/subagent-without-skills.json > /tmp/project-gate-probe-after.json
```

5. Judge it through the Copilot adapter, which learns it is looking at a subagent from the `--subagent` flag rather
   than from an `agent_id` field.

```bash
python3 .agents/hooks/preflight_gate.py --format copilot --subagent < /repo/e2e/fixtures/gate-payloads/subagent-without-skills.json > /tmp/project-gate-probe-copilot.json
```

6. Judge it through the plain adapter, the one the OpenCode and Kilo Code plugin shim reads. This one signals through
   its exit status, so read the status immediately after the step.

```bash
python3 .agents/hooks/preflight_gate.py --format plain --subagent < /repo/e2e/fixtures/gate-payloads/subagent-without-skills.json
```

7. Judge a subagent that does declare skills, `code-reviewer`, which the import delivered.

```bash
python3 .agents/hooks/preflight_gate.py --format claude < /repo/e2e/fixtures/gate-payloads/subagent-with-skills.json > /tmp/project-gate-specialist.json
```

8. Delete the probe. The container is discarded on exit anyway, but a fixture written into an agent directory is
   always removed by the spec that wrote it.

```bash
rm -f /work/project/.claude/agents/e2e-no-skills-probe.md
```

---

### Expected

The project's own gate copy denies the main-thread source edit.

```bash
jq -e '.hookSpecificOutput.permissionDecision == "deny"' /tmp/project-gate-source.json
```

Expect exit 0.

Before the probe definition existed, the same subagent payload was allowed. An allow prints nothing, so the captured
file is empty. This is the baseline that makes the next assertion attributable to the fixture.

```bash
test ! -s /tmp/project-gate-probe-before.json
```

Expect exit 0.

The probe definition is where the gate looks for it.

```bash
test -f /work/project/.claude/agents/e2e-no-skills-probe.md
```

Expect exit 0.

With the definition on disk, the same payload is denied.

```bash
jq -e '.hookSpecificOutput.permissionDecision == "deny"' /tmp/project-gate-probe-after.json
```

Expect exit 0.

The refusal is rule B and names the probe, which is what separates it from the main-thread rule.

```bash
jq -e '.hookSpecificOutput.permissionDecisionReason | contains("e2e-no-skills-probe")' /tmp/project-gate-probe-after.json
```

Expect exit 0.

The Copilot adapter refuses it too, in its own flatter shape, and for the same reason.

```bash
jq -e '.permissionDecision == "deny" and (.permissionDecisionReason | contains("declares no skills"))' /tmp/project-gate-probe-copilot.json
```

Expect exit 0.

The plain adapter refuses by exiting 2, which is the signal the OpenCode and Kilo Code plugin shim turns into a
blocked call.

```bash
echo $?
```

Expect `2`, read straight after run step 6.

A subagent that declares skills is allowed, so delegation to a specialist is never blocked.

```bash
test ! -s /tmp/project-gate-specialist.json
```

Expect exit 0.

The probe is gone again.

```bash
test ! -e /work/project/.claude/agents/e2e-no-skills-probe.md
```

Expect exit 0.

---

### Fixtures

- `e2e/fixtures/e2e-no-skills-probe.md`: subagent definition carrying the canary marker `E2E-GATE-CANARY-9134` and
  declaring no skills, in front matter or body.
- `e2e/fixtures/gate-payloads/main-thread-source-edit.json`: main-thread `Edit` of `src/e2e_canary_app.py`.
- `e2e/fixtures/gate-payloads/subagent-without-skills.json`: subagent payload naming `e2e-no-skills-probe`.
- `e2e/fixtures/gate-payloads/subagent-with-skills.json`: subagent payload naming `code-reviewer`, which declares a
  long list of skills in its front matter.

---

### Concurrency

- Mutates: `/work/project` inside the container, including `/work/project/.claude/agents/e2e-no-skills-probe.md`,
  which this spec creates and deletes. Nothing outside the container: `/repo` is mounted read-only and the container
  is discarded on exit.
- Conflicts with: any spec executed in the same container shell as this one, and in particular
  [9-global-gate-enforcement-test.md](9-global-gate-enforcement-test.md), which writes a probe of the same name into
  the global agent directory that the gate also searches. Nothing at all when every spec gets its own
  `docker compose run --rm` container.
- Serial: false
