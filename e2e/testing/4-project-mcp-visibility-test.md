# Project MCP visibility: e2e test

Suite A, per-project setup. Setup cost class 3: the full project import, a trust record written into the container's
own home directory so Codex will look at the project at all, and five agent command-line calls.

---

### What this verifies

- Every one of the five agents, asked in its own terms, names every MCP server the shared templates ship. The
  expected set is read from `.mcp.json` in the mounted repository at run time, so adding a server upstream never
  makes this spec stale.
- The MCP block is present in each of the four project files the agents actually read, which is what makes the
  listings possible: `.mcp.json`, `.codex/config.toml`, `opencode.json`, and `.vscode/mcp.json`.
- Codex only sees any of its `.codex/` layer once the project is trusted. This spec writes that trust record itself,
  so the assertion measures the configuration rather than the trust prompt.
- Out of scope, because the container is given no provider credentials and carries neither `uvx` nor `docker`: the
  servers are listed, not proven healthy. Several cannot connect from inside this container, which is a property of
  the container and not of the configuration. A listing that names a server proves the agent read the configuration
  and registered it.
- Also out of scope: `.vscode/mcp.json` is asserted as a file only. Copilot in VS Code is not installed here, and the
  Copilot command-line tool reads `.mcp.json` instead, so no listing command can speak for that file.

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

Build the clean project and run the documented import into it.

```bash
/sandbox/setup-project.sh
```

Create the Codex configuration directory in the container's home.

```bash
mkdir -p "$HOME/.codex"
```

Write the trust record. Without it Codex ignores the entire `.codex/` layer and reports no servers at all, which
would make the assertion below measure the trust prompt rather than the configuration. This file lives in the
container's home directory and dies with the container.

```bash
printf '[projects."/work/project"]\ntrust_level = "trusted"\n' > "$HOME/.codex/config.toml"
```

Move into the imported project. Every command below runs from here.

```bash
cd /work/project
```

---

### Run

Each step writes the tool's own output to a file so the assertions can read it. Several take minutes, because the
tools try to connect to servers that cannot be reached from inside the container. Read `echo $?` immediately after
each step, before running the next one.

1. Ask Claude Code which MCP servers it sees.

```bash
claude mcp list > /tmp/claude-mcp.txt 2>&1
```

2. Ask Codex.

```bash
codex mcp list > /tmp/codex-mcp.txt 2>&1
```

3. Ask OpenCode.

```bash
opencode mcp list > /tmp/opencode-mcp.txt 2>&1
```

4. Ask Kilo Code.

```bash
kilocode mcp list > /tmp/kilocode-mcp.txt 2>&1
```

5. Ask GitHub Copilot.

```bash
copilot mcp list > /tmp/copilot-mcp.txt 2>&1
```

---

### Expected

The file Claude Code and the Copilot command-line tool read declares at least one server.

```bash
jq -e '(.mcpServers | length) > 0' /work/project/.mcp.json
```

Expect exit 0.

The file Codex reads declares at least one server.

```bash
python3 -c "import sys,tomllib;sys.exit(0 if tomllib.load(open('/work/project/.codex/config.toml','rb')).get('mcp_servers') else 1)"
```

Expect exit 0.

The file OpenCode reads declares at least one server.

```bash
jq -e '(.mcp | length) > 0' /work/project/opencode.json
```

Expect exit 0.

The file Copilot in VS Code reads declares at least one server, under its own `servers` key rather than
`mcpServers`.

```bash
jq -e '(.servers | length) > 0' /work/project/.vscode/mcp.json
```

Expect exit 0.

Claude Code exited 0 on run step 1.

```bash
echo $?
```

Expect `0`, read straight after run step 1.

Claude Code names every server the shared templates ship. A failure prints the ones that were missing.

```bash
python3 -c "import json,sys;n=sorted(json.load(open('/repo/.mcp.json'))['mcpServers']);t=open('/tmp/claude-mcp.txt').read();m=[x for x in n if x not in t];print(m);sys.exit(1 if m else 0)"
```

Expect exit 0.

Codex exited 0 on run step 2.

```bash
echo $?
```

Expect `0`, read straight after run step 2.

Codex names every server, from its own TOML tables.

```bash
python3 -c "import json,sys;n=sorted(json.load(open('/repo/.mcp.json'))['mcpServers']);t=open('/tmp/codex-mcp.txt').read();m=[x for x in n if x not in t];print(m);sys.exit(1 if m else 0)"
```

Expect exit 0.

OpenCode exited 0 on run step 3.

```bash
echo $?
```

Expect `0`, read straight after run step 3.

OpenCode names every server.

```bash
python3 -c "import json,sys;n=sorted(json.load(open('/repo/.mcp.json'))['mcpServers']);t=open('/tmp/opencode-mcp.txt').read();m=[x for x in n if x not in t];print(m);sys.exit(1 if m else 0)"
```

Expect exit 0.

Kilo Code exited 0 on run step 4.

```bash
echo $?
```

Expect `0`, read straight after run step 4.

Kilo Code names every server. Kilo reads OpenCode-format project configuration and performs no environment-variable
substitution, so a template that leaves `{env:VAR}` references in place is the likeliest cause of an empty listing
here.

```bash
python3 -c "import json,sys;n=sorted(json.load(open('/repo/.mcp.json'))['mcpServers']);t=open('/tmp/kilocode-mcp.txt').read();m=[x for x in n if x not in t];print(m);sys.exit(1 if m else 0)"
```

Expect exit 0.

GitHub Copilot exited 0 on run step 5.

```bash
echo $?
```

Expect `0`, read straight after run step 5.

Copilot names every server, read from the same `.mcp.json` Claude Code uses.

```bash
python3 -c "import json,sys;n=sorted(json.load(open('/repo/.mcp.json'))['mcpServers']);t=open('/tmp/copilot-mcp.txt').read();m=[x for x in n if x not in t];print(m);sys.exit(1 if m else 0)"
```

Expect exit 0.

---

### Fixtures

None. The expected server set is read from `.mcp.json` in the mounted repository at run time rather than from a
fixture, so the spec cannot drift from the templates.

---

### Concurrency

- Mutates: `/work/project` inside the container, `$HOME/.codex/config.toml` inside the container, and whatever state
  the five tools write under the container's `$HOME`. Nothing outside the container: `/repo` is mounted read-only and
  the container is discarded on exit.
- Conflicts with: any spec executed in the same container shell as this one. This spec overwrites
  `$HOME/.codex/config.toml`, which is the same file
  [8-global-mcp-visibility-test.md](8-global-mcp-visibility-test.md) writes its global server tables into, so those
  two would destroy each other in a shared container. Nothing at all when every spec gets its own
  `docker compose run --rm` container.
- Serial: false
