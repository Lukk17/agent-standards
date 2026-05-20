# MCP Setup

Human setup guide for the Model Context Protocol (MCP) servers shipped by agent-standards. Covers prerequisites,
acquiring keys, setting environment variables system-wide, per-machine config files, and verification.

This file is for the **person** configuring the machine. The AI agent reads `AGENTS.md` and uses whatever MCP tools the
running agent exposes — it doesn't need this document.

---

## What ships

Two committed templates in the repo root:

- `.mcp.json.example` — Claude Code project scope. Schema key `mcpServers`. Env-var syntax: `${VAR}` and
  `${VAR:-default}`.
- `opencode.json.example` — OpenCode + Kilo Code project scope (they share the file). Schema key `mcp` alongside
  `instructions`. Env-var syntax: `{env:VAR}` (no `$`).

Eight default servers, in order:

| Server            | Purpose                                     | External dependency                              |
| ----------------- | ------------------------------------------- | ------------------------------------------------ |
| `context7`        | Up-to-date library docs lookup              | none (hosted HTTP, free tier without API key)    |
| `mongodb`         | Read-only MongoDB introspection             | a running MongoDB (dev only, never prod)         |
| `grafana`         | Grafana dashboards, queries, alerts         | a Grafana instance + service-account token       |
| `playwright`      | Cross-browser automation for UI tests       | downloads ~500 MB of browsers on first run       |
| `chrome-devtools` | Performance / network / console debugging   | Chrome installed locally                         |
| `redis`           | Redis cache / queue introspection           | a running Redis (dev only)                       |
| `sonarqube`       | Code-quality issues lookup                  | Docker + a SonarQube instance + token            |
| `n8n`             | n8n workflow node docs + optional control   | none for docs-only; n8n instance + key for full  |

Disable a server you don't use. In `opencode.json` set `"enabled": false` on the block. In `.mcp.json` delete the
block — Claude Code's schema has no `enabled` flag.

---

## Step 1 — Copy the templates

From the project root:

```bash
cp .mcp.json.example .mcp.json
```

```bash
cp opencode.json.example opencode.json
```

Both files are gitignored at the agent-standards repo level. In your consumer project, decide per-team whether to commit
them. If you keep `${VAR}` / `{env:VAR}` placeholders and never inline secrets, the files are commit-safe.

---

## Step 2 — Install prerequisites

- **`npx`** ships with Node.js. Verify: `node --version`.
- **`uv`** runs the `grafana` and `redis` MCPs. Install per OS:
  - Linux/macOS: `curl -LsSf https://astral.sh/uv/install.sh | sh` or `brew install uv`.
  - Windows: `winget install --id=astral-sh.uv`.
- **Docker** runs the `sonarqube` MCP. Verify: `docker --version`.
- The backing services (`mongodb`, `grafana`, `redis`, `sonarqube`, `n8n`) must be running before the MCP can connect.
  If you don't have one, disable that server.

---

## Step 3 — Acquire keys

| Key                              | Where to get it                                                                  | Required? |
| -------------------------------- | -------------------------------------------------------------------------------- | --------- |
| `CONTEXT7_API_KEY`               | <https://context7.com/dashboard>                                                 | optional  |
| `GRAFANA_SERVICE_ACCOUNT_TOKEN`  | Grafana UI → Administration → Service accounts → Add service account → token     | yes       |
| `SONARQUBE_TOKEN`                | SonarQube UI → My Account → Security → Generate Token                            | yes       |
| `N8N_API_KEY`                    | n8n UI → Settings → API → Create API key                                         | optional  |

Use read-only or least-privilege tokens. The Grafana account just needs `Viewer` for dashboards and `Editor` only if
you want the MCP to create alerts. The SonarQube token needs `Execute Analysis` only if you also write code-quality
results back; otherwise read-only.

---

## Step 4 — Set environment variables system-wide

Prefer system-wide variables over per-shell so every agent inherits them: Claude Code, OpenCode, Kilo Code CLI,
JetBrains plugins, GUI apps.

### Linux

Append to `/etc/environment` (system-wide, all users) or `~/.profile` (your user):

```bash
echo 'CONTEXT7_API_KEY=ctx7_xxxxxxxxxxxx' | sudo tee -a /etc/environment
```

```bash
echo 'GRAFANA_SERVICE_ACCOUNT_TOKEN=glsa_xxxxxxxxxxxx' >> ~/.profile
```

Log out and back in to apply. For interactive shells only, append to `~/.bashrc` or `~/.zshrc`:

```bash
export CONTEXT7_API_KEY=ctx7_xxxxxxxxxxxx
```

### macOS

Append to `~/.zprofile` (loaded by Terminal and GUI sessions started from Terminal):

```bash
echo 'export CONTEXT7_API_KEY=ctx7_xxxxxxxxxxxx' >> ~/.zprofile
```

For GUI apps launched from Finder (Claude Desktop, IDEs), set via `launchctl`:

```bash
launchctl setenv CONTEXT7_API_KEY ctx7_xxxxxxxxxxxx
```

Persist `launchctl` values across reboots with a `~/Library/LaunchAgents/setenv.<name>.plist` entry or a tool like
[direnv](https://direnv.net/) scoped per project.

### Windows

Set persistently for the current user (visible to new processes after restart):

```powershell
[Environment]::SetEnvironmentVariable('CONTEXT7_API_KEY', 'ctx7_xxxxxxxxxxxx', 'User')
```

System-wide (requires Administrator):

```powershell
[Environment]::SetEnvironmentVariable('CONTEXT7_API_KEY', 'ctx7_xxxxxxxxxxxx', 'Machine')
```

Verify in a fresh PowerShell session:

```powershell
$env:CONTEXT7_API_KEY
```

Restart your terminal, IDE, and any running agent shell after changing system variables. Claude Desktop must be fully
quit (system-tray icon) and relaunched.

---

## Step 5 — Variables to set

| Variable                          | Used by      | Default if unset                  |
| --------------------------------- | ------------ | --------------------------------- |
| `CONTEXT7_API_KEY`                | `context7`   | none (free tier works without it) |
| `MONGODB_URL`                     | `mongodb`    | `mongodb://localhost:27017`       |
| `GRAFANA_URL`                     | `grafana`    | `http://localhost:3000`           |
| `GRAFANA_SERVICE_ACCOUNT_TOKEN`   | `grafana`    | none — server will fail to start  |
| `REDIS_URL`                       | `redis`      | `redis://localhost:6379/0`        |
| `SONARQUBE_TOKEN`                 | `sonarqube`  | none — server will fail to start  |
| `SONARQUBE_URL`                   | `sonarqube`  | `http://localhost:9000`           |
| `N8N_API_URL`                     | `n8n`        | `http://localhost:5678`           |
| `N8N_API_KEY`                     | `n8n`        | empty (n8n MCP runs docs-only)    |

`.mcp.json.example` uses `${VAR:-default}` so unset optional variables resolve to the listed defaults.
`opencode.json.example` uses `{env:VAR}` with no default — if you skip a server, set `"enabled": false` on it rather
than leaving its env vars empty.

---

## Step 6 — User-global configs (per machine, not committed)

The committed templates cover project scope. Three more files run user-global; none of them ships in the import.

### Claude Code user-global

Path: `~/.claude.json`. Same `mcpServers` schema as the project file. Same `${VAR}` substitution.

Used when you're working outside any project that defines its own `.mcp.json`. Project file wins on name collisions.

If the file already exists, merge the `mcpServers` block by hand — Claude Code keeps other top-level keys there too
(`theme`, `editorMode`, etc.).

To populate from scratch:

```bash
cp .mcp.json.example ~/.claude.json
```

### Claude Desktop

Paths:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: no official Claude Desktop build.

Same `mcpServers` schema. **Does not support env-var substitution** — replace each `${VAR}` with the actual value.
This file is per-machine personal, so inlining is acceptable; just never commit it.

Example:

```json
{
  "mcpServers": {
    "context7": {
      "type": "http",
      "url": "https://mcp.context7.com/mcp",
      "headers": {
        "CONTEXT7_API_KEY": "ctx7_actual_value_here"
      }
    }
  }
}
```

### Codex CLI

Path: `~/.codex/config.toml`. Different format (TOML, not JSON). Global-only, no project scope.

```toml
[mcp_servers.context7]
command = "npx"
args = ["-y", "@upstash/context7-mcp@latest"]

[mcp_servers.mongodb]
command = "npx"
args = [
    "-y",
    "mongodb-mcp-server@latest",
    "--readOnly",
    "--connectionString",
    "mongodb://localhost:27017",
]
```

Codex has no built-in env-var substitution. If you want secrets out of the file, wrap the command in a small shell
script that reads from your secrets manager.

---

## Env-var substitution support matrix

Useful when debugging why a variable isn't being picked up.

| Tool / config file                              | Substitution syntax            | Supported fields                              |
| ----------------------------------------------- | ------------------------------ | --------------------------------------------- |
| Claude Code, `.mcp.json` and `~/.claude.json`   | `${VAR}`, `${VAR:-default}`    | `command`, `args`, `env`, `url`, `headers`    |
| OpenCode / Kilo Code, `opencode.json`           | `{env:VAR}`                    | string values in any MCP field                |
| Claude Desktop, `claude_desktop_config.json`    | **not supported**              | inline literal values                         |
| Codex CLI, `~/.codex/config.toml`               | TOML; no built-in substitution | inline literal values                         |

---

## Verifying the setup

After editing the configs and exporting env vars, restart the agent. Then:

- **Claude Code** — run `claude mcp list` to see which servers loaded.
- **OpenCode / Kilo Code** — start the agent and check the startup log for MCP connection lines, or run `/mcp` inside
  the shell.
- **Claude Desktop** — open the Developer panel; the MCP indicator in the input box shows connected servers.
- **Codex CLI** — start `codex` and check `/mcp` (Codex 0.20+).

If a server fails to connect:

- Claude Code logs the reason to its standard log.
- Claude Desktop logs land in `~/Library/Logs/Claude/` (macOS) or `%APPDATA%\Claude\logs\` (Windows). Files named
  `mcp-server-<name>.log` carry the per-server stderr.

---

## Adding or changing a server

Edit `.mcp.json.example` and `opencode.json.example` in the agent-standards repo, commit, and consumer projects pull via
the Step 2 update flow in [`AGENT_TOOLING.md`](AGENT_TOOLING.md). To customise per-project without affecting upstream,
edit the copied `.mcp.json` and `opencode.json` directly — those are local to each consumer.
