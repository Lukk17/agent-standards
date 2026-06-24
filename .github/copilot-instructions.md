# GitHub Copilot instructions

This is the agent-standards repo itself, not a consumer project. The authoritative instructions for working here live
in [AGENTS.md](../AGENTS.md). Read it first, then return to this file. Copilot CLI and VS Code chat read `AGENTS.md`
directly; this bridge file exists because local IntelliJ chat and some surfaces do not auto-read `AGENTS.md`, and
because Copilot has no hook mechanism to re-inject the gate per turn.

Copilot cannot enforce the preflight gate the way Claude Code, OpenCode, and Kilo Code do (those use hooks, plugins,
and rules). There is no Copilot equivalent, so the agent must self-apply the gate below on every task.

---

## Required opening move

Before any code work on a task, name the skill(s) and subagent(s) that own it and invoke them, or state "none apply"
and why. State this as the first line of your reply. It is a required output you produce, not a passive banner to skim
past. This is a hard gate.

Investigation, review, and bounded implementation are delegated by default. Doing a specialist's work inline from the
main session is the failure mode this gate prevents. Re-run the check at the start of every task. Most work in this
repo is documentation and the Python generator, so `markdown-writer`, `python-patterns`, and `python-testing` are the
usual owners, with `code-reviewer` before any merge.
