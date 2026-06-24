# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
