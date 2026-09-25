# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
  shows each reply with its dashes, bold and italic fixed and leaves code untouched, and on `Stop` and `SubagentStop`.
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

### Changed

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

- Every GitHub Copilot subagent that may write or edit now lists `apply_patch`, and the Copilot gate matcher names it.
  Copilot gives a GPT model `apply_patch` as its only file tool, and neither `create` nor `edit` grants it, so in live
  run 36168529868 the docs-architect subagent reached gpt-6-luna with only `view` and `bash`, under a system prompt
  telling it not to write files, and reported the file as not created.
- The preflight gate reads the patch a shell `apply_patch` command carries, from a heredoc, a pipe or its argument, and
  denies a main-thread write it names. Codex runs `apply_patch <<'PATCH'` from `exec_command` as a file change, and
  live run 36163866070 wrote `live-probe/main-thread.txt` that way past the gate.
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

### Removed

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
