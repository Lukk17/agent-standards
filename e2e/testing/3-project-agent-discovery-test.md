# Project agent discovery: e2e test

Suite A, per-project setup. Setup cost class 3: the full project import plus four agent command-line calls, each of
which can take minutes on a cold container.

---

### What this verifies

- OpenCode, asked in its own terms, names every subagent the import delivered.
- Kilo Code, asked in its own terms, names every subagent the import delivered.
- Kilo Code accepts the project configuration instead of rejecting it. A rejected file takes the plugin declaration
  that carries the preflight gate down with it, so this one assertion covers more than it looks.
- GitHub Copilot, asked in its own terms, loads every imported skill and parses all of them.
- Claude Code and Codex publish no skills or subagents listing command, so their equivalents are path and count
  assertions and they live in [2-project-import-shape-test.md](2-project-import-shape-test.md). This spec says so
  rather than pretending to cover them.
- Out of scope, because the container is given no provider credentials: none of these commands starts a model
  session. A listing proves the tool found and parsed the definitions. It does not prove the tool would pick the
  right one during real work.

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

Build the clean project and run the documented import into it. The script deletes and rebuilds `/work/project`, which
is the whole reset this spec needs.

```bash
/harness/setup-project.sh
```

Move into the imported project. Every command below runs from here, because every one of these tools resolves its
project configuration from the working directory.

```bash
cd /work/project
```

---

### Run

Each step writes the tool's own output to a file so the assertions can read it, and each can take minutes. Read
`echo $?` immediately after each step, before running the next one.

1. Ask OpenCode which subagents it can see.

```bash
opencode agent list > /tmp/opencode-agents.txt 2>&1
```

2. Ask Kilo Code the same question.

```bash
kilocode agent list > /tmp/kilocode-agents.txt 2>&1
```

3. Ask Kilo Code whether it accepts the project configuration at all.

```bash
kilocode config check > /tmp/kilocode-config.txt 2>&1
```

4. Ask GitHub Copilot which skills it loaded.

```bash
copilot skill list > /tmp/copilot-skills.txt 2>&1
```

---

### Expected

OpenCode exited 0 on run step 1.

```bash
echo $?
```

Expect `0`, read straight after run step 1.

OpenCode names every subagent the canonical tree holds. The expected set is read from the mounted repository, so
adding a subagent upstream never makes this spec stale. A failure prints the names that were missing.

```bash
python3 -c "import os,sys;n=[f[:-3] for f in os.listdir('/repo/.agents/agents') if f.endswith('.md')];t=open('/tmp/opencode-agents.txt').read();m=sorted(x for x in n if x not in t);print(m);sys.exit(1 if m else 0)"
```

Expect exit 0.

Kilo Code exited 0 on run step 2.

```bash
echo $?
```

Expect `0`, read straight after run step 2.

Kilo Code names every subagent too, from the same canonical set.

```bash
python3 -c "import os,sys;n=[f[:-3] for f in os.listdir('/repo/.agents/agents') if f.endswith('.md')];t=open('/tmp/kilocode-agents.txt').read();m=sorted(x for x in n if x not in t);print(m);sys.exit(1 if m else 0)"
```

Expect exit 0.

Kilo Code's configuration check exited 0 on run step 3.

```bash
echo $?
```

Expect `0`, read straight after run step 3.

Kilo Code did not reject the configuration file. A rejection discards the whole file, including the `plugin`
declaration that carries the preflight gate, so this assertion is about the gate as much as about the servers.

```bash
grep -qF "Configuration is invalid" /tmp/kilocode-config.txt
```

Expect exit 1, meaning the phrase does not appear. Exit 0 here is a failure of the test.

GitHub Copilot exited 0 on run step 4.

```bash
echo $?
```

Expect `0`, read straight after run step 4.

Copilot loaded every skill the canonical tree holds. A failure prints the skill names that were missing.

```bash
python3 -c "import os,sys;n=sorted(os.listdir('/repo/.agents/skills'));t=open('/tmp/copilot-skills.txt').read();m=[x for x in n if x not in t];print(m);sys.exit(1 if m else 0)"
```

Expect exit 0.

Copilot parsed all of them. One skill with broken YAML front matter is enough to produce this line, and the skill is
then invisible to Copilot even though it is on disk.

```bash
grep -qiE "failed to (load|parse)" /tmp/copilot-skills.txt
```

Expect exit 1, meaning no such line appears. Exit 0 here is a failure of the test.

---

### Fixtures

None. This spec reads only what the import produced and the canonical trees in the mounted repository.

---

### Concurrency

- Mutates: `/work/project` inside the container, which `setup-project.sh` deletes and rebuilds itself, plus whatever
  state OpenCode, Kilo Code, and Copilot write under the container's `$HOME`. Nothing outside the container: `/repo`
  is mounted read-only and the container is discarded on exit.
- Conflicts with: any spec executed in the same container shell as this one, because `setup-project.sh` wipes
  `/work/project` and the `/tmp` filenames would collide. Nothing at all when every spec gets its own
  `docker compose run --rm` container.
- Serial: false
