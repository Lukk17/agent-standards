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
| [.mcp.json](../.mcp.json) | `mcpServers` | Claude Code and the GitHub Copilot CLI | holds `context7` alone, `"type": "http"` for remote, `"type": "stdio"` for local |
| [opencode.json](../opencode.json) | `mcp` | OpenCode and Kilo Code | `"type": "remote"` or `"type": "local"`, sits at the project root |
| [.codex/config.toml](../.codex/config.toml) | `[mcp_servers.*]` | Codex | TOML, also carries the preflight hook tables |
| [.vscode/mcp.json](../.vscode/mcp.json) | `servers` | GitHub Copilot in VS Code | key is `servers`, not `mcpServers` |
| [.github/mcp.json](../.github/mcp.json) | `mcpServers` | the GitHub Copilot CLI, only in a folder that has no `.mcp.json` | a fallback, `"type": "http"` for remote, `"type": "local"` for a stdio server |

The five files do not carry the same set. [.mcp.json](../.mcp.json) holds `context7` alone, and the other four hold the full set with the exceptions below.

[.mcp.json](../.mcp.json) is short because Claude Code starts every server in it, in every chat of every project that imports it. With the nine servers the file held before, one chat started 8 local processes and one image pull and loaded 303 tools, and five of those servers need a service most projects do not run. So Claude Code starts one hosted server by default, and a project adds each other server it uses, as [Adding a server to Claude Code](#adding-a-server-to-claude-code) shows. All nine stay available to Claude Code as plugins.

The Copilot CLI reads the same file, so in a folder that has `.mcp.json` it gets `context7` alone as well. A project that runs the Copilot CLI and wants the full set either adds the servers to its `.mcp.json`, which both tools then read, or leaves `.mcp.json` out, and the CLI then reads [.github/mcp.json](../.github/mcp.json), as [the next section](#the-cli-mcpjson-and-why-a-fifth-file-exists) describes.

The other four files carry one server set, with two exceptions. [opencode.json](../opencode.json) also carries `atlassian`. Only [.vscode/mcp.json](../.vscode/mcp.json) carries `home-assistant`. [.github/mcp.json](../.github/mcp.json) leaves it out, because its schema has no enable flag to ship it switched off, and a Copilot CLI project that uses the server adds it to its `.mcp.json`. [opencode.json](../opencode.json) and [.codex/config.toml](../.codex/config.toml) leave it out too, because their project files cannot hold a path that works on every machine, so a project that uses the server on OpenCode, Kilo Code or Codex declares it in its own copy of those two files. The reasons are under [Home Assistant server](#home-assistant-server). Only the file name, the schema key, the `type` value, and the
environment-variable syntax change between them. The V1 shape in [opencode.json](../opencode.json), flat `mcp` plus `enabled`, loads on OpenCode 1.x and on 2.0.26, measured 2026-10-15: `opencode plugin list` from the repo shows the repo plugin, and `opencode debug config` shows the same file as `mcp.servers` plus `disabled`. V2 keeps the V1 file working by change in memory. There is no per-tool overlay beyond these five: one file per agent
surface, and that is the whole set.

Two surfaces get no shipped file, because there is nothing a repository could ship that they would read:

- GitHub Copilot in JetBrains reads MCP only from the global path `~/.config/github-copilot/intellij/mcp.json`
  (`%USERPROFILE%\.config\github-copilot\intellij\mcp.json` on Windows). There is no per-project MCP file for that
  plugin, and GitHub documents only the in-IDE screen (Settings, Tools, GitHub Copilot, Model Context Protocol), not
  the path, so treat the path itself as community knowledge rather than official. Manual block below.
- The GitHub Copilot cloud agent takes its MCP configuration as JSON pasted into a page in the repository
  settings, not from a file in the tree. Manual block below.

Of Copilot's four surfaces, VS Code reads [.vscode/mcp.json](../.vscode/mcp.json), the CLI reads
[.mcp.json](../.mcp.json), and the other two are manual. The CLI reads [.github/mcp.json](../.github/mcp.json) only in
a folder that has no `.mcp.json`.

#### The CLI, `.mcp.json`, and why a fifth file exists

The GitHub Copilot CLI reads the project `.mcp.json`, the same file and the same `mcpServers` schema Claude Code uses. When it starts a server it expands `$VAR`, `${VAR}` and `${VAR:-default}` in `command`, `args`, `env`, `url` and `headers`, measured on 1.0.103 on 2026-10-25. So the `${VAR:-default}` entries in `.mcp.json` work for the CLI the same way they work for Claude Code. Two cases need care when a variable is not set:

1. `${VAR}` with no default stays the literal text `${VAR}`.
2. `${VAR:-}` gives an empty value. For `context7` with no `CONTEXT7_API_KEY`, the CLI sends an empty `CONTEXT7_API_KEY` header, not the literal text. How Context7 answers an empty header was not measured.

The CLI reference lists expansion only for a local server's `env`, "Supports `$VAR`, `${VAR}`, and `${VAR:-default}` expansion", and for a remote server's `headers`, "Supports variable expansion." ([CLI command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference), "Local server configuration fields" and "Remote server configuration fields", read 2026-10-25). The measurement shows that `command`, `args` and `url` expand too. Do not check a value with `copilot mcp get NAME --json`: it prints the text of the file as written, so it does not show what the server receives.

The CLI reads one project file per folder, not one entry per server name. The vendor page says "If both `.mcp.json` and `.github/mcp.json` exist in the same directory, `.mcp.json` takes precedence." ([Adding MCP servers for GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers), read 2026-10-25). Measured on 1.0.103 on 2026-10-25 with both files in one folder, the CLI did not read `.github/mcp.json` at all: a server defined only there was missing, and `copilot mcp get gh-local --json` printed `Error: Server "gh-local" not found.`. With `.mcp.json` removed, the servers of `.github/mcp.json` appeared, with `sourcePath` set to `.github/mcp.json`.

So [.github/mcp.json](../.github/mcp.json) is kept only as a fallback. The CLI reads it only in a folder that has no `.mcp.json`, for example a project that pulled the Copilot files from this repository but not `.mcp.json`. In this repository, and in every project that has both files, the CLI never reads it, and gets only the servers `.mcp.json` holds.

Every local server the CLI starts also receives the whole environment of the process that started the CLI, tokens for other servers included. [Step 4](#step-4-variables-you-can-override) says what that means.

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

The one value that cannot arrive that way is the Context7 API key, because it travels as an HTTP header on a remote server rather than in the server process environment. It cannot live in a project file: Kilo rejects any project file that holds an environment reference, and it would throw away the MCP block and the `plugin` array declaring the preflight gate along with it. A global config could expand it, but no server goes into a global config, as [Where a server is declared](#where-a-server-is-declared) explains. So OpenCode and Kilo Code talk to Context7 on the free tier, which is the shipped default, while Claude Code and the Copilot CLI send your key from [.mcp.json](../.mcp.json).

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
| `home-assistant` | Home Assistant control and configuration | a Home Assistant instance plus a long-lived access token of an administrator user that may log in only from the local network, both keys in the credential env file, see [Home Assistant server](#home-assistant-server) |

Every local server command in the five files names one exact release, as [Updating a pinned server](#updating-a-pinned-server) explains.

The `n8n` block sets `N8N_MCP_TELEMETRY_DISABLED` to `"true"` in every place that carries the server: the four files beside [.mcp.json](../.mcp.json), the `mcp-n8n` plugin and the `claude mcp add` command under [Adding a server to Claude Code](#adding-a-server-to-claude-code). The n8n-mcp package sends usage data by default and writes `"enabled": true` to `~/.n8n-mcp/telemetry.json` on its first run. In n8n-mcp 2.102.0, the release every file pins, read 2026-11-24, `isEnabled` in `dist/telemetry/config-manager.js` calls `isDisabledByEnvironment` before it reads that file, so the variable turns usage data off whatever the file says, and a first run with it set writes `"enabled": false`. It is a fixed value in every file, not a variable to override, so keep the line when you change your local copy.

Turn off a server you do not use. In [opencode.json](../opencode.json) set `"enabled": false` on its block, and in
[.codex/config.toml](../.codex/config.toml) set `enabled = false` in its table. In [.mcp.json](../.mcp.json),
[.vscode/mcp.json](../.vscode/mcp.json), and [.github/mcp.json](../.github/mcp.json) delete the block, because those
schemas have no enable flag. A server you never disable still spawns and still fills your log with authentication
failures.

Two commands do it from the project root, each naming the server at the end, here `mongodb`. The first sets the flag in the two files that have one and changes only that line, so the rest of each file stays as upstream wrote it. Unix shell:

```bash
python3 -c 'import re,sys;n=re.escape(sys.argv[1]);p="opencode.json";t=open(p,encoding="utf-8").read();open(p,"w",encoding="utf-8").write(re.sub(r"(\x22"+n+r"\x22: \{.*?\x22enabled\x22: )(?:true|false)",r"\1false",t,count=1,flags=re.S));p=".codex/config.toml";t=open(p,encoding="utf-8").read();open(p,"w",encoding="utf-8").write(re.sub(r"(?m)^(\[mcp_servers\."+n+r"\])$(?!\nenabled = false)",r"\1\nenabled = false",t))' mongodb
```

PowerShell 7.4 or later:

```powershell
python -c 'import re,sys;n=re.escape(sys.argv[1]);p="opencode.json";t=open(p,encoding="utf-8").read();open(p,"w",encoding="utf-8").write(re.sub(r"(\x22"+n+r"\x22: \{.*?\x22enabled\x22: )(?:true|false)",r"\1false",t,count=1,flags=re.S));p=".codex/config.toml";t=open(p,encoding="utf-8").read();open(p,"w",encoding="utf-8").write(re.sub(r"(?m)^(\[mcp_servers\."+n+r"\])$(?!\nenabled = false)",r"\1\nenabled = false",t))' mongodb
```

The second deletes the block from the three files without a flag. It writes each of them back with two-space indentation, which is fine because those three files are yours outright, as [AGENTS-UPDATE.md](AGENTS-UPDATE.md#what-this-skips-and-why) explains. Unix shell:

```bash
python3 -c 'import json,sys;n=sys.argv[1];[(lambda s:(s[k].pop(n,None),open(f,"w",encoding="utf-8").write(json.dumps(s,indent=2)+"\n")))(json.load(open(f,encoding="utf-8"))) for f,k in ((".mcp.json","mcpServers"),(".vscode/mcp.json","servers"),(".github/mcp.json","mcpServers"))]' mongodb
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,sys;n=sys.argv[1];[(lambda s:(s[k].pop(n,None),open(f,"w",encoding="utf-8").write(json.dumps(s,indent=2)+"\n")))(json.load(open(f,encoding="utf-8"))) for f,k in ((".mcp.json","mcpServers"),(".vscode/mcp.json","servers"),(".github/mcp.json","mcpServers"))]' mongodb
```

Check what changed, in either shell:

```bash
git diff --stat -- opencode.json .codex/config.toml .mcp.json .vscode/mcp.json .github/mcp.json
```

The agent-standards live pipeline, which runs every agent against a real model, loads `context7` alone. It has the
smallest tool descriptions of the shipped servers and needs no secret, and the descriptions of all of them together pushed a
single test past the provider's per-minute token limit. So only `context7` is proven to answer a real model there,
and the others are proven to be discovered by every agent, not to answer.

---

### Where a server is declared

Each project declares the MCP servers it uses in its own project files, and no server sits in a user-scope or global configuration file of any agent. Every chat starts its own copy of every server it loads, so a server at user scope runs once for each open chat in every project, whether that project uses it or not. As an example with round numbers: a local server that holds about 100 MB of memory per copy, kept at user scope while ten chats are open, holds about 1 GB, even when only one project ever calls it. Declared in that one project, it runs only in the chats opened there.

Where each agent reads the project's servers:

1. Claude Code reads `.mcp.json` at the project root, and `claude mcp add --scope project` writes it: "When you add a project-scoped server, Claude Code automatically creates or updates this file" ([MCP docs](https://code.claude.com/docs/en/mcp), "Project scope", read 2026-11-20). It asks once before it uses each server from that file, "For security reasons, Claude Code prompts for approval in interactive sessions before using project-scoped servers from `.mcp.json` files" (same section), and keeps your yes in `enabledMcpjsonServers`: "Claude Code writes this key to `.claude/settings.local.json` when you approve a server in the approval dialog" ([settings reference](https://code.claude.com/docs/en/settings-reference), "`enabledMcpjsonServers`", read 2026-11-20). That file counts only after you accept the workspace trust dialog in the folder (MCP docs, "Project server approvals and workspace trust"). A server that comes from a plugin is declared in the project only when the plugin is installed at project scope, with `claude plugin install <name>@agent-standards --scope project`, because a plugin at user scope starts its server in every project, as [Adding a server to Claude Code](#adding-a-server-to-claude-code) explains.
2. The Copilot CLI reads the same `.mcp.json`, in a trusted folder only, as [Verifying the setup](#verifying-the-setup) describes.
3. Copilot in VS Code reads `.vscode/mcp.json`.
4. OpenCode and Kilo Code read the `mcp` block of `opencode.json` at the project root, which holds no `{env:VAR}` token, as [What ships](#what-ships) explains.
5. Codex reads the `[mcp_servers.<name>]` tables of `.codex/config.toml` in the project, and only in a trusted project: "you can also scope MCP servers to a project with `.codex/config.toml` (trusted projects only)" ([MCP docs](https://learn.chatgpt.com/docs/extend/mcp), read 2026-11-20). `codex mcp add` has no project option and always writes the user file, so the commands in this guide write the project table themselves, above the first `[[hooks.` table, because an update replaces everything from that table to the end of the file, as [AGENTS-UPDATE.md](AGENTS-UPDATE.md) says under "Taking only the gate half".

Codex keeps trust in the user configuration, as the `projects.<path>.trust_level` key: "Untrusted projects skip project-scoped .codex/ layers, including project-local config, hooks, and rules" ([configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference), read 2026-11-20). A trust entry is not a server, so it belongs in `~/.config/codex/config.toml` under the layout in [GLOBAL_SETUP.md](GLOBAL_SETUP.md). For a project folder it reads, with the absolute path of that folder in place of `<project path>`:

```toml
[projects."<project path>"]
trust_level = "trusted"
```

Measured on 2026-11-20 with Codex 0.169.0: `codex mcp list` in a trusted project folder listed the servers of its `.codex/config.toml` as `enabled`, and in an untrusted folder whose `.codex/config.toml` held one server it printed `No MCP servers configured yet.`.

Remove what an older setup put at user scope, so the project entry is the only one. Claude Code, naming each server, in either shell:

```bash
claude mcp remove --scope user home-assistant
```

Codex, which edits the user file in the folder `CODEX_HOME` names, in either shell:

```bash
codex mcp remove home-assistant
```

OpenCode, Kilo Code and the Copilot CLI keep their user servers in JSON files, the Copilot one at its path under the layout in [GLOBAL_SETUP.md](GLOBAL_SETUP.md). This command removes the servers you name at the end, here `home-assistant` and `arch`, from each of the three files that exists and keeps every other key. Unix shell:

```bash
python3 -c 'import json,sys,pathlib;h=pathlib.Path.home();[(lambda p,k,s:([s.get(k,{}).pop(n,None) for n in sys.argv[1:]],p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")))(h/f,k,json.loads((h/f).read_text(encoding="utf-8"))) for f,k in ((".config/opencode/opencode.json","mcp"),(".config/kilo/kilo.jsonc","mcp"),(".config/copilot/mcp-config.json","mcpServers")) if (h/f).exists()]' home-assistant arch
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,sys,pathlib;h=pathlib.Path.home();[(lambda p,k,s:([s.get(k,{}).pop(n,None) for n in sys.argv[1:]],p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")))(h/f,k,json.loads((h/f).read_text(encoding="utf-8"))) for f,k in ((".config/opencode/opencode.json","mcp"),(".config/kilo/kilo.jsonc","mcp"),(".config/copilot/mcp-config.json","mcpServers")) if (h/f).exists()]' home-assistant arch
```

---

### Adding a server to Claude Code

[.mcp.json](../.mcp.json) starts `context7` alone. Each of the other eight servers comes into a project in one of two ways. Both declare it in the project and never at user scope, as [Where a server is declared](#where-a-server-is-declared) requires.

The first way is the server's own plugin from the marketplace, named `mcp-<server>`. Install it at project scope. User scope is the default of `claude plugin install`, and there "the plugin is enabled for you in every project on this machine" ([Install plugins](https://code.claude.com/docs/en/plugins/install), "Choose an install scope", read 2026-11-23), so its server would start in every chat of every project. The user scope is for plugins that carry no server, such as the `core` bundle in [GLOBAL_SETUP.md](GLOBAL_SETUP.md#claude-code), and never for an `mcp-<server>` plugin or `mcp-all`. Add the marketplace to the project once, from the project root, in either shell:

```bash
claude plugin marketplace add Lukk17/agent-standards --scope project
```

Then install the server, here `mongodb`:

```bash
claude plugin install mcp-mongodb@agent-standards --scope project
```

At project scope, "The entry goes in `.claude/settings.json`, which you commit" (same section), so everyone who works in the repository gets the same servers. Each of them runs the same install command once in their own clone, because committing the entry "doesn't download it to their machines". The plugins are `mcp-mongodb`, `mcp-grafana`, `mcp-playwright`, `mcp-chrome-devtools`, `mcp-redis`, `mcp-sonarqube`, `mcp-n8n` and `mcp-home-assistant`. `mcp-all` installs all nine servers, so use it only in a project that uses all of them. In a project that has the shipped `.mcp.json`, `mcp-context7` adds nothing: Claude Code "matches plugins and connectors by endpoint, so one that points at the same URL or command as an enabled server above counts as a duplicate" ([MCP docs](https://code.claude.com/docs/en/mcp), "Scope hierarchy and precedence", read 2026-11-23).

The second way is `claude mcp add --scope project`, which writes the block into the project's `.mcp.json`. Each command below writes the same block its plugin carries, measured with Claude Code 2.1.325 on 2026-11-23. The single quotes keep each `${VAR:-default}` as text, so the file holds it unchanged and Claude Code expands it when it starts the server. Run the ones you need from the project root, in either shell. MongoDB:

```bash
claude mcp add --scope project mongodb -- npx -y mongodb-mcp-server@3.3.0 --readOnly --connectionString '${MONGODB_URL:-mongodb://localhost:27017}'
```

Grafana:

```bash
claude mcp add --scope project grafana -e 'GRAFANA_URL=${GRAFANA_URL:-http://localhost:3000}' -e 'GRAFANA_SERVICE_ACCOUNT_TOKEN=${GRAFANA_SERVICE_ACCOUNT_TOKEN:-}' -- uvx mcp-grafana==2.2.0
```

Playwright:

```bash
claude mcp add --scope project playwright -- npx @playwright/mcp@0.0.85
```

Chrome DevTools:

```bash
claude mcp add --scope project chrome-devtools -- npx -y chrome-devtools-mcp@1.13.0
```

Redis:

```bash
claude mcp add --scope project redis -- uvx --from redis-mcp-server==0.5.1 redis-mcp-server --url '${REDIS_URL:-redis://localhost:6379/0}'
```

SonarQube:

```bash
claude mcp add --scope project sonarqube -e 'SONARQUBE_TOKEN=${SONARQUBE_TOKEN:-}' -e 'SONARQUBE_URL=${SONARQUBE_URL:-http://localhost:9000}' -- docker run --init -i --rm -e SONARQUBE_TOKEN -e SONARQUBE_URL sonarsource/sonarqube-mcp:1.32.0.5118
```

n8n:

```bash
claude mcp add --scope project n8n -e 'N8N_API_URL=${N8N_API_URL:-http://localhost:5678}' -e 'N8N_API_KEY=${N8N_API_KEY:-}' -e 'N8N_MCP_TELEMETRY_DISABLED=true' -- npx n8n-mcp@2.102.0
```

Home Assistant has its own section, [Home Assistant server](#home-assistant-server), because it needs a credential file first.

Start `claude` in the folder once and approve each server you added, as [Where a server is declared](#where-a-server-is-declared) describes. Use one way per server. A server that is in `.mcp.json` and also comes from a plugin is the duplicate described above. Take one out of `.mcp.json` again, in either shell:

```bash
claude mcp remove --scope project mongodb
```

Take a plugin out again, in either shell:

```bash
claude plugin uninstall mcp-mongodb@agent-standards --scope project
```

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

`uv` runs the `grafana`, `redis` and `home-assistant` servers.

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

The backing services (`mongodb`, `grafana`, `redis`, `sonarqube`, `n8n`, `home-assistant`) have to be running before their server can
connect. If you do not have one, disable that server rather than leaving it to fail.

The `sonarqube` server checks its instance when it starts, and needs SonarQube Server 2025.1 or SonarQube Community Build 25.1 or newer: "At startup, the MCP server reads the connected instance version and exits with an error if it is too old" ([sonarqube-mcp-server README](https://github.com/SonarSource/sonarqube-mcp-server), "SonarQube Server", read 2026-11-23). Measured with `sonarsource/sonarqube-mcp:1.32.0.5118` on 2026-11-23, it also answers `initialize` with an error and stops with exit code 1 when nothing answers at `SONARQUBE_URL`.

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
| `HOMEASSISTANT_TOKEN` | Home Assistant, signed in as the agent user, your profile, Security, Long-lived access tokens, Create token | you use the home-assistant server. It goes into the credential env file, never into Step 3, see [Home Assistant server](#home-assistant-server) |

Use read-only or least-privilege tokens. A Grafana service account needs `Viewer` for dashboards, and `Editor` only
if you want the agent to create alerts. A SonarQube token needs `Execute Analysis` only if you also write
code-quality results back, otherwise read-only is enough. It has to be a user token, because the connection "will not function properly if project tokens or global tokens are used" ([sonarqube-mcp-server README](https://github.com/SonarSource/sonarqube-mcp-server), "SonarQube Server", read 2026-11-23).

---

### Step 3, set environment variables system-wide

Prefer system-wide variables over per-shell ones, so every agent inherits them: Claude Code, OpenCode, Codex, the Kilo
command-line client, the JetBrains plugins, and graphical applications alike.

Every command below asks for the four keys from Step 2 in turn, through a hidden prompt, so a value is never typed on a command line and never lands in your shell history. Press Enter at a prompt to skip a key you do not use. No check below prints a value.

#### Windows

Set persistently for the current user. New processes see it after a restart. `-MaskInput` needs PowerShell 7.1 or later.

```powershell
foreach ($n in 'CONTEXT7_API_KEY', 'GRAFANA_SERVICE_ACCOUNT_TOKEN', 'SONARQUBE_TOKEN', 'N8N_API_KEY') { $v = Read-Host "$n, Enter to skip" -MaskInput; if ($v) { [Environment]::SetEnvironmentVariable($n, $v, 'User') } }; Remove-Variable v
```

System-wide, which needs an Administrator shell:

```powershell
foreach ($n in 'CONTEXT7_API_KEY', 'GRAFANA_SERVICE_ACCOUNT_TOKEN', 'SONARQUBE_TOKEN', 'N8N_API_KEY') { $v = Read-Host "$n, Enter to skip" -MaskInput; if ($v) { [Environment]::SetEnvironmentVariable($n, $v, 'Machine') } }; Remove-Variable v
```

Check it in a fresh PowerShell session. It prints each name with `True` when the variable holds a value, and never the value itself:

```powershell
'CONTEXT7_API_KEY', 'GRAFANA_SERVICE_ACCOUNT_TOKEN', 'SONARQUBE_TOKEN', 'N8N_API_KEY' | ForEach-Object { "$_ $([bool][Environment]::GetEnvironmentVariable($_))" }
```

Restart your terminal, your editor, and any running agent shell after changing a system variable.

#### Linux

Append to `/etc/environment` for all users. Every account on the machine can read that file, so use it only on a machine where you are the one user:

```bash
for n in CONTEXT7_API_KEY GRAFANA_SERVICE_ACCOUNT_TOKEN SONARQUBE_TOKEN N8N_API_KEY; do printf '%s, Enter to skip: ' "$n"; IFS= read -rs v; echo; [ -n "$v" ] && printf '%s=%s\n' "$n" "$v" | sudo tee -a /etc/environment >/dev/null; done; unset v
```

Check it. It prints the line number and the name of each key it holds, never the value:

```bash
grep -n -o -E '^(CONTEXT7_API_KEY|GRAFANA_SERVICE_ACCOUNT_TOKEN|SONARQUBE_TOKEN|N8N_API_KEY)=' /etc/environment
```

Or to `~/.profile` for your user only. The `export` makes each value reach the programs your login shell starts:

```bash
for n in CONTEXT7_API_KEY GRAFANA_SERVICE_ACCOUNT_TOKEN SONARQUBE_TOKEN N8N_API_KEY; do printf '%s, Enter to skip: ' "$n"; IFS= read -rs v; echo; [ -n "$v" ] && printf "export %s='%s'\n" "$n" "$v" >> ~/.profile; done; unset v
```

Check it:

```bash
grep -n -o -E '^export (CONTEXT7_API_KEY|GRAFANA_SERVICE_ACCOUNT_TOKEN|SONARQUBE_TOKEN|N8N_API_KEY)=' ~/.profile
```

Log out and back in to apply either one. For interactive shells only, append the same `export` lines to `~/.zshrc` or `~/.bashrc` instead. For zsh:

```bash
for n in CONTEXT7_API_KEY GRAFANA_SERVICE_ACCOUNT_TOKEN SONARQUBE_TOKEN N8N_API_KEY; do printf '%s, Enter to skip: ' "$n"; IFS= read -rs v; echo; [ -n "$v" ] && printf "export %s='%s'\n" "$n" "$v" >> ~/.zshrc; done; unset v
```

For bash:

```bash
for n in CONTEXT7_API_KEY GRAFANA_SERVICE_ACCOUNT_TOKEN SONARQUBE_TOKEN N8N_API_KEY; do printf '%s, Enter to skip: ' "$n"; IFS= read -rs v; echo; [ -n "$v" ] && printf "export %s='%s'\n" "$n" "$v" >> ~/.bashrc; done; unset v
```

Check it:

```bash
grep -n -o -E '^export (CONTEXT7_API_KEY|GRAFANA_SERVICE_ACCOUNT_TOKEN|SONARQUBE_TOKEN|N8N_API_KEY)=' ~/.zshrc ~/.bashrc 2>/dev/null
```

`read -s` hides what you type in bash and zsh. A value that itself holds a single quote would break its quoted `export` line, which no Context7, Grafana, SonarQube or n8n key does.

#### macOS

Append to `~/.zprofile`, which Terminal and anything started from it will load:

```bash
for n in CONTEXT7_API_KEY GRAFANA_SERVICE_ACCOUNT_TOKEN SONARQUBE_TOKEN N8N_API_KEY; do printf '%s, Enter to skip: ' "$n"; IFS= read -rs v; echo; [ -n "$v" ] && printf "export %s='%s'\n" "$n" "$v" >> ~/.zprofile; done; unset v
```

Check it:

```bash
grep -n -o -E '^export (CONTEXT7_API_KEY|GRAFANA_SERVICE_ACCOUNT_TOKEN|SONARQUBE_TOKEN|N8N_API_KEY)=' ~/.zprofile
```

For applications launched from Finder, set them through `launchctl`. This command reads the values from `~/.zprofile` in a login shell, so you never type them again, and sets each key that holds a value. `launchctl setenv` takes a value as an argument, so it shows in the process list for the moment the command runs, though never in your shell history:

```bash
zsh -lc 'for v in CONTEXT7_API_KEY GRAFANA_SERVICE_ACCOUNT_TOKEN SONARQUBE_TOKEN N8N_API_KEY; do if [ -n "${(P)v}" ]; then launchctl setenv "$v" "${(P)v}"; fi; done'
```

Check it. It prints each name with the number of characters in its value, and never the value:

```bash
for v in CONTEXT7_API_KEY GRAFANA_SERVICE_ACCOUNT_TOKEN SONARQUBE_TOKEN N8N_API_KEY; do printf '%s %s\n' "$v" "$(launchctl getenv "$v" | tr -d '\n' | wc -c)"; done
```

`launchctl` values do not survive a reboot on their own. To set them at every login, write a LaunchAgent that runs the same command. It holds no secret, because it reads `~/.zprofile` each time it runs. Create its folder:

```bash
mkdir -p ~/Library/LaunchAgents
```

Write the file. The quotes around `EOF` keep the shell from changing anything inside it:

```bash
tee ~/Library/LaunchAgents/local.mcp.environment.plist >/dev/null <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>local.mcp.environment</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-lc</string>
    <string>for v in CONTEXT7_API_KEY GRAFANA_SERVICE_ACCOUNT_TOKEN SONARQUBE_TOKEN N8N_API_KEY; do if [ -n "${(P)v}" ]; then launchctl setenv "$v" "${(P)v}"; fi; done</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
</dict>
</plist>
EOF
```

Check that the file is valid. It prints the path followed by `OK`:

```bash
plutil -lint ~/Library/LaunchAgents/local.mcp.environment.plist
```

Load it once now, and launchd loads it at every login after:

```bash
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/local.mcp.environment.plist
```

None of the macOS commands was run on a Mac for this guide. You can also scope a variable per project with [direnv](https://direnv.net/).

---

### Step 4, variables you can override

Every variable here is optional. The defaults are already in place, either as `${VAR:-default}` in
[.mcp.json](../.mcp.json), in the server plugins and in the commands under [Adding a server to Claude Code](#adding-a-server-to-claude-code), or as hardcoded literals in the other four files. Set one only when you need a non-default host
or a real token.

| Variable | Used by | Effect when unset |
| --- | --- | --- |
| `CONTEXT7_API_KEY` | `context7`, from [.mcp.json](../.mcp.json) for Claude Code and the Copilot CLI, and never for OpenCode and Kilo Code, which use the free tier, as [What ships](#what-ships) explains | Context7 free tier. The Copilot CLI then sends the header with an empty value, measured on 1.0.103 on 2026-10-25, and how Context7 answers that was not measured |
| `MONGODB_URL` | `mongodb` | falls back to `mongodb://localhost:27017` |
| `GRAFANA_URL` | `grafana` | falls back to `http://localhost:3000` |
| `GRAFANA_SERVICE_ACCOUNT_TOKEN` | `grafana` | token sent empty, Grafana rejects the connection |
| `REDIS_URL` | `redis` | falls back to `redis://localhost:6379/0` |
| `SONARQUBE_TOKEN` | `sonarqube` | the server stops when it starts, with `SONARQUBE_TOKEN environment variable or property must be set` and exit code 1, measured with `sonarsource/sonarqube-mcp:1.32.0.5118` on 2026-11-23 |
| `SONARQUBE_URL` | `sonarqube` | falls back to `http://localhost:9000` |
| `N8N_API_URL` | `n8n` | falls back to `http://localhost:5678` |
| `N8N_API_KEY` | `n8n` | the n8n server runs in documentation-only mode |

The asymmetry between the files matters when you are debugging. [.mcp.json](../.mcp.json) is the only file that uses a default fallback, in its `context7` block and in every block the commands above add to it, so it resolves cleanly with nothing set, for Claude Code and for the Copilot CLI alike. [opencode.json](../opencode.json),
[.vscode/mcp.json](../.vscode/mcp.json) and [.codex/config.toml](../.codex/config.toml) hardcode their URLs, because `{env:VAR}` and `${env:VAR}` have no fallback
syntax and TOML has no substitution at all. [.github/mcp.json](../.github/mcp.json) hardcodes them too. The Copilot CLI would expand `${VAR:-default}` there as well, measured on 1.0.103 on 2026-10-25, but it reads that file only in a folder that has no `.mcp.json`. To point one
of those at a different host, change the literal string in your local copy. OpenCode also accepts
`OPENCODE_CONFIG_CONTENT` for a session-scoped override.

One command changes the string in all four files from the project root, and nothing else in them. The last two words are the address the files hold now and the one you want, so put your own host in place of `http://grafana.lan:3000`. Unix shell:

```bash
python3 -c 'import sys;[(lambda t:open(f,"w",encoding="utf-8").write(t.replace(sys.argv[1],sys.argv[2])))(open(f,encoding="utf-8").read()) for f in ("opencode.json",".vscode/mcp.json",".codex/config.toml",".github/mcp.json")]' http://localhost:3000 http://grafana.lan:3000
```

PowerShell 7.4 or later:

```powershell
python -c 'import sys;[(lambda t:open(f,"w",encoding="utf-8").write(t.replace(sys.argv[1],sys.argv[2])))(open(f,encoding="utf-8").read()) for f in ("opencode.json",".vscode/mcp.json",".codex/config.toml",".github/mcp.json")]' http://localhost:3000 http://grafana.lan:3000
```

Check what changed, in either shell:

```bash
git diff -- opencode.json .vscode/mcp.json .codex/config.toml .github/mcp.json
```

`opencode.json` goes one step further and carries no references at all, not even ones without a fallback, because a
single `{env:VAR}` makes Kilo Code reject the file. Every token it used to name is now read from the environment by
the server process itself.

The Copilot CLI passes on more than its vendor page says. The page says "The `PATH` variable is automatically inherited from your environment. All other environment variables must be configured here." ([Adding MCP servers for GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers), read 2026-10-25). Measured on 1.0.103 on 2026-10-25, a local server received the whole environment of the process that started the CLI, variables that no configuration named included, in prompt mode and in interactive mode, from `.mcp.json`, `.github/mcp.json` and `~/.copilot/mcp-config.json` alike. So an exported token does reach its server under the Copilot CLI. The risk is that every local server receives every exported variable, tokens meant for other servers included.

To give a token to a Copilot CLI server, export the variable as [Step 3](#step-3-set-environment-variables-system-wide) says, and the `${VAR:-}` entry of that server in the project's `.mcp.json` passes it on.

Codex does not pass an exported variable on. It starts a local server with an empty environment and adds back only a fixed list. In the Codex source at tag `rust-v0.162.1`, read 2026-10-25, `Command::new` in [codex-rs/utils/pty/src/child_command.rs](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/utils/pty/src/child_command.rs) calls `.env_clear()`, and `create_env_for_mcp_server` in [codex-rs/rmcp-client/src/utils.rs](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/rmcp-client/src/utils.rs) then sets `DEFAULT_ENV_VARS`, which on Unix is `"HOME"`, `"LOGNAME"`, `"PATH"`, `"SHELL"`, `"USER"`, `"__CF_USER_TEXT_ENCODING"`, `"LANG"`, `"LC_ALL"`, `"TERM"`, `"TMPDIR"` and `"TZ"`, plus the certificate variables in `CUSTOM_CA_ENV_KEYS`, plus every name in the server's `env_vars`, and lays the `env` table over all of them last. The Codex MCP page says `env_vars` is "(optional): Environment variables to allow and forward" ([MCP docs](https://learn.chatgpt.com/docs/extend/mcp), read 2026-10-25). To pass an exported token to a Codex server, name it in `env_vars` and remove it from `env`, because the empty string the shipped `env` table holds for it would replace the value.

An unset token variable is a local, noisy failure and nothing worse: that one server fails to authenticate and the
rest keep working.

---

### Step 5, the surfaces with no project file

Four configurations that live per machine or per repository setting, and therefore ship in this document rather than in the tree. Copilot in JetBrains, the Copilot cloud agent and Claude Desktop read no project file, so their servers stay in the places below. Claude Code, Codex and the Copilot CLI do read a project file, so their user-scope files below hold no server, as [Where a server is declared](#where-a-server-is-declared) says.

#### GitHub Copilot in JetBrains

Path: `~/.config/github-copilot/intellij/mcp.json`, or
`%USERPROFILE%\.config\github-copilot\intellij\mcp.json` on Windows. Global only, no per-project equivalent. Schema key
`servers`, same as the VS Code file, but remote servers nest their authentication under `requestInit.headers` and need
a personal access token, because the JetBrains plugin does not do OAuth yet. Placeholder substitution is unconfirmed,
so the file holds literal values. Keep it out of version control. The result looks like this:

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

The command below writes that entry and keeps every other server in the file. It reads the key from `CONTEXT7_API_KEY`, which [Step 3](#step-3-set-environment-variables-system-wide) sets. In a shell that does not have it yet, read it first through a hidden prompt. Unix shell:

```bash
printf 'CONTEXT7_API_KEY: ' && IFS= read -rs CONTEXT7_API_KEY && echo && export CONTEXT7_API_KEY
```

PowerShell:

```powershell
$env:CONTEXT7_API_KEY = Read-Host 'CONTEXT7_API_KEY' -MaskInput
```

Then write the entry. Unix shell:

```bash
python3 -c 'import json,os,pathlib;p=pathlib.Path.home()/".config/github-copilot/intellij/mcp.json";s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};s.setdefault("servers",{})["context7"]={"url":"https://mcp.context7.com/mcp","requestInit":{"headers":{"CONTEXT7_API_KEY":os.environ["CONTEXT7_API_KEY"]}}};p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")'
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,os,pathlib;p=pathlib.Path.home()/".config/github-copilot/intellij/mcp.json";s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};s.setdefault("servers",{})["context7"]={"url":"https://mcp.context7.com/mcp","requestInit":{"headers":{"CONTEXT7_API_KEY":os.environ["CONTEXT7_API_KEY"]}}};p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")'
```

Check it. It prints each server with its header names, and never a value. Unix shell:

```bash
python3 -c 'import json,pathlib;s=json.loads((pathlib.Path.home()/".config/github-copilot/intellij/mcp.json").read_text(encoding="utf-8"))["servers"];print({k:sorted(v.get("requestInit",{}).get("headers",{})) for k,v in s.items()})'
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,pathlib;s=json.loads((pathlib.Path.home()/".config/github-copilot/intellij/mcp.json").read_text(encoding="utf-8"))["servers"];print({k:sorted(v.get("requestInit",{}).get("headers",{})) for k,v in s.items()})'
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

Path: `~/.claude.json`, same `mcpServers` schema and same `${VAR}` substitution as the project file. Claude Code keeps its other settings and state in the same file, so never copy a file over it. Keep no MCP server there, as [Where a server is declared](#where-a-server-is-declared) says: a server in this file starts in every chat of every project. Declare it in the project instead, with `claude mcp add --scope project`, which writes the project's [.mcp.json](../.mcp.json). Remove a server an older setup added at user scope with the command under [Where a server is declared](#where-a-server-is-declared).

Check it from a folder that has no `.mcp.json`, in either shell. A server that is gone from every scope prints `No MCP server named "home-assistant".`, measured with Claude Code 2.1.325 on 2026-11-20:

```bash
claude mcp get home-assistant
```

#### Claude Desktop

Paths: `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS,
`%APPDATA%\Claude\claude_desktop_config.json` on Windows. There is no official Linux build. Same `mcpServers` schema,
but no environment-variable substitution at all, so the file holds the real value. The file is personal to the
machine, so inlining is fine. Never commit it. The result looks like this:

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

The command below writes that entry and keeps every other key in the file. It reads the key from `CONTEXT7_API_KEY`, set in [Step 3](#step-3-set-environment-variables-system-wide) or read through a hidden prompt as under [GitHub Copilot in JetBrains](#github-copilot-in-jetbrains). macOS:

```bash
python3 -c 'import json,os,sys,pathlib;p=pathlib.Path(sys.argv[1]);s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};s.setdefault("mcpServers",{})["context7"]={"type":"http","url":"https://mcp.context7.com/mcp","headers":{"CONTEXT7_API_KEY":os.environ["CONTEXT7_API_KEY"]}};p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")' "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
```

Windows, PowerShell 7.4 or later:

```powershell
python -c 'import json,os,sys,pathlib;p=pathlib.Path(sys.argv[1]);s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};s.setdefault("mcpServers",{})["context7"]={"type":"http","url":"https://mcp.context7.com/mcp","headers":{"CONTEXT7_API_KEY":os.environ["CONTEXT7_API_KEY"]}};p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")' "$env:APPDATA\Claude\claude_desktop_config.json"
```

Check it. It prints each server with its header names, and never a value. macOS:

```bash
python3 -c 'import json,sys;s=json.load(open(sys.argv[1],encoding="utf-8"))["mcpServers"];print({k:sorted(v.get("headers",{})) for k,v in s.items()})' "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
```

Windows, PowerShell 7.4 or later:

```powershell
python -c 'import json,sys;s=json.load(open(sys.argv[1],encoding="utf-8"))["mcpServers"];print({k:sorted(v.get("headers",{})) for k,v in s.items()})' "$env:APPDATA\Claude\claude_desktop_config.json"
```

Claude Desktop must be fully quit from the system tray and relaunched after an edit, not just closed.

#### Codex and Copilot CLI globals

Codex reads `config.toml` in its home directory for global scope, `~/.config/codex/config.toml` under the layout in [GLOBAL_SETUP.md](GLOBAL_SETUP.md), which sets `CODEX_HOME`, and `~/.codex/config.toml` without it. Keep no `[mcp_servers.*]` table there, as [Where a server is declared](#where-a-server-is-declared) says, so leave `codex mcp add` unused, because it writes only that user file. Put the table into the project's [.codex/config.toml](../.codex/config.toml) instead, in the same TOML shape, and trust the project, or Codex skips the file. Check what Codex loads, from the project root. "Run `codex mcp list` to see configured servers" ([MCP docs](https://learn.chatgpt.com/docs/extend/mcp), read 2026-10-23):

```bash
codex mcp list
```

Codex has no built-in substitution. To keep a secret out of the file, wrap the command in a small script that reads it from your secrets manager.

The Copilot CLI reads the project [.mcp.json](../.mcp.json), the same file Claude Code reads. It reads [.github/mcp.json](../.github/mcp.json) only in a folder that has no `.mcp.json`, because it picks one file per folder, not one entry per server name, as [The CLI, `.mcp.json`, and why a fifth file exists](#the-cli-mcpjson-and-why-a-fifth-file-exists) shows. Project files load only in a trusted folder, as [Verifying the setup](#verifying-the-setup) describes. The CLI also reads a user file, `~/.copilot/mcp-config.json` (relocatable with `COPILOT_HOME`, so `~/.config/copilot/mcp-config.json` under the layout in [GLOBAL_SETUP.md](GLOBAL_SETUP.md)), keyed `mcpServers`, with a `tools` allowlist per server. That file needs no folder trust, the CLI expands `$VAR`, `${VAR}` and `${VAR:-default}` in it the same way as in the project files, and a project server hides a user server of the same name, all measured on 1.0.103 on 2026-10-25. Keep no server in that file, for the reason under [Where a server is declared](#where-a-server-is-declared), and keep it out of version control.

#### Arch Linux operations server, not shipped

`arch-ops-server` (the Arch Wiki, AUR and pacman tools from [nihalxkumar/arch-mcp](https://github.com/nihalxkumar/arch-mcp)) is not one of the shipped servers, because it only helps on an Arch machine. Declare it in the project that uses it, as [Where a server is declared](#where-a-server-is-declared) says, and start it with both pins:

```bash
uvx --from arch-ops-server==3.4.0 --with 'mcp<2' arch-ops-server
```

The `--with 'mcp<2'` is not optional. Release 3.4.0 declares `mcp>=1.0.0` with no upper bound, so `uvx` resolves the newest `mcp`, and `mcp` 2.0, released on 2026-07-28, removed the decorator API the server registers its handlers with: the SDK's migration guide lists "Lowlevel decorators replaced with `on_*` constructor params" with the symptom "`AttributeError: 'Server' object has no attribute 'list_tools'`", and the server fails at start with the same `AttributeError` on `list_resources`. With `mcp<2` it starts and answers `tools/list`, measured on 2026-10-13. The last commit upstream is from 2026-03-10 and carries no fix.

Declare it with one command per agent, run from the project root. Claude Code writes it into the project's `.mcp.json`, in either shell:

```bash
claude mcp add --scope project arch -- uvx --from arch-ops-server==3.4.0 --with 'mcp<2' arch-ops-server
```

Start `claude` in the folder once and approve the server, then check it:

```bash
claude mcp get arch
```

Codex gets the table in the project's `.codex/config.toml`. The command creates the file when there is none, puts the table above the first `[[hooks.` table, and leaves a table of the same name as it is. Unix shell:

```bash
python3 -c 'import json,sys,pathlib;p=pathlib.Path(".codex/config.toml");t=p.read_text(encoding="utf-8") if p.exists() else "";h="[mcp_servers."+sys.argv[1]+"]";b=h+"\ncommand = "+json.dumps(sys.argv[2])+"\nargs = ["+", ".join(json.dumps(a) for a in sys.argv[3:])+"]\n\n";i=t.find("[[hooks.");t=t if h in t else (t[:i]+b+t[i:] if i>=0 else t+("\n" if t and not t.endswith("\n") else "")+b);p.parent.mkdir(exist_ok=True);p.write_text(t,encoding="utf-8")' arch uvx --from arch-ops-server==3.4.0 --with 'mcp<2' arch-ops-server
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,sys,pathlib;p=pathlib.Path(".codex/config.toml");t=p.read_text(encoding="utf-8") if p.exists() else "";h="[mcp_servers."+sys.argv[1]+"]";b=h+"\ncommand = "+json.dumps(sys.argv[2])+"\nargs = ["+", ".join(json.dumps(a) for a in sys.argv[3:])+"]\n\n";i=t.find("[[hooks.");t=t if h in t else (t[:i]+b+t[i:] if i>=0 else t+("\n" if t and not t.endswith("\n") else "")+b);p.parent.mkdir(exist_ok=True);p.write_text(t,encoding="utf-8")' arch uvx --from arch-ops-server==3.4.0 --with 'mcp<2' arch-ops-server
```

Check it from the project root, which Codex must trust:

```bash
codex mcp list
```

OpenCode and Kilo Code get the block in the project's `opencode.json`. The command adds or replaces only that entry and keeps the rest of the file. Unix shell:

```bash
python3 -c 'import json,sys,pathlib;p=pathlib.Path("opencode.json");s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};s.setdefault("mcp",{})[sys.argv[1]]={"type":"local","command":sys.argv[2:],"enabled":True};p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")' arch uvx --from arch-ops-server==3.4.0 --with 'mcp<2' arch-ops-server
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,sys,pathlib;p=pathlib.Path("opencode.json");s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};s.setdefault("mcp",{})[sys.argv[1]]={"type":"local","command":sys.argv[2:],"enabled":True};p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")' arch uvx --from arch-ops-server==3.4.0 --with 'mcp<2' arch-ops-server
```

In a `.mcp.json` style file the same command is:

```json
{
  "mcpServers": {
    "arch": {
      "command": "uvx",
      "args": ["--from", "arch-ops-server==3.4.0", "--with", "mcp<2", "arch-ops-server"]
    }
  }
}
```

Remove the `mcp<2` pin, and move the version pin forward, once a release of `arch-ops-server` declares `mcp>=2` or an upper bound below 2 itself. Check its dependencies on [PyPI](https://pypi.org/project/arch-ops-server/) before you do.

#### Home Assistant server

`home-assistant` runs [ha-mcp](https://github.com/homeassistant-ai/ha-mcp), pinned to release 9.2.0 from [PyPI](https://pypi.org/project/ha-mcp/9.2.0/), over stdio. The server reads two keys, `HOMEASSISTANT_URL` and `HOMEASSISTANT_TOKEN`. They live in the credential env file `~/.local/state/agents/workspace/homelab.env`, never in a configuration file and never in a system-wide variable. `uvx` reads that file itself through its `--env-file` flag ("Load environment variables from a `.env` file", `uvx --help`, uv 0.13.1), so no wrapper script is needed. Release 9.2.0 declares `Requires-Python` as `<3.15,>=3.13`, and `uvx` picks a matching Python on its own.

Give the agent its own Home Assistant user. The ha-mcp README suggests an account made just for ha-mcp under Settings, People, Add person, with Allow login, Local access only and Administrator switched on, so a leaked token works only from the local network. Sign in as that user and create the token under your profile, Security, Long-lived access tokens, Create token. `HOMEASSISTANT_URL` is the address of your instance, for example `http://homeassistant.local:8123`.

Write both keys into the file through a hidden prompt, so a value never lands on a command line or in your shell history. Create the folder first. Unix shell:

```bash
mkdir -p ~/.local/state/agents/workspace
```

PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path "$HOME\.local\state\agents\workspace" | Out-Null
```

On Linux and macOS, create the file before any key goes in, and let only your own user read it. `touch` leaves a file that already exists as it is:

```bash
touch ~/.local/state/agents/workspace/homelab.env
```

```bash
chmod 600 ~/.local/state/agents/workspace/homelab.env
```

Add the two keys. Press Enter at a prompt to skip a key the file already holds. Unix shell:

```bash
for n in HOMEASSISTANT_URL HOMEASSISTANT_TOKEN; do printf '%s, Enter to skip: ' "$n"; IFS= read -rs v; echo; [ -n "$v" ] && printf '%s=%s\n' "$n" "$v" >> ~/.local/state/agents/workspace/homelab.env; done; unset v
```

PowerShell 7.4 or later:

```powershell
foreach ($n in 'HOMEASSISTANT_URL', 'HOMEASSISTANT_TOKEN') { $v = Read-Host "$n, Enter to skip" -MaskInput; if ($v) { Add-Content -Path "$HOME\.local\state\agents\workspace\homelab.env" -Value "$n=$v" -Encoding utf8NoBOM } }; Remove-Variable v
```

Check it. It prints each key name the file holds, and never a value. Unix shell:

```bash
grep -n -o -E '^(HOMEASSISTANT_URL|HOMEASSISTANT_TOKEN)=' ~/.local/state/agents/workspace/homelab.env
```

PowerShell:

```powershell
Select-String -Path "$HOME\.local\state\agents\workspace\homelab.env" -Pattern '^(HOMEASSISTANT_URL|HOMEASSISTANT_TOKEN)=' | ForEach-Object { $_.Matches[0].Value }
```

Know the minus before you rely on it: `uvx` loads every key in the file into the ha-mcp process, so the server sees every lab secret the file holds, not only the two Home Assistant keys. A missing file is a hard error, so the server does not start: `uvx --env-file` on a path that does not exist stops with `Error: No environment file found at: <path>` and exit code 2, measured with uv 0.13.1 on 2026-10-25.

uv does not expand `~` or `$HOME` inside that path, so each project file writes the home folder in its own way:

| File | Path to the env file | State |
| --- | --- | --- |
| [.mcp.json](../.mcp.json) | none in the shipped file, which holds `context7` alone. The `mcp-home-assistant` plugin and the `claude mcp add` command below both write `${HOME}/.local/state/agents/workspace/homelab.env`, which Claude Code expands, because "Environment variables can be expanded in" `command`, `args` and `env` ([MCP docs](https://code.claude.com/docs/en/mcp), "Expansion locations", read 2026-10-25). The Copilot CLI expands it too in a `.mcp.json`, measured on 1.0.103 on 2026-10-25 | not present, added per project |
| [.vscode/mcp.json](../.vscode/mcp.json) | `${userHome}/.local/state/agents/workspace/homelab.env`. The VS Code reference says "You can use predefined variables in the server configuration" ([MCP configuration reference](https://code.visualstudio.com/docs/agents/reference/mcp-configuration), read 2026-10-25), and `${userHome}` is the "Path of the user's home folder" ([variables reference](https://code.visualstudio.com/docs/reference/variables-reference)) | on |
| [opencode.json](../opencode.json) | none, the server is left out. A project that uses it adds the block with an absolute path, as below | not present |
| [.codex/config.toml](../.codex/config.toml) | none, the server is left out. A project that uses it adds the table with an absolute path, as below | not present |
| [.github/mcp.json](../.github/mcp.json) | none, the server is left out | not present |

The Claude Code block uses `${HOME}` with no `:-default`, unlike the other blocks, because no default path would be right. When `HOME` is unset, Claude Code names the variable in a warning: "If a referenced environment variable isn't set and has no default value, the config still loads: Claude Code reports a missing-variable warning for that server in `claude mcp list` output and uses the unexpanded `${VAR}` text as-is" (same page, "Unset variables without a default").

[opencode.json](../opencode.json) and [.codex/config.toml](../.codex/config.toml) leave the server out, because a shipped file cannot hold a path that works on every machine: Kilo Code throws the whole project file away on an `{env:HOME}` token, as [What ships](#what-ships) explains, and Codex has no substitution at all. A project that uses the server on OpenCode, Kilo Code or Codex declares it in its own copy of both files, with the commands below, which write the absolute path.

[.github/mcp.json](../.github/mcp.json) leaves the server out, because its schema has no enable flag. The Copilot CLI reads `home-assistant` from the project's `.mcp.json` once the `claude mcp add` command below has put it there, because that is the file it reads in place of `.github/mcp.json`, as [What ships](#what-ships) describes, and it expands `${HOME}` in `args`. Measured on 1.0.103 on 2026-10-25 with `HOME=/home/node`, a stand-in `uvx` received `--env-file /home/node/.local/state/agents/workspace/homelab.env ha-mcp==8.7.0`, the pin of that day. So a `home-assistant` entry in `.mcp.json` starts under the Copilot CLI too. The CLI reference lists expansion only for `env` and `headers`, so this rests on the measurement.

Switch the server off for the Copilot CLI in one of three ways. For one run, the reference documents `--disable-mcp-server SERVER-NAME` "to disable a specific one" ([CLI command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference), read 2026-10-25). It lasts for that one run and saves nothing, measured on 1.0.103 on 2026-10-25:

```bash
copilot --disable-mcp-server home-assistant
```

Inside a session, "`/mcp disable SERVER-NAME`. A disabled server remains configured but is not used by Copilot. This setting persists across sessions." ([Adding MCP servers for GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers), read 2026-10-25):

```text
/mcp disable home-assistant
```

From a terminal, the reference documents `copilot mcp disable`: "Enable or disable a server by name. The change persists to the user configuration and applies to future sessions." (same reference, "copilot mcp subcommand"). In either shell:

```bash
copilot mcp disable home-assistant
```

Both `/mcp disable` and `copilot mcp disable` write the name into `disabledMcpServers` in `~/.copilot/settings.json`, measured on 1.0.103 on 2026-10-25. That works by name, so the server stays off in every project. Turn it back on, in either shell:

```bash
copilot mcp enable home-assistant
```

Keep one entry per agent. The ha-mcp README warns "Configure exactly one install method per client", and says that two entries for the same server in one client are "a known cause of connection hangs". Declare the server in the project only, and remove any user entry an older setup left, with the commands under [Where a server is declared](#where-a-server-is-declared). Where one is still left, the name `home-assistant` decides which entry loads, because one wins by name:

1. Claude Code: "Claude Code matches duplicates across the three scopes by name", and project scope ranks above user scope ([MCP docs](https://code.claude.com/docs/en/mcp), "Scope hierarchy and precedence", read 2026-10-25). In a project whose `.mcp.json` holds the server, the project entry runs.
2. Copilot CLI: "Project-level definitions also take precedence over those in `~/.copilot/mcp-config.json`" ([Adding MCP servers for GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers), read 2026-10-25). Measured on 1.0.103 on 2026-10-25, a project server hides a user server of the same name.
3. Codex, OpenCode and Kilo Code: a project entry wins by name over the user entry, even when the project entry is switched off. Measured on 2026-10-25 with a working user entry in a temporary configuration, while this repository's [opencode.json](../opencode.json) and [.codex/config.toml](../.codex/config.toml) still carried a switched-off `home-assistant` entry: in this repository, `codex mcp list` (Codex 0.162.1) showed `home-assistant` as `disabled`, and in an empty folder as `enabled`. `opencode mcp list` (OpenCode 2.0.26) showed it as `disabled`, and `kilocode debug config` (Kilo Code 7.8.15) showed the project block with `"enabled": false`. That is why neither file ships a switched-off `home-assistant` entry: it hid the working entry beside it.

Declare it in the project with one command per agent, run from the project root. On Claude Code, either install the `mcp-home-assistant` plugin at project scope, as [Adding a server to Claude Code](#adding-a-server-to-claude-code) shows, which reads the credential env file at the path in the table above, or run the command below, in either shell, with the path of the credential env file in place of `<env file>`. Write a path under your home folder as `${HOME}/` followed by the rest of the path, the way the plugin does. The single quotes keep `${HOME}` as text, so `.mcp.json` holds it unchanged and Claude Code expands it when it starts the server, measured with Claude Code 2.1.325 on 2026-11-20:

```bash
claude mcp add --scope project home-assistant -- uvx --env-file '<env file>' ha-mcp==9.2.0
```

Start `claude` in the folder once and approve the server, as [Where a server is declared](#where-a-server-is-declared) describes. Then check it, in either shell. This starts the server once to test the connection:

```bash
claude mcp get home-assistant
```

Codex, OpenCode and Kilo Code read no variable in a project file, so the next commands write an absolute path. Put the absolute path of the credential env file in place of `<env file>`, and the file then holds the home folder of that one machine. Declare the server this way only in a folder that is yours on one machine, or keep that change out of version control. Codex, with the command from [Arch Linux operations server, not shipped](#arch-linux-operations-server-not-shipped). Unix shell:

```bash
python3 -c 'import json,sys,pathlib;p=pathlib.Path(".codex/config.toml");t=p.read_text(encoding="utf-8") if p.exists() else "";h="[mcp_servers."+sys.argv[1]+"]";b=h+"\ncommand = "+json.dumps(sys.argv[2])+"\nargs = ["+", ".join(json.dumps(a) for a in sys.argv[3:])+"]\n\n";i=t.find("[[hooks.");t=t if h in t else (t[:i]+b+t[i:] if i>=0 else t+("\n" if t and not t.endswith("\n") else "")+b);p.parent.mkdir(exist_ok=True);p.write_text(t,encoding="utf-8")' home-assistant uvx --env-file "<env file>" ha-mcp==9.2.0
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,sys,pathlib;p=pathlib.Path(".codex/config.toml");t=p.read_text(encoding="utf-8") if p.exists() else "";h="[mcp_servers."+sys.argv[1]+"]";b=h+"\ncommand = "+json.dumps(sys.argv[2])+"\nargs = ["+", ".join(json.dumps(a) for a in sys.argv[3:])+"]\n\n";i=t.find("[[hooks.");t=t if h in t else (t[:i]+b+t[i:] if i>=0 else t+("\n" if t and not t.endswith("\n") else "")+b);p.parent.mkdir(exist_ok=True);p.write_text(t,encoding="utf-8")' home-assistant uvx --env-file "<env file>" ha-mcp==9.2.0
```

Check it from the project root, which Codex must trust, in either shell:

```bash
codex mcp list
```

OpenCode and Kilo Code share the project's `opencode.json`, so one command covers both. It adds or replaces only the `home-assistant` entry and keeps the rest of the file. Unix shell:

```bash
python3 -c 'import json,sys,pathlib;p=pathlib.Path("opencode.json");s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};s.setdefault("mcp",{})[sys.argv[1]]={"type":"local","command":sys.argv[2:],"enabled":True};p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")' home-assistant uvx --env-file "<env file>" ha-mcp==9.2.0
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,sys,pathlib;p=pathlib.Path("opencode.json");s=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {};s.setdefault("mcp",{})[sys.argv[1]]={"type":"local","command":sys.argv[2:],"enabled":True};p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")' home-assistant uvx --env-file "<env file>" ha-mcp==9.2.0
```

Check Kilo Code, in either shell:

```bash
kilocode mcp list
```

Check OpenCode, in either shell:

```bash
opencode mcp list
```

On OpenCode 2.0.26, `opencode mcp list` lists MCP servers only inside a git repository (measured 2026-10-25: in a folder without git it printed `No MCP servers configured`, after `git init` in the same folder it listed `arch` and `home-assistant` as connected, and `opencode debug config` showed both global servers in both cases).

`opencode mcp list` and `opencode debug config` go through the OpenCode background service when it runs (for example the one the desktop app starts), and that service starts and keeps a full set of MCP servers for each folder it is asked about. `opencode service --help` calls it the background server ("Manage the background server"), and `restart` is "Restart the background server". Clean up with this command, which on 2026-10-25, with the desktop app's `opencode-cli` 2.0.29, stopped every server the old service had started:

```bash
opencode service restart
```

When the desktop app owns the service, run the restart with the desktop app's own `opencode-cli` binary, so the service keeps its version.

The ha-mcp README calls local stdio "not recommended" and warns that "stdio has known transport issues", recommending its Home Assistant custom component or an HTTP setup for real use. If the server hangs over stdio, follow the ha-mcp [Setup Wizard](https://homeassistant-ai.github.io/ha-mcp/setup/) for an HTTP setup and replace the `home-assistant` entry rather than adding a second one.

---

### Substitution support matrix

Useful when a variable is stubbornly not being picked up.

| File | Substitution syntax | Applies to |
| --- | --- | --- |
| `.mcp.json` and `~/.claude.json`, Claude Code | `${VAR}`, `${VAR:-default}` | `command`, `args`, `env`, `url`, `headers` |
| `.mcp.json`, GitHub Copilot CLI | `$VAR`, `${VAR}`, `${VAR:-default}`, measured on 1.0.103 on 2026-10-25 | `command`, `args`, `env`, `url`, `headers` |
| `.github/mcp.json`, GitHub Copilot CLI, read only in a folder that has no `.mcp.json` | the same, measured on 1.0.103 on 2026-10-25 | the same fields |
| `~/.copilot/mcp-config.json`, GitHub Copilot CLI user file | the same, measured on 1.0.103 on 2026-10-25 | the same fields |
| `opencode.json`, OpenCode | `{env:VAR}` | any string value in an MCP block, though the shipped file uses none |
| `opencode.json`, Kilo Code | none at project level, and one token invalidates the whole file | inline literals only |
| `~/.config/opencode/opencode.json`, OpenCode global | `{env:VAR}` | any string value, global config is trusted |
| `~/.config/kilo/kilo.jsonc`, Kilo Code global | `{env:VAR}` | any string value, global config is trusted |
| `.vscode/mcp.json`, Copilot in VS Code | `${env:VAR}`, `${input:NAME}`, predefined variables such as `${userHome}` | any string value in a server block |
| JetBrains global `mcp.json` | none documented | inline literals, token in `requestInit.headers` |
| Copilot cloud agent, settings page | none | inline literals plus Copilot secrets |
| `claude_desktop_config.json` | not supported | inline literals |
| `.codex/config.toml` and `~/.codex/config.toml` | none, TOML has no substitution | inline literals |

---

### Verifying the setup

Restart the agent after editing configs or exporting variables, then check.

- Claude Code: run `claude mcp list` and read which servers loaded. A project that imported the shipped `.mcp.json` and added nothing lists `context7` alone.
- OpenCode: start it and run `/mcp`, or read the connection lines in the startup log.
- Kilo Code: run `kilocode config check` first, which prints nothing but `No config warnings.` when the project
  config is accepted, then open the MCP Servers panel in settings, under agent behaviour, where each server shows
  connected or error. `kilocode mcp list` answers the same question from a terminal.
- Codex: start `codex` and run `/mcp`. Remember the project layer loads only after you trust the project.
- Copilot in VS Code: open Chat, switch to agent mode, open the tools picker. Every server in
  [.vscode/mcp.json](../.vscode/mcp.json) appears with its tools and a start or stop control.
- Copilot CLI: start `copilot` and run `/mcp`, or run `copilot mcp list` from a terminal. Either way, project files load only after you confirm on first launch that you trust the folder. Measured on 1.0.103 on 2026-10-25: an untrusted folder lists only the servers from `~/.copilot/mcp-config.json`, with no user file the CLI prints `No MCP servers configured.`, `copilot mcp list` has no flag to skip the trust prompt, and `copilot --trust-folder -p "..."` loads the project files for one prompt-mode run and saves no trust. The reference says `--trust-folder` trusts "the working directory's hooks, workspace MCP servers, and repository plugin settings for one new non-interactive session" and "The trust is not saved to `trustedFolders`" ([CLI command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference), read 2026-10-25). `copilot mcp get NAME --json` shows the file text, not the values a server receives.
- Claude Desktop: open the developer panel, or check the indicator in the input box.

When a server fails to connect, Claude Code writes the reason to its standard log, and Claude Desktop writes per-server
standard-error output to `mcp-server-<name>.log` under `~/Library/Logs/Claude/` on macOS or `%APPDATA%\Claude\logs\`
on Windows.

---

### Updating a pinned server

Every local server command names one exact release: an npm package as `name@1.2.3`, a PyPI package as `name==1.2.3`, and the SonarQube image as `name:1.2.3.4`, a version tag. No command says `@latest`, leaves the version out or pulls an image on every start, so a server changes only when someone changes its pin. Upstream moves the pins from time to time, and you can move one in your own copy the same way:

1. Read the releases from the registry itself. For an npm package, here `mongodb-mcp-server`, this prints every version with the time it was published, in either shell:

   ```bash
   npm view mongodb-mcp-server time --json
   ```

   For a PyPI package, here `mcp-grafana`, this prints every release with its upload time. Unix shell:

   ```bash
   python3 -c 'import json,sys,urllib.request;d=json.load(urllib.request.urlopen("https://pypi.org/pypi/"+sys.argv[1]+"/json"));[print(v,f[0]["upload_time_iso_8601"]) for v,f in d["releases"].items() if f]' mcp-grafana
   ```

   PowerShell 7.4 or later:

   ```powershell
   python -c 'import json,sys,urllib.request;d=json.load(urllib.request.urlopen("https://pypi.org/pypi/"+sys.argv[1]+"/json"));[print(v,f[0]["upload_time_iso_8601"]) for v,f in d["releases"].items() if f]' mcp-grafana
   ```

   For the SonarQube image, `sonarsource/sonarqube-mcp` on Docker Hub, this prints every tag with the time it was pushed. Unix shell:

   ```bash
   python3 -c 'import json,sys,urllib.request;d=json.load(urllib.request.urlopen("https://hub.docker.com/v2/repositories/"+sys.argv[1]+"/tags?page_size=100"));[print(t["name"],t["tag_last_pushed"]) for t in d["results"]]' sonarsource/sonarqube-mcp
   ```

   PowerShell 7.4 or later:

   ```powershell
   python -c 'import json,sys,urllib.request;d=json.load(urllib.request.urlopen("https://hub.docker.com/v2/repositories/"+sys.argv[1]+"/tags?page_size=100"));[print(t["name"],t["tag_last_pushed"]) for t in d["results"]]' sonarsource/sonarqube-mcp
   ```

2. Take the newest stable release that is at least 7 days old. The wait gives a bad or malicious release time to be caught and withdrawn before you run it. A release under a tag such as `alpha`, `canary`, `next` or `pre` is not stable.
3. Write the new version into every file of yours that names the old one. The last two words are the pin the files hold now and the one you chose, so put your own in place of `3.4.0`. Unix shell:

   ```bash
   python3 -c 'import sys,pathlib;[p.write_text(p.read_text(encoding="utf-8").replace(sys.argv[1],sys.argv[2]),encoding="utf-8") for p in map(pathlib.Path,(".mcp.json","opencode.json",".vscode/mcp.json",".codex/config.toml",".github/mcp.json")) if p.exists()]' mongodb-mcp-server@3.3.0 mongodb-mcp-server@3.4.0
   ```

   PowerShell 7.4 or later:

   ```powershell
   python -c 'import sys,pathlib;[p.write_text(p.read_text(encoding="utf-8").replace(sys.argv[1],sys.argv[2]),encoding="utf-8") for p in map(pathlib.Path,(".mcp.json","opencode.json",".vscode/mcp.json",".codex/config.toml",".github/mcp.json")) if p.exists()]' mongodb-mcp-server@3.3.0 mongodb-mcp-server@3.4.0
   ```

4. Start the server once and check that it connects, here on Claude Code, in either shell:

   ```bash
   claude mcp get mongodb
   ```

A server you installed as a plugin moves when upstream raises its pin and with it the plugin's version. Refresh the marketplace, in either shell:

```bash
claude plugin marketplace update agent-standards
```

Then update the plugin:

```bash
claude plugin update mcp-mongodb@agent-standards
```

The SonarQube server runs SonarSource's own image, `sonarsource/sonarqube-mcp`. Its README says to use the bare name "for automatic updates (with `--pull=always`), or pin to a version tag (e.g., `sonarsource/sonarqube-mcp:1.19.0.2785`) for reproducible deployments", and with a pinned image to "remove `--pull=always` so Docker does not silently upgrade the image" ([sonarqube-mcp-server README](https://github.com/SonarSource/sonarqube-mcp-server), "Manual setup" and "I want to pin to a specific version", read 2026-11-23). `docker run` pulls an image it does not have and then reuses the local copy, so the server does not pull on every start.

A tag of four numbers, such as `1.32.0.5118`, is one release of the server. Among those pushed at least 7 days ago, take the one with the highest version, because an older line still gets fixes and its newest tag can be pushed later than a higher version. A tag of three numbers, such as `2026.5.2`, is a second name for one of those releases: "Some releases are also tagged with the SonarQube Server version they are aligned with, in the form `<SQS major>.<SQS minor>.<patch>`" (same README, "Manual setup"). The tag `latest` moves from release to release, so a pin never names it. Each tag holds an image for `linux/amd64` and one for `linux/arm64` (Docker Hub tag list, read 2026-11-23). Write the tag you chose with the command of step 3, here from `sonarsource/sonarqube-mcp:1.32.0.5118` to the new one.

---

### Adding or changing a server

Upstream keeps one list of servers, with one pinned command each, and renders the `mcp-<server>` plugins from it. A new server goes into that list and into the four project files that carry the full set: [opencode.json](../opencode.json), the
`[mcp_servers]` tables in [.codex/config.toml](../.codex/config.toml), [.vscode/mcp.json](../.vscode/mcp.json), and
[.github/mcp.json](../.github/mcp.json). [.mcp.json](../.mcp.json) keeps `context7` alone, for the reason under [What ships](#what-ships). Then update the two manual blocks in this document, the JetBrains one and the
cloud-agent one, which ship no file.

Keep the server set identical across those four, apart from the exceptions listed under [What ships](#what-ships), each with its reason in this document. Only the per-schema syntax is allowed to differ, and every file names the same version of a server.

To customise a single project without touching upstream, change its local copies, with the commands in this document
where one fits. These five files are
consumer-owned, so the routine update flow leaves every one of them alone. Picking up an upstream server change is a
deliberate, separate step, with its own diff-and-checkout command at the end of each shell section of
[AGENTS-UPDATE.md](AGENTS-UPDATE.md). That command covers the five MCP
files together, [.mcp.json](../.mcp.json), [opencode.json](../opencode.json), [.vscode/mcp.json](../.vscode/mcp.json),
[.github/mcp.json](../.github/mcp.json), and [.codex/config.toml](../.codex/config.toml). Diff before you run it, because it replaces every one of those
files wholesale.
