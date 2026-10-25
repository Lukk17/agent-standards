# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `tools/check-skill-mentions.py`, run by CI and listed under Local checks in `CONTRIBUTING.md`, which fails when a skill file names a skill that has no folder under `.agents/skills`. It reads a backticked name as a skill only where the skills name one another: after "use" in the description or in a "When not to activate" bullet, at the start of a "Related skills" bullet, and as "`name` skill", so a command or a package in backticks never counts. Tests in `tools/tests/test_check_skill_mentions.py`. Run on the tree before the fix below, it named `user-communication` in `.agents/skills/research/SKILL.md` lines 3, 35 and 89 and exited 1.
- OpenCode 2.x in the container sandbox, so every run covers OpenCode 1.x, OpenCode 2.x and Kilo Code. `@opencode/cli` installs into its own prefix, because it and `opencode-ai` both own the `opencode` binary name, and runs as `opencode2` through `sandbox-agent/opencode2.sh`, which gives it its own `XDG_DATA_HOME`: with a shared data directory, 1.18.25 refuses to start after a 2.0.28 turn with `Database is not empty and has no session table`, measured in the container. `sandbox-agent/lib-opencode2.sh` runs real 2.x turns against `sandbox-agent/mock-model.mjs`, a scripted OpenAI-compatible model, and asserts in both the project and the global suite that the plugin loads from its directory entry with no `configured plugin path must be a directory` warning, that the gate refuses a main-thread `write`, that the main session's agent turns carry the reply rules and a subagent's carry none, and that 1.x still starts afterwards. Project suite 88 passed, global 151, scoped 24, against 2.0.28 and 1.18.25.
- `sandbox-agent/mcp-guard.sh`, first on the sandbox `PATH` as `docker`, `npx` and `uvx`, the only launchers the shipped MCP blocks use. It records and refuses every call, so no suite can start a real MCP server, download a package or pull an image. The project suite's `mcp list` assertions had been launching the `npx` servers inside the container, 50 launches per run now refused, and an earlier host run pulled `mcp/sonarqube`.

- `global/AGENTS.md.example`, an anonymised template for the user-level `~/.config/agents/AGENTS.md`, holding only rules that apply to anybody, with no personal placeholders and no optional sections. Step 3 of `docs/GLOBAL_SETUP.md` now copies it from there instead of telling you to cut down the per-project `AGENTS.md.example`, and states that neither updater ever writes the file once it exists.

- `.agents/hooks/claude/sync_skill_links.py`, which keeps `~/.claude/skills` and `$CODEX_HOME/skills` as real folders holding one link per skill in `~/.config/agents/skills`. It links a new skill, removes a link whose skill is gone, never touches `synced`, `.trash`, a dot entry, a real directory or a foreign link, does nothing while the folder is itself a link or on Windows, and always exits 0. Claude Code runs it on `SessionStart` for `startup` and `resume`, and both global updaters run it after an update. Tests in `tools/tests/test_sync_skill_links.py`.
- `.agents/plugin/index.js`, so a `plugin` entry can name the `.agents/plugin` directory. The plugin's default export is now `{ id, server, setup }`: OpenCode 1.x and Kilo Code call `server`, OpenCode 2.x calls `setup`, which registers the gate on the tool `execute.before` hook and adds `.agents/instructions/reply-rules.md` as a system part through the session `context` hook, project copy first and `~/.config/agents/instructions/reply-rules.md` second. Measured on OpenCode 1.19.0 and 2.0.26 and Kilo Code 7.8.9.
- A section in `docs/MCP_SETUP.md` for the unshipped `arch-ops-server`, with the `--with 'mcp<2'` pin it needs and when the pin can go.
- The `home-assistant` MCP server, [ha-mcp](https://github.com/homeassistant-ai/ha-mcp) 8.7.0 over stdio, started as `uvx --env-file <path> ha-mcp==8.7.0` so `HOMEASSISTANT_URL` and `HOMEASSISTANT_TOKEN` come from the credential env file `~/.local/state/agents/workspace/homelab.env`, with no wrapper script and no system-wide variable. `.mcp.json` names the file through `${HOME}` and `.vscode/mcp.json` through `${userHome}`, so both run it. `opencode.json` and `.codex/config.toml` leave it out, so OpenCode, Kilo Code and Codex get it only from the user-level configuration: their project files cannot hold a path that works on every machine, because Kilo Code rejects a project file holding `{env:...}` and Codex has no substitution, and a switched-off project entry overrides the user entry by name, measured on Codex 0.162.1, OpenCode 2.0.26 and Kilo Code 7.8.15. `.github/mcp.json` leaves it out, because its schema has no enable flag. `sandbox-agent/verify-project.sh` and `e2e/testing/4-project-mcp-visibility-test.md` now check each agent against the server names in its own file: `.mcp.json` for Claude Code and the Copilot CLI, the `mcp_servers` tables of `.codex/config.toml` for Codex, and the `mcp` keys of `opencode.json` for OpenCode and Kilo Code, which brings `atlassian` into the OpenCode and Kilo Code checks. A "Home Assistant server" section in `docs/MCP_SETUP.md` covers the token, writing the two keys, the user-scope commands for Claude Code, Codex, OpenCode and Kilo Code in both shells, switching it off in the Copilot CLI, and the minus that `uvx` hands every key of the file to ha-mcp. The MCP badge and the social card count 9.

- `.claude/workflows/skill-audit.js`, a saved Claude Code workflow run as `/skill-audit`. It audits every skill under
  `.agents/skills/` read-only, and a second agent tries to refute each finding before it is reported. It is documented
  in `docs/AGENT_TOOLING.md`, and the update routines in `docs/AGENTS-UPDATE.md` and `README.md` now refresh
  `.claude/workflows` along with the other imported trees.
- A containerised end-to-end sandbox in `sandbox-agent/`. It installs all five agent CLIs, updates them to the latest
  release on container start, imports the shared configuration into a throwaway project, and asserts what each agent
  actually discovers. The repository is mounted read-only and the host home is never touched.
- Two capability test suites in `e2e/`, authored against the `e2e-runbooks` OpenSpec schema. Specs 1 to 5 cover the
  per-project import, specs 6 to 9 cover a global user-home install and refuse to run unless the working directory is
  free of per-project files, so a global result cannot be attributed to the wrong layer.
- [docs/GLOBAL_SETUP.md](docs/GLOBAL_SETUP.md), covering installation of the same skills, subagents and gate into the
  user home, per agent and per shell, with an honest list of what cannot be installed globally.
- `global/bin/update-global.sh` and `global/bin/update-global.ps1`, one command that updates the global install from
  the committed state of the repository, with a dry run and a printed summary. The install copies them to
  `~/.agents/bin`, and every update keeps them current. Both forms match a previously shipped skill folder by path
  prefix, and both stop with an error naming the commit when `git ls-tree` or `git diff` fails.
- One shared preflight rule at `.agents/hooks/preflight_gate.py`, called by every agent surface. The gate is
  enforcing rather than advisory: it denies any tool call from a subagent whose own definition declares no skills,
  and any error inside the gate fails open, except in the repository-boundary helpers, which fail toward deny. Its
  main-thread write rule and its web-research rule were both widened again before this release shipped. The entries
  under Changed below give the state they landed in.
- `.agents/hooks/no_ai_markers_check.py`, the reply formatting check. Claude Code runs it on `MessageDisplay`, which
  shows each reply with its dashes, bold and italic fixed and leaves code untouched, and on `Stop`.
  Codex runs it on `Stop` and GitHub Copilot on `agentStop`. The OpenCode and Kilo Code runner runs it on every tool
  call and on `experimental.text.complete`, which stores a fixed copy of each finished text part.
- One preflight plugin at `.agents/plugin/hooks.js`, declared once by path in the `plugin` array of the root
  `opencode.json`, which both OpenCode and Kilo Code read. It carries no rules of its own: it discovers every hook in
  `.agents/hooks/`, runs them in the order each hook declares, and speaks the versioned JSON envelope documented in
  `docs/hooks-contract.md`.
- GitHub Copilot hook configuration at `.github/hooks/preflight.json`, on `sessionStart`, `subagentStart`,
  `userPromptTransformed`, `preToolUse` and `agentStop`. Event names are camelCase, and each hook entry carries `bash`
  and `powershell` as sibling string fields next to `type`, not a nested `command` object, which Copilot ignores.
- Symlinks `.opencode/agents` and `.kilo/agents`, both pointing at `../.agents/agents`, created and repaired by the
  generator. On Windows they need `git config core.symlinks true` and Developer Mode, or Git checks them out as plain
  text files holding their target path.
- Codex custom agents generated to `.codex/agents/*.toml`, so all five supported agents now receive native subagent
  files from the one canonical `subagents/` source.
- A pytest suite in `tools/tests/`, covering all five hook scripts, the plugin runner, the generator, the lint
  scripts, the update scripts and the live harness, run locally and in CI.
- `tools/pyproject.toml` as the single hand-written declaration of the tooling dependencies and the pytest
  configuration. Every version is an exact pin and no lock file ships beside it, so CI installs the project and its
  `dev` dependency group in one `pip install` command, after pinning pip to a version that understands `--group`.
- `docs/agent-compatibility.md`: a per-surface matrix of what each agent reads (skills, instructions, subagents,
  preflight, MCP), with GitHub Copilot split by client, linked from the README and from `repository-layout.md`.
- Diff-first configuration-file commands at the end of each shell section in `docs/AGENTS-UPDATE.md`, covering the
  five files the routine refresh never touches, plus an ownership table in the section on what the refresh skips,
  naming which half of each file is the consumer's and which should track upstream.
- A `sandbox` job in the CI workflow. It builds the sandbox image once and then runs the container suite three times:
  the per-project import assertions, a global install run twice against the container's own home to prove it is
  idempotent, and a scoped single-agent install that proves only that agent's paths were written. It runs alongside
  `actionlint` and `validate` rather than behind them, and it never touches a runner's real home directory.
- A fifth MCP config file, `.github/mcp.json` (key `mcpServers`, `"type": "local"` for a stdio server), so the GitHub
  Copilot CLI reads a file written in its own literal-values schema instead of Claude Code's `.mcp.json`, which
  carries `${VAR:-default}` substitution syntax the CLI cannot resolve. The CLI's own precedence rule still makes
  `.mcp.json` win over `.github/mcp.json` whenever both name the same server, which every server here does; measured
  against Copilot CLI 1.0.81 and documented as an open limitation in `docs/MCP_SETUP.md`.
- `tools/check-badges.py`, a lint step that fails when a count badge in `README.md` (skills, subagents, MCP servers)
  no longer matches the tree, wired into the CI `validate` job.
- Five subagents: `agent-engineer`, which owns skills, subagent definitions, hooks, MCP blocks and `AGENTS.md`, and is
  the agent the main thread hands web research to now that Rule C denies it directly; `go-pro`; `ml-engineer`;
  `project-manager`; and `release-manager`.
- A `jetbrains-ide-ops` skill: run configuration XML per type and the option-name trap, which `.idea/` files
  are committed and which a build tool regenerates, the root module and per-build Gradle links for a monorepo,
  the cold-reopen procedure, the rename checklist and the Windows traps, each vendor claim carrying its source.
- A `user-communication` skill that every agent reads for how to write a reply to the user and how to ask the user a
  question: self-contained points for a newcomer, the user's own questions answered first, and numbers only on points
  that need the user's decision.
- A `research` skill for answering a question from outside the repository: an ordered source list from Context7
  through vendor docs, vendor source, changelogs and issue trackers down to community sources and general search,
  the deciding sentence quoted with its section and link, measurement before reading where possible, every claim
  labelled verified or inferred with a confidence and a fetch date, and like-for-like comparison tables. It splits a
  broad topic into 3 to 5 sub-questions with one parallel subagent each, prefers recent sources, offers an optional
  long-report layout, and lists Firecrawl and Exa MCP as optional search routes. The `agent-engineer` subagent
  preloads it.
- An `obsidian` skill for working with Obsidian vaults on Windows, Linux and macOS: the `obsidian.json` vault list
  per platform, including Flatpak and Snap, installing `notesmd-cli` (the renamed `obsidian-cli`), non-interactive
  search, create, link-updating move, and a confirm-with-the-user rule before any delete.
- A language-neutral `backend-patterns` skill covering idempotency keys, timeouts and capped retries, the
  transactional outbox, cache invalidation, pagination and graceful shutdown, with the runtime-specific material left
  to `node-backend-patterns` and `springboot-patterns`.
- Two more hooks in `.agents/hooks/`. `markdown_lint_check.py` runs on `PostToolUse` after an edit to a linted file
  and reports violations back as `additionalContext`. `task_list_sync.py` mirrors the Claude Code `TaskCreated` and
  `TaskCompleted` events into `tasks.md` at the project root, injects that file at `SessionStart` including the
  `compact` source, and blocks a `Stop` once while items are open or in progress.
- `tasks.md`, git-ignored runtime state written by that hook and by the model. It is the one path Rule A exempts, so
  the main thread keeps ownership of its own list. A consumer adds `/tasks.md` to their own `.gitignore`.
- Generator validation. `tools/gen_subagents.py` now exits with an error when a canonical subagent lists a skill with
  no folder under `.agents/skills/`, so a renamed skill fails the build rather than silently preloading nothing. It
  also emits a per-format tools list including Copilot's own tool names, sets `permissionMode: plan` on Claude Code
  for the five read-only agents, and accepts `model: inherit`.
- `subagents/*.md` in the markdown lint scope, so a canonical source is held to the same style as the shipped docs.
  The four generated trees stay out of scope, because linting them would report the same violation five times.
- A prerequisites section, a PowerShell block beside every Quickstart command, a Configuration section, and a second
  Mermaid diagram tracing one tool call from the agent through the hook to the gate's allow or deny, all in
  `README.md`.
- An `e2e-runner-max-parallel: <N>` slot in `AGENTS.md.example`, which the orchestration bullet already referred to
  and which had nowhere to be set.
- The OpenCode and Kilo Code plugin injects the preflight reminder on every main-thread prompt through
  `chat.message`, a stable hook in both runtimes. It appends the reminder to the user message as a synthetic text
  part, which reaches the model with the prompt. Only a root session gets the reminder: a subagent's child session
  gets the subagent text instead, and a session the plugin cannot read gets nothing, see Fixed. Measured on OpenCode
  1.18.32 and Kilo Code 7.7.9: the model quoted the reminder back verbatim. `tools/tests/test_hook_runner.py`
  compares the plugin's wording with the Claude Code wiring.
- `.agents/hooks/copilot/prompt_reminder.py`, which GitHub Copilot runs on `userPromptTransformed`. It appends the
  reminder to `transformedPrompt` and returns it as `modifiedTransformedPrompt`, so Copilot now gets the gate text on
  every prompt rather than only at session and subagent start. It sits in a subdirectory, out of the directory the
  OpenCode and Kilo Code runner discovers, so it does not start an interpreter on their every tool call.
- A second fixed text on Claude Code's `SessionStart`, the subagent supervision rule: note how long each background
  subagent should take, check every running one every 10 minutes, and step in only when one is far over or clearly
  looping. The global install in `docs/GLOBAL_SETUP.md` and `sandbox-agent/setup-global.sh` carries it word for word.
- `HOOK_TEXT_EVENT = True`, a declaration in the hook runner contract. The OpenCode and Kilo Code plugin hands
  `experimental.text.complete` only to hooks that carry it, so a finished text part no longer starts an interpreter
  for the gate, the task list and the markdown lint. `no_ai_markers_check.py` is the one hook that declares it.
- `tools/tests/test_claude_wiring.py`, which checks that the Claude Code `PreToolUse` matcher sends every writing tool,
  `PowerShell` and both web tools to the gate, and that the global install carries the same matcher.
- A fourth gate rule: the main thread may not run a script or a module (`python x.py`, `python -m`, `node x.js`,
  `bash x.sh`, `pwsh -File`, `npm run`, `npx`, `uv run`, `pip`, a relative or script-named program, and git's
  `bisect run`, `rebase --exec`, `submodule foreach` and `filter-branch`), because the gate cannot see what a script
  writes. A command that passes `MAIN_THREAD_ALLOWLIST` stays allowed: `python -m pytest`, `node --check` and
  `bash -n`, each with only the options it lists. A project adds entries in `main-thread-allowlist.txt` at its
  root, and this repository lists its markdown, badge and drift checks there. `python tools/gen_subagents.py`
  without `--check`, which the gate used to allow, now denies on the main thread.
- `.github/workflows/agent-live-tests.yml` and `sandbox-agent/live/`, which drive each agent against a real model
  through Requesty: DeepSeek V4 Flash for Claude Code, OpenCode, Kilo Code and GitHub Copilot, GPT-6 Luna on the
  Responses route for Codex. The workflow runs only on `workflow_dispatch`, needs the `REQUESTY_API_KEY` secret, and
  spends money on every run.
- A global fallback in the OpenCode and Kilo Code plugin. A project without its own `.agents/hooks/` now runs the hooks
  from `~/.agents/hooks/`, where `docs/GLOBAL_SETUP.md` installs them, so a global install gates every project. A
  project opts out with an `.agents/no-global-hooks` file. Before this a project that never ran the import had no gate
  on those two tools at all.
- `tools/check-agents-md.py` and its tests, a guard the CI `validate` job runs. It fails on any tracked `CLAUDE.md`,
  on a root `AGENTS.md` or `AGENTS.md.example` of 200 lines or more or of 32 KiB or more, the most Codex reads by
  default, and on any other `AGENTS.md` of 60 lines or more. It is a copy of a guard another project already ran,
  with the template added to the root rule. It stays in `tools/` and is not shipped.
- `windows` and `macos` skills for administering one machine from an agent, with the owner's install and shell order as hard rules. On Windows, PowerShell 7 (`pwsh`) runs every PowerShell command, its install through winget id `Microsoft.PowerShell` is recommended before any fallback to Windows PowerShell 5.1, and software installs through winget first, Chocolatey second and the vendor's installer last, with Scoop only on request. On macOS, everything Homebrew carries installs through Homebrew, a formula for a command line tool and a cask for a GUI app, and only what it lacks comes from the App Store through `mas` or the vendor's installer.
- `machine-health` skill, a read-only health and configuration check for one Linux, macOS or Windows machine. The first run writes a dated baseline into a Health section of `MACHINE.md`, later runs record drift against it, `owner` rows are never overwritten, root and elevated commands go to the owner through Needs root, and findings are handed over rather than fixed. It covers CPU, RAM speed against the module rating and the CPU vendor's quoted limit, disks, system errors, PATH, packages, GPU, displays, audio, network, time sync and the security baseline. The Linux commands were executed read-only on CachyOS, the macOS and Windows ones are marked UNVERIFIED.
- `arch-linux` skill: `scripts/cleanup-leftovers.sh` and a "Real leftovers only" section first in `references/orphans-and-cleanup.md`, with "clean up leftovers" as a new trigger phrase. With no argument the script scans eight groups and removes nothing: pacman cache files of packages no longer installed and versions beyond the last 2, orphans without kernel, microcode, firmware, driver, boot and init packages, paru build folders of packages no longer installed, matched by the `pkgbase` and every `pkgname` in `.SRCINFO` so split packages stay while one is installed, Docker dangling images no container uses and the build cache, Flatpak runtimes no app needs, JetBrains folders of IDE versions no longer installed, found by `dataDirectoryName` in `product-info.json`, the Trash in `~/.local/share/Trash` only, emptied directly and never with `gio trash --empty`, which also empties the trash on other drives, and thumbnails whose `Thumb::URI` file is gone. With `--clean` each group asks `Remove? [y/N]`, and root steps call `sudo` only after the `y`. Stopped containers, named images, volumes and caches of tools in use stay. The Docker section now says stopped containers always stay and `docker container prune` and `docker system prune` are never used and `docker volume prune` only when the owner names exactly what goes, as one statement, and where the containerd image store keeps images, and the Btrfs section says root snapshots keep old Docker data until they go. Tests in `scripts/tests/`, run by `scripts/tests/run-tests.sh` in containers with no network and no host folder, 25 passed, ShellCheck clean.
- `syncthing` skill for running Syncthing 2.x from an agent on Linux, Windows and macOS through `syncthing cli` and the REST API, with no step in the web page. It covers the start as the user (systemd user unit, a logon task, `brew services`), reading the API key into a variable and passing it to curl on standard input, the folder layout under `~/Documents/sync` with the default folder path set to it, the Default Folder that only 1.x created, pairing, adding a folder by its folder ID, the folder types, ignoreDelete for an archive, introducer and autoAcceptFolders off on both sides, moving a folder by pausing it and setting the path, direct addresses for a peer in Docker, the database disk space error under `minHomeDiskFree`, a peer that shows 0 files, and the linuxserver image. The cli commands were executed on Syncthing 2.1.7 between throwaway containers on an isolated network, the Windows and macOS ones are marked UNVERIFIED.
- `proxmox` skill for working with a Proxmox VE 9.2 host from an agent. The main option is an admin token on a user of its own, made with `-privsep 0`, with `PVEAdmin` on `/` and on each node `PVEAdmin` again beside a custom `AgentDownload` role holding `Sys.AccessNetwork`, because `PVEAdmin` lacks that privilege, which downloading an ISO by URL needs, and a role on a deeper path replaces the inherited one. The owner ran those commands on Proxmox VE 8.3.2 and measured the token with `GET /access/permissions`: 35 privileges on `/`, `Sys.AccessNetwork` as well on the node, and no `Sys.Modify`, `Sys.PowerMgmt`, `Permissions.Modify` or `Realm.Allocate`. It comes with the web page path, how to check and revoke it, how to switch to it from a narrower token, and every change and every delete still asked of the owner first. Narrower tokens follow as alternatives: a separated API token with `PVEAuditor`, and, for an owner who wants the agent to resize disks, take snapshots and start or stop VMs, a separated token on a user of its own with `PVEAuditor` on `/`, `PVEVMAdmin` on `/vms` and `PVEDatastoreUser` on `/storage`, with the role contents read from `AccessControl.pm` and the resize check on `Datastore.AllocateSpace` read from `Qemu.pm`. A third alternative adds to that token what creating and deleting a whole VM needs, read from `create_vm` in `Qemu.pm`, `check_vnet_access` in `GuestHelpers.pm` and the upload and download calls in `pve-storage` on both branches: `PVESDNUser` on `/sdn/zones/localnetwork/<bridge>` for the network device, and a custom role with `Datastore.AllocateTemplate` alone on the ISO storage, because `PVEDatastoreAdmin` also carries `Datastore.Allocate`, which can change and remove storage configurations. A second custom role with `Sys.AccessNetwork` on the node, for downloading an ISO by URL, is optional, and 8.x has that privilege only from `libpve-access-control` 8.1.2. Each deeper ACL names the inherited role again, because a deeper permission replaces the one above it, and every delete is asked of the owner for that one VM after its newest backup is named. The token commands and API calls hold on Proxmox VE 8.x as well, checked against the 8.x branches, with the 8.x role contents, which still carry `VM.Monitor` and no `VM.GuestAgent.*`, measured on 8.3.2. The secret in an env file outside any repository and sent to curl on standard input, TLS checked by the cluster CA or a pinned public key, read-only API calls with the privilege each needs, growing a VM disk on the host and then inside a Linux or Windows guest, the free space Ubuntu Server leaves in its volume group, snapshots, `vzdump` and backup jobs, and thin pool data and metadata use with what an overfull pool does. No agent executed anything against a Proxmox host, so every command but the owner's admin token commands is marked UNVERIFIED, and API paths and privileges were checked against the API schema.
- `asus-router` skill for reading an ASUS router over SSH from an agent, on stock Asuswrt 3.0.0.4.388 and 3.0.0.6.102 and on Asuswrt-Merlin where it differs, every change asked of the owner first. SSH runs on the LAN only with password login off and one ed25519 key shared with the other home lab machines, read through the env file keys `ASUS_ROUTER_SSH`, `ASUS_ROUTER_SSH_PORT` and `HOMELAB_SSH_KEY`, with the field labels and nvram names of Administration, System, Service read in the stock GT-AX6000 image 3.0.0.6.102_37437, which carries Dropbear 2020.81 with ed25519, and in the Asuswrt-Merlin source at 3006.102.9. It covers the system log in `/jffs/syslog.log` or `/tmp/syslog.log` with one rotated copy, the WAN log lines of a port link drop, a PPPoE session drop and a DHCP lease, the `nvram get` names for the WAN type, interfaces and state, the PPPoE keep alive options read without printing the PPPoE password beside them, the WAN port link through `/sys` and `ethctl`, reaching the ONT page from the LAN while the WAN runs PPPoE, until reboot on stock and through `wan-event` and `nat-start` on Merlin, and telling a WAN link drop from an ISP outage with a ping log kept in the LAN. The owner tested the SSH login, the log files, the `nvram get` reads, the PPP options, the PPPoE drop lines, the WAN port link with `ethctl`, the routes, interface counters, ping and traceroute on a GT-AX6000 with stock firmware build 386, including a one hour offset between `pppd` lines and the router clock and the absence of `ethtool` there, and those are marked VERIFIED. The ONT steps are changes nobody approved yet and stay UNVERIFIED. The ping log commands ran in a throwaway container. Every other router command is marked UNVERIFIED.
- `homelab-services` skill for running a Docker Compose homelab on one VM from an agent, every change on a server asked of the owner first, with a hub and a reference file per topic. It covers AdGuard Home (a `*.internal` wildcard rewrite, upstreams, query log and statistics retention, that a lower `querylog.interval` deletes the older log file at the next start or hourly check, ignored domains, and an `AdGuardHome.yaml` edit through `docker exec` with a backup and a restart), Uptime Kuma 2.x (monitor intervals, the read-only `/metrics` API key, the `Added label ... is not included in initial labelset` log flood after a new tag, and a monitor edit in the SQLite database with a stop and a backup), a Telegraf network watch with ping, DNS and HTTP probes every second into rotated CSV files and the traffic of `internet_speed`, about 685 MB a test at 200 Mbit/s, Samba with its login in a `.env` file written with hidden input and checked by length, File Browser 2.x and its first admin password, Plex on host networking with a claim token and a read-only media mount, Homepage, Nginx Proxy Manager, deploying from a local clone with `scp`, folders created before the first start, `json-file` log limits per service after a 24.7 GB log filled a disk, a USB or NTFS data disk with `ntfs3`, `ntfsfix -d`, `nofail` and `chattr +i` on the empty mount point, and the symptoms of a full disk. The facts were measured on the owner's homelab on 2026-10-23 against pinned image versions, except that a flagged empty mount point refuses a write, which rests on chattr(1) and the kernel's `fs/namei.c` and is marked UNVERIFIED, and the `AdGuardHome.yaml` and database edits also ran end to end in throwaway containers of `adguard/adguardhome:v0.107.78` and `louislam/uptime-kuma:2.5.5`.
- `homelab-services` skill: `references/local-ca.md`, a local certificate authority that gives every `.internal` name `https`, with a new row in the task table, hard rule 11, three checklist lines, `alpine/openssl:3.5.9` in the baseline, and "https for the .internal names" as a new trigger phrase. It covers why (no public certificate for `.internal`, and the Secure login cookie of the Proxmox web UI), the CA (EC P-256, 10 years, `basicConstraints`, `keyUsage`, and a critical `nameConstraints` permitting `DNS:internal` and excluding every IPv4 and IPv6 address, written without a leading dot as RFC 5280 defines it), why every name is listed rather than `*.internal` (Chromium `X509Certificate::VerifyHostname`), the one-shot Compose service with a pinned openssl image, no network, a read-only root and `:?` variables from `.env` holding the CA in base64, when it issues again (changed names, a replaced CA, under 30 days left) and when it refuses (a name outside the constraint, a wildcard, a CA without the constraint), the optional include `/data/nginx/custom/server_proxy[.]conf` that Nginx Proxy Manager 2.15.1 puts at the end of every proxy host, the `a duplicate listen 0.0.0.0:443` failure when a host also has a certificate picked on its SSL tab, the restart a new certificate needs, trusting the CA on Linux (Arch Linux, Debian and Ubuntu, Chrome's and Firefox's NSS databases), Windows, macOS, iPhone and Android, and revoking it. Each fact is marked VERIFIED with its version and date (OpenSSL 3.5.9 and NSS 3.110 `vfychain` on 2026-10-24 for the name constraint, nginx 1.30.4 for the duplicate listen) or UNVERIFIED where it was only read. `references/nginx-proxy-manager.md` now sends `https` to the local CA with the SSL tab on None, instead of telling you to pick a certificate there, and the skill description was shortened to stay under the 1024 character cap.
- `kde-plasma` skill: `references/widget-development.md` and `references/theme-development.md`, two new rows in the task table, four new trigger phrases ("write a plasmoid", "publish my widget on the KDE Store", "make a Plasma theme", "build a Global Theme"), and the line that kept plasmoid writing out of the skill removed. The widget file covers the package layout and `metadata.json`, `PlasmoidItem` and the Plasma 6 imports, `main.xml` and KCM configuration pages, an own KConfig settings file for data that has to survive a Global Theme layout or a panel reset, keys saved through the KWallet D-Bus API and read with `secret-tool` into curl on standard input, the executable engine and its risks, unit tests with `node --test` and QML tests with `qmltestrunner` in containers with no host folder, the `.plasmoid` zip, `kpackagetool6` install, upgrade and remove, `knshandler` with a `kns://plasmoids.knsrc/api.kde-look.org/<id>` address, and publishing on store.kde.org, with the undocumented download lock box and the OCS API, which answers statuscode 999 for an id that does not exist yet and for a wrong id alike. The theme file covers proving a visual change from source and a render before anyone installs it, the Plasma Style package, which of `translucent/`, `opaque/` and the top-level files Plasma loads, the `blurred-` pieces of desktop widgets and the normal pieces menus use, `[ContrastEffect]` defaults and what it still changes after KWin 6.5 removed the contrast effect, color scheme alpha, style and decoration forks, icon inheritance, the Global Theme `defaults` file and `kdedefaults`, the layout script that deletes every panel and desktop widget, `plasma-apply-lookandfeel --resetLayout`, and a konsave backup and undo order. Facts were read in libplasma, plasma-workspace, plasma5support and KWin v6.7.5, KPackage, KSvg, KNewStuff, KWallet and frameworkintegration v6.31.0, konsave 2.3.0 and the develop.kde.org pages. `kpackagetool6` and `kreadconfig6` behaviour was measured in throwaway folders and the store API answers on 2026-10-23. The rest is marked UNVERIFIED.

### Changed

- `docs/GLOBAL_SETUP.md`, `docs/MCP_SETUP.md`, `docs/AGENTS-UPDATE.md`, `docs/manual-setup.md` and `README.md` give a copy-paste one-line command, followed by a check, for every step that told the reader to edit a file by hand: the global `AGENTS.md` note and rules, the macOS LaunchAgents, the hook wiring of Claude Code, Codex and Copilot (merged from the guide's own JSON block in the temporary copy, replacing only the groups the install wrote), the OpenCode and Kilo Code `skills.paths` and `plugin` entries, the MCP servers per agent, the global and project gitignore lines, migration step 9, the update merges, the undo, turning off or repointing a project server, and taking only the gate half of a split file. Every secret is read through a hidden prompt or from its variable, never from a command line. This also replaces `cp .mcp.json ~/.claude.json`, which overwrote every other setting Claude Code keeps in that file, with `claude mcp add-json --scope user`, and the `~/.profile` token line, which had no `export`, with an exported one.
- `tools/check-badges.py` also checks the skill, subagent and MCP server counts drawn on `docs/assets/social-card.svg`, so the card fails CI the moment it disagrees with the tree, as the README badges already did. The card showed 84 skills and 30 subagents and now shows 67 skills, 35 subagents and 8 MCP servers. Tests in `tools/tests/test_check_badges.py`.
- `task_list_sync.py` never writes `tasks.md` or `tasks.widget.json` in the home directory. A start directory that resolves to home is never a project, even when a linked `~/.agents` gives it a `.agents/hooks`. The user-level copy keeps a non-project session's list and widget together in the directory the session started in, and a session started in home in `$XDG_STATE_HOME/agents`, `~/.local/state/agents` when that variable is unset or relative. The widget no longer goes to `~/.config/agents`. Tests in `tools/tests/test_task_list_sync.py`, each seen failing on the old code first.
- The `machine-health` skill checks where environment variables and zsh files live: shared variables and PATH in `~/.config/environment.d/*.conf`, `~/.zshenv` only importing them, setting `ZDOTDIR` and deduplicating PATH, interactive-only setup in `.zshrc`, nothing in `~/.profile` with zsh as the login shell, zsh files under `$ZDOTDIR` in `~/.config/zsh`, and the graphical session's variables and PATH against the terminal's through `/proc/$(pgrep -x plasmashell)/environ` and `systemctl --user show-environment`. Commands executed read-only on CachyOS with zsh 5.9.2 and systemd 262.
- `global/AGENTS.md.example` no longer lists commit timestamps among the values to ask about in "Working and deciding" rule 9.
- Step 4 of `docs/GLOBAL_SETUP.md` now says to skip the line that sources `60-agents.conf` from `~/.zshenv` or `~/.profile` when the shell already imports every `~/.config/environment.d/*.conf`, gives a `grep` that shows whether it does, and shows the recommended zsh layout: `~/.zshenv` setting `ZDOTDIR` to `~/.config/zsh`, and `~/.config/zsh/.zshenv` deduplicating PATH, importing every `.conf` file under `set -a` and dropping PATH entries that are not a directory.
- On OpenCode 1.x and Kilo Code the reply-style hooks now skip subagent sessions, as they already did on 2.x. `.agents/plugin/hooks.js` places the session through the cached `client.session.get` lookup the gate already used, and a session with a `parentID` hands its tool calls an empty `assistant_text` and its finished text parts skip every `experimental.text.complete` hook, so the em dash rewrite, the markers, status block and question numbering checks never touch a subagent. A session that cannot be read keeps both, the gate still runs for every session, and the `instructions` key in `opencode.json` is unchanged. Placement was measured first with real turns against a mock model on OpenCode 1.19.0 and Kilo Code 7.8.9: the root session answered `session.get` with no `parentID`, the `task` tool's child with the caller's id, both runtimes pass `sessionID` to `experimental.text.complete` (`packages/opencode/src/session/processor.ts` at `v1.19.0`, `v1.18.25`, `v7.8.9` and `v7.5.5`), and a thrown lookup placed every session as unknown rather than as a subagent. Ten cases in `tools/tests/test_hook_runner.py` and twelve real-turn assertions in the project sandbox suite (`verify_reply_style_v1` in `sandbox-agent/lib-opencode2.sh`, with `sandbox-agent/mock-model.mjs` gaining prose-then-tool replies and the `task` tool) cover it. Each capability case fails on the previous plugin, and each regression case fails on a plugin that places every session as a subagent, the defect an earlier `is_subagent: Boolean(sessionID)` shipped, or on one that skips the gate for subagents.
- The markdown lint's default scope covers `global/*.md` and `global/*.md.example`, so `global/AGENTS.md.example`, `global/MACHINE.md.example` and `global/bootstrap-machine.prompt.md` are checked like every other shipped document. The default list now lives in `default_targets` in `.agents/hooks/_check_markdown.py` (`test_a_violation_in_a_global_template_is_caught_by_default`).
- The container sandbox's global install copies `global/AGENTS.md.example` into `~/.config/agents/AGENTS.md`, as step 3 of `docs/GLOBAL_SETUP.md` does, instead of the per-project template, and `verify-global.sh` asserts the file equals the global template and differs from the per-project one. Spec 6 and its tasks template say the same.
- Reply rules and reply-style checks serve the main thread only, because nobody reads a subagent's reply style and both cost tokens. On OpenCode 2.x the plugin's `setup` adds no `.agents/instructions/reply-rules.md` system part to a session whose `parentID` marks it as a subagent, and hands the hooks an empty `assistant_text` for it, so `no_ai_markers_check.py`, `question_numbering_check.py` and `status_block_check.py` cannot block a subagent there, while the gate still runs on every call. A session the plugin cannot place keeps both. Claude Code no longer wires `no_ai_markers_check.py` on `SubagentStop`, in `.claude/settings.json` and in the global settings in `docs/GLOBAL_SETUP.md`, which also stops the Copilot CLI running it through the Claude wiring it borrows. OpenCode 1.x and Kilo Code are unchanged: `instructions` still loads the rules into every agent. Codex and Copilot need no change, since Codex `Stop` and Copilot `agentStop` belong to the main thread. Tests in `tools/tests/test_hook_runner.py` and `tools/tests/test_no_ai_markers.py`.
- The global install moves from `~/.agents` to `~/.config/agents` (`%USERPROFILE%\.config\agents` on Windows), which now also holds the one instruction file `AGENTS.md` and the reply rules. Claude Code stays in `~/.claude`, because `CLAUDE_CONFIG_DIR` has eight open leak issues, with `~/.claude/CLAUDE.md` a real file importing `@~/.config/agents/AGENTS.md`. Codex and Copilot move under `~/.config` through `CODEX_HOME` and `COPILOT_HOME`, Copilot finds the skills and instructions through `COPILOT_SKILLS_DIRS` and `COPILOT_CUSTOM_INSTRUCTIONS_DIRS`, and OpenCode and Kilo Code get an `AGENTS.md` link and `skills.paths`. `docs/GLOBAL_SETUP.md` documents the environment variables per platform, the migration from `~/.agents`, and the OpenCode 1.x and 2.x database clash. Both updaters, the gate, `task_list_sync.py`, the plugin and the container sandbox follow, and the updaters refuse an install still in `~/.agents` with a pointer to the migration.
- The project `opencode.json` declares the plugin as `./.agents/plugin` rather than `./.agents/plugin/hooks.js`.

- Every agent now reads `AGENTS.md` natively, Claude Code included. Claude Code 2.1.277 and later reads it only while
  the project holds no `CLAUDE.md` (`https://code.claude.com/docs/en/memory`), so nothing ships one any more and every
  document that called `.claude/CLAUDE.md` the Claude Code entry point now describes native loading. Measured in a
  Gradle multi-module project on 2026-10-10 with Claude Code 2.1.281, dropping its `.claude/CLAUDE.md`, which imported
  20 `AGENTS.md` files, and shrinking those files cut a session at the repository root from 206,376 to 4,739 tokens of
  instructions, and work in one module folder from 42,757 to 6,516 tokens on average.
- `AGENTS.md.example` is a short index with a new "Writing AGENTS.md files" section: a file holds "before X, read Y"
  links and the few rules nothing else catches, the root stays under 200 lines and 32 KiB, any other file under 60
  lines, and no `CLAUDE.md` is ever added. The detail it used to carry is in `docs/AGENT_TOOLING.md`, which gains an
  "Instruction files" section. `docs/AGENTS-UPDATE.md` gains the one-off step that deletes an old `.claude/CLAUDE.md`,
  and `docs/bootstrap-prompt.md` now checks for a `CLAUDE.md` and for file sizes instead of diffing imports.
- This repository's own `AGENTS.md` follows the same rules. The per-surface wiring details and the known limits of the
  write rule moved to `docs/agent-compatibility.md`, and the local checks to `CONTRIBUTING.md`.

- Every new tracker item now gets a parent and labels when it is created. `project-tracking` says every item except
  an epic has a parent epic, a Subtask takes its item as parent, and an item that fits no epic waits until the
  requester names the outcome it belongs to, never going in without a parent or under a catch-all epic. Its
  parentless search now leaves epics out and should return nothing. `jira-integration` and the `project-manager`
  subagent set the parent epic and the required labels from the project's own list on every new ticket, and every
  other field only when the requester names it. Creating a ticket still needs approval per ticket.
- `AGENTS.md` is about half its former length. The per-surface detail moved to `docs/agent-compatibility.md`,
  `docs/hooks-contract.md`, `docs/GLOBAL_SETUP.md` and `sandbox-agent/README.md`, and the Working Principles section
  stays as it was.
- The live pipeline loads only the `context7` MCP server, through each agent's own mechanism and never an edited MCP
  file, and live test 6 proves it is the only server loaded and answers a `resolve-library-id` call. All eight
  servers added about 34,500 tokens of tool descriptions to every request, and Copilot's subagent test used 206,000
  tokens, above the OpenAI key's 200,000 tokens per minute. The containerised sandbox still checks discovery of all
  eight.
- The live pipeline runs Codex and GitHub Copilot on OpenAI's own API with `gpt-6-luna` and the new
  `OPENAI_API_KEY` secret, while Claude Code, OpenCode and Kilo Code stay on Requesty with
  `deepinfra/deepseek-v4-flash-0731`. Requesty translated Codex's Responses request and dropped the `multi_agent_v1`
  namespace of `spawn_agent`, so no Codex subagent started. Each job receives only the key its agent needs, and the
  health check maps OpenAI's documented errors to plain causes.
- The skills tree consolidated from 65 skills to 55, so each stack is one hub with its depth in `references/` instead
  of a family of sibling skills. Spring Boot went from six skills to two, `springboot-patterns` and
  `java-coding-standards`, absorbing `springboot-security`, `springboot-tdd`, `springboot-verification` and
  `jpa-patterns`. Python went from three to two, `python-patterns` and `pytorch-patterns`, absorbing
  `python-testing`. Go went from two to one, `golang-patterns` absorbing `golang-testing`. MongoDB went from four to
  one, `mongodb-patterns` absorbing `mongodb-connection`, `mongodb-query-optimizer`, `mongodb-schema-design` and
  `mongodb-search-and-ai`. Keycloak went from two to one, `keycloak-patterns` absorbing `keycloak-administration`
  and `keycloak-auth-services`. `frontend-patterns` was renamed `react-patterns`. Every `skills` list in
  `subagents/*.md` names the replacement, and the four generated subagent trees were regenerated.
- Configuration files are no longer templates. `.mcp.json`, `opencode.json`, `.codex/config.toml`, and
  `.vscode/mcp.json` are committed as real files that a consumer pulls and uses unchanged. `AGENTS.md.example` is the
  only `.example` file left in the repo, because only `AGENTS.md` carries repo-specific content while hooks, MCP,
  skills, and subagents are universal.
- MCP mapped one row per file: `.mcp.json` (key `mcpServers`) serves Claude Code, `opencode.json` (key `mcp`) serves
  OpenCode and Kilo Code, which accepts `opencode.json` as a valid config filename, `.codex/config.toml`
  (`[mcp_servers.*]` tables) serves Codex, and `.vscode/mcp.json` (key `servers`) serves Copilot in VS Code. Kilo
  rejects a project-level config file outright when it contains an `{env:VAR}` reference, so the shared
  `opencode.json` carries none and declares `context7` without a `headers` block. A paid Context7 key now belongs in
  a user's own global OpenCode or Kilo config. The GitHub Copilot CLI got its own file, `.github/mcp.json`, listed
  separately under Added above, once the CLI's inability to resolve `.mcp.json`'s substitution syntax was measured.
- Kilo Code moved its configuration root to `.kilo/` and reads `.agents/skills/` natively, so its subagent tree is now
  a symlink to the shared `.agents/agents/` rather than a generated copy of its own.
- Codex preflight hooks moved into inline `[[hooks.*]]` tables in `.codex/config.toml`. Codex supports both that form
  and a separate `hooks.json`, and warns when a single configuration layer carries both.
- The subagent generator emits four trees (`.claude/agents/`, `.agents/agents/`, `.codex/agents/`, `.github/agents/`)
  and maintains the two agent symlinks, instead of writing one independent copy per tool.
- Widened Rule A in `.agents/hooks/preflight_gate.py` to deny a main-thread write of any file resolving inside the
  repository working tree, removing the earlier exemption for markdown, configuration, and documentation. A write
  that resolves outside the repository, a write to the null device, and a git branch switch stay allowed, so the
  main thread keeps full use of git; a `git checkout` or `git restore` that overwrites a tracked file is still
  denied.
- Added Rule C to the same gate: it denies the main thread a direct web fetch or web search call, currently scoped
  to the Claude Code format only, because no confirmed tool name exists yet for the equivalent call on Codex.
- Changed caller identification in the gate from a boolean to a tri-state (subagent, main thread, unknown). GitHub
  Copilot's `preToolUse` payload carries no field that identifies the caller, and its wiring never passes
  `--subagent`, so its identity now resolves to unknown and none of Rule A, Rule B, or Rule C fires there; the
  surface is left unenforced rather than denied blind.
- Corrected the GitHub Copilot claims. Copilot does have a per-turn injection channel, `userPromptTransformed`, on the
  CLI and on the cloud agent. Copilot hooks are no longer CLI-only and run in VS Code and JetBrains from the same
  `.github/hooks/` path. The Copilot CLI additionally reads hooks from `.claude/settings.json`, while the JetBrains
  plugin does not: it hardcodes `.github/hooks/**/*.json` and rejects PascalCase event names. The JetBrains plugin also
  scans `.claude/agents` but understands only its own `*.agent.md` format, so subagent definitions are not shareable.
- CI validates the five real configuration files and the two hook files instead of the deleted templates, and runs the
  new pytest suite.
- Documentation updated to the verified mid-2026 state: GitHub Copilot, including the JetBrains plugin, reads
  `AGENTS.md` and `.agents/skills/` natively, and Codex gained custom agents, hooks, and project-level config.
- The import flow renames the one remaining template to its real name (`mv AGENTS.md.example AGENTS.md`) instead of
  copying it, so a consumer keeps no dead `.example` twin and a remaining `.example` marks a template not yet
  activated.
- CI is no longer manual. `.github/workflows/ci.yml` runs on every pull request and on every push to `master`, and
  keeps `workflow_dispatch` so it can still be started by hand and `workflow_call` so the release workflow goes on
  calling it. Nothing fires without a push or a pull request. `AGENTS.md` and `CONTRIBUTING.md` no longer claim
  otherwise.
- The sandbox job checks out full history and puts the commit under test on a `master` branch before starting the
  container. The import inside the container reads `agent-standards/master`, and a pull request checkout is a detached
  HEAD with no branch for it to find.
- `AGENTS.md` now records why the Claude Code hook block the GitHub Copilot CLI also reads is inert on that surface,
  and why widening it would be worse than leaving it alone. Copilot names its tools in lower case and compares a
  matcher anchored and case sensitively, so the PascalCase Claude pattern never matches there, and the CLI would run
  the gate twice per tool call if it did.
- Claude Code's `PreToolUse` command, from a one-line Python wrapper that discarded the gate's standard error with
  `subprocess.DEVNULL` to a direct call. `.agents/hooks/preflight_gate.py` now silences its own standard error:
  `main()` swaps `sys.stderr` for a null sink for the duration of the call and restores it in a `finally`, so Claude
  Code can call the script directly like every other wiring already does. The wrapper cost a measured 119 ms of a
  290 ms gate call. The direct call now measures around 110 ms. The `plain` format that OpenCode and Kilo Code read,
  where standard error is the deny channel, is unchanged.
- Every pinned version in the pipeline and in the sandbox container, bumped by hand now that Dependabot is gone. The
  three actions keep their commit-hash pin with a version comment: `actions/checkout` v4.2.2 to v7.0.1,
  `actions/setup-python` v5.3.0 to v7.0.0, and `reviewdog/action-actionlint` v1.72.0 to v1.73.2. The first two now run
  on Node 24, which is what the deprecation warning on every run was about. The `validate` job moves from Python 3.12,
  which has been security-fix-only since April 2025, to 3.14. `pip==26.2.1` was already the current release and is
  unchanged.
- The two pinned Python dependencies in `tools/pyproject.toml`, now that CI runs on Python 3.14. `pyyaml` moves from
  6.0.2 to 6.0.3, the release that added Python 3.14 support. 6.0.2 publishes no wheel newer than cp313, so every
  install on 3.14 fell back to the source archive and compiled the C extension on the runner. 6.0.3 publishes a cp314
  manylinux wheel and pip downloads that instead. `pytest` moves from 9.0.3 to 9.1.1. Nothing here uses what 9.1.0
  deprecated or changed: the suite defines no fixtures and no custom markers, every `parametrize` argument list is a
  literal list, and its `conftest.py` holds only path constants that the test modules import directly rather than
  anything pytest has to discover. One 9.1.0 fix does reach it, because `--strict-markers` and `--strict-config` in
  `addopts` had been silently ignored since 9.0 and now take effect again. 9.1.1 rather than 9.1.0 because 9.1.0 shipped
  three regressions of its own and the patch release costs nothing. `setuptools` was checked at the same time and 84.0.0
  is still the current release.
- The pinned agent CLI versions in `sandbox-agent/Dockerfile`: Claude Code to 2.1.250, Codex to 0.150.1, OpenCode to
  1.18.25, Kilo Code to 7.5.5, and GitHub Copilot CLI to 1.0.81.
- The runner label, from the floating `ubuntu-latest` to the exact `ubuntu-24.04` it resolves to today. Ubuntu 26.04 is
  in preview, and when it reaches general availability GitHub moves the `-latest` label over one to two months. With no
  Dependabot to open a pull request, a floating label is the one version in this repo that could change under us
  without a commit, so it now matches how everything else here is pinned.
- The skill catalogue, from 85 folders to 65. Eighteen `flutter-*` skills folded into `dart-flutter-patterns`, and
  `nextjs-best-practices` and `nextjs-turbopack` into `nextjs-app-router-patterns`, each as one hub manifest with a
  `references/` file per topic instead of a family of siblings competing to match the same phrase.
- Every skill manifest now carries standard front matter, `name` and `description` plus an optional `license` or
  `compatibility` and nothing else, following the open Agent Skills specification at
  `https://agentskills.io/specification`. Descriptions are written in trigger form: what the skill covers, the
  phrases a user would actually say, and what it is not for with the skill that owns that instead. Depth moved out of
  the manifests and into `references/`.
- `automation-audit-ops` renamed to `automation-inventory`, and the old `backend-patterns` renamed to
  `node-backend-patterns` to free the name for the language-neutral skill listed under Added.
- `ascend-web-scrapper` renamed to `ascend-web-hunter`, and the `kicad` skill expanded. `ascend-web-hunter` now
  triggers only on pages that block normal fetching or need a login, and names `research` as the skill for general
  research and web search.
- The comment rule in `coding-standards` now requires a ticketed task marker rather than tolerating one. A gap left
  deliberately unimplemented must name what is missing and the ticket that closes it, and a gap with no marker is a
  defect. The ban survives by its real criterion, a reference standing in place of the explanation, not a ticket
  appearing at all. Placeholders across `coding-standards`, `code-formatter` and `git-workflow` moved to a generic
  `TICKET-001` so no example carries a reader into someone else's tracker.
- `project-tracking` rewritten to be tracker-independent. The always-loaded body is halved and the per-tracker detail
  moved to a reference file that loads only when an agent is acting inside a named tracker.
- Eight skills no longer mandate one test-phase comment convention. The rule is stated once in `coding-standards`,
  which shows the same test labelled both ways so the choice is visibly the project's.
- The sandbox grants the Copilot CLI folder trust through its own `trustedFolders` setting, scoped to the one
  throwaway project, so the CLI's MCP assertion runs against a trusted workspace.
- `AGENTS.md.example` carries no bold or italic markers any more, matching the style the formatting hook enforces on
  replies. Its gate section now carries the same rules as `AGENTS.md`, written for a consumer: the reminder and the
  subagent text word for word, the script-run rule with `main-thread-allowlist.txt` as the project's own extension
  file, every wired event per agent, and the fail-open rule with its fail-toward-deny boundary helpers. Detail that
  only this repository needs stays in `AGENTS.md`.
- The sandbox base image, from `node:24-bookworm-slim` to `node:24-trixie-slim`. Node 24 is still the active long-term
  support line, Node 26 does not become one until October 2026, but Debian 13 (trixie) has been stable since August
  2025 and bookworm is oldstable. The image gains the newer distribution toolchain that comes with it: python3 3.13
  instead of 3.11, git 2.47 instead of 2.39.
- Claude Code's `Stop` check blocks only on what the display fix cannot remove, such as a semicolon. It trusts the
  display fix only where it ran: the `MessageDisplay` hook records, per session and message id, every line it changed,
  and `--display-fixed` skips a fixable marker only on a recorded line. A reply with no record, because the display
  hook is older than Claude Code 2.1.152, failed or could not write its file, is checked in full. Measured on Claude
  Code 2.1.281 with `claude -p`: `MessageDisplay` ran before `Stop` and the check stayed silent, and replaying the same
  `Stop` payload without the record blocked.
- The hook runner envelope moved to contract version 3. `agent_type` now names the primary agent as well as a
  subagent, so it no longer tells the main thread from a subagent on its own, and `is_subagent` may be absent. Version
  2 always sent `is_subagent`.
- The preflight reminder wording, identical in every wiring: it now also tells the agent to follow the
  `user-communication` skill, to answer every question in the prompt before starting the work, and to end every reply
  with the status block. The status block is now spelled out as the exact template, line breaks and blank lines
  included, with the finished lines as `~~DONE: ...~~`. Claude Code prints it with `echo` and real newlines, Codex and
  Copilot carry `\n` escapes in JSON printed by `printf '%s\n'` on POSIX and `echo` in PowerShell.
- `user-communication` keeps its rules and pointers in the manifest, and its depth in three reference files:
  `writing-style.md`, `question-points.md` and `status-block.md`.
- The claude-format formatting check now recognises the GitHub Copilot CLI's borrowed `Stop` by three fields the hooks
  reference documents for its VS Code compatible payload together: `stop_reason` present, `timestamp` an ISO 8601
  string, and no `last_assistant_message`. `stop_reason` alone was the only signal before, one field Claude Code could
  add in any release, which would have silenced the check on Claude Code itself.
- The OpenCode and Kilo Code plugin resolves its interpreter the way every other wiring does, `python3` first and
  `python` second, keeping the first name that answers a one-line probe, so a Windows Store alias that exists but runs
  nothing is skipped. It used to pick `python` on Windows and `python3` everywhere else. It also reads a hook's
  declarations from the first 16384 characters instead of 4096, because the formatting check's docstring had grown
  past 4096 and its `HOOK_ORDER` would have fallen back to the default.
- `AGENTS.md`, `docs/GLOBAL_SETUP.md` and spec 6 no longer claim that the Claude Code hook commands parse in both bash
  and PowerShell. They are POSIX shell. Claude Code passes a command hook "to a shell: `sh -c` on macOS and Linux, Git
  Bash on Windows, or PowerShell when Git Bash isn't installed", and Claude Code 2.1.281 on Windows 11 with Git Bash
  ran a probe hook under bash 5.3.9. PowerShell rejects these commands with a parse error, so on Windows without Git
  Bash every Claude hook allows, and the setup docs now say to install Git for Windows there.
- `AGENTS.md` records the known limits of the main-thread write rule in its gate section, with the policy that the
  rule is re-audited only when it changes and a newly found limit is added to that list.

### Fixed

- The documents said the GitHub Copilot CLI cannot expand `${VAR}` in a project file, picks between `.mcp.json` and `.github/mcp.json` by server name, passes only `PATH` to a local server, and cannot start `home-assistant`. Measured on Copilot CLI 1.0.103 on 2026-10-25 in a throwaway container, it expands `$VAR`, `${VAR}` and `${VAR:-default}` in `command`, `args`, `env`, `url` and `headers` in `.mcp.json`, `.github/mcp.json` and `~/.copilot/mcp-config.json`, it reads `.github/mcp.json` only in a folder that has no `.mcp.json`, every local server receives the whole environment of the process that started the CLI, and `home-assistant` starts from `.mcp.json` with `${HOME}` expanded. `docs/MCP_SETUP.md`, `README.md`, `docs/AGENT_TOOLING.md`, `docs/agent-compatibility.md`, `docs/repository-layout.md`, `docs/manual-setup.md`, `docs/bootstrap-prompt.md`, `AGENTS.md.example`, `e2e/testing/4-project-mcp-visibility-test.md`, `sandbox-agent/README.md`, the comment above `agent_configure` in `sandbox-agent/live/copilot.sh` and two check labels in `sandbox-agent/verify-project.sh` now say so. `.github/mcp.json` stays, as the fallback for a folder that has no `.mcp.json`. The steps that wrote tokens into a local copy of `.github/mcp.json` are gone, and the Home Assistant section adds `copilot mcp disable home-assistant` and `copilot mcp enable home-assistant`. The sandbox image moves from `@github/copilot@1.0.81` to `@github/copilot@1.0.103`.
- `docs/MCP_SETUP.md` said an exported token reaches a Codex server. Codex starts a local server with a cleared environment and passes only `DEFAULT_ENV_VARS` (on Unix `HOME`, `LOGNAME`, `PATH`, `SHELL`, `USER`, `__CF_USER_TEXT_ENCODING`, `LANG`, `LC_ALL`, `TERM`, `TMPDIR`, `TZ`), the certificate variables, the names in `env_vars` and the `env` table, read in `codex-rs/rmcp-client/src/utils.rs` and `codex-rs/utils/pty/src/child_command.rs` at `rust-v0.162.1` on 2026-10-25. The guide now says so and how to forward a token with `env_vars`. The server counts written in prose in `README.md`, `docs/MCP_SETUP.md`, `docs/AGENT_TOOLING.md`, `docs/agent-compatibility.md`, `sandbox-agent/README.md` and `e2e/testing/8-global-mcp-visibility-test.md` are gone, because a count lives only in the badge and on the social card.
- An updater that replaced itself with a longer copy failed after it had finished. `global/bin/update-global.sh` ended on `main "$@"`, so once `main` returned the shell read on from the byte offset it had reached in the old copy, which `cp` had overwritten in place. Measured on 2026-10-23, the old copy of 12487 bytes read the new one of 12609 bytes and ended with `update-global.sh: line 395: ooling: command not found` after every update had landed. The last line is now `main "$@"; exit`, so the shell parses that whole line before it runs it and never reads the file again. `test_an_updater_that_replaces_itself_with_a_longer_copy_finishes_cleanly` in `tools/tests/test_update_global.py` runs an installed copy that installs a copy 122 bytes longer over itself. Against the old script it failed with exit 127 and `ooling: not found` under dash, and it passes now. `update-global.ps1` needs no change: PowerShell reads a script to the end and closes it before it runs it (`ReadScriptContents` in `src/System.Management.Automation/engine/ExternalScriptInfo.cs` calls `scriptReader.ReadToEnd()`), and the same test passes for it on PowerShell 7.6.8, before and after this change.
- Both updaters told you to merge a hook wiring change into your own files by hand. They now name the one-line command under "Per-agent setup" in `docs/GLOBAL_SETUP.md` that writes the hook file of each agent, and the tests in `tools/tests/test_update_global.py` match the new wording.
- An update of another home linked that home's skills into your own Codex home. Both updaters ran `sync_skill_links.py` with only `HOME` (and in `update-global.ps1` also `USERPROFILE`) pointing at the home given by `--home-dir` or `-HomeDir`, so the `CODEX_HOME` of the person running them reached `_codex_home` in the hook, and the links `alpha`, `delta` and `mine` landed in that folder's `skills` instead of in the updated home. Both updaters now also set `CODEX_HOME` to `.config/codex` inside the home they update, the folder they already update the Codex subagents in. The hook reads no other variable that names a place: `CLAUDE_CONFIG_DIR`, `COPILOT_HOME` and the XDG base directory variables play no part, and neither updater reads them. `test_an_update_of_another_home_links_nothing_into_the_callers_agent_homes` in `tools/tests/test_update_global.py` points `CODEX_HOME`, `CLAUDE_CONFIG_DIR` and `COPILOT_HOME` at three stand-in folders. In a container on the code before the fix it failed for both `sh` and `pwsh` with `{'CODEX_HOME': ['alpha', 'delta', 'mine', 'skills']} != {'CODEX_HOME': []}`, and it passes for both after it. `docs/GLOBAL_SETUP.md` says so under "The skill link hook".
- Skills named skills that a reader may not have. `research` sent the wording of the reply to `user-communication`, a skill removed in f6df036, in its description, a "When not to activate" bullet, rule 20, "Related skills", its checklist and `references/evidence-and-output.md`, and every one of those mentions is gone. `research`, `ascend-web-hunter`, `ascend-memory` and `audio-scribe` also named `ascend-web-hunter`, `ascend-memory` and `audio-scribe` as if every project carried them, though each needs its own self-hosted service. Each mention now says to use the skill if it is installed and what to do without it, and "Pages that block fetching" in `research/references/source-order.md` says how to report a page no route could read.
- The updater tests wrote skill links into the real Codex home. `run_updater` in `tools/tests/test_update_global.py` handed the updater the whole test environment with only `HOME` and `USERPROFILE` replaced, so a `CODEX_HOME` set on the machine reached `_codex_home` in `.agents/hooks/claude/sync_skill_links.py`, and `test_an_update_brings_the_claude_code_skill_links_in_step` left the links `alpha`, `delta` and `mine` in the real `~/.config/codex/skills`, pointing into a pytest temp folder that was later deleted. Found on a real machine on 2026-10-23. A new autouse fixture, `isolated_home_directory` in `tools/tests/conftest.py`, now gives every test a fresh `HOME` and `USERPROFILE` and removes `CODEX_HOME`, `CLAUDE_CONFIG_DIR`, `COPILOT_HOME` and the four XDG base directory variables. That test now also checks the Codex links in its own home, and `tools/tests/test_isolated_home_directory.py` fails if the fixture stops covering a variable. In a container with `CODEX_HOME` pointing at a stand-in folder, the old test left the three links there and the fixed suite leaves it empty.
- `sandbox-agent/setup-global.sh` assigned `PREFLIGHT_JSON` and never read it, which ShellCheck 0.10.0 reported as SC2034 under `--severity=style`. The assignment is gone, nothing else in the repository named it, and `shellcheck --severity=style -x -P SCRIPTDIR sandbox-agent/*.sh` now reports nothing.
- Outside a git repository the OpenCode 1.x and Kilo Code plugin made the whole disk the project. Both runtimes hand `server` the worktree `/` there (OpenCode 1.18.25 `packages/opencode/src/project/project.ts`: `data.id === ProjectV2.ID.make("global") && !data.vcs ? "/" : data.directory`), and `.agents/plugin/hooks.js` took the worktree as the root, so the envelope `cwd` was `/` from every non-git start folder, measured on 2026-10-13, so the gate judged every path against the whole disk instead of the start folder, and the hooks a non-git start folder shipped were never found. The root is now the worktree only while it is a git root holding the start folder, compared after links are followed, and the start folder otherwise, which is the folder Claude Code, Codex and OpenCode 2.x already treat as the project. Inside a git repository nothing changes, and a session started in home still never makes home a project for `task_list_sync.py`. Six tests in `tools/tests/test_hook_runner.py` failed on the old plugin, among them `test_a_session_started_outside_a_git_repository_uses_its_start_folder` and `test_the_shipped_gate_outside_git_protects_the_start_folder_and_not_the_whole_disk`, and three guard the git cases. `verify_start_folder_v1` in `sandbox-agent/lib-opencode2.sh` runs real 1.x and Kilo Code turns from a non-git start folder in both suites, and on the old plugin failed two assertions in each, on OpenCode 1.18.25 and Kilo Code 7.5.5.
- A global OpenCode or Kilo Code plugin started in the home directory stood down, and so ran no gate, when `~/.agents` was a link to `~/.config/agents`, because `standsDown` in `.agents/plugin/hooks.js` compared the two plugin paths without following links and took its own file for a project copy. It now compares real paths through `fs.realpathSync`, and a path that cannot be followed is compared as written. Tests `test_global_plugin_started_in_home_does_not_stand_down_for_a_linked_copy_of_itself` and its OpenCode 2.x twin in `tools/tests/test_hook_runner.py`, both seen failing on the old plugin.
- Eleven pytest failures that also failed on a clean `HEAD`. The hooks were right and the tests were stale: commit 31cf8f6 changed `status_block_check.py` to deny only on a user-reply event and to require the tail shape in `.agents/instructions/reply-rules.md`, and added the `todo.updated` handler to `.agents/plugin/hooks.js`, without touching either test file. `tools/tests/test_status_block_check.py` now drives a reply event with the current tail shape, so its five "exits zero" cases stop passing vacuously, and asserts that a tool event and a subagent payload log without blocking. `tools/tests/test_hook_runner.py` expects the three handler keys and drives `todo.updated` through a new `todo` step in `tools/tests/hook_runner_driver.mjs`. Every new deny case was seen to fail against a mutated hook.
- Spec 6 still looked for the global hooks under `/.agents/hooks/` in twelve jq checks, and its tasks template named `~/.agents` in six places, said `~/.claude/skills` is a link, and listed Kilo Code instruction checks the spec no longer makes. Against a real global install in the sandbox the old checks pass 0 of 12 and the new ones 12 of 12.
- Skills Claude Code synced from claude.ai landed in the shared skills tree. The guide linked `~/.claude/skills` to `~/.agents/skills` as a whole, so `~/.claude/skills/synced/` was `~/.agents/skills/synced/`, which every other agent scans and the updater reported as `skip ~/.agents/skills/synced (not an upstream skill)`. Found on a real install on 2026-10-13. Codex does the same with `$CODEX_HOME/skills/.system/`, measured with Codex 0.162.1. Both folders are now real directories of per-skill links kept by `sync_skill_links.py`, and both updaters ignore `synced`, `.trash` and dot folders (`test_claude_code_owned_folders_in_the_skills_tree_are_not_reported`).
- `docs/GLOBAL_SETUP.md` said OpenCode falls back to `~/.claude/CLAUDE.md` and that Kilo Code reads no global `AGENTS.md`. OpenCode 2.0.26 does not fall back and ignores the `instructions` key, and Kilo Code 7.8.9 reads `~/.config/kilo/AGENTS.md`, so every agent now gets an `AGENTS.md` link in its own directory.
- The plugin did not load on OpenCode 2.x, which calls a default export's `setup` and never `server`, so a 2.x session ran with no gate at all. The plugin now exports both (`test_opencode_2_denies_through_the_tool_hook`). 2.x has no hook after a finished reply, so there the formatting check only blocks the next tool call.
- Read-only subagents were not read-only on OpenCode and Kilo Code. Both read the `tools` map as overrides on top of every tool, so `code-reviewer`, `security-auditor` and the other `read`, `grep`, `glob` agents still had `edit` and `bash`. The generator now emits `permission` with `edit: deny` unless `write` or `edit` is listed and `bash: deny` unless `bash` is (`test_a_read_only_agent_is_denied_edit_and_bash_on_opencode`), and the 14 affected definitions are regenerated.
- Moving the gate to `~/.config/agents/hooks` would have made `~/.config` look like a project to Rule A and hidden every global subagent tree from Rule B, and sent `task_list_sync.py` to `~/.config/tasks.md`. Both hooks now recognise the user-level install (`test_a_config_install_reads_every_agent_tree_of_the_global_layout`, `test_the_user_level_copy_keeps_the_list_in_home_and_the_widget_beside_itself`). This one was introduced by this change and caught by its own tests before it shipped.
- `arch-ops-server` 3.4.0 fails at start with `AttributeError: 'Server' object has no attribute 'list_resources'`, because it declares `mcp>=1.0.0` and `mcp` 2.0 removed the decorator API. `docs/MCP_SETUP.md` now starts it with `--with 'mcp<2'`, measured both ways on 2026-10-13.

- The markdown lint hook now works in a consumer repository. Its rules moved from `tools/check-markdown.py`, which never ships, to `.agents/hooks/_check_markdown.py`, which every import of `.agents/hooks` delivers, and `tools/check-markdown.py` only runs that file for CI. The leading underscore keeps the OpenCode and Kilo Code runner from treating it as a hook.
- Skills no longer link into other skill folders, so a consumer that removed a skill it does not use, such as `node-backend-patterns`, keeps no dead link in the rest. Each link now names the other skill in backticks, and the markdown lint rejects a skill link that leaves its own folder.
- The 85 defects the first skill audit confirmed across the skills. Rules that their own examples contradicted now
  agree with them. Skills that handed the same job to each other in their "when not to activate" lists now name one
  owner. Broken references are repaired, among them a link into `subagents/`, which consumers never receive.
- The `code-reviewer` skill description held an unquoted colon, so YAML cut it in half. It is now quoted and loads
  whole.
- The `jira-integration` skill named `jira_*` tools that no server here provides. It now points at Atlassian's own
  remote MCP server and uses that server's tool names, and it proposes each tracker write to the user rather than
  making it.
- `AGENTS.md` defects: the GitHub Copilot `preToolUse` matcher cell in the wiring table was garbled, a pointer named a
  follow-up that did not exist, and a claim was still marked unverified after it had been measured. Comments in
  `.agents/hooks/preflight_gate.py` cited an `AGENTS.md` "Defect 3" section that no longer exists, and now cite
  nothing.
- Live test 2 reports `KNOWN-GAP` on GitHub Copilot, not `FAIL`, when the subagent never tried to write under the
  `CRITICAL: Do NOT write output to files` block that Copilot CLI 1.0.81 appends to every custom subagent's system
  prompt. In live run 36176881215 docs-architect was offered `apply_patch` and still made no tool call. A write the
  subagent tried and lost stays a `FAIL`.
- The formatting check asks a blocked subagent for its whole report again rather than for `Correction:` lines. A
  subagent's next reply replaces the report its caller receives, so in live run 36176881215 Copilot handed the main
  thread only the corrected sentence and dropped the docs-architect's statement that it had not created the file.
- The Codex and Copilot live jobs share one job concurrency group and no longer run side by side. Both draw on one
  OpenAI organisation's per-minute token limit for gpt-6-luna, and in live run 36168529868 OpenAI refused Copilot's
  first request with a 429 because the Codex job had already used most of that minute.
- The formatting check skips a Copilot `agentStop` whose `sessionId` does not name the session log it points at. A
  subagent's agentStop carries its own id with the main session's log and fires before its final reply is written
  there, so in live run 36168529868 the check blocked the docs-architect subagent over a semicolon in its first
  message rather than its last.
- Every GitHub Copilot subagent that may write or edit now lists `apply_patch`, and the Copilot gate matcher names it.
  Copilot gives a GPT model `apply_patch` as its only file tool, and neither `create` nor `edit` grants it, so in live
  run 36168529868 the docs-architect subagent reached gpt-6-luna with only `view` and `bash`, under a system prompt
  telling it not to write files, and reported the file as not created.
- The preflight gate reads the patch a shell `apply_patch` command carries, from a heredoc, a pipe or its argument, and
  denies a main-thread write it names. Codex runs `apply_patch <<'PATCH'` from `exec_command` as a file change, and
  live run 36163866070 wrote `live-probe/main-thread.txt` that way past the gate.
- The Copilot `userPromptTransformed` reminder prints nothing for a prompt that opens with the subagent text, which
  Copilot puts at the start of a subagent's first prompt. In live run 36176881215 both subagent sessions were told
  to delegate their own task.
- The Codex `UserPromptSubmit` reminder prints nothing when the payload carries `agent_id`. Codex fires that event
  for a subagent's opening message too, so a subagent was told to delegate its own task.
- The gate treats a `COPILOT_CLI` call as an unknown caller only when the payload has no `transcript_path`, so Claude
  Code started from a Copilot shell keeps its main thread gated.
- Live test 1 passes when the gate denied the main-thread write and the file came from a subagent the model then
  started. The Codex live checks read hook text only from developer messages, so the imported `AGENTS.md` no longer
  counts as the reminder. The OpenAI health check counts a reply cut off at the token limit as an answer instead of
  as `model_not_found`.
- The Codex live test reports a rejected `spawn_agent` call, one Codex answers with `unsupported call`, as the
  subagent never starting. It used to count that call as a started subagent.
- The preflight gate treats a `claude`-format call made by the GitHub Copilot CLI, recognised by `COPILOT_CLI` in the
  hook environment, as an unknown caller. The CLI runs the `.claude/settings.json` hooks with no `agent_id`, so every
  write a Copilot subagent made was denied as a main-thread write. `AGENTS.md` no longer claims that wiring is inert
  on Copilot.
- `docs/GLOBAL_SETUP.md` shows the GitHub Copilot wiring literally, as it already did for Claude Code and Codex.
- The live pipeline runs `setup-project.sh` through `bash`, because a Windows checkout commits scripts without the
  executable bit. Each run gets its own `GIT_CONFIG_GLOBAL` under the work directory, so a local run never writes the
  user's `~/.gitconfig`. Codex on Requesty uses `openai/gpt-6-luna`, the id the Requesty model list carries.
- The preflight gate treats PowerShell's local-computer name `.` as this machine before it trims trailing dots. The
  trim left an empty name whose resolution differs by platform, so the remote-run rule was platform dependent and
  allowed `Invoke-Command -ComputerName .` on Linux.
- The preflight gate reads a .NET file call whatever shell the tool name claims. Codex on Windows names its shell tool
  `Bash` and runs the command in PowerShell, so `[System.IO.File]::WriteAllText($target, ...)` from a Codex main
  thread was read as a POSIX command and allowed. A `[System.IO.*]` or `[IO.*]` call, and a `New-Object` of an
  `IO.*` or `System.IO.*` type with or without `-TypeName`, now denies under any shell tool when its path is a
  variable, an expression or an expandable string, and the table of known writers adds the async
  `WriteAll*` and `AppendAll*` methods, `AppendAllBytes`, `OpenHandle`, `CreateSymbolicLink`, `Encrypt`, `Decrypt`,
  `SetAttributes`, `SetUnixFileMode` and the `Set*Time` methods on `File` and `Directory`.
- Live test 1 in `sandbox-agent/live/lib.sh` counts any gate denial as the block. It matched only the file-write
  sentence, so a correct denial with the script-run reason was recorded as a failure. It now reads the fixed text of
  every `RULE_*_REASON` out of `preflight_gate.py`, and a probe file that landed still fails. Live test 2 also
  fails unless the subagent's own transcript carries the subagent text and not the main-thread reminder, read
  through a new `agent_subagent_context` function in each agent script.
- A subagent no longer gets the main-thread reminder, which tells its reader to delegate. On OpenCode with
  `opencode-go/gpt-6-luna` the plugin's `chat.message` handler appended it to the subagent's task prompt too, and the
  delegated `docs-architect` subagent refused to write in three runs out of three. Every surface that reaches a
  subagent now injects a separate subagent text instead, held word for word to a second block in `AGENTS.md`: the
  plugin in a child session, Claude Code and Codex on `SubagentStart` (new on Claude Code), Copilot on
  `subagentStart`. With it, three isolated OpenCode runs out of three had the subagent write the file.
- The preflight gate closes every gap from the third security audit. High: a leading assignment, `env`, `export`,
  cmd `set`, `setx`, `$env:`, `Env:` or `SetEnvironmentVariable` setting of a variable that changes which program or
  file a command uses (git configuration, directory, work tree and external diff, library preloads, `NODE_OPTIONS`,
  `PYTHONPATH`, `PYTHONSTARTUP`, `PERL5OPT`, `RUBYOPT`, `BASH_ENV`, `ENV`, `PATH`, `PYTEST_ADDOPTS` and more) denies.
  The file a git `--output` option, `format-patch`, `archive -o` or `bundle create` writes is judged, a `git config`
  write lands in `.git/config` or its `-f` file, and a setting that runs a program or includes more configuration
  denies.
- High: every built-in allowlist entry names the only options it takes. pytest options that load a plugin,
  configuration, root directory or conftest from elsewhere, set the temporary base, write a report or import a
  warning category deny, and so do test paths outside the repository. `node --check` takes no preload, `bash -n`
  nothing that runs the script. A shell handed an allowlisted script file has the script read as shell code.
- High: build runners and compilers (`make`, `cargo`, `go run`, `go generate`, `go test`, `dotnet`, `mvn`, `gradle`,
  `gradlew`, `just`, `rake` and their kin) are script runs, so a project entry such as `make check` now decides
  something. A native program named by a path denies unless it is a known read-only tool outside the repository.
- High: the loopback share mapping runs again on the resolved path, so a link resolving to a share of the project is
  still inside.
- Medium: a UNC host is this machine by any loopback spelling, IPv4-mapped IPv6 included, its own name with a domain
  or a trailing dot, or any name or LAN address resolving to its addresses. An administrative drive share on any host,
  a volume GUID path and a `GLOBALROOT` path cannot be placed and deny. A project entry whose first word holds a slash
  matches only the file it names, and no built-in entry matches a program spelled with a path.
- Low: the built-in git entries exempted nothing and are removed. git is judged by what it writes.
- Hard links from Python and JavaScript count the source as written. PowerShell that holds a `System.IO` type as a
  value, imports with `using`, turns a string into a type, uses reflection or compiles code with `Add-Type` denies,
  as do WMI and CIM method calls and `wmic ... call create`. Inline Python that imports outside the standard library,
  imports a module a working-directory file shadows, or loads code through `runpy`, `importlib` or `ctypes` denies,
  and so does inline JavaScript loading a module that is not built in. Archive extraction, URL download, database
  files, logging file handlers and temporary files in a named directory are placed. `ssh`, `plink`, `winrs`,
  `Invoke-Command` and PowerShell sessions aimed at this machine, `psexec`, container bind mounts of the repository,
  `docker exec` and `compose up`, and `schtasks /create`, `at`, `batch`, `crontab`, `systemd-run` and
  `Register-ScheduledTask` deny on the main thread. A PowerShell statement opening with a quoted string is read as the
  value it is rather than as a program, and one handed to `&` is read as the program it runs.
- The runs-code-elsewhere rule no longer denies read-only container and WMI commands on the main thread. `docker` and
  `podman` `compose ls`, `ps`, `logs` and `config`, `buildx ls`, and a `[wmisearcher]` query now allow, as `ps`,
  `images`, `inspect`, `logs`, `stats`, `network ls`, `volume ls`, `schtasks /query`, `crontab -l`,
  `Get-ScheduledTask`, `Get-CimInstance` and `Get-WmiObject` already did. `compose build` and `cp`,
  `docker image build`, `builder build`, `buildx bake`, `unpause`, `podman kube play` and `runlabel`,
  `stack deploy`, `service create` or `update`, `docker cp` into a container, `docker save` or `export` into the
  repository, and a `Create`, `Change` or `InvokeMethod` call on a WMI object now deny.
- The preflight gate closes every gap from the second security audit. High: a hard link whose source is a project
  file (`ln` without `-s`, `cp -l`, `fsutil hardlink create`, `New-Item -ItemType HardLink`), including one made at
  `tasks.md`, now denies. A `\\?\`, `\\.\`, `\\?\UNC\` or loopback `\\localhost\C$` path is read as the drive
  path it names. Command substitution inside double quotes and backquotes is judged, a line continuation before CR LF
  joins the line, a PowerShell cmdlet fed its path through the pipeline is judged or unplaceable, and `busybox` and
  `toybox` are peeled like wrappers instead of read as shells.
- Medium: `popd`, `Push-Location`, `Pop-Location`, `env --chdir`, `sudo --chdir` and `pwsh -WorkingDirectory` move
  the directory the gate resolves against, and PowerShell and cmd parentheses and PowerShell pipelines no longer
  restore it. An unexpanded `$VAR`, `{a,b}`, `%VAR%` or `!VAR!` in a target denies. New handlers read `xcopy`,
  `robocopy`, `replace`, `expand`, `esentutl`, `certutil`, `bitsadmin` and `mklink`, `Start-Transcript`, every
  `Export-*` cmdlet, `Start-Process` (`saps`, `start`) with its redirects and argument list, `Set-ItemProperty` (`sp`),
  and any other `System.IO` use. In-place editors and formatters, `sort -o`, `yq -i`, writes from inside `awk` and
  `sed` programs, Lua, R, Julia and `sqlite3` are judged, and PHP, Perl and Ruby code that runs a process or writes a
  computed path denies instead of passing a pattern list. `su -c`, `setsid`, `flock`, `watch`, `script`, `wsl` and
  `git -c alias.x=!...` are peeled or unplaceable. A non-string shell command, or an unknown tool carrying a command,
  denies. A case-insensitive POSIX file system (macOS, WSL `/mnt`) compares paths without case.
- Lexer: bash `$'...'` quoting, a lone CR as a line break, PowerShell backtick escapes, `--%`, typographic quotes, the
  reserved `<` no longer failing the whole command open, nested code that cannot be lexed denying, cmd `/c` with the
  command attached, and native argv split by `CommandLineToArgvW` rules under cmd.
- Low: AGENTS.md lists the MCP tools that write files and are not matched, and a test pins 8.3 short names.
- The preflight gate on Windows read a Git Bash drive path such as `/c/Users/x` as a folder on the current drive, so
  a main-thread `cd` into one landed nowhere and the relative write after it was denied, while an absolute
  `/d/...` target inside the repository was allowed. A leading `/<letter>/` is now read as that drive, on Windows
  only.
- Every per-agent import block in `README.md` omitted `docs/AGENT_TOOLING.md`, so a project set up from one agent's
  subsection pulled the update instructions and the MCP setup but not the walkthrough that explains them. All twenty
  pathspecs, ten initial pulls and ten refreshes, now match the Quickstart set.
- The skills and subagents count badges, stale at 85 and 30 against a tree holding 65 and 35.
- Two steps of `docs/bootstrap-prompt.md` told the main thread to write `AGENTS.md` and trim `docs/MCP_SETUP.md`
  itself, which Rule A denies, so the bootstrap ended in a refusal on every gated surface. Both now delegate to
  `agent-engineer` with `markdown-writer` named, the gathering stays in the main thread, and the prompt no longer
  sends a consumer's agent to a badge on this repository's README that the consumer does not have.
- The symlink instruction, which showed the repository-local form in some documents and the `--global` form in others
  with no explanation of the difference. Every document now leads with `git config core.symlinks true` and says in one
  line what adding `--global` buys.
- The `e2e-runbooks` schema install in `docs/AGENT_TOOLING.md`. It cloned the whole companion repository and copied a
  root-level `e2e-runbooks/` directory that no longer exists on `master`, and it called `openspec new` without the
  required `change` subcommand. It now fetches `openspec/schemas/e2e-runbooks` straight into the matching path. The
  links pointing at the old root-level directory were returning 404 and now resolve.
- Documentation that still described the deleted `.opencode/opencode.json` overlay and the pre-move `tools/` test
  paths.
- The Claude Code `PreToolUse` matcher is now anchored, `^(Edit|Write|NotebookEdit|Bash|WebFetch|WebSearch)$`, and it
  carries the two research tools the gate's third rule judges. It matches the shape the
  Codex adapter already used. The unanchored `Edit|Write|NotebookEdit|Bash` was not firing on `TodoWrite`, because a
  matcher made only of letters and pipes is evaluated as a list of exact tool names rather than as a regular
  expression. Anchoring keeps that behaviour explicit, so adding one metacharacter to the list later cannot silently
  flip the whole pattern onto the unanchored regular-expression path where `Write` would match `TodoWrite`. It has
  since been widened to `MultiEdit` and `PowerShell`, see below.
- The global installer's Codex hooks now carry a `commandWindows` beside every `command`, the way the project-scoped
  `.codex/config.toml` already does, because Codex picks one of the two by platform. `sandbox-agent/verify-global.sh`
  asserts the pairing so it cannot regress unnoticed.
- The wiring table in `AGENTS.md` escapes the pipes inside its matcher cells. Raw pipes were splitting those rows into
  extra columns, so the Codex and Copilot matchers rendered as broken table cells.
- The global installer now writes Codex a `SubagentStart` hook, the third event the project-scoped `.codex/config.toml`
  has always wired. Without it a subagent under a globally installed Codex received no preflight injection at all,
  while the same subagent inside an imported project did.
- The Codex gate call the global installer writes now ends in `|| exit 0` and discards standard error, on the POSIX
  command and on its Windows sibling. It was a bare invocation, so a globally installed Codex whose gate script was
  missing would have denied every tool call rather than allowing it, the same fail-closed break already fixed for
  Claude Code. `sandbox-agent/verify-global.sh` asserts the forced zero exit, the third event, and the canonical
  wording on both injecting events, so none of the three can come back silently.
- The `Stop` hook the global installer writes for Claude Code now ends in `; exit 0`, the way the project-scoped
  `.claude/settings.json` already does. The formatting checker signals by printing JSON and always exits 0 itself, so
  the only way that hook returned non-zero was Python failing to open a missing script, which would have blocked the
  end of every turn.
- Two capability specs asserted a literal string the Claude Code gate command did not contain while the Python
  wrapper was still in the way. `6-global-install-shape-test.md` and `2-project-import-shape-test.md` now match the
  script path and the format flag as separate substrings, the way the verification scripts already did, so they hold
  whether or not anything sits between the shell and the gate. With the wrapper removed, both also assert that the
  command ends in `; exit 0` and no longer mentions `subprocess.DEVNULL`. Spec 6 gained the Codex matcher, event-set,
  and Windows-sibling assertions it was missing.
- Every hook wiring invoked its script as `python`, while every script under `.agents/hooks/` carries a
  `#!/usr/bin/env python3` shebang. Debian 11 and Ubuntu 20.04 onward ship no `/usr/bin/python` unless the
  `python-is-python3` package is installed, so on those machines every hook failed, and because each wiring ends in `;
  exit 0` or `|| exit 0` it failed silently: the gate `AGENTS.md` calls enforcing did nothing at all. Swapping to
  `python3` alone would have broken the other half, because the python.org Windows installer provides `python.exe` and
  usually no `python3.exe`. Each POSIX wiring now resolves the interpreter itself with `PY=$(command -v python3 ||
  command -v python)`: the nine commands in `.claude/settings.json`, the three `command` values in `.codex/config.toml`,
  and the two `bash` values in `.github/hooks/preflight.json`. The three `commandWindows` values and the two
  `powershell` values stay on `python`, because those are cmd.exe and PowerShell one-liners where it is the name that
  exists. `.agents/plugin/hooks.js` chose the name per platform at the time, so the repository had held both answers at
  once, and it now probes `python3` then `python`, see Changed. A retry of the form `python3 ... || python ...` was
  rejected rather than overlooked: the formatting check exits 2 to block a reply, and the retry would run it a second
  time. `sandbox-agent/verify-project.sh` asserted the old literal on all three surfaces and now asserts the resolution
  on the POSIX halves and `python` on the Windows halves, so the asymmetry is checked rather than assumed. The global
  install surface carried the same defect and is fixed with it. `sandbox-agent/setup-global.sh` writes its own Claude
  Code and Codex wirings instead of copying the shipped files, so its eleven POSIX `command` strings now resolve the
  interpreter and its three `commandWindows` strings stay on `python`. Its Copilot wiring is the shipped
  `.github/hooks/preflight.json` with the script paths rewritten to absolute, so that one inherited the fix and needed
  no edit, which is also why `sandbox-agent/verify-global.sh` had already begun disagreeing with what the installer
  produces. That script pinned `startswith("python -S -E /")` on all three surfaces, folding a POSIX command and its
  Windows sibling into a single assertion each. It now carries five assertions rather than three: the resolution on
  Claude Code's one command field, on Codex's `command` and on Copilot's `bash`, and `python` on `commandWindows` and
  `powershell`. `e2e/testing/6-global-install-shape-test.md` carries the same five filters byte for byte, and the eleven
  snippets in `docs/GLOBAL_SETUP.md` show the invocation a reader is meant to paste.
- The preflight gate denies a main-thread delete, move or rename of the repository root or of any directory containing
  it: `rm -rf ..`, `rm -rf ~`, `Remove-Item -Recurse`, `rmdir /s`, `mv` and `Move-Item`. It judges `find -delete` and
  `find -exec`, `git clean`, `rm`, `mv`, `git reset --hard` and `git stash`, `curl`, `wget`, `touch`, `mkdir`, `tar`,
  `unzip`, .NET IO calls and PowerShell cmdlets by their bound parameters, and judges a wildcard operand against the
  repository root and every directory above it.
- The preflight gate checks the inner command of `cmd /c`, `sh -c`, and `pwsh -Command` or `-EncodedCommand`, and reads
  inline Python or JavaScript for the path it writes. It reads heredoc, piped, `eval`, `Invoke-Expression` and sourced
  code as the receiving program's own code, follows Python and JavaScript import aliases, and denies process spawns and
  computed file calls in inline code. A command nested or wrapped past the gate's limit is denied instead of allowed
  unread.
- The preflight gate lexes PowerShell and cmd with their own quoting and escapes, so a quoted path ending in a
  backslash is judged. It splits a PowerShell comma array into separate paths, judges `apply_patch` delete, move and
  rename headers, and denies keyword forms such as `if` and `then`, braces and negation that hid a write.
- The formatting check read a backslash-escaped marker (`\*` or `\_`) as emphasis, although markdown renders it as a
  literal character. The `Stop` check reported it as italic, and the display fix mangled it with stray backslashes.
  Escaped markers are now left exactly as written, while an em dash on the same line is still fixed.
- The Claude Code `PreToolUse` matcher never sent the `PowerShell` tool to the gate, so on Windows, where Claude Code
  routes shell commands through that tool whenever it is on, a main-thread `Set-Content` into the repository was never
  checked. The hooks reference says "A hook that matches only `Bash` never fires there". The matcher is now
  `^(Edit|Write|MultiEdit|NotebookEdit|Bash|PowerShell|WebFetch|WebSearch)$` in `.claude/settings.json`,
  `docs/GLOBAL_SETUP.md` and `sandbox-agent/setup-global.sh`, and both sandbox verify scripts and spec 6 assert it. The
  tool's payload, measured on Claude Code 2.1.281, is `tool_name: "PowerShell"` with the command in
  `tool_input.command`, which the gate already read as a PowerShell command.
- The OpenCode and Kilo Code runner sent `is_subagent: true` for every call that carried a session id, the main
  thread's included, so a main-thread edit passed the gate there. It now reads the session with `client.session.get`:
  a session with a `parentID` is a subagent's child session, one without is the main thread, and a failed lookup
  leaves the field out so the gate allows. The answer is cached per session, and `agent_type` comes from the newest
  session message that names an agent, reading only the newest eight messages unless those name none. Measured on
  OpenCode 1.18.32 and Kilo Code 7.7.9: a main-thread write was denied and a `general` subagent write was allowed.
- The runner spawned each hook with `spawnSync`, which under the Bun runtime both tools ship on Windows returned
  `ETIMEDOUT` within 100 ms on most tool calls after the first. Every hook was skipped on those calls without a trace,
  the gate included, so main-thread writes went through. Each hook now runs through an asynchronous spawn with the
  runner's own 10 second timer.
- The preflight gate read a leading `~` in a write target as a folder named `~` inside the repository, so
  `rm -rf ~/.cache/x` was denied although the shell expands it to the home directory. A leading `~` or `~user` is now
  expanded the way the shell would, and a quoted tilde, which the shell leaves literal, still is not.
- The formatting check's loop guard read only `stop_hook_active`. It now accepts `stopHookActive` as well and keeps a
  per-session counter of blocks in a row, allowing the next stop after a block, so a block nobody can satisfy cannot
  force turn after turn on a payload that carries neither flag.
- The built-in main-thread allowlist named this repository's own `tools/check-markdown.py`, `tools/check-badges.py` and
  `tools/gen_subagents.py --check`, so a consumer project's same-named script, which could write files, ran on the main
  thread. Those three now live in this repository's root `main-thread-allowlist.txt`, which no import pathspec
  carries, and the project extension file moved from `.agents/main-thread-allowlist.txt` to the project root, because
  the Quickstart imports `.agents` whole and would have shipped it and overwritten a consumer's own.
- The preflight gate read a loopback UNC path to a share that is not an administrative drive share, such as
  `\\localhost\share` or `\\127.0.0.1\share`, as outside the repository and allowed a main-thread write to it. The
  gate cannot map such a share to a folder, so it now treats the path as unplaceable and denies.
- No Codex hook ran on Windows. Every `commandWindows` value in `.codex/config.toml`, `docs/GLOBAL_SETUP.md` and
  `sandbox-agent/setup-global.sh` failed to parse in the PowerShell Codex runs it under: the gate text was an unquoted
  `echo {...}`, and the script hooks used `2>nul || exit 0`, which Windows PowerShell 5.1 has no `||` for. The gate
  text is now `echo '<json>'; exit 0`, and each script hook moves to the project root and ends in `2>$null; exit 0`.
- The Limitations list in `docs/GLOBAL_SETUP.md` said linked directories are documented for two agents and then named
  three. It now says three.

### Removed

- The markdown lint's 120-character limit on prose lines. Prose is never hard-wrapped, so a paragraph is one physical line however long it runs.
- `.claude/CLAUDE.md`, which held only `@../AGENTS.md`. Any `CLAUDE.md` switches off Claude Code's native `AGENTS.md`
  loading, and an `@` import loads every imported file in every session.
- The `finance-billing-ops` skill, which encoded one product's revenue and billing workflow and never belonged in a
  shared catalogue.
- `argparse` from every hook. It exits 2 on a usage error, and 2 is the deny code in the plain format, so a stray
  flag read as a block. Each hook scans `sys.argv` by hand and treats an unknown flag as an allow. Every hook is also
  invoked with `-S -E` now, which is safe because every hook is standard library only.
- `.github/dependabot.yml`, and with it Dependabot itself. Nothing opens automated dependency pull requests here any
  more. The exact pins in `tools/pyproject.toml` and the SHA-pinned actions in the workflows are bumped by hand.
- The `.kilocode/` directory in full: the generated subagent tree, the `rules/00-preflight.md` gate rule, and its MCP
  templates. Kilo Code moved its configuration root to `.kilo/` and accepts `opencode.json`.
- `.codex/hooks.json`, replaced by the inline `[[hooks.*]]` tables in `.codex/config.toml`.
- `.opencode/plugin/preflight.js`, superseded by the shared `.agents/plugin/hooks.js` that both OpenCode and Kilo
  Code load from the root `opencode.json`.
- `.opencode/opencode.json`, the OpenCode-only MCP overlay. It existed to carry the one `{env:VAR}` header the shared
  file could not hold, and a second project file only one of the two tools reads was a second place for the server set
  to drift. `.opencode/` now holds nothing but the `agents` symlink.
- Every `.example` template except `AGENTS.md.example`, now that the configuration files ship as real committed files.
- The `.opencode/skills` and `.codex/skills` symlinks. OpenCode and Codex read `.agents/skills/` natively, leaving
  `.claude/skills` as the only skill symlink.
- The `.github/copilot-instructions.md` bridge and its `.example`. GitHub Copilot reads `AGENTS.md` natively in the
  JetBrains plugin, VS Code, and the CLI, so the bridge only duplicated it. Copilot code review and the IDEs that read
  only that file (Visual Studio, Xcode, Eclipse) are now out of scope, so add a bridge back per project if you target
  them.

## [1.0.0] - 2026-06-25

First tagged release. A consumer pins this tag and pulls updates with one `git fetch`.

### Added

- 84 canonical skills under `.agents/skills/`, shared by every supported agent through symlinks.
- 30 subagents defined once in `subagents/` and generated per tool.
- GitHub Copilot support: subagents generated to `.github/agents/*.agent.md`, a `.github/copilot-instructions.md`
  template for local IntelliJ and VS Code chat, and a `.vscode/mcp.json.example` MCP template.
- Four supported agents already wired before Copilot: Claude Code, Kilo Code, OpenCode, and Codex.
- 8 MCP servers shipped in four schema templates (Claude Code, OpenCode, Kilo Code, and VS Code Copilot).
- OpenSpec scaffolding and a companion `e2e-runbooks` schema reference.
- A preflight gate enforced by a Claude Code hook, an OpenCode plugin, and a Kilo Code rule, and stated as
  instruction text for Copilot.
- Four new domain skills: `observability-and-logging`, `build-dependency-management`, `web-accessibility`, and
  `performance-optimization`.
- Three new subagents: `embedded-c-engineer`, `home-assistant-engineer`, and `unity-game-dev`.

### Changed

- Aligned every skill with the project owner's engineering standards (SOLID and error-handling in the
  `coding-standards` hub, RFC 7807 errors, discriminated async state, blocking-over-reactive backend defaults,
  approval-gated automation, a 90 percent coverage target, Given/When/Then tests).
- Applied one consistent markdown style across all skills, docs, and templates (level-3 sections with dividers, no
  em-dashes or en-dashes, prose wrapped at 120), now enforced by `tools/check-markdown.py`.
- Relocated the canonical startup-readiness log from `coding-standards` into `observability-and-logging`.

[1.0.0]: https://github.com/Lukk17/agent-standards/releases/tag/v1.0.0
