# Global gate enforcement: e2e test

Suite B, global setup. Setup cost class 5: the whole global installation, plus a probe subagent definition written
into the global agent directory and deleted again inside the same run.

---

### What this verifies

- The gate copy in the home directory denies a main-thread edit of a source file when it is called from a directory
  that has none of the per-project files in it. This is the assertion the whole global suite exists for: the same
  refusal from a bare working directory can only have come from the home layer.
- Rule B reaches the global subagent trees. The gate searches its own grandparent as well as the working directory,
  so a copy at `~/.agents/hooks/preflight_gate.py` finds `~/.claude/agents` and `~/.agents/agents`. This spec proves
  that, with the probe definition and the baseline that makes the deny attributable to it.
- A subagent that does declare skills is allowed, from the same bare directory, so the rule stays targeted.
- The project-relative path the shipped wirings use resolves to nothing here, which is the concrete reason the global
  wirings had to be rewritten to an absolute path in
  [6-global-install-shape-test.md](6-global-install-shape-test.md).
- Out of scope, because the container is given no provider credentials: no agent runtime fires the hook and no model
  is asked anything. This spec proves the global gate copy refuses the payload each adapter would hand it.
- Also out of scope, and a real limitation rather than a gap in the test: the OpenCode and Kilo Code plugin resolves
  the gate script against the project directory it was started in and allows the call when the file is missing, by
  design, so that a broken gate never breaks a session. In a bare directory that file is missing, so the global copy
  of the plugin is inert. This spec asserts that the file really is missing from the working directory, which is the
  honest statement of the limitation, and it drives the plain adapter directly instead.

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

Check the sandbox image exists. PowerShell:

```powershell
docker image inspect agent-standards-sandbox:local
```

Unix shell:

```bash
docker image inspect agent-standards-sandbox:local
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

Move into the sandbox directory, which is where Compose finds its `compose.yaml`. The same line works in
PowerShell and in a Unix shell.

```bash
cd sandbox-agent
```

Start the container shell. Everything after this block is typed into that shell. PowerShell:

```powershell
docker compose run --rm sandbox /bin/bash
```

Unix shell:

```bash
docker compose run --rm sandbox /bin/bash
```

Then perform the whole global installation by running every command in the Reset state and Run sections of
[6-global-install-shape-test.md](6-global-install-shape-test.md), in order, ending in `/work/bare`. That command list
is not repeated here, so there is one copy of it to keep correct. Do not continue until it has finished.

Remove any probe left behind by an interrupted earlier run, so the baseline step below means something.

```bash
rm -f "$HOME/.claude/agents/e2e-no-skills-probe.md"
```

Confirm where you are, because every assertion in this spec depends on it.

```bash
pwd
```

Expect `/work/bare`.

---

### Run

1. Judge a main-thread source edit with the gate copy in the home directory, called from the bare working directory.

```bash
python3 "$HOME/.agents/hooks/preflight_gate.py" --format claude < /repo/e2e/fixtures/gate-payloads/main-thread-source-edit.json > /tmp/global-gate-source.json
```

2. The same payload through the Codex adapter.

```bash
python3 "$HOME/.agents/hooks/preflight_gate.py" --format codex < /repo/e2e/fixtures/gate-payloads/main-thread-source-edit.json > /tmp/global-gate-source-codex.json
```

3. The same payload through the plain adapter, which signals through its exit status, so read the status immediately
   after the step.

```bash
python3 "$HOME/.agents/hooks/preflight_gate.py" --format plain < /repo/e2e/fixtures/gate-payloads/main-thread-source-edit.json
```

4. Establish the baseline: judge the probe subagent's payload before the probe definition exists anywhere.

```bash
python3 "$HOME/.agents/hooks/preflight_gate.py" --format claude < /repo/e2e/fixtures/gate-payloads/subagent-without-skills.json > /tmp/global-gate-probe-before.json
```

5. Write the probe definition into the global subagent directory.

```bash
cp /repo/e2e/fixtures/e2e-no-skills-probe.md "$HOME/.claude/agents/e2e-no-skills-probe.md"
```

6. Judge the same payload again, now that the definition is on disk in the home directory.

```bash
python3 "$HOME/.agents/hooks/preflight_gate.py" --format claude < /repo/e2e/fixtures/gate-payloads/subagent-without-skills.json > /tmp/global-gate-probe-after.json
```

7. Judge a subagent that does declare skills, `code-reviewer`, which the global install placed in the same directory.

```bash
python3 "$HOME/.agents/hooks/preflight_gate.py" --format claude < /repo/e2e/fixtures/gate-payloads/subagent-with-skills.json > /tmp/global-gate-specialist.json
```

8. Delete the probe. The container is discarded on exit anyway, but a fixture written into an agent directory is
   always removed by the spec that wrote it.

```bash
rm -f "$HOME/.claude/agents/e2e-no-skills-probe.md"
```

---

### Expected

The working directory holds none of the per-project files, so nothing the gate decided could have come from here.
Assert this first: every other assertion in this spec depends on it.

```bash
ls -A /work/bare | grep -E "^(\.agents|\.claude|\.codex|\.github|\.kilo|\.opencode|\.vscode|\.mcp\.json|opencode\.json|AGENTS\.md)$"
```

Expect exit 1, meaning `grep` matched nothing. Exit 0 here is a failure of the test.

There is no project-relative gate script to fall back on, which is the concrete reason the global wirings name the
gate by absolute path.

```bash
test ! -e /work/bare/.agents/hooks/preflight_gate.py
```

Expect exit 0.

The gate copy in the home directory denies the main-thread source edit.

```bash
jq -e '.hookSpecificOutput.permissionDecision == "deny"' /tmp/global-gate-source.json
```

Expect exit 0.

The refusal is rule A rather than rule B, which the reason field distinguishes.

```bash
jq -e '.hookSpecificOutput.permissionDecisionReason | contains("may not edit source files")' /tmp/global-gate-source.json
```

Expect exit 0.

The Codex adapter denies the same payload.

```bash
jq -e '.hookSpecificOutput.permissionDecision == "deny"' /tmp/global-gate-source-codex.json
```

Expect exit 0.

The plain adapter denies by exiting 2.

```bash
echo $?
```

Expect `2`, read straight after run step 3.

Before the probe definition existed, the subagent payload was allowed. An allow prints nothing, so the captured file
is empty. This is the baseline that makes the next assertion attributable to the fixture.

```bash
test ! -s /tmp/global-gate-probe-before.json
```

Expect exit 0.

With the definition in the home directory, the same payload is denied, which proves the gate found the global
subagent tree from a working directory that has none.

```bash
jq -e '.hookSpecificOutput.permissionDecision == "deny"' /tmp/global-gate-probe-after.json
```

Expect exit 0.

The refusal is rule B and names the probe.

```bash
jq -e '.hookSpecificOutput.permissionDecisionReason | contains("e2e-no-skills-probe")' /tmp/global-gate-probe-after.json
```

Expect exit 0.

A subagent that declares skills is allowed, read from the same global directory.

```bash
test ! -s /tmp/global-gate-specialist.json
```

Expect exit 0.

The probe is gone again.

```bash
test ! -e "$HOME/.claude/agents/e2e-no-skills-probe.md"
```

Expect exit 0.

---

### Fixtures

- `e2e/fixtures/e2e-no-skills-probe.md`: subagent definition carrying the canary marker `E2E-GATE-CANARY-9134` and
  declaring no skills, in front matter or body.
- `e2e/fixtures/gate-payloads/main-thread-source-edit.json`: main-thread `Edit` of `src/e2e_canary_app.py`.
- `e2e/fixtures/gate-payloads/subagent-without-skills.json`: subagent payload naming `e2e-no-skills-probe`.
- `e2e/fixtures/gate-payloads/subagent-with-skills.json`: subagent payload naming `code-reviewer`.

---

### Concurrency

- Mutates: the container's home directory, through the install this spec inherits from
  [6-global-install-shape-test.md](6-global-install-shape-test.md), plus
  `$HOME/.claude/agents/e2e-no-skills-probe.md`, which this spec creates and deletes. Nothing outside the container:
  `/repo` is mounted read-only and the container is discarded on exit.
- Conflicts with: every other spec in either suite when they share a container shell, and in particular
  [5-project-gate-subagent-rule-test.md](5-project-gate-subagent-rule-test.md), which writes a probe of the same name
  into a project agent directory that a gate run could also search. Nothing at all when every spec gets its own
  `docker compose run --rm` container.
- Serial: false
