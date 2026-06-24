# AGENTS.md

Instructions for AI coding agents working on the **agent-standards repo itself**. This is the upstream source, not a
consumer project. Claude Code loads this via [.claude/CLAUDE.md](.claude/CLAUDE.md) (`@../AGENTS.md`); Kilo Code,
OpenCode, and Codex read it from the project root.

The consumer-facing template is [AGENTS.md.example](AGENTS.md.example). This real `AGENTS.md` describes how to work on
the standards themselves and is never shipped downstream: consumer projects copy the `.example`, never this file.

---

## Required opening move

Before any code work on a task, name the skill(s) and subagent(s) that own it and invoke them, or state "none apply"
and why. State this as the first line of your reply. It is a required output you produce, not a passive banner to skim
past. This is a hard gate.

Investigation, review, and bounded implementation are delegated by default. Doing a specialist's work inline from the
main session is the failure mode this gate prevents. Re-run the check at the start of every task. Most work in this
repo is documentation and the Python generator, so `markdown-writer`, `python-patterns`, and `python-testing` are the
usual owners, with `code-reviewer` before any merge.

The same gate is enforced per agent: Claude Code re-injects it every turn via a `UserPromptSubmit` hook
([.claude/settings.json](.claude/settings.json)), OpenCode via a plugin
([.opencode/plugin/preflight.js](.opencode/plugin/preflight.js)), and Kilo Code via a rule
([.kilocode/rules/00-preflight.md](.kilocode/rules/00-preflight.md)).

---

## What this repo is

agent-standards is a single source of AI-agent configuration (skills, subagents, MCP server templates, shared
instructions) imported into other projects via Git selective checkout. Consumer projects pull production-ready folders
and template files and pull updates with one `git fetch`. The canonical [subagents/](subagents/) source and the
[tools/](tools/) generator stay here and are never imported downstream.

The load-bearing distinction is **canonical vs generated**. Some trees are hand-edited here; some are emitted by a
script and must never be hand-edited.

| Tree | Status | How to edit |
| --- | --- | --- |
| `subagents/*.md` | canonical | edit directly, then regenerate |
| `.claude/agents/`, `.opencode/agents/`, `.github/agents/` | generated from `subagents/` | never hand-edit; run the generator |
| `.agents/skills/*/SKILL.md` | canonical | edit directly |
| `.claude/skills`, `.opencode/skills`, `.codex/skills` | symlinks to `.agents/skills/` | never edit through the link |
| `AGENTS.md.example`, `*.example`, `docs/*.md` | canonical | edit directly |

Regenerate the subagent trees after any `subagents/*.md` change:

```bash
python tools/gen_subagents.py
```

Full layout reference: [docs/repository-layout.md](docs/repository-layout.md). This repo does not use OpenSpec itself;
the OpenSpec sections in the `.example` are for consumers.

---

## Repo conventions

On top of the global rules in `~/.claude/CLAUDE.md`:

- **Never hand-edit generated subagent files.** Edit `subagents/<name>.md`, then run the generator. CI fails if the
  generated trees drift from canonical.
- **Markdown lint.** `README.md`, `AGENTS.md.example`, and `docs/*.md` must contain no em-dashes or en-dashes and no
  prose line over 120 characters. This real `AGENTS.md` is not in the lint scope, but match the style anyway.
- **One runnable command per fenced code block** in any doc a human copies, with the matching language tag and no
  `#` comment lines inside the block (global rule).
- **Four MCP templates, one server set.** [.mcp.json.example](.mcp.json.example) (Claude Code),
  [opencode.json.example](opencode.json.example) (OpenCode), [.kilocode/mcp.json.example](.kilocode/mcp.json.example)
  (Kilo Code VS Code extension), and [.vscode/mcp.json.example](.vscode/mcp.json.example) (GitHub Copilot in VS Code)
  ship the same servers in four schemas. Change all four together; only the top-level key, the `type` value, and the
  env-var syntax differ. Details in [docs/MCP_SETUP.md](docs/MCP_SETUP.md).
- **Four preflight wordings, one gate.** The canonical text is the Required opening move above. Three enforced
  adapters repeat it ([.claude/settings.json](.claude/settings.json),
  [.opencode/plugin/preflight.js](.opencode/plugin/preflight.js),
  [.kilocode/rules/00-preflight.md](.kilocode/rules/00-preflight.md)), and the GitHub Copilot copy in
  [.github/copilot-instructions.md](.github/copilot-instructions.md) states it as instruction text, since Copilot has
  no hook to enforce it. Keep all four in sync.
- **CI is manual.** Workflows run on `workflow_dispatch` / `workflow_call` only, so nothing runs on push. Verify
  locally before declaring work done.

Local verification (the same checks CI runs):

```bash
python tools/gen_subagents.py --check
```

```bash
python tools/check-markdown.py
```

```bash
python -c "import json; json.load(open('.mcp.json.example')); json.load(open('opencode.json.example')); json.load(open('.kilocode/mcp.json.example')); json.load(open('.vscode/mcp.json.example')); json.load(open('.claude/settings.json'))"
```

---

## Adding or changing things

- **A skill:** create `.agents/skills/<name>/SKILL.md` (plus a `references/` subdir if it needs depth). The symlinks
  expose it to every agent automatically. Bump the skill-count badge in [README.md](README.md).
- **A subagent:** add or edit `subagents/<name>.md`, run the generator, and commit the canonical source and the
  generated trees together. Bump the subagent-count badge.
- **An MCP server:** add the block to all four MCP templates, document it in [docs/MCP_SETUP.md](docs/MCP_SETUP.md),
  and bump the MCP-count badge.

---

## Subagents and skills

Use subagents proactively, not reactively, and spawn them in parallel when the work is independent (one message,
multiple `Agent` calls). Direct a generalist subagent to invoke specific skills as part of its task. Full catalogue:
list `.claude/agents/*.md` or `.opencode/agents/*.md`; browse skills in [.agents/skills/](.agents/skills/).

For this repo specifically: `markdown-writer` owns doc work, `python-patterns` and `python-testing` own the generator
and lint scripts, `code-reviewer` runs before any merge, and `bash` / `powershell` own the update scripts in
[docs/AGENTS-UPDATE.md](docs/AGENTS-UPDATE.md).

---

## Working Principles

Apply these to every task, in order. They govern how you work; the `coding-standards` skill governs what the code
should look like.

1. **Think before coding.** State assumptions. When the prompt is ambiguous, surface the interpretations and ask
   rather than silently picking one. Propose a simpler approach if one exists.
2. **Simplicity first.** Write the minimum that solves the problem. No unrequested features, abstractions, or
   configurability. If 200 lines could be 50, rewrite it.
3. **Surgical changes.** Touch only what the task requires. Do not "improve" adjacent code or reformat untouched
   lines. Match existing style. Remove only the imports and helpers your own change orphans.
4. **Goal-driven execution.** Convert vague asks into verifiable checks, state the plan, then loop until each check
   passes. Do not claim a task is done without running the verification.

---

## Maintenance follow-ups

- **OpenCode preflight plugin rides an experimental hook.** [.opencode/plugin/preflight.js](.opencode/plugin/preflight.js)
  uses `experimental.chat.system.transform`. Periodically check whether OpenCode has stabilised or renamed it
  (`https://opencode.ai/docs/plugins/`). When it leaves experimental, drop the `experimental.` prefix or update the
  key, refresh the docs, and remove this note. This is tracked in project memory so it resurfaces each session.
