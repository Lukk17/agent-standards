# Global agent discovery: e2e test

Suite B, global setup. Setup cost class 5: the whole global installation, plus agent command-line calls run from a
directory into which nothing has been imported.

---

### What this verifies

- OpenCode, asked in its own terms from a bare directory, names every subagent the global install placed in its
  global location. Nothing in the working directory could have supplied them.
- Kilo Code does the same, from its own separate global location.
- Kilo Code accepts the global configuration file instead of rejecting it. That file carries `skills.paths`, which is
  the only route by which Kilo Code ever sees the shared skills tree from a home directory, so a rejection takes the
  skills with it.
- GitHub Copilot, asked in its own terms from the same bare directory, loads every skill in the shared tree and
  parses all of them. Copilot reads `~/.agents/skills` natively, so this is the cleanest single proof that the shared
  tree is doing its job globally.
- Claude Code and Codex publish no skills or subagents listing command. Their global equivalents are the path and
  count assertions in [6-global-install-shape-test.md](6-global-install-shape-test.md). This spec says so rather than
  pretending to cover them.
- Out of scope, because the container is given no provider credentials: none of these commands starts a model
  session. A listing proves the tool found and parsed the definitions from the home directory. It does not prove the
  tool would pick the right one during real work.

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
invocations of [setup-global.sh](../../sandbox-agent/setup-global.sh) with the reset around them, and it is not
repeated here so there is one copy to keep correct. Do not continue until it has finished.

Confirm where you are, because every assertion in this spec depends on it.

```bash
pwd
```

Expect `/work/bare`.

---

### Run

Each step writes the tool's own output to a file so the assertions can read it, and each can take minutes. Read
`echo $?` immediately after each step, before running the next one.

1. Ask OpenCode which subagents it can see from here.

```bash
opencode agent list > /tmp/global-opencode-agents.txt 2>&1
```

2. Ask Kilo Code the same question.

```bash
kilocode agent list > /tmp/global-kilocode-agents.txt 2>&1
```

3. Ask Kilo Code whether it accepts the global configuration at all.

```bash
kilocode config check > /tmp/global-kilocode-config.txt 2>&1
```

4. Ask GitHub Copilot which skills it loaded.

```bash
copilot skill list > /tmp/global-copilot-skills.txt 2>&1
```

---

### Expected

The working directory still holds none of the per-project files, so nothing an agent reported could have come from
here. Assert this first: every other assertion in this spec depends on it.

```bash
ls -A /work/bare | grep -E "^(\.agents|\.claude|\.codex|\.github|\.kilo|\.opencode|\.vscode|\.mcp\.json|opencode\.json|AGENTS\.md)$"
```

Expect exit 1, meaning `grep` matched nothing. Exit 0 here is a failure of the test.

OpenCode exited 0 on run step 1.

```bash
echo $?
```

Expect `0`, read straight after run step 1.

OpenCode names every subagent the canonical tree holds. The expected set is read from the mounted repository, so
adding a subagent upstream never makes this spec stale. A failure prints the names that were missing.

```bash
python3 -c "import os,sys;n=[f[:-3] for f in os.listdir('/repo/.agents/agents') if f.endswith('.md')];t=open('/tmp/global-opencode-agents.txt').read();m=sorted(x for x in n if x not in t);print(m);sys.exit(1 if m else 0)"
```

Expect exit 0.

Kilo Code exited 0 on run step 2.

```bash
echo $?
```

Expect `0`, read straight after run step 2.

Kilo Code names every subagent too, from its own global directory.

```bash
python3 -c "import os,sys;n=[f[:-3] for f in os.listdir('/repo/.agents/agents') if f.endswith('.md')];t=open('/tmp/global-kilocode-agents.txt').read();m=sorted(x for x in n if x not in t);print(m);sys.exit(1 if m else 0)"
```

Expect exit 0.

Kilo Code's configuration check exited 0 on run step 3.

```bash
echo $?
```

Expect `0`, read straight after run step 3.

Kilo Code did not reject the global configuration file.

```bash
grep -qF "Configuration is invalid" /tmp/global-kilocode-config.txt
```

Expect exit 1, meaning the phrase does not appear. Exit 0 here is a failure of the test.

GitHub Copilot exited 0 on run step 4.

```bash
echo $?
```

Expect `0`, read straight after run step 4.

Copilot loaded every skill in the shared tree, from the home directory, with nothing in the working directory to help
it. A failure prints the skill names that were missing.

```bash
python3 -c "import os,sys;n=sorted(os.listdir('/repo/.agents/skills'));t=open('/tmp/global-copilot-skills.txt').read();m=[x for x in n if x not in t];print(m);sys.exit(1 if m else 0)"
```

Expect exit 0.

Copilot parsed all of them. One skill with broken YAML front matter is enough to produce this line, and the skill is
then invisible even though it is on disk.

```bash
grep -qiE "failed to (load|parse)" /tmp/global-copilot-skills.txt
```

Expect exit 1, meaning no such line appears. Exit 0 here is a failure of the test.

---

### Fixtures

None. The global Kilo Code configuration that `kilocode config check` judges, the one carrying `skills.paths`, is
written by [setup-global.sh](../../sandbox-agent/setup-global.sh) during the install this spec inherits from
[6-global-install-shape-test.md](6-global-install-shape-test.md). Nothing here is copied from a fixture, so what the
tools read is what a reader's own machine would get.

---

### Concurrency

- Mutates: the container's home directory, through the install this spec inherits from
  [6-global-install-shape-test.md](6-global-install-shape-test.md), plus whatever state OpenCode, Kilo Code, and
  Copilot write under `$HOME`. Nothing outside the container: `/repo` is mounted read-only and the container is
  discarded on exit.
- Conflicts with: every other spec in either suite when they share a container shell, because the inherited install
  deletes and rewrites the whole global layer. Nothing at all when every spec gets its own
  `docker compose run --rm` container.
- Serial: false
