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

Four files carry the same eight servers. [opencode.json](../opencode.json) carries those eight plus `atlassian`, nine in total. Only the file name, the schema key, the `type` value, and the
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
Code), which is trusted config and does expand `{env:VAR}`. The command for each file is under
[Kilo Code in GLOBAL_SETUP.md](GLOBAL_SETUP.md#kilo-code), and it writes the reference, never the key. It cannot live in a project file: Kilo rejects any project
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
smallest tool descriptions of the nine and needs no secret, and the descriptions of all nine together pushed a
single test past the provider's per-minute token limit. So only `context7` is proven to answer a real model there,
and the other eight are proven to be discovered by every agent, not to answer.

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

`.github/mcp.json` cannot rely on that same inheritance for a secret. A local (`"type": "local"`) server under the
Copilot CLI only receives `PATH` from the process that started the CLI; the CLI's own documentation states that
every other environment variable a server needs must be listed explicitly in the server's `env` object in the config
file. Exporting `GRAFANA_SERVICE_ACCOUNT_TOKEN`, `SONARQUBE_TOKEN`, or `N8N_API_KEY` system-wide, the way Step 3
above recommends, reaches the same server under Claude Code, OpenCode, Kilo Code, and Codex, but does not reach it
under the Copilot CLI, because `.github/mcp.json` deliberately omits those three keys to avoid committing a secret.
Authenticating one of those servers for the Copilot CLI specifically means adding the real value to that key in your
own local, uncommitted copy of `.github/mcp.json`, the same way [Claude Desktop](#claude-desktop) below needs a
literal value because it has no substitution either.

One command does it from the project root. It reads each token from the variable you set in [Step 3](#step-3-set-environment-variables-system-wide), so the value never appears on the command line, writes it into the `env` object of its server, and skips a variable that is not set. It writes the file back with two-space indentation. Unix shell:

```bash
python3 -c 'import json,os,sys;p=".github/mcp.json";s=json.load(open(p,encoding="utf-8"));a=sys.argv[1:];[s["mcpServers"][a[i]].setdefault("env",{}).update({a[i+1]:os.environ[a[i+1]]}) for i in range(0,len(a),2) if os.environ.get(a[i+1])];open(p,"w",encoding="utf-8").write(json.dumps(s,indent=2)+"\n")' grafana GRAFANA_SERVICE_ACCOUNT_TOKEN sonarqube SONARQUBE_TOKEN n8n N8N_API_KEY
```

PowerShell 7.4 or later:

```powershell
python -c 'import json,os,sys;p=".github/mcp.json";s=json.load(open(p,encoding="utf-8"));a=sys.argv[1:];[s["mcpServers"][a[i]].setdefault("env",{}).update({a[i+1]:os.environ[a[i+1]]}) for i in range(0,len(a),2) if os.environ.get(a[i+1])];open(p,"w",encoding="utf-8").write(json.dumps(s,indent=2)+"\n")' grafana GRAFANA_SERVICE_ACCOUNT_TOKEN sonarqube SONARQUBE_TOKEN n8n N8N_API_KEY
```

Check it. It prints each server with the names in its `env` object, and never a value. Unix shell:

```bash
python3 -c 'import json;print({k:sorted(v.get("env",{})) for k,v in json.load(open(".github/mcp.json",encoding="utf-8"))["mcpServers"].items()})'
```

PowerShell 7.4 or later:

```powershell
python -c 'import json;print({k:sorted(v.get("env",{})) for k,v in json.load(open(".github/mcp.json",encoding="utf-8"))["mcpServers"].items()})'
```

The file now holds secrets, so never commit it. `git status --short .github/mcp.json` shows it as modified for as long as it does.

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

Path: `~/.claude.json`, same `mcpServers` schema and same `${VAR}` substitution as the project file. It applies when
you work outside a project that defines its own [.mcp.json](../.mcp.json), and the project file wins on a name
collision. Claude Code keeps its other settings and state in the same file, so never copy a file over it. Add the
servers with `claude mcp add-json`, which writes one entry and leaves the rest of the file alone. The MCP docs say "You
can use `--scope user` to add the server to your user configuration instead of the project-specific one"
([MCP docs](https://code.claude.com/docs/en/mcp), "Add MCP servers from JSON configuration", read 2026-10-23).

To add every server of the project file at user scope, run this from the project root. A name that already exists at
that scope is refused and left as it is: the MCP docs say running `claude mcp add` "again with the same server name at
the same scope fails with `MCP server sentry already exists in local config`", and `add-json` is expected to behave the
same, which was not measured. PowerShell 7.4 or later:

```powershell
(Get-Content -Raw .mcp.json | ConvertFrom-Json).mcpServers.PSObject.Properties | ForEach-Object { claude mcp add-json $_.Name ($_.Value | ConvertTo-Json -Depth 10 -Compress) --scope user }
```

Unix shell:

```bash
python3 -c 'import json,subprocess;[subprocess.run(["claude","mcp","add-json",n,json.dumps(c),"--scope","user"]) for n,c in json.load(open(".mcp.json",encoding="utf-8"))["mcpServers"].items()]'
```

Check it, in either shell. "To check that Claude Code connected, run `claude mcp get <name>`" (MCP docs):

```bash
claude mcp get context7
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

Codex reads `config.toml` in its home directory for global scope, `~/.config/codex/config.toml` under the layout in [GLOBAL_SETUP.md](GLOBAL_SETUP.md), which sets `CODEX_HOME`, and `~/.codex/config.toml` without it, in the same TOML shape as the project file:

```toml
[mcp_servers.context7]
command = "npx"
args = ["-y", "@upstash/context7-mcp@latest"]
```

`codex mcp add` writes that table for you, in whichever home `CODEX_HOME` names. The Codex MCP page gives the same
example: "to add Context7 (a free MCP server for developer documentation), you can run the following command: `codex
mcp add context7 -- npx -y @upstash/context7-mcp`" ([MCP docs](https://learn.chatgpt.com/docs/extend/mcp), read
2026-10-23). In either shell:

```bash
codex mcp add context7 -- npx -y @upstash/context7-mcp@latest
```

Check it. "Run `codex mcp list` to see configured servers" (same page):

```bash
codex mcp list
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
`~/.copilot/mcp-config.json` (relocatable with `COPILOT_HOME`, so `~/.config/copilot/mcp-config.json` under the layout in [GLOBAL_SETUP.md](GLOBAL_SETUP.md)), keyed `mcpServers`, with a `tools` allowlist per
server, no directory-trust requirement, and no substitution. Keep that one out of version control too.

#### Arch Linux operations server, not shipped

`arch-ops-server` (the Arch Wiki, AUR and pacman tools from [nihalxkumar/arch-mcp](https://github.com/nihalxkumar/arch-mcp)) is not one of the eight servers, because it only helps on an Arch machine. Add it to your own user-scope configuration, and start it with both pins:

```bash
uvx --from arch-ops-server==3.4.0 --with 'mcp<2' arch-ops-server
```

The `--with 'mcp<2'` is not optional. Release 3.4.0 declares `mcp>=1.0.0` with no upper bound, so `uvx` resolves the newest `mcp`, and `mcp` 2.0, released on 2026-07-28, removed the decorator API the server registers its handlers with: the SDK's migration guide lists "Lowlevel decorators replaced with `on_*` constructor params" with the symptom "`AttributeError: 'Server' object has no attribute 'list_tools'`", and the server fails at start with the same `AttributeError` on `list_resources`. With `mcp<2` it starts and answers `tools/list`, measured on 2026-10-13. The last commit upstream is from 2026-03-10 and carries no fix.

Add it at user scope with one command per agent. Claude Code, in either shell:

```bash
claude mcp add --scope user arch -- uvx --from arch-ops-server==3.4.0 --with 'mcp<2' arch-ops-server
```

Check it:

```bash
claude mcp get arch
```

Codex, in either shell:

```bash
codex mcp add arch -- uvx --from arch-ops-server==3.4.0 --with 'mcp<2' arch-ops-server
```

Check it:

```bash
codex mcp list
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

To customise a single project without touching upstream, change its local copies, with the commands in this document
where one fits. These five files are
consumer-owned, so the routine update flow leaves every one of them alone. Picking up an upstream server change is a
deliberate, separate step, with its own diff-and-checkout command at the end of each shell section of
[AGENTS-UPDATE.md](AGENTS-UPDATE.md). That command covers all six configuration files together: the five MCP
files, [.mcp.json](../.mcp.json), [opencode.json](../opencode.json), [.vscode/mcp.json](../.vscode/mcp.json),
[.github/mcp.json](../.github/mcp.json), and [.codex/config.toml](../.codex/config.toml), plus the unrelated
[.claude/settings.json](../.claude/settings.json). Diff before you run it, because it replaces every one of those
files wholesale.
