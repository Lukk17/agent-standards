# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Codex custom agents generated to `.codex/agents/*.toml` and Kilo Code subagents to `.kilocode/agents/*.md`. All five
  supported agents now receive native subagent files from the one canonical `subagents/` source.
- Codex preflight enforcement via a `UserPromptSubmit` hook (`.codex/hooks.json`, injecting the gate every turn) and
  GitHub Copilot via a `sessionStart` hook (`.github/hooks/preflight.json`, once per session, since Copilot discards
  `userPromptSubmitted` hook output).
- Kilo CLI MCP servers in the `mcp` block of `.kilocode/kilo.jsonc.example`, and Codex project MCP servers in
  `.codex/config.toml.example`.

### Changed

- The subagent generator emits five per-tool trees instead of three. Kilo Code now reads `.kilocode/agents/` (its
  documented path) rather than relying on a shared `.opencode/agents/` directory.
- Documentation updated to the verified mid-2026 state: GitHub Copilot, including the JetBrains plugin, reads
  `AGENTS.md` and `.agents/skills/` natively, and Codex gained custom agents, hooks, and project-level config.
- CI now validates the `.vscode/mcp.json.example`, `.kilocode/kilo.jsonc.example`, `.codex/config.toml.example`, and
  the two new hook files alongside the existing templates.

### Removed

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
