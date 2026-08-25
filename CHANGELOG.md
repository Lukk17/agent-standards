# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- A containerised end-to-end harness in `test-harness/`. It installs all five agent CLIs, updates them to the latest
  release on container start, imports the shared configuration into a throwaway project, and asserts what each agent
  actually discovers. The repository is mounted read-only and the host home is never touched.
- Two capability test suites in `e2e/`, authored against the `e2e-runbooks` OpenSpec schema. Specs 1 to 5 cover the
  per-project import, specs 6 to 9 cover a global user-home install and refuse to run unless the working directory is
  free of per-project files, so a global result cannot be attributed to the wrong layer.
- [docs/global-setup.md](docs/global-setup.md), covering installation of the same skills, subagents and gate into the
  user home, per agent and per shell, with an honest list of what cannot be installed globally.
- One shared preflight rule at `.agents/hooks/preflight_gate.py`, called by every agent surface. The gate is now
  enforcing rather than advisory: it denies a source-file edit made from the main thread and tells it to delegate, and
  denies an edit from a subagent whose own definition declares no skills. Markdown, configuration, and documentation
  edits from the main thread are allowed, and any error inside the gate fails open.
- `.agents/hooks/no_ai_markers_check.py`, wired as the Claude Code `Stop` hook.
- One preflight plugin at `.agents/plugin/hooks.js`, a thin shim over the shared rule, declared once by path in the
  `plugin` array of the root `opencode.json`, which both OpenCode and Kilo Code read.
- `subagentStart` and `preToolUse` hooks for GitHub Copilot in `.github/hooks/preflight.json`, alongside the existing
  `sessionStart`. Event names are camelCase and each command is an object with a `bash` key and a `powershell` key.
- Symlinks `.opencode/agents` and `.kilo/agents`, both pointing at `../.agents/agents`, created and repaired by the
  generator. On Windows they need `git config core.symlinks true` and Developer Mode, or Git checks them out as plain
  text files holding their target path.
- A pytest suite under `tools/` covering both shared hook scripts, run locally and in CI with `python -m pytest tools/`.
- Codex custom agents generated to `.codex/agents/*.toml` and Kilo Code subagents to `.kilocode/agents/*.md`. All five
  supported agents now receive native subagent files from the one canonical `subagents/` source.
- Codex preflight enforcement via a `UserPromptSubmit` hook (`.codex/hooks.json`, injecting the gate every turn) and
  GitHub Copilot via a `sessionStart` hook (`.github/hooks/preflight.json`, once per session, since Copilot discards
  `userPromptSubmitted` hook output).
- Kilo CLI MCP servers in the `mcp` block of `.kilocode/kilo.jsonc.example`, and Codex project MCP servers in
  `.codex/config.toml.example`.
- `docs/agent-compatibility.md`: a per-surface matrix of what each agent reads (skills, instructions, subagents,
  preflight, MCP), with GitHub Copilot split by client, linked from the README and from `repository-layout.md`.

### Changed

- Configuration files are no longer templates. `.mcp.json`, `opencode.json`, `.codex/config.toml`, and
  `.vscode/mcp.json` are committed as real files that a consumer pulls and uses unchanged. `AGENTS.md.example` is the
  only `.example` file left in the repo, because only `AGENTS.md` carries repo-specific content while hooks, MCP,
  skills, and subagents are universal.
- MCP mapped one row per file: `.mcp.json` (key `mcpServers`) serves Claude Code and the GitHub Copilot CLI, which
  reads a repo-root `.mcp.json` with the same schema. `opencode.json` (key `mcp`) serves OpenCode and Kilo Code, which
  accepts `opencode.json` as a valid config filename. `.codex/config.toml` (`[mcp_servers.*]` tables) serves Codex, and
  `.vscode/mcp.json` (key `servers`) serves Copilot in VS Code. Kilo rejects a project-level config file outright when
  it contains an `{env:VAR}` reference, so the shared `opencode.json` carries none, and the one value that cannot be
  inherited from the process environment lives in an `.opencode/opencode.json` overlay that only OpenCode reads.
- Kilo Code moved its configuration root to `.kilo/` and reads `.agents/skills/` natively, so its subagent tree is now
  a symlink to the shared `.agents/agents/` rather than a generated copy of its own.
- Codex preflight hooks moved into inline `[[hooks.*]]` tables in `.codex/config.toml`. Codex supports both that form
  and a separate `hooks.json`, and warns when a single configuration layer carries both.
- The subagent generator emits four trees (`.claude/agents/`, `.agents/agents/`, `.codex/agents/`, `.github/agents/`)
  and maintains the two agent symlinks, instead of writing five independent copies.
- Corrected the GitHub Copilot claims. Copilot does have a per-turn injection channel, `userPromptTransformed`, on the
  CLI and on the cloud agent. Copilot hooks are no longer CLI-only and run in VS Code and JetBrains from the same
  `.github/hooks/` path. The Copilot CLI additionally reads hooks from `.claude/settings.json`, while the JetBrains
  plugin does not: it hardcodes `.github/hooks/**/*.json` and rejects PascalCase event names. The JetBrains plugin also
  scans `.claude/agents` but understands only its own `*.agent.md` format, so subagent definitions are not shareable.
- CI validates the real configuration files instead of the deleted templates, and runs the new pytest suite.
- The subagent generator emits five per-tool trees instead of three. Kilo Code now reads `.kilocode/agents/` (its
  documented path) rather than relying on a shared `.opencode/agents/` directory.
- Documentation updated to the verified mid-2026 state: GitHub Copilot, including the JetBrains plugin, reads
  `AGENTS.md` and `.agents/skills/` natively, and Codex gained custom agents, hooks, and project-level config.
- CI now validates the `.vscode/mcp.json.example`, `.kilocode/kilo.jsonc.example`, `.codex/config.toml.example`, and
  the two new hook files alongside the existing templates.
- Kilo Code MCP consolidated onto `.kilocode/kilo.jsonc` (`mcp` key), which the VS Code extension, the JetBrains
  plugin, and the CLI now all read. The MCP docs also document the two global-only GitHub Copilot surfaces (the
  JetBrains plugin and the CLI's `~/.copilot/mcp-config.json`), which read no per-project file and ship no template.
- The import flow renames each activated template to its real name (`mv`) instead of copying it, so a consumer keeps
  no dead `.example` twin and a remaining `.example` marks a template not yet activated. Configs that hold inlined
  secrets and are gitignored keep the `cp` path so the template stays tracked.

### Removed

- The `.kilocode/` directory in full: the generated subagent tree, the `rules/00-preflight.md` gate rule, and the
  `kilo.jsonc.example` MCP template. Kilo Code moved its configuration root to `.kilo/` and accepts `opencode.json`.
- `.codex/hooks.json`, replaced by the inline `[[hooks.*]]` tables in `.codex/config.toml`.
- `.opencode/plugin/preflight.js`, superseded by the shared `.agents/plugin/hooks.js` that both OpenCode and Kilo
  Code load from the root `opencode.json`.
- Every `.example` template except `AGENTS.md.example`, now that the configuration files ship as real committed files.
- The `.kilocode/mcp.json.example` template. Kilo unified MCP config onto `kilo.jsonc` (`mcp` key) across all clients,
  so the separate extension template (keyed `mcpServers`, `streamable-http`) was redundant.
- The `.opencode/skills` and `.codex/skills` symlinks. OpenCode and Codex read `.agents/skills/` natively, leaving
  `.claude/skills` as the only skill symlink.
- The `.github/copilot-instructions.md` bridge and its `.example`. GitHub Copilot reads `AGENTS.md` natively in the
  JetBrains plugin, VS Code, and the CLI, so the bridge only duplicated it. Copilot code review and the IDEs that read
  only that file (Visual Studio, Xcode, Eclipse) are now out of scope; add a bridge back per project if you target
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
