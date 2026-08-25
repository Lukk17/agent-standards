# Project gate decisions: e2e test

Suite A, per-project setup. Setup cost class 1: a container and nothing else. No project import, no agent tool
invoked, no state written.

---

### What this verifies

- The shared preflight gate denies a main-thread edit of a source file, in all four output formats the agent
  adapters use: `claude`, `codex`, `copilot`, and `plain`.
- It denies a shell command that redirects into a source file, which is the obvious way around a blocked editor call.
- It allows a main-thread edit of a documentation file, so the rule is targeted rather than a blanket block.
- It fails open on a payload it cannot parse, so a broken gate never breaks a session.
- Out of scope, because the container is given no provider credentials: no agent runtime fires the hook here and no
  model is asked anything. This spec proves the gate script decides correctly for the payload each adapter would hand
  it. It does not prove the runtime delivers that payload in that shape, and it does not prove a model obeys the
  refusal.

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

Expect exit 0 and a version line.

Check the harness image was built by the sweep step in [../README.md](../README.md). PowerShell:

```powershell
docker image inspect agent-standards-harness:local
```

Unix shell:

```bash
docker image inspect agent-standards-harness:local
```

Expect exit 0. A non-zero exit means the image is missing, so build it before continuing.

Record the commit under test, because the container reads committed state only. PowerShell:

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

None. This test writes no persisted state. The container is discarded on exit and the repository is mounted
read-only, so there is nothing to wipe.

---

### Run

1. Start the container shell from the repository root. Everything after this step is typed into that shell.
   PowerShell:

```powershell
docker compose -f test-harness\docker-compose.yml run --rm harness /bin/bash
```

Unix shell:

```bash
docker compose -f test-harness/docker-compose.yml run --rm harness /bin/bash
```

Wait for the version table the entrypoint prints, then copy it into the run record.

2. Move to the mounted repository, which fixes the gate's first search root and makes the run deterministic.

```bash
cd /repo
```

3. Ask the gate to judge a main-thread source edit in Claude Code's format.

```bash
python3 /repo/.agents/hooks/preflight_gate.py --format claude < /repo/e2e/fixtures/gate-payloads/main-thread-source-edit.json > /tmp/gate-claude-source.json
```

4. The same payload in Codex format.

```bash
python3 /repo/.agents/hooks/preflight_gate.py --format codex < /repo/e2e/fixtures/gate-payloads/main-thread-source-edit.json > /tmp/gate-codex-source.json
```

5. The same payload in GitHub Copilot format.

```bash
python3 /repo/.agents/hooks/preflight_gate.py --format copilot < /repo/e2e/fixtures/gate-payloads/main-thread-source-edit.json > /tmp/gate-copilot-source.json
```

6. The same payload in the plain format the OpenCode and Kilo Code plugin shim reads. This one signals through its
   exit status, so read the status immediately after the step.

```bash
python3 /repo/.agents/hooks/preflight_gate.py --format plain < /repo/e2e/fixtures/gate-payloads/main-thread-source-edit.json
```

7. A shell command that redirects into a source file.

```bash
python3 /repo/.agents/hooks/preflight_gate.py --format claude < /repo/e2e/fixtures/gate-payloads/main-thread-shell-redirect.json > /tmp/gate-claude-redirect.json
```

8. A main-thread edit of a documentation file, which the gate is meant to allow.

```bash
python3 /repo/.agents/hooks/preflight_gate.py --format claude < /repo/e2e/fixtures/gate-payloads/main-thread-markdown-edit.json > /tmp/gate-claude-markdown.json
```

9. A payload that is not JSON at all.

```bash
python3 /repo/.agents/hooks/preflight_gate.py --format claude < /repo/e2e/fixtures/gate-payloads/malformed.txt > /tmp/gate-claude-malformed.json
```

---

### Expected

Claude Code's adapter denies the source edit. The decision field says `deny`.

```bash
jq -e '.hookSpecificOutput.permissionDecision == "deny"' /tmp/gate-claude-source.json
```

Expect exit 0.

The refusal is rule A rather than rule B, which the reason field distinguishes.

```bash
jq -e '.hookSpecificOutput.permissionDecisionReason | contains("may not edit source files")' /tmp/gate-claude-source.json
```

Expect exit 0.

Codex's adapter denies the same payload, in the same shape.

```bash
jq -e '.hookSpecificOutput.permissionDecision == "deny"' /tmp/gate-codex-source.json
```

Expect exit 0.

GitHub Copilot's adapter denies it too, in its own flatter shape.

```bash
jq -e '.permissionDecision == "deny"' /tmp/gate-copilot-source.json
```

Expect exit 0.

The plain adapter denies by exiting 2, which is the signal the OpenCode and Kilo Code plugin shim turns into a
blocked call. Read the status straight after run step 6.

```bash
echo $?
```

Expect `2`.

The shell redirect into a source file is denied as well.

```bash
jq -e '.hookSpecificOutput.permissionDecision == "deny"' /tmp/gate-claude-redirect.json
```

Expect exit 0.

The blocked target named in the refusal is the redirect target, not the shell binary.

```bash
jq -e '.hookSpecificOutput.permissionDecisionReason | contains("src/e2e_canary_app.py")' /tmp/gate-claude-redirect.json
```

Expect exit 0.

The documentation edit is allowed. An allow prints nothing at all, so the captured file is empty.

```bash
test ! -s /tmp/gate-claude-markdown.json
```

Expect exit 0.

The unparseable payload fails open, which is the same empty output.

```bash
test ! -s /tmp/gate-claude-malformed.json
```

Expect exit 0.

---

### Fixtures

- `e2e/fixtures/gate-payloads/main-thread-source-edit.json`: main-thread `Edit` of `src/e2e_canary_app.py`.
- `e2e/fixtures/gate-payloads/main-thread-shell-redirect.json`: `Bash` command redirecting into the same file.
- `e2e/fixtures/gate-payloads/main-thread-markdown-edit.json`: main-thread `Edit` of `docs/e2e-canary-note.md`.
- `e2e/fixtures/gate-payloads/malformed.txt`: a line of prose where JSON is expected.

---

### Concurrency

- Mutates: none. The gate only reads, `/repo` is mounted read-only, and the run's only writes go to `/tmp` inside a
  throwaway container that is deleted on exit.
- Conflicts with: any spec executed in the same container shell as this one, because the `/tmp` filenames would
  collide. Nothing at all when every spec gets its own `docker compose run --rm` container, which is what
  [../README.md](../README.md) tells the runner to do.
- Serial: false
