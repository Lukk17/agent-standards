# Global MCP visibility: e2e test

Suite B, global setup. Setup cost class 5: the whole global installation, the user-scope MCP configuration on top of
it, and five agent command-line calls run from a directory into which nothing has been imported.

---

### What this verifies

- Each of the five agents, asked in its own terms from a bare directory, names the MCP servers its own user-scope
  configuration declares. Nothing in the working directory could have supplied them.
- The scope split holds. Only the two servers that are genuinely machine-wide, Context7 and Playwright, are installed
  globally. A connection string, a Grafana address, or a SonarQube token belongs to one project and stays out of the
  home directory, which is why the expected set here is smaller than the eight servers
  [4-project-mcp-visibility-test.md](4-project-mcp-visibility-test.md) expects.
- Codex needs the working directory trusted before it looks at anything, so the trust record here names `/work/bare`
  rather than a project.
- Claude Code is asserted on Context7 only. The documentation gives the exact `claude mcp add` invocation for an HTTP
  server and none for a local one, and guessing the local form would be inventing a command rather than testing one.
- Out of scope, because the container is given no provider credentials and carries neither `uvx` nor `docker`: the
  servers are listed, not proven healthy. A listing that names a server proves the agent read the user-scope
  configuration and registered it.
- Also out of scope: Copilot in VS Code and in JetBrains. Their MCP files are outside anything the container can
  reach, and only the Copilot command-line tool is installed here.

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
is not repeated here, so there is one copy of it to keep correct. Do not continue until it has finished. It already
puts the OpenCode and Kilo Code server blocks in place, so the commands below add only what it does not cover.

Give Codex its user-scope server tables and the trust record for the bare directory. Without the trust record Codex
reports nothing at all and the assertion would be measuring the trust prompt rather than the configuration.

```bash
cp /repo/e2e/fixtures/global/codex-config.toml "$HOME/.codex/config.toml"
```

Give the Copilot command-line tool its user-scope server file.

```bash
cp /repo/e2e/fixtures/global/copilot-mcp-config.json "$HOME/.copilot/mcp-config.json"
```

Add the one server to Claude Code at user scope. Claude Code stores user-scope servers in `~/.claude.json`, and the
supported way to write that file is this command rather than hand-editing it.

```bash
claude mcp add --transport http context7 --scope user https://mcp.context7.com/mcp
```

Confirm where you are, because every assertion in this spec depends on it.

```bash
pwd
```

Expect `/work/bare`.

---

### Run

Each step writes the tool's own output to a file so the assertions can read it. Several take minutes, because the
tools try to connect to servers that cannot be reached from inside the container. Read `echo $?` immediately after
each step, before running the next one.

1. Ask Claude Code which MCP servers it sees from here.

```bash
claude mcp list > /tmp/global-claude-mcp.txt 2>&1
```

2. Ask Codex.

```bash
codex mcp list > /tmp/global-codex-mcp.txt 2>&1
```

3. Ask OpenCode.

```bash
opencode mcp list > /tmp/global-opencode-mcp.txt 2>&1
```

4. Ask Kilo Code.

```bash
kilocode mcp list > /tmp/global-kilocode-mcp.txt 2>&1
```

5. Ask GitHub Copilot.

```bash
copilot mcp list > /tmp/global-copilot-mcp.txt 2>&1
```

---

### Expected

The working directory still holds none of the per-project files, so no server an agent reported could have come from
here. Assert this first: every other assertion in this spec depends on it.

```bash
ls -A /work/bare | grep -E "^(\.agents|\.claude|\.codex|\.github|\.kilo|\.opencode|\.vscode|\.mcp\.json|opencode\.json|AGENTS\.md)$"
```

Expect exit 1, meaning `grep` matched nothing. Exit 0 here is a failure of the test.

Claude Code exited 0 on run step 1.

```bash
echo $?
```

Expect `0`, read straight after run step 1.

Claude Code names the server added at user scope.

```bash
grep -qF "context7" /tmp/global-claude-mcp.txt
```

Expect exit 0.

Codex exited 0 on run step 2.

```bash
echo $?
```

Expect `0`, read straight after run step 2.

Codex names every server its own user-scope file declares. The expected set is read from that file rather than
written into this spec.

```bash
python3 -c "import sys,tomllib;n=sorted(tomllib.load(open('/repo/e2e/fixtures/global/codex-config.toml','rb'))['mcp_servers']);t=open('/tmp/global-codex-mcp.txt').read();m=[x for x in n if x not in t];print(m);sys.exit(1 if m else 0)"
```

Expect exit 0.

OpenCode exited 0 on run step 3.

```bash
echo $?
```

Expect `0`, read straight after run step 3.

OpenCode names every server its own global configuration declares.

```bash
python3 -c "import json,sys;n=sorted(json.load(open('/repo/e2e/fixtures/global/opencode.json'))['mcp']);t=open('/tmp/global-opencode-mcp.txt').read();m=[x for x in n if x not in t];print(m);sys.exit(1 if m else 0)"
```

Expect exit 0.

Kilo Code exited 0 on run step 4.

```bash
echo $?
```

Expect `0`, read straight after run step 4.

Kilo Code names every server its own global configuration declares. Kilo Code performs no environment-variable
substitution, which is why the global file carries literal values and no `{env:VAR}` references.

```bash
python3 -c "import json,sys;n=sorted(json.load(open('/repo/e2e/fixtures/global/kilo.jsonc'))['mcp']);t=open('/tmp/global-kilocode-mcp.txt').read();m=[x for x in n if x not in t];print(m);sys.exit(1 if m else 0)"
```

Expect exit 0.

GitHub Copilot exited 0 on run step 5.

```bash
echo $?
```

Expect `0`, read straight after run step 5.

Copilot names every server its own user-scope file declares.

```bash
python3 -c "import json,sys;n=sorted(json.load(open('/repo/e2e/fixtures/global/copilot-mcp-config.json'))['mcpServers']);t=open('/tmp/global-copilot-mcp.txt').read();m=[x for x in n if x not in t];print(m);sys.exit(1 if m else 0)"
```

Expect exit 0.

No project-scope server leaked into the global listings. Grafana is in the project templates and in none of the
global files, so its name appearing here would mean an agent read a project layer that is not supposed to exist in
this directory.

```bash
cat /tmp/global-claude-mcp.txt /tmp/global-codex-mcp.txt /tmp/global-opencode-mcp.txt /tmp/global-kilocode-mcp.txt /tmp/global-copilot-mcp.txt | grep -qF "grafana"
```

Expect exit 1, meaning the name appears nowhere. Exit 0 here is a failure of the test.

---

### Fixtures

- `e2e/fixtures/global/codex-config.toml`: two `[mcp_servers]` tables plus the trust record for `/work/bare`.
- `e2e/fixtures/global/copilot-mcp-config.json`: Copilot command-line MCP configuration, keyed `mcpServers`.
- `e2e/fixtures/global/opencode.json`: global OpenCode configuration, copied into place by the inherited install.
- `e2e/fixtures/global/kilo.jsonc`: global Kilo Code configuration, copied into place by the inherited install.

All four carry literal values and no variable references, so no assertion here can fail because a variable was unset
in the container.

---

### Concurrency

- Mutates: the container's home directory, through the install this spec inherits from
  [6-global-install-shape-test.md](6-global-install-shape-test.md), plus `$HOME/.codex/config.toml`,
  `$HOME/.copilot/mcp-config.json`, and `$HOME/.claude.json`, which `claude mcp add` writes. Nothing outside the
  container: `/repo` is mounted read-only and the container is discarded on exit.
- Conflicts with: every other spec in either suite when they share a container shell. In particular
  [4-project-mcp-visibility-test.md](4-project-mcp-visibility-test.md) writes its Codex trust record into the same
  `$HOME/.codex/config.toml` this spec fills with server tables, so those two would destroy each other. Nothing at
  all when every spec gets its own `docker compose run --rm` container.
- Serial: false
