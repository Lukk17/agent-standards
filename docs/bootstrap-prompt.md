# Bootstrap prompt (first run)

Paste the block below into the agent on its very first run in a freshly-imported project. It forces the agent to
verify the wiring works (instead of just claiming it does), discover the instruction tree, confirm the subagent
strategy, trim the MCP docs to what the project actually uses, and patch any gaps before it writes a single line of
code.

The prompt deliberately names no specific MCP server, subagent, or skill. Those vary per project. It asks the agent to
read the project's own [AGENTS.md.example](../AGENTS.md.example) for the canonical rules so this file does not have to
be re-edited every time the upstream rules change.

This file stays in the agent-standards repo only. It is not shipped to consumer projects.

---

### Prompt, paste this verbatim

````text
You are bootstrapping into a project that just imported agent-standards. Before any other work, run this verification
and wiring pass and report back as a checklist.

## 1. Verify skills wiring

Skills live canonically in `.agents/skills/`. The `.claude/skills/`, `.opencode/skills/`, and `.codex/skills/`
directories are symlinks pointing there. Kilo Code reads `.agents/skills/` natively without a symlink. Symlinks
frequently break on Windows checkouts, so do not trust a directory listing.

For your own agent's skills directory, open ONE skill through the symlink path (e.g.
`.claude/skills/coding-standards/SKILL.md` for Claude Code, or the equivalent for your agent) and quote the first
heading line back. If the read fails, the symlink is broken. Report it and stop; do not silently fall back to
`.agents/skills/`.

Then list which of the agent directories (`.claude`, `.opencode`, `.codex`) actually exist in this repo so missing
setups surface.

## 2. Verify subagent files exist

Subagent definitions ship as plain files (not symlinks) in `.claude/agents/` and `.opencode/agents/`. The latter is
shared by OpenCode and Kilo Code. Confirm that the directory your tool reads is non-empty and lists several `.md`
files (cross-check against the subagent badge count on the agent-standards README if you want a target). If it is
empty or missing, the agent-standards import pulled an incomplete subset. Flag it and ask the user to re-run the
checkout.

Codex CLI has no per-agent file mechanism. From Codex this step is N/A. Report "no subagent mechanism" and move on.

## 3. Verify MCP runtime

Look at your current tool list. Report the names of any MCP servers actively exposing tools in this session. If you
see none, say "no MCP servers active in this session" and note that this is fine. The project may not need any, may
have them disabled, or may not have copied `.mcp.json.example` and `opencode.json.example` yet. Do not assume specific
servers should be present; just report what is there.

If the project ships `.mcp.json.example` or `opencode.json.example` but the corresponding `.mcp.json` or
`opencode.json` does not exist, mention it. The user may want to copy the templates.

## 4. Trim docs/MCP_SETUP.md to what this project actually uses

The default `docs/MCP_SETUP.md` shipped from agent-standards documents every MCP server in the canonical template
(Context7, MongoDB, Grafana, Playwright, Chrome DevTools, Redis, SonarQube, n8n). Most projects use only a subset.

Diff the active MCP server names from step 3 (or the names present in `.mcp.json` / `opencode.json` if step 3 found
none active) against the servers documented in `docs/MCP_SETUP.md`. For every server NOT used in this project,
remove its dedicated rows from the tables, its env-var lines from the variable list, its block from the example
configs, and any prose that names it.

Goal: a consumer reading `docs/MCP_SETUP.md` sees instructions only for the MCPs that actually run in this project.
Less noise, less drift, less "why is X documented if I don't have it".

Show the diff in your report. Do not delete the file itself; only trim its content. If the project uses every
default MCP, say so and leave the file alone.

## 5. Verify OpenSpec is callable

OpenSpec is a spec-driven workflow that MUST be used to plan any change beyond a trivial single-file edit (typo,
comment, one-liner). Verify it:

- Confirm an `openspec/` directory exists at the repo root with `specs/` and `changes/` subdirectories.
- Confirm your agent's OpenSpec command is registered. Name the slash command you would use to start a proposal in
  this shell.
- If your agent shell allows running binaries, optionally run `openspec --version` and report it. If your shell is
  sandboxed and the binary is unreachable, the directory and slash-command checks above are sufficient.

If OpenSpec is missing or not callable, report it. Do not proceed to implementation work without it for any
non-trivial change.

## 5b. Check for e2e runbook tests

If the repo has an `e2e/` directory with `e2e/testing/*-test.md` files, list them and confirm at least one runner
tool is callable (Bruno CLI via `bru --version`, hurl via `hurl --version`, or fall back to plain `curl`). If the
directory is absent, that's ✅ (not every project ships e2e runbook tests). If it exists but no runner is
installed, flag it.

If the project ships an `e2e-runner` subagent (look in `.claude/agents/` or `.opencode/agents/`), the orchestration
contract is one subagent per test with a parallel cap (default 5, confirmed with the user before each sweep and
typically 3-10 depending on the test environment) governed by each spec's `Concurrency` section. That's a sweep-time
concern, not a bootstrap concern; just confirm the subagent exists so the orchestrator pattern is available.

Restate the conflict-graph rule in one sentence so you commit to it before any sweep: tests with overlapping
`Mutates:` resources cannot run in parallel, tests marked `Serial: true` must run alone, and the confirmed cap is the
ceiling, never raised by missing edges. If you cannot restate this rule, re-read the `e2e-runbooks` skill's
Concurrency-constraints section before running anything.

If the project ships an `openspec/schemas/e2e-runbooks/` directory, also confirm the schema validates
(`openspec schema validate e2e-runbooks`). If the schema is missing but `e2e/` exists, the project is using
the methodology without the OpenSpec lifecycle integration; that is fine.

## 6. Map the instruction tree

The root `AGENTS.md` is the canonical instruction file. More `AGENTS.md` files MAY exist in submodules or
subdirectories.

- Linux or macOS: `find . -name AGENTS.md -not -path './node_modules/*'`
- Windows PowerShell:
  `Get-ChildItem -Recurse -Filter AGENTS.md | Where-Object { $_.FullName -notmatch 'node_modules' }`
- For Claude Code: open `.claude/CLAUDE.md` and list every `@`-imported path. Diff that list against the find output.
  Any `AGENTS.md` not imported is drift. Flag it.

## 7. Fill the AGENTS.md stubs

The `AGENTS.md.example` template ships with intentionally empty sections that every project must fill. This is the
WHOLE POINT of the bootstrap. Do not skip it and do not treat it as a side note.

Open the root `AGENTS.md` and look for empty sections or HTML-comment placeholders (e.g.
`<!-- Describe your project here -->`). At minimum:

- `## What This Repo Is`: one short paragraph. What the project does, who uses it, what stack. Derive from
  `package.json`, `pom.xml`, `pyproject.toml`, `Cargo.toml`, `go.mod`, plus the top-level file tree. Do not invent
  purpose; if the repo's purpose is unclear from evidence, say so and ask the user.
- `## Architecture`: bullet list. Framework plus version, key patterns in use (e.g. "App Router", "hexagonal",
  "BLoC"), deploy target, notable constraints (monorepo, SSR-only, offline-first, etc.). Derive from config files,
  folder structure, and any existing ADRs under `docs/` or `openspec/specs/`.

Filling these stubs is low-risk (editing an existing file the user just imported and expects to fill). DO IT. Write
the drafted content straight into root `AGENTS.md` as part of this bootstrap pass. Show the diff in your report so
the user can review and revise after. Do NOT stop and ask for approval before this edit.

## 8. Confirm the subagent strategy

Open `AGENTS.md` (or `AGENTS.md.example` if it has not been copied yet) and read the `## Subagents` section,
including the `### When to use them` subsection.

Restate in your own words, in three or four sentences:

- When you will spawn subagents (proactively, not reactively).
- How you will run them in parallel when work is independent.
- How you will direct them to invoke specific skills.
- Which work patterns trigger which subagents (reviewing, adding a feature, debugging, migrations, docs).

This is a posture check. The user needs to know you understood the delegation rules before you start work. If your
agent has no subagent mechanism (Codex CLI), say so and confirm you will lean on skills instead.

## 9. Decide if subdir AGENTS.md files are needed

Create an `AGENTS.md` in a subdirectory ONLY when that subdirectory has:

- its own toolchain or build system, OR
- its own deploy target or runtime, OR
- conventions that meaningfully differ from the root.

Single-app repos almost never need this. Three near-empty files are worse than one good root file. If nothing
qualifies, that is a ✅, not a warning.

## 10. Report, then wait

End your bootstrap with this checklist (✅ pass / ❌ broken, needs fixing). "Considered and not needed" is ✅, not a
warning. Use ❌ only for things that are actually broken or missing wiring.

- [ ] Skills readable through my agent's symlink (quote the heading line)
- [ ] Agent directories present (`.claude`, `.opencode`, `.codex`; Kilo Code reads `.agents/` and `.opencode/`
      natively)
- [ ] Subagent files present (Claude Code: `.claude/agents/`; OpenCode / Kilo: `.opencode/agents/`; Codex: N/A)
- [ ] MCP runtime checked (list names, or "none active")
- [ ] docs/MCP_SETUP.md trimmed to active servers (show diff, or "no trim needed")
- [ ] OpenSpec callable (slash command name; version if available)
- [ ] E2E runbook tests checked (list spec files in `e2e/testing/`, name the API client tool found and whether the
      `e2e-runner` subagent is present, or ✅ "no e2e directory")
- [ ] AGENTS.md inventory (paths found)
- [ ] CLAUDE.md `@` imports vs inventory (list drift, or ✅ "no drift")
- [ ] Root AGENTS.md stubs filled (show the diff that was just applied)
- [ ] Subagent strategy restated (or "N/A, no subagent mechanism in this agent")
- [ ] Subdirectory AGENTS.md needed? (yes plus paths, or ✅ "no, single-app repo")

Auto-apply (no approval needed), already done as part of this pass:

- Filling empty stub sections in root `AGENTS.md`.
- Trimming `docs/MCP_SETUP.md` to only the MCPs this project actually uses.

Wait for approval before:

- Creating any NEW `AGENTS.md` files in subdirectories.
- Adding NEW `@` imports to `.claude/CLAUDE.md`.

After approval, apply those changes and re-run the inventory diff to confirm. If the user pushes back on the stub fill
or MCP_SETUP trim, revise based on their feedback.

## Operating rules from here on

- Any change beyond a trivial edit MUST start with an OpenSpec proposal.
- Skills are invoked via slash syntax. Use them instead of reinventing guidance. Check `.agents/skills/` for the full
  catalogue.
- Subagents are spawned proactively and in parallel where work is independent. See the `## Subagents` section in
  `AGENTS.md` for the full strategy.
- MCP tools that are active in the session take precedence over re-deriving the same answer from local files.
- Treat `AGENTS.md` as the source of truth for project conventions.
````
