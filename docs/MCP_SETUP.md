# MCP Setup

Human setup guide for the Model Context Protocol servers shipped by agent-standards. Covers what ships, what does not
and why, prerequisites, acquiring keys, setting environment variables system-wide, and verification.

This file is for the person configuring the machine. The agent reads [AGENTS.md](../AGENTS.md) and uses whatever
MCP tools its runtime exposes, so it never needs this document.

---

### What ships

Five real config files, committed and ready to use. They are not templates any more, so there is nothing to rename.

| File | Schema key | Serves | Notes |
| --- | --- | --- | --- |
| [.mcp.json](../.mcp.json) | `mcpServers` | Claude Code | `"type": "http"` for remote, `"type": "stdio"` for local |
| [opencode.json](../opencode.json) | `mcp` | OpenCode and Kilo Code | `"type": "remote"` or `"type": "local"`, sits at the project root |
| [.codex/config.toml](../.codex/config.toml) | `[mcp_servers.*]` | Codex | TOML, also carries the preflight hook tables |
| [.vscode/mcp.json](../.vscode/mcp.json) | `servers` | GitHub Copilot in VS Code | key is `servers`, not `mcpServers` |
| [.github/mcp.json](../.github/mcp.json) | `mcpServers` | the GitHub Copilot CLI | `"type": "http"` for remote, `"type": "local"` for a stdio server |

All five carry the same eight servers. Only the file name, the schema key, the `type` value, and the
environment-variable syntax change between them. There is no per-tool overlay beyond these five: one file per agent
surface, and that is the whole set.

Two surfaces get no shipped file, because there is nothing a repository could ship that they would read:

- GitHub Copilot in JetBrains reads MCP only from the global path `~/.config/github-copilot/intellij/mcp.json`
  (`%USERPROFILE%\.config\github-copilot\intellij\mcp.json` on Windows). There is no per-project MCP file for that
  plugin, and GitHub documents only the in-IDE screen (Settings, Tools, GitHub Copilot, Model Context Protocol), not
  the path, so treat the path itself as community knowledge rather than official. Manual block below.
- The GitHub Copilot cloud agent takes its MCP configuration as JSON pasted into a page in the repository
  settings, not from a file in the tree. Manual block below.

Of Copilot's four surfaces, VS Code reads [.vscode/mcp.json](../.vscode/mcp.json), the CLI reads
[.github/mcp.json](../.github/mcp.json), and the other two are manual.

#### The CLI, `.mcp.json`, and why a fifth file exists

The GitHub Copilot CLI's own documentation states it is capable of reading a project-level `.mcp.json`, in the same
`mcpServers` schema Claude Code uses, in addition to `.github/mcp.json`. This repo does not rely on that, because
`.mcp.json` is Claude Code's file and carries Claude Code's `${VAR:-default}` substitution syntax. The Copilot CLI
has no substitution engine of its own for project-level files, so it would read a placeholder such as
`${CONTEXT7_API_KEY:-}` as a literal string rather than resolving it, which is a broken header, not an empty one.
`.github/mcp.json` exists so the CLI has a file written in its own literal-values-only schema instead.

Shipping both files side by side has a real, measured consequence worth knowing before you rely on it. The Copilot
CLI documents its own precedence rule: when `.mcp.json` and `.github/mcp.json` exist in the same directory and
define a server with the same name, `.mcp.json` wins. All eight servers in this repo share their name across both
files, so as things stand the CLI resolves every one of them from `.mcp.json`, not from `.github/mcp.json`. Verified
directly against Copilot CLI 1.0.81 with both files present: `copilot mcp get context7 --json` reports
`"sourcePath": "/work/project/.mcp.json"` and a `headers` block holding the literal, unresolved string
`${CONTEXT7_API_KEY:-}`. Removing `.mcp.json` from the same directory made the same command report
`"sourcePath": "/work/project/.github/mcp.json"` with no `headers` block at all, the correct unauthenticated
default. There is no Copilot CLI flag or setting that disables one workspace source while keeping the other; the
options that exist (`--disable-mcp-server=NAME`, `/mcp disable NAME`) disable a named server in the CLI's own
persisted configuration, not a source file. Until `.mcp.json` and `.github/mcp.json` stop naming the same eight
servers, `.github/mcp.json` is present, correct, and shadowed.

One catch with the shared OpenCode and Kilo file. Kilo Code accepts `opencode.json` as a valid project config
filename, which is why one file serves both. Kilo does not merely leave `{env:VAR}` literal, which is what this
guide used to say. It treats an environment reference in project-level config as a fatal error and throws the whole
file away:

```text
Configuration is invalid at ./opencode.json: environment references are not allowed in project config: "{env:GRAFANA_SERVICE_ACCOUNT_TOKEN}"
```

After that message Kilo lists no MCP servers from the file at all, and it also loses the `plugin` array in the same
file, which is what declares the preflight gate. One token would leave Kilo running with no servers and no gate. Kilo
discards only the offending file and keeps the rest of its configuration chain, so nothing else breaks with it.

An environment or file reference inside an MCP `headers` block is treated more gently. Kilo drops just that one server
and reports it as a skip, but `kilocode config check` still exits non-zero, so it is not a state worth shipping
either.

The shipped [opencode.json](../opencode.json) therefore contains no `{env:VAR}` and no `{file:...}` token anywhere,
and its `context7` block carries no `headers` at all. Nothing is lost for a local server, because OpenCode and Kilo
both start it with the environment of the process that started the agent, and an `environment` block in the config is
merged on top of that rather than replacing it. Exporting the variable is enough.

The one value that cannot arrive that way is the Context7 API key, because it travels as an HTTP header on a remote
server rather than in the server process environment. If you have a paid Context7 key, put the whole `context7` block
into your own global config (`~/.config/opencode/opencode.json` for OpenCode, `~/.config/kilo/kilo.jsonc` for Kilo
Code), which is trusted config and does expand `{env:VAR}`. It cannot live in a project file: Kilo rejects any project
file that holds an environment reference, and it would throw away the MCP block and the `plugin` array declaring the
preflight gate along with it. Without the global block, both tools talk to Context7 on the free tier, which is the
shipped default.

---

### Default servers

| Server | Purpose | External dependency |
| --- | --- | --- |
| `context7` | Up-to-date library documentation lookup | none, hosted, free tier without a key |
| `mongodb` | Read-only MongoDB introspection | a running MongoDB, development only, never production |
| `grafana` | Grafana dashboards, queries, alerts | a Grafana instance plus a service-account token |
| `playwright` | Cross-browser automation for UI tests | downloads roughly 500 MB of browsers on first run |
| `chrome-devtools` | Performance, network, and console debugging | Chrome installed locally |
| `redis` | Redis cache and queue introspection | a running Redis, development only |
| `sonarqube` | Code-quality issue lookup | Docker plus a SonarQube instance and token |
| `n8n` | n8n workflow node documentation, optional control | none for documentation only, instance plus key for control |

Turn off a server you do not use. In [opencode.json](../opencode.json) set `"enabled": false` on its block. In
[.mcp.json](../.mcp.json), [.vscode/mcp.json](../.vscode/mcp.json), [.codex/config.toml](../.codex/config.toml), and
[.github/mcp.json](../.github/mcp.json) delete the block, because those schemas have no enable flag. A server you
never disable still spawns and still fills your log with authentication failures.

---

### Step 1, install prerequisites

`npx` ships with Node.js. Check it is there.

PowerShell:

```powershell
node --version
```

Unix shell:

```bash
node --version
```

`uv` runs the `grafana` and `redis` servers.

Windows, PowerShell:

```powershell
winget install --id=astral-sh.uv
```

Linux or macOS:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Docker runs the `sonarqube` server.

PowerShell:

```powershell
docker --version
```

Unix shell:

```bash
docker --version
```

The backing services (`mongodb`, `grafana`, `redis`, `sonarqube`, `n8n`) have to be running before their server can
connect. If you do not have one, disable that server rather than leaving it to fail.

---

### Step 2, acquire keys

Only for the servers you actually use. Nothing is required for the config files to parse: [.mcp.json](../.mcp.json)
has a fallback for every variable, and the other four hardcode their defaults.

| Key | Where to get it | Needed when |
| --- | --- | --- |
| `CONTEXT7_API_KEY` | [Context7 dashboard](https://context7.com/dashboard) | you want the paid tier or higher rate limits |
| `GRAFANA_SERVICE_ACCOUNT_TOKEN` | Grafana, Administration, Service accounts, add account, add token | you use the grafana server |
| `SONARQUBE_TOKEN` | SonarQube, My Account, Security, Generate Token | you use the sonarqube server |
| `N8N_API_KEY` | n8n, Settings, API, Create API key | you want n8n workflow management, not just docs |

Use read-only or least-privilege tokens. A Grafana service account needs `Viewer` for dashboards, and `Editor` only
if you want the agent to create alerts. A SonarQube token needs `Execute Analysis` only if you also write
code-quality results back, otherwise read-only is enough.

---

### Step 3, set environment variables system-wide

Prefer system-wide variables over per-shell ones, so every agent inherits them: Claude Code, OpenCode, Codex, the Kilo
command-line client, the JetBrains plugins, and graphical applications alike.

#### Windows

Set persistently for the current user. New processes see it after a restart.

```powershell
[Environment]::SetEnvironmentVariable('CONTEXT7_API_KEY', 'ctx7_xxxxxxxxxxxx', 'User')
```

System-wide, which needs an Administrator shell:

```powershell
[Environment]::SetEnvironmentVariable('CONTEXT7_API_KEY', 'ctx7_xxxxxxxxxxxx', 'Machine')
```

Check it in a fresh PowerShell session:

```powershell
$env:CONTEXT7_API_KEY
```

Restart your terminal, your editor, and any running agent shell after changing a system variable.

#### Linux

Append to `/etc/environment` for all users:

```bash
echo 'CONTEXT7_API_KEY=ctx7_xxxxxxxxxxxx' | sudo tee -a /etc/environment
```

Or to `~/.profile` for your user only:

```bash
echo 'GRAFANA_SERVICE_ACCOUNT_TOKEN=glsa_xxxxxxxxxxxx' >> ~/.profile
```

Log out and back in to apply either one. For interactive shells only, append an `export` line to `~/.bashrc` or
`~/.zshrc`:

```bash
export CONTEXT7_API_KEY=ctx7_xxxxxxxxxxxx
```

#### macOS

Append to `~/.zprofile`, which Terminal and anything started from it will load:

```bash
echo 'export CONTEXT7_API_KEY=ctx7_xxxxxxxxxxxx' >> ~/.zprofile
```

For applications launched from Finder, set it through `launchctl`:

```bash
launchctl setenv CONTEXT7_API_KEY ctx7_xxxxxxxxxxxx
```

`launchctl` values do not survive a reboot on their own. Persist them with a
`~/Library/LaunchAgents/setenv.<name>.plist` entry, or scope them per project with [direnv](https://direnv.net/).

---

### Step 4, variables you can override

Every variable here is optional. The defaults are already in the files, either as `${VAR:-default}` in
[.mcp.json](../.mcp.json) or as hardcoded literals in the other four. Set one only when you need a non-default host
or a real token.

| Variable | Used by | Effect when unset |
| --- | --- | --- |
| `CONTEXT7_API_KEY` | `context7`, and only from a global OpenCode or Kilo config, never from a project file | no header sent, Context7 free tier |
| `MONGODB_URL` | `mongodb` | falls back to `mongodb://localhost:27017` |
| `GRAFANA_URL` | `grafana` | falls back to `http://localhost:3000` |
| `GRAFANA_SERVICE_ACCOUNT_TOKEN` | `grafana` | token sent empty, Grafana rejects the connection |
| `REDIS_URL` | `redis` | falls back to `redis://localhost:6379/0` |
| `SONARQUBE_TOKEN` | `sonarqube` | token sent empty, SonarQube rejects the connection |
| `SONARQUBE_URL` | `sonarqube` | falls back to `http://localhost:9000` |
| `N8N_API_URL` | `n8n` | falls back to `http://localhost:5678` |
| `N8N_API_KEY` | `n8n` | the n8n server runs in documentation-only mode |

The asymmetry between the files matters when you are debugging. Only [.mcp.json](../.mcp.json) supports a default
fallback, so only it resolves cleanly with nothing set. [opencode.json](../opencode.json),
[.vscode/mcp.json](../.vscode/mcp.json), [.codex/config.toml](../.codex/config.toml), and
[.github/mcp.json](../.github/mcp.json) hardcode their URLs, because `{env:VAR}` and `${env:VAR}` have no fallback
syntax, TOML has no substitution at all, and the Copilot CLI's own project-file schema has none either. To point one
of those at a different host, edit the literal string in your local copy. OpenCode also accepts
`OPENCODE_CONFIG_CONTENT` for a session-scoped override.

`opencode.json` goes one step further and carries no references at all, not even ones without a fallback, because a
single `{env:VAR}` makes Kilo Code reject the file. Every token it used to name is now read from the environment by
the server process itself.

`.github/mcp.json` cannot rely on that same inheritance for a secret. A local (`"type": "local"`) server under the
Copilot CLI only receives `PATH` from the process that started the CLI; the CLI's own documentation states that
every other environment variable a server needs must be listed explicitly in the server's `env` object in the config
file. Exporting `GRAFANA_SERVICE_ACCOUNT_TOKEN`, `SONARQUBE_TOKEN`, or `N8N_API_KEY` system-wide, the way Step 3
above recommends, reaches the same server under Claude Code, OpenCode, Kilo Code, and Codex, but does not reach it
under the Copilot CLI, because `.github/mcp.json` deliberately omits those three keys to avoid committing a secret.
Authenticating one of those servers for the Copilot CLI specifically means adding the real value to that key in your
own local, uncommitted copy of `.github/mcp.json`, the same way [Claude Desktop](#claude-desktop) below needs a
literal value because it has no substitution either.

An unset token variable is a local, noisy failure and nothing worse: that one server fails to authenticate and the
rest keep working.

---

### Step 5, the surfaces with no project file

Four configurations that live per machine or per repository setting, and therefore ship in this document rather than
in the tree.

#### GitHub Copilot in JetBrains

Path: `~/.config/github-copilot/intellij/mcp.json`, or
`%USERPROFILE%\.config\github-copilot\intellij\mcp.json` on Windows. Global only, no per-project equivalent. Schema key
`servers`, same as the VS Code file, but remote servers nest their authentication under `requestInit.headers` and need
a personal access token, because the JetBrains plugin does not do OAuth yet. Placeholder substitution is unconfirmed,
so paste literal values and keep the file out of version control.

```json
{
  "servers": {
    "context7": {
      "url": "https://mcp.context7.com/mcp",
      "requestInit": {
        "headers": {
          "CONTEXT7_API_KEY": "ctx7_actual_value_here"
        }
      }
    }
  }
}
```

#### GitHub Copilot cloud agent

The cloud agent has no file in the repository. Open the repository on GitHub, go to Settings, Copilot, then Coding
agent, and paste the JSON into the MCP configuration box. Same shape as the VS Code file, keyed `servers`, with
literal values and no substitution. Secrets go into the repository or organisation Copilot secrets, not into the JSON.

```json
{
  "servers": {
    "context7": {
      "type": "http",
      "url": "https://mcp.context7.com/mcp",
      "tools": ["*"]
    }
  }
}
```

#### Claude Code user-global

Path: `~/.claude.json`, same `mcpServers` schema and same `${VAR}` substitution as the project file. It applies when
you work outside a project that defines its own [.mcp.json](../.mcp.json), and the project file wins on a name
collision. If the file already exists, merge the `mcpServers` block by hand, because Claude Code keeps other top-level
keys in there too.

To populate it from the project file, PowerShell:

```powershell
Copy-Item .mcp.json $HOME\.claude.json
```

Unix shell:

```bash
cp .mcp.json ~/.claude.json
```

#### Claude Desktop

Paths: `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS,
`%APPDATA%\Claude\claude_desktop_config.json` on Windows. There is no official Linux build. Same `mcpServers` schema,
but no environment-variable substitution at all, so replace every `${VAR}` with the real value. The file is
personal to the machine, so inlining is fine. Never commit it.

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

Claude Desktop must be fully quit from the system tray and relaunched after an edit, not just closed.

#### Codex and Copilot CLI globals

Codex reads `~/.codex/config.toml` for global scope, in the same TOML shape as the project file:

```toml
[mcp_servers.context7]
command = "npx"
args = ["-y", "@upstash/context7-mcp@latest"]
```

Codex has no built-in substitution. To keep a secret out of the file, wrap the command in a small script that reads it
from your secrets manager.

The Copilot CLI reads [.github/mcp.json](../.github/mcp.json), the file this repo ships for it, plus
[.mcp.json](../.mcp.json), the same file Claude Code reads, because its own documentation names both as valid
per-project sources. When both name the same server, as all eight do here, the CLI's own precedence rule makes
`.mcp.json` win, so see [What ships](#what-ships) above for what that means in practice before assuming
`.github/mcp.json` is the file actually in effect. Project-level sources, both of them, load only once you confirm
you trust the directory on first launch and are silently skipped otherwise; there is no flag to skip that prompt for
`copilot mcp list` itself. For servers you want available everywhere, the CLI also reads
`~/.copilot/mcp-config.json` (relocatable with `COPILOT_HOME`), keyed `mcpServers`, with a `tools` allowlist per
server, no directory-trust requirement, and no substitution. Keep that one out of version control too.

---

### Substitution support matrix

Useful when a variable is stubbornly not being picked up.

| File | Substitution syntax | Applies to |
| --- | --- | --- |
| `.mcp.json` and `~/.claude.json`, Claude Code | `${VAR}`, `${VAR:-default}` | `command`, `args`, `env`, `url`, `headers` |
| `.mcp.json`, GitHub Copilot CLI | none, literal only | inline literals, and this repo ships `.github/mcp.json` instead so this row should not matter, see the precedence caveat above |
| `.github/mcp.json`, GitHub Copilot CLI | none, literal only | inline literals |
| `opencode.json`, OpenCode | `{env:VAR}` | any string value in an MCP block, though the shipped file uses none |
| `opencode.json`, Kilo Code | none at project level, and one token invalidates the whole file | inline literals only |
| `~/.config/opencode/opencode.json`, OpenCode global | `{env:VAR}` | any string value, global config is trusted |
| `~/.config/kilo/kilo.jsonc`, Kilo Code global | `{env:VAR}` | any string value, global config is trusted |
| `.vscode/mcp.json`, Copilot in VS Code | `${env:VAR}`, `${input:NAME}` | any string value in a server block |
| JetBrains global `mcp.json` | none documented | inline literals, token in `requestInit.headers` |
| Copilot cloud agent, settings page | none | inline literals plus Copilot secrets |
| `claude_desktop_config.json` | not supported | inline literals |
| `.codex/config.toml` and `~/.codex/config.toml` | none, TOML has no substitution | inline literals |

---

### Verifying the setup

Restart the agent after editing configs or exporting variables, then check.

- Claude Code: run `claude mcp list` and read which servers loaded.
- OpenCode: start it and run `/mcp`, or read the connection lines in the startup log.
- Kilo Code: run `kilocode config check` first, which prints nothing but `No config warnings.` when the project
  config is accepted, then open the MCP Servers panel in settings, under agent behaviour, where each server shows
  connected or error. `kilocode mcp list` answers the same question from a terminal.
- Codex: start `codex` and run `/mcp`. Remember the project layer loads only after you trust the project.
- Copilot in VS Code: open Chat, switch to agent mode, open the tools picker. Every server in
  [.vscode/mcp.json](../.vscode/mcp.json) appears with its tools and a start or stop control.
- Copilot CLI: start `copilot` and run `/mcp`, or run `copilot mcp list` from a terminal. Either way, project-level
  sources load only after you confirm you trust the directory on first launch; an untrusted directory reports
  `No MCP servers configured.` even with both files present and valid.
- Claude Desktop: open the developer panel, or check the indicator in the input box.

When a server fails to connect, Claude Code writes the reason to its standard log, and Claude Desktop writes per-server
standard-error output to `mcp-server-<name>.log` under `~/Library/Logs/Claude/` on macOS or `%APPDATA%\Claude\logs\`
on Windows.

---

### Adding or changing a server

Edit all five project files together: [.mcp.json](../.mcp.json), [opencode.json](../opencode.json), the
`[mcp_servers]` tables in [.codex/config.toml](../.codex/config.toml), [.vscode/mcp.json](../.vscode/mcp.json), and
[.github/mcp.json](../.github/mcp.json). Then update the two manual blocks in this document, the JetBrains one and the
cloud-agent one, which ship no file.

Keep the server set identical across all of them. Only the per-schema syntax is allowed to differ.

To customise a single project without touching upstream, edit its local copies directly. These five files are
consumer-owned, so the routine update flow leaves every one of them alone. Picking up an upstream server change is a
deliberate, separate step, with its own diff-and-checkout command at the end of each shell section of
[AGENTS-UPDATE.md](AGENTS-UPDATE.md). That command covers all six configuration files together: the five MCP
files, [.mcp.json](../.mcp.json), [opencode.json](../opencode.json), [.vscode/mcp.json](../.vscode/mcp.json),
[.github/mcp.json](../.github/mcp.json), and [.codex/config.toml](../.codex/config.toml), plus the unrelated
[.claude/settings.json](../.claude/settings.json). Diff before you run it, because it replaces every one of those
files wholesale.
