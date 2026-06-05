# Preflight gate

Before any code work on a task, in one line, name the skill(s) and subagent(s) that own it and invoke them, or
state "none apply" and why.

This is a hard gate, not a suggestion. Investigation, review, and bounded implementation are delegated by default.
Doing a specialist's work inline from the main session is the failure mode this prevents. Re-run this check at the
start of every task, not just the first.

Canonical wording lives at the top of `AGENTS.md`. This file is the Kilo Code adapter; Kilo has no event-hook
mechanism, so the gate ships as a rule that loads into context on every task.
