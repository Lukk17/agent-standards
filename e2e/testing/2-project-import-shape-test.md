# Project import shape: e2e test

Suite A, per-project setup. Setup cost class 2: a container plus the full documented import into a brand-new project.
No agent tool is invoked, so every assertion here is a filesystem or configuration-file check.

---

### What this verifies

- The documented selective checkout lands every shared tree in a clean project, and lands nothing it should not:
  `AGENTS.md.example` is renamed rather than copied, and the upstream-only `subagents/` and `tools/` trees stay
  behind.
- Skills are discoverable at the path each agent reads. Codex, OpenCode, Kilo Code, and GitHub Copilot read
  `.agents/skills/` directly, and Claude Code reaches the same files through the `.claude/skills` symlink.
- Subagent definitions are present in each agent's own format, and there are as many of them as the canonical source
  holds: Claude Code markdown, Codex TOML, Copilot `*.agent.md`, and the OpenCode-format tree that OpenCode and Kilo
  Code reach through symlinks.
- The preflight gate is wired into the file each agent actually reads, calling the shared script with that agent's
  output format.
- Out of scope, because the container is given no provider credentials: nothing here starts an agent session. This
  spec proves the files landed and point at the right places. Whether each tool then reports what it found is
  [3-project-agent-discovery-test.md](3-project-agent-discovery-test.md), and whether the gate really refuses is
  [1-project-gate-decisions-test.md](1-project-gate-decisions-test.md) and
  [5-project-gate-subagent-rule-test.md](5-project-gate-subagent-rule-test.md).

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

Record the commit under test, because the import fetches committed state only. PowerShell:

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

None beyond the fresh container. `setup-project.sh` deletes and rebuilds `/work/project` itself on every invocation,
and `/repo` is mounted read-only, so there is nothing else to wipe.

---

### Run

1. Move into the sandbox directory, which is where Compose finds its `compose.yaml`. The same line works in
   PowerShell and in a Unix shell.

```bash
cd sandbox-agent
```

   Start the container shell. Everything after this step is typed into that shell. PowerShell:

```powershell
docker compose run --rm sandbox /bin/bash
```

Unix shell:

```bash
docker compose run --rm sandbox /bin/bash
```

Wait for the version table the entrypoint prints, then copy it into the run record.

2. Build the clean project and run the documented import into it. Wait for the script to exit before continuing.

```bash
/sandbox/setup-project.sh
```

3. Move into the imported project. Every assertion below runs from here.

```bash
cd /work/project
```

---

### Expected

Run step 2 exits 0. Read the status straight after it.

```bash
echo $?
```

Expect `0`.

The one template was activated, so the project has real instructions.

```bash
test -f /work/project/AGENTS.md
```

Expect exit 0.

The template was renamed rather than copied, so no consumer ends up maintaining two copies.

```bash
test ! -e /work/project/AGENTS.md.example
```

Expect exit 0.

The canonical subagent source stayed upstream. A consumer that edits it would lose the edit on the next generator
run.

```bash
test ! -e /work/project/subagents
```

Expect exit 0.

The generator stayed upstream too.

```bash
test ! -e /work/project/tools
```

Expect exit 0.

The shared gate script landed, which every hook wiring below points at.

```bash
test -f /work/project/.agents/hooks/preflight_gate.py
```

Expect exit 0.

The OpenCode and Kilo Code plugin shim landed.

```bash
test -f /work/project/.agents/plugin/hooks.js
```

Expect exit 0.

Every canonical skill landed, counted against the mounted repository rather than a number written into this spec.

```bash
test "$(find /work/project/.agents/skills -mindepth 1 -maxdepth 1 -type d | wc -l)" -eq "$(find /repo/.agents/skills -mindepth 1 -maxdepth 1 -type d | wc -l)"
```

Expect exit 0.

Claude Code's skills path is a symlink that resolves to a directory rather than a text file holding a path, which is
the failure mode on a machine where git was not told to honour symlinks.

```bash
test -L /work/project/.claude/skills -a -d /work/project/.claude/skills
```

Expect exit 0.

The same number of skills is reachable through that symlink, so nothing flattened on the way.

```bash
test "$(find -L /work/project/.claude/skills -mindepth 2 -maxdepth 2 -name SKILL.md | wc -l)" -eq "$(find /repo/.agents/skills -mindepth 2 -maxdepth 2 -name SKILL.md | wc -l)"
```

Expect exit 0.

One named skill resolves through the link, which catches a symlink that resolves as a directory but points somewhere
empty.

```bash
test -f /work/project/.claude/skills/python-patterns/SKILL.md
```

Expect exit 0.

OpenCode's subagents symlink resolves to a directory.

```bash
test -L /work/project/.opencode/agents -a -d /work/project/.opencode/agents
```

Expect exit 0.

Kilo Code's subagents symlink resolves to a directory.

```bash
test -L /work/project/.kilo/agents -a -d /work/project/.kilo/agents
```

Expect exit 0.

Claude Code sees every subagent in its own markdown format.

```bash
test "$(find /work/project/.claude/agents -maxdepth 1 -name '*.md' | wc -l)" -eq "$(find /repo/.agents/agents -maxdepth 1 -name '*.md' | wc -l)"
```

Expect exit 0.

Codex sees every subagent in TOML, which is the format it takes and no other agent does.

```bash
test "$(find /work/project/.codex/agents -maxdepth 1 -name '*.toml' | wc -l)" -eq "$(find /repo/.agents/agents -maxdepth 1 -name '*.md' | wc -l)"
```

Expect exit 0.

GitHub Copilot sees every subagent as `*.agent.md`.

```bash
test "$(find /work/project/.github/agents -maxdepth 1 -name '*.agent.md' | wc -l)" -eq "$(find /repo/.agents/agents -maxdepth 1 -name '*.md' | wc -l)"
```

Expect exit 0.

Claude Code calls the gate on `PreToolUse`, in its own format. Its command runs the gate through a one-line Python
wrapper, so the flag arrives as two separately quoted arguments rather than as ` --format claude` in the command
string. Path and flag are therefore matched separately.

```bash
jq -e '[.hooks.PreToolUse[].hooks[].command] | any(contains("preflight_gate.py") and test("--format.,.claude"))' /work/project/.claude/settings.json
```

Expect exit 0.

That wrapper is also how Claude Code discards the gate's standard error, and the command ends by forcing a zero exit
so a broken gate allows rather than denies.

```bash
jq -e '[.hooks.PreToolUse[].hooks[].command] | any(contains("stderr=subprocess.DEVNULL") and endswith("; exit 0"))' /work/project/.claude/settings.json
```

Expect exit 0.

Claude Code also injects the gate text on every prompt, which is the advisory half of the same rule.

```bash
jq -e '[.hooks.UserPromptSubmit[].hooks[].command] | any(contains("PREFLIGHT"))' /work/project/.claude/settings.json
```

Expect exit 0.

Codex calls the gate on `PreToolUse`, in its own format, from the TOML file it reads.

```bash
python3 -c "import sys,tomllib;h=tomllib.load(open('/work/project/.codex/config.toml','rb'))['hooks']['PreToolUse'];sys.exit(0 if any('preflight_gate.py --format codex' in i['command'] for e in h for i in e['hooks']) else 1)"
```

Expect exit 0.

Codex injects the gate text on every prompt too.

```bash
python3 -c "import sys,tomllib;h=tomllib.load(open('/work/project/.codex/config.toml','rb'))['hooks']['UserPromptSubmit'];sys.exit(0 if any('PREFLIGHT' in i['command'] for e in h for i in e['hooks']) else 1)"
```

Expect exit 0.

GitHub Copilot calls the gate on `preToolUse`, spelled with its own lower-case first letter, in its own format.

```bash
jq -e '[.hooks.preToolUse[].bash] | any(contains("preflight_gate.py --format copilot"))' /work/project/.github/hooks/preflight.json
```

Expect exit 0.

Copilot injects the gate text once per session, which is the only injection channel it offers.

```bash
jq -e '[.hooks.sessionStart[].bash] | any(contains("PREFLIGHT"))' /work/project/.github/hooks/preflight.json
```

Expect exit 0.

OpenCode declares the shared plugin by path, which is how the gate reaches it.

```bash
jq -e '[.plugin[]] | any(contains(".agents/plugin/hooks.js"))' /work/project/opencode.json
```

Expect exit 0.

OpenCode is pointed at `AGENTS.md` as its instruction file.

```bash
jq -e '[.instructions[]] | any(. == "AGENTS.md")' /work/project/opencode.json
```

Expect exit 0.

Kilo Code reads OpenCode-format project configuration. The import delivers that as `opencode.json`, and
`.kilo/kilo.jsonc` is the alternative location for the same keys, so the assertion accepts whichever one the current
layout ships and only cares that the shared plugin is declared somewhere Kilo reads. Whether Kilo then accepts the
file is a behaviour check and belongs to
[3-project-agent-discovery-test.md](3-project-agent-discovery-test.md).

```bash
cat /work/project/opencode.json /work/project/.kilo/kilo.jsonc 2>/dev/null | grep -qF ".agents/plugin/hooks.js"
```

Expect exit 0.

---

### Fixtures

None. This spec reads only what the import produced and what the mounted repository already holds.

---

### Concurrency

- Mutates: `/work/project` inside the container, which `setup-project.sh` deletes and rebuilds itself. Nothing
  outside the container: `/repo` is mounted read-only and the container is discarded on exit.
- Conflicts with: any spec executed in the same container shell as this one, because `setup-project.sh` wipes
  `/work/project` out from under it. Nothing at all when every spec gets its own `docker compose run --rm` container.
- Serial: false
