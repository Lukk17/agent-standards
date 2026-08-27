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
- One shared preflight rule at `.agents/hooks/preflight_gate.py`, called by every agent surface. The gate is now
  enforcing rather than advisory: it denies a source-file edit made from the main thread and tells it to delegate, and
  denies an edit from a subagent whose own definition declares no skills. Markdown, configuration, and documentation
  edits from the main thread are allowed, and any error inside the gate fails open.
- `.agents/hooks/no_ai_markers_check.py`, wired as the Claude Code `Stop` hook.
- One preflight plugin at `.agents/plugin/hooks.js`, declared once by path in the `plugin` array of the root
  `opencode.json`, which both OpenCode and Kilo Code read. It carries no rules of its own: it discovers every hook in
  `.agents/hooks/`, runs them in the order each hook declares, and speaks the versioned JSON envelope documented in
  `docs/hooks-contract.md`.
- GitHub Copilot hook configuration at `.github/hooks/preflight.json`, on `sessionStart`, `subagentStart`, and
  `preToolUse`. Event names are camelCase and each command is an object with a `bash` key and a `powershell` key.
- Symlinks `.opencode/agents` and `.kilo/agents`, both pointing at `../.agents/agents`, created and repaired by the
  generator. On Windows they need `git config core.symlinks true` and Developer Mode, or Git checks them out as plain
  text files holding their target path.
- Codex custom agents generated to `.codex/agents/*.toml`, so all five supported agents now receive native subagent
  files from the one canonical `subagents/` source.
- A pytest suite in `tools/tests/`, covering both shared hook scripts, run locally and in CI.
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

### Changed

- Configuration files are no longer templates. `.mcp.json`, `opencode.json`, `.codex/config.toml`, and
  `.vscode/mcp.json` are committed as real files that a consumer pulls and uses unchanged. `AGENTS.md.example` is the
  only `.example` file left in the repo, because only `AGENTS.md` carries repo-specific content while hooks, MCP,
  skills, and subagents are universal.
- MCP mapped one row per file: `.mcp.json` (key `mcpServers`) serves Claude Code and the GitHub Copilot CLI, which
  reads a repo-root `.mcp.json` with the same schema. `opencode.json` (key `mcp`) serves OpenCode and Kilo Code, which
  accepts `opencode.json` as a valid config filename. `.codex/config.toml` (`[mcp_servers.*]` tables) serves Codex, and
  `.vscode/mcp.json` (key `servers`) serves Copilot in VS Code. Kilo rejects a project-level config file outright when
  it contains an `{env:VAR}` reference, so the shared `opencode.json` carries none and declares `context7` without a
  `headers` block. A paid Context7 key now belongs in a user's own global OpenCode or Kilo config.
- Kilo Code moved its configuration root to `.kilo/` and reads `.agents/skills/` natively, so its subagent tree is now
  a symlink to the shared `.agents/agents/` rather than a generated copy of its own.
- Codex preflight hooks moved into inline `[[hooks.*]]` tables in `.codex/config.toml`. Codex supports both that form
  and a separate `hooks.json`, and warns when a single configuration layer carries both.
- The subagent generator emits four trees (`.claude/agents/`, `.agents/agents/`, `.codex/agents/`, `.github/agents/`)
  and maintains the two agent symlinks, instead of writing one independent copy per tool.
- Corrected the GitHub Copilot claims. Copilot does have a per-turn injection channel, `userPromptTransformed`, on the
  CLI and on the cloud agent. Copilot hooks are no longer CLI-only and run in VS Code and JetBrains from the same
  `.github/hooks/` path. The Copilot CLI additionally reads hooks from `.claude/settings.json`, while the JetBrains
  plugin does not: it hardcodes `.github/hooks/**/*.json` and rejects PascalCase event names. The JetBrains plugin also
  scans `.claude/agents` but understands only its own `*.agent.md` format, so subagent definitions are not shareable.
- CI validates the four real configuration files and the two hook files instead of the deleted templates, and runs the
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
- The runner label, from the floating `ubuntu-latest` to the exact `ubuntu-24.04` it resolves to today. Ubuntu 26.04 is
  in preview, and when it reaches general availability GitHub moves the `-latest` label over one to two months. With no
  Dependabot to open a pull request, a floating label is the one version in this repo that could change under us
  without a commit, so it now matches how everything else here is pinned.
- The sandbox base image, from `node:24-bookworm-slim` to `node:24-trixie-slim`. Node 24 is still the active long-term
  support line, Node 26 does not become one until October 2026, but Debian 13 (trixie) has been stable since August
  2025 and bookworm is oldstable. The image gains the newer distribution toolchain that comes with it: python3 3.13
  instead of 3.11, git 2.47 instead of 2.39.

### Fixed

- The `e2e-runbooks` schema install in `docs/AGENT_TOOLING.md`. It cloned the whole companion repository and copied a
  root-level `e2e-runbooks/` directory that no longer exists on `master`, and it called `openspec new` without the
  required `change` subcommand. It now fetches `openspec/schemas/e2e-runbooks` straight into the matching path. The
  links pointing at the old root-level directory were returning 404 and now resolve.
- Documentation that still described the deleted `.opencode/opencode.json` overlay, the pre-move `tools/` test paths,
  and a `docs/GLOBAL_SETUP.md` listed as shipped to consumers although no import command ever pulled it.
- The Claude Code `PreToolUse` matcher is now anchored, `^(Edit|Write|NotebookEdit|Bash)$`, matching the shape the
  Codex adapter already used. The unanchored `Edit|Write|NotebookEdit|Bash` was not firing on `TodoWrite`, because a
  matcher made only of letters and pipes is evaluated as a list of exact tool names rather than as a regular
  expression. Anchoring keeps that behaviour explicit, so adding one metacharacter to the list later cannot silently
  flip the whole pattern onto the unanchored regular-expression path where `Write` would match `TodoWrite`.
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
- Two capability specs asserted a literal string that the Claude Code gate command can no longer contain. That command
  runs the gate through a Python wrapper that passes `--format claude` as two separately quoted arguments, so
  `6-global-install-shape-test.md` and `2-project-import-shape-test.md` now match the path and the flag separately,
  the way the verification scripts already did. Both specs also gained the standard-error and zero-exit assertions the
  scripts make, and spec 6 gained the Codex matcher, event-set, and Windows-sibling assertions it was missing.

### Removed

- The Claude Code `SessionStart` preflight hook from `.claude/settings.json`. The `UserPromptSubmit` hook in the same
  file injects the identical wording on every prompt, including the first, so on Claude Code the gate text appeared
  twice a moment apart at the start of a session. `UserPromptSubmit`, `PreToolUse`, and `Stop` are unchanged. This is a
  Claude Code change only: GitHub Copilot keeps its `sessionStart` injection, which is the only injection channel it
  has on the surfaces without a per-turn one, and Codex keeps its `SubagentStart` table.
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
