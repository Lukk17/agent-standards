# Bootstrap prompt (first run)

Paste the block below into the agent on its very first run in a freshly imported project. It forces the agent to
verify the wiring actually works instead of claiming it does, discover the instruction tree, confirm the delegation
strategy, trim the MCP document to what the project really uses, and patch the gaps before it writes a line of code.

The prompt deliberately names no specific MCP server, subagent, or skill, because those vary per project. It sends the
agent to the project's own [AGENTS.md.example](../AGENTS.md.example) for the canonical rules, so this file does not
need re-editing every time the upstream rules move.

This file stays in the agent-standards repo only. It is not shipped to consumer projects.

---

### Prompt, paste this verbatim

````text
You are bootstrapping into a project that just imported agent-standards. Before any other work, run this verification
and wiring pass and report back as a checklist.

## 1. Verify the skills wiring

Skills live canonically in `.agents/skills/`. Codex, OpenCode, Kilo Code and every GitHub Copilot surface read that
directory natively. Claude Code does not, and reaches it through the `.claude/skills` symlink. Symlinks break often on
Windows checkouts, so do not trust a directory listing.

If you are Claude Code, open ONE skill through the symlink path (`.claude/skills/coding-standards/SKILL.md`) and quote
its first heading line back. If the read fails the symlink is broken: report it and stop, do not quietly fall back to
`.agents/skills/`. Every other agent opens one skill directly from `.agents/skills/` and quotes its heading.

Then list which of `.agents`, `.claude`, `.opencode`, `.kilo`, `.codex` and `.github` actually exist here, so a missing
piece of the import surfaces immediately.

## 2. Verify the subagent files

Subagent definitions ship as four generated trees plus two symlinks:

- `.claude/agents/*.md` for Claude Code
- `.agents/agents/*.md` in OpenCode format
- `.codex/agents/*.toml` for Codex
- `.github/agents/*.agent.md` for GitHub Copilot
- `.opencode/agents` and `.kilo/agents`, both symlinks into `.agents/agents/`

Confirm the directory your own tool reads is non-empty and lists a good number of files. Cross-check against the
subagent badge count on the agent-standards README if you want a target. If yours is empty or missing, the import
pulled an incomplete subset: flag it and ask the user to re-run the checkout.

Check the two symlinks specifically. If `.opencode/agents` or `.kilo/agents` came through as a small text file holding
a path instead of a link, say so, because OpenCode and Kilo Code then have no subagents at all.

## 3. Verify the preflight gate

The gate is one shared script, `.agents/hooks/preflight_gate.py`, wired into each agent through its own hook surface:
`.claude/settings.json`, the inline `[[hooks.*]]` tables in `.codex/config.toml`, the plugin at
`.agents/plugin/hooks.js` declared by path in `opencode.json`, and `.github/hooks/preflight.json`.

Confirm the script exists and that the hook configuration your own runtime reads names it. Do not try to trigger the
gate on purpose. Just report whether the wiring is present, and name the surface you are running on.

## 4. Verify the MCP runtime

Look at your current tool list. Report the names of any MCP servers actively exposing tools in this session. If there
are none, say "no MCP servers active in this session" and note that this is fine: the project may not need any, may
have disabled them, or may not have the keys set yet.

The four project MCP files are real files, not templates, so there is nothing to rename:

- `.mcp.json` (key `mcpServers`) for Claude Code and the GitHub Copilot CLI
- `opencode.json` (key `mcp`) for OpenCode and Kilo Code
- `.codex/config.toml` (`[mcp_servers.*]` tables) for Codex
- `.vscode/mcp.json` (key `servers`) for GitHub Copilot in VS Code

Report which of those exist. Do not assume any particular server should be present, just report what is there.

## 5. Trim docs/MCP_SETUP.md to what this project actually uses

The shipped `docs/MCP_SETUP.md` documents every server in the canonical set (Context7, MongoDB, Grafana, Playwright,
Chrome DevTools, Redis, SonarQube, n8n). Most projects use a subset.

Diff the active server names from step 4, or the names present in the config files if none were active, against the
servers documented in `docs/MCP_SETUP.md`. For every server this project does not use, remove its table rows, its
environment-variable lines, and any prose that names it.

Goal: a reader of `docs/MCP_SETUP.md` sees instructions only for the servers that actually run here. Show the diff in
your report. Do not delete the file, only trim it. If the project uses every default server, say so and leave it
alone.

## 6. Verify OpenSpec is callable

OpenSpec is a spec-driven workflow that MUST be used to plan any change beyond a trivial single-file edit (a typo, a
comment, a one-liner). Verify it:

- Confirm an `openspec/` directory exists at the repository root with `specs/` and `changes/` inside.
- Confirm your agent's OpenSpec command is registered, and name the slash command you would use to open a proposal.
- If your shell can run binaries, run `openspec --version` and report it. If it is sandboxed, the two checks above are
  enough.

If OpenSpec is missing, report it, and note that the correct way to initialise it here is `openspec init --tools
agents`. That vendor-neutral target writes skills into `.agents/skills/` and creates no per-tool directories, which is
what this layout expects. Per-tool targets fragment it, and the `kilocode` target in particular still writes to the
old `.kilocode` directory that Kilo Code no longer uses.

Do not start implementation work on a non-trivial change without OpenSpec.

## 6b. Check for end-to-end runbook tests

If the repository has an `e2e/` directory with `e2e/testing/*-test.md` files, list them and confirm at least one
runner is callable (`bru --version`, `hurl --version`, or plain `curl` as the fallback). If the directory is absent
that is a pass, not every project ships runbook tests. If it exists but no runner is installed, flag it.

If the project ships an `e2e-runner` subagent (look in `.agents/agents/` or `.claude/agents/`), the orchestration
contract is one subagent per test with a parallel cap, default 5, confirmed with the user before each sweep and
typically 3 to 10 depending on the environment, governed by each spec's Concurrency section. That is a sweep-time
concern, not a bootstrap concern. Just confirm the subagent exists so the pattern is available.

Restate the conflict-graph rule in one sentence before any sweep: tests with overlapping `Mutates:` resources cannot
run in parallel, tests marked `Serial: true` run alone, and the confirmed cap is a ceiling that a missing edge never
raises. If you cannot restate it, re-read the Concurrency-constraints section of the `e2e-runbooks` skill first.

If `openspec/schemas/e2e-runbooks/` exists, confirm the schema validates with
`openspec schema validate e2e-runbooks`. If the schema is missing but `e2e/` exists, the project uses the methodology
without the OpenSpec lifecycle integration, which is fine.

## 7. Map the instruction tree

The root `AGENTS.md` is canonical. More `AGENTS.md` files MAY exist in subdirectories or submodules.

- Linux or macOS: `find . -name AGENTS.md -not -path './node_modules/*'`
- Windows PowerShell:
  `Get-ChildItem -Recurse -Filter AGENTS.md | Where-Object { $_.FullName -notmatch 'node_modules' }`
- Claude Code only: open `.claude/CLAUDE.md`, list every `@`-imported path, and diff that against the find output.
  Any `AGENTS.md` that is not imported is drift. Flag it.

## 8. Fill the AGENTS.md stubs

The `AGENTS.md.example` template ships with intentionally empty sections that every project has to fill. This is the
WHOLE POINT of the bootstrap. Do not skip it and do not treat it as a footnote.

Open the root `AGENTS.md` and find the empty sections and HTML-comment placeholders. At minimum:

- `## What This Repo Is`: one short paragraph on what the project does, who uses it, and what stack it runs. Derive it
  from `package.json`, `pom.xml`, `pyproject.toml`, `Cargo.toml`, `go.mod`, and the top-level file tree. Do not invent
  a purpose. If the evidence does not support one, say so and ask.
- `## Architecture`: a bullet list. Framework and version, the patterns actually in use, the deploy target, and the
  notable constraints (monorepo, server-rendered only, offline-first, and so on). Derive it from config files, folder
  structure, and any decision records under `docs/` or `openspec/specs/`.

This is low-risk: you are filling a file the user just imported and expects to fill. DO IT. Write the drafted content
straight into the root `AGENTS.md` as part of this pass and show the diff in your report. Do NOT stop and ask for
approval first.

## 8b. Verify docs/AGENTS-UPDATE.md shipped

`docs/AGENTS-UPDATE.md` arrives with the Step 1 checkout. It documents how this project refreshes agent-standards
content selectively, enumerating the skills and subagents already present and pulling only those, and it refreshes
itself on every run.

Confirm it exists. If it is missing, the project was imported before it shipped: pull it with a one-off
`git checkout agent-standards/master -- docs/AGENTS-UPDATE.md` and flag it.

## 9. Confirm the delegation strategy

Open `AGENTS.md` (or `AGENTS.md.example` if it has not been renamed yet) and read the `## Subagents` section including
its `### When to use them` subsection.

Restate in your own words, in three or four sentences:

- When you will spawn subagents, proactively rather than reactively.
- How you will run them in parallel when the work is independent.
- How you will direct them to invoke specific skills.
- Which work patterns trigger which subagents (reviewing, adding a feature, debugging, migrating, documenting).

This is a posture check. The user needs to know you understood the delegation rules before you start, and the
preflight gate will block a main-thread source edit anyway, so getting this right is not optional.

## 10. Decide whether subdirectory AGENTS.md files are needed

Create an `AGENTS.md` in a subdirectory ONLY when that subdirectory has its own toolchain or build system, its own
deploy target or runtime, or conventions that meaningfully differ from the root. Single-application repositories
almost never need one. Three near-empty files are worse than one good root file. If nothing qualifies, that is a pass,
not a warning.

## 11. Report, then wait

End with this checklist. Pass or "broken, needs fixing". "Considered and not needed" counts as a pass. Reserve the
failure mark for wiring that is genuinely broken or missing.

- [ ] Skills readable (Claude Code through `.claude/skills`, every other agent directly from `.agents/skills/`)
- [ ] Agent directories present (`.agents`, `.claude`, `.opencode`, `.kilo`, `.codex`, `.github`)
- [ ] Subagent trees present (`.claude/agents/`, `.agents/agents/`, `.codex/agents/`, `.github/agents/`) and the
      `.opencode/agents` and `.kilo/agents` symlinks intact
- [ ] Preflight gate wired (`.agents/hooks/preflight_gate.py` plus the hook config your runtime reads)
- [ ] MCP runtime checked (names, or "none active") and the four config files accounted for
- [ ] docs/MCP_SETUP.md trimmed to the active servers (show the diff, or "no trim needed")
- [ ] OpenSpec callable (slash command name, version if available)
- [ ] End-to-end runbook tests checked (spec files, runner tool, `e2e-runner` subagent present, or "no e2e directory")
- [ ] AGENTS.md inventory (paths found)
- [ ] CLAUDE.md imports versus that inventory (drift listed, or "no drift")
- [ ] Root AGENTS.md stubs filled (show the diff you just applied)
- [ ] docs/AGENTS-UPDATE.md present
- [ ] Delegation strategy restated
- [ ] Subdirectory AGENTS.md needed? (yes plus paths, or "no, single-application repo")

Apply without asking, as part of this pass:

- Filling the empty stub sections in the root `AGENTS.md`.
- Trimming `docs/MCP_SETUP.md` to the servers this project actually uses.

Wait for approval before:

- Creating any NEW `AGENTS.md` file in a subdirectory.
- Adding NEW `@` imports to `.claude/CLAUDE.md`.

After approval, apply those and re-run the inventory diff to confirm. If the user pushes back on the stub fill or the
MCP trim, revise from their feedback.

## Operating rules from here on

- Any change beyond a trivial edit MUST start with an OpenSpec proposal.
- Skills are invoked with slash syntax. Use them instead of reinventing the guidance. The catalogue is
  `.agents/skills/`.
- Subagents are spawned proactively and in parallel where the work is independent. The full strategy is the
  `## Subagents` section of `AGENTS.md`.
- The main thread delegates source edits. The preflight gate enforces it on every surface that can tell who is asking.
- MCP tools active in this session beat re-deriving the same answer from local files.
- `AGENTS.md` is the source of truth for this project's conventions.
````
