# Global gate enforcement: e2e test

Suite B, global setup. Setup cost class 5: the whole global installation, plus a probe subagent definition written
into the global agent directory and deleted again inside the same run.

---

### What this verifies

- The gate copy in the home directory denies a main-thread edit of a source file when it is called from a directory
  that has none of the per-project files in it. This is the assertion the whole global suite exists for: the same
  refusal from a bare working directory can only have come from the home layer.
- There are two home copies. Claude Code runs the one its `hook-preflight-gate` plugin holds in the plugin cache, installed with the user scope, and every `claude` format step here drives that copy. Codex, Copilot, OpenCode and Kilo Code run the shared copy at `~/.config/agents/hooks/preflight-gate/preflight_gate.py`, which the `codex` and `plain` steps drive.
- Rule B reaches a subagent of the user's own. The plugin copy reads `~/.claude/agents`, the folder Claude Code keeps for subagents you wrote yourself, which the install leaves empty. This spec proves
  that, with the probe definition and the baseline that makes the deny attributable to it.
- Rule E reaches a subagent from a plugin with the user scope. The read-only `code-reviewer` of the `review-and-security` bundle is denied an edit and allowed a listed git command, from its definition in the plugin cache, so the rule stays targeted.
- A main-thread write to `~/.claude/settings.json`, the file that switches the plugins on, is denied on the `claude` format.
- The project-relative path the shipped wirings use resolves to nothing here, which is the concrete reason the global
  wirings of Codex and Copilot had to be rewritten to an absolute path in
  [6-global-install-shape-test.md](6-global-install-shape-test.md), and the reason the Claude Code hook plugins run their script from the plugin's own folder.
- Out of scope, because the container is given no provider credentials: no agent runtime fires the hook and no model
  is asked anything. This spec proves the global gate copy refuses the payload each adapter would hand it.
- Also out of scope: the OpenCode and Kilo Code plugin itself. In a bare directory it finds no project
  `.agents/hooks/` and falls back to the home copies this spec drives, unless the project holds the
  `.agents/no-global-hooks` opt-out. No agent is started here, so this spec asserts that no project-relative gate
  script exists in the working directory, which makes any deny attributable to the home copy, and it drives the plain
  adapter directly instead.

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
[6-global-install-shape-test.md](6-global-install-shape-test.md), in order, ending in `/work/bare`. That is two
installs and one update with [setup-global.sh](../../sandbox-agent/setup-global.sh), with the reset around them, and it is not
repeated here so there is one copy to keep correct. Do not continue until it has finished.

Remove any probe left behind by an interrupted earlier run, so the baseline step below means something.

```bash
rm -f "$HOME/.claude/agents/e2e-no-skills-probe.md"
```

Name the gate copy Claude Code runs, the one in its plugin cache. Every `claude` format step below uses it.

```bash
CLAUDE_GATE="$(ls "$HOME"/.claude/plugins/cache/agent-standards/hook-preflight-gate/*/preflight_gate.py)"
```

```bash
test -f "$CLAUDE_GATE"
```

Expect exit 0.

Confirm where you are, because every assertion in this spec depends on it.

```bash
pwd
```

Expect `/work/bare`.

---

### Run

1. Judge a main-thread source edit with the gate copy Claude Code runs, called from the bare working directory.

```bash
python3 "$CLAUDE_GATE" --format claude < /repo/e2e/fixtures/gate-payloads/main-thread-source-edit.json > /tmp/global-gate-source.json
```

2. The same payload through the Codex adapter, with the shared gate copy.

```bash
python3 "$HOME/.config/agents/hooks/preflight-gate/preflight_gate.py" --format codex < /repo/e2e/fixtures/gate-payloads/main-thread-source-edit.json > /tmp/global-gate-source-codex.json
```

3. The same payload through the plain adapter, which signals through its exit status, so read the status immediately
   after the step.

```bash
python3 "$HOME/.config/agents/hooks/preflight-gate/preflight_gate.py" --format plain < /repo/e2e/fixtures/gate-payloads/main-thread-source-edit.json
```

4. Establish the baseline: judge the probe subagent's payload before the probe definition exists anywhere.

```bash
python3 "$CLAUDE_GATE" --format claude < /repo/e2e/fixtures/gate-payloads/subagent-without-skills.json > /tmp/global-gate-probe-before.json
```

5. Write the probe definition into the folder for subagents of your own, which the install left absent.

```bash
mkdir -p "$HOME/.claude/agents" && cp /repo/e2e/fixtures/e2e-no-skills-probe.md "$HOME/.claude/agents/e2e-no-skills-probe.md"
```

6. Judge the same payload again, now that the definition is on disk in the home directory.

```bash
python3 "$CLAUDE_GATE" --format claude < /repo/e2e/fixtures/gate-payloads/subagent-without-skills.json > /tmp/global-gate-probe-after.json
```

7. Judge an edit by the read-only `code-reviewer`, which the install gave Claude Code as a plugin with the user scope.

```bash
printf '%s' '{"agent_id":"e2e-canary-1","agent_type":"agent-code-reviewer:code-reviewer","tool_name":"Edit","tool_input":{"file_path":"src/e2e_canary_app.py"}}' | python3 "$CLAUDE_GATE" --format claude > /tmp/global-gate-reviewer-edit.json
```

8. Judge a git command its definition lists.

```bash
printf '%s' '{"agent_id":"e2e-canary-1","agent_type":"agent-code-reviewer:code-reviewer","tool_name":"Bash","tool_input":{"command":"git --no-pager diff"}}' | python3 "$CLAUDE_GATE" --format claude > /tmp/global-gate-reviewer-diff.json
```

9. Judge a main-thread write to the user settings that switch the plugins on.

```bash
printf '{"tool_name":"Edit","tool_input":{"file_path":"%s"},"cwd":"/work/bare"}' "$HOME/.claude/settings.json" | python3 "$CLAUDE_GATE" --format claude > /tmp/global-gate-settings.json
```

10. Delete the probe and the folder made for it. The container is discarded on exit anyway, but a fixture written into an agent directory is
   always removed by the spec that wrote it.

```bash
rm -f "$HOME/.claude/agents/e2e-no-skills-probe.md" && rmdir "$HOME/.claude/agents"
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
test ! -e /work/bare/.agents/hooks/preflight-gate/preflight_gate.py
```

Expect exit 0.

The gate copy in the Claude Code plugin cache denies the main-thread source edit.

```bash
jq -e '.hookSpecificOutput.permissionDecision == "deny"' /tmp/global-gate-source.json
```

Expect exit 0.

The refusal is rule A rather than rule B, which the reason field distinguishes.

```bash
jq -e '.hookSpecificOutput.permissionDecisionReason | contains("may not write files directly")' /tmp/global-gate-source.json
```

Expect exit 0.

The shared gate copy denies the same payload through the Codex adapter.

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

With the definition in the home directory, the same payload is denied, which proves the gate found the user's own
subagent folder from a working directory that has none.

```bash
jq -e '.hookSpecificOutput.permissionDecision == "deny"' /tmp/global-gate-probe-after.json
```

Expect exit 0.

The refusal is rule B and names the probe.

```bash
jq -e '.hookSpecificOutput.permissionDecisionReason | contains("e2e-no-skills-probe")' /tmp/global-gate-probe-after.json
```

Expect exit 0.

The read-only reviewer from a plugin is denied the edit, and the reason names it as read-only, which proves the gate read its definition in the plugin cache.

```bash
jq -e '.hookSpecificOutput.permissionDecision == "deny" and (.hookSpecificOutput.permissionDecisionReason | contains("is read-only"))' /tmp/global-gate-reviewer-edit.json
```

Expect exit 0.

The same reviewer is allowed the git command its definition lists. An allow prints nothing.

```bash
test ! -s /tmp/global-gate-reviewer-diff.json
```

Expect exit 0.

The main-thread write to the user settings is denied.

```bash
jq -e '.hookSpecificOutput.permissionDecision == "deny"' /tmp/global-gate-settings.json
```

Expect exit 0.

The probe is gone again, and Claude Code is back to no subagent folder of its own.

```bash
test ! -e "$HOME/.claude/agents"
```

Expect exit 0.

---

### Fixtures

- `e2e/fixtures/e2e-no-skills-probe.md`: subagent definition carrying the canary marker `E2E-GATE-CANARY-9134` and
  declaring no skills, in front matter or body.
- `e2e/fixtures/gate-payloads/main-thread-source-edit.json`: main-thread `Edit` of `src/e2e_canary_app.py`, with
  `is_subagent: false` for the plain runner envelope, which the other formats ignore.
- `e2e/fixtures/gate-payloads/subagent-without-skills.json`: subagent payload naming `e2e-no-skills-probe`.
- The two reviewer payloads and the settings payload are written inline by their run steps, because they name a plugin subagent and the container's own home directory.

---

### Concurrency

- Mutates: the container's home directory, through the install this spec inherits from
  [6-global-install-shape-test.md](6-global-install-shape-test.md), plus
  `$HOME/.claude/agents/e2e-no-skills-probe.md`, which this spec creates and deletes with its folder. Nothing outside the container:
  `/repo` is mounted read-only and the container is discarded on exit.
- Conflicts with: every other spec in either suite when they share a container shell, and in particular
  [5-project-gate-subagent-rule-test.md](5-project-gate-subagent-rule-test.md), which writes a probe of the same name
  into a project agent directory that a gate run could also search. Nothing at all when every spec gets its own
  `docker compose run --rm` container.
- Serial: false
