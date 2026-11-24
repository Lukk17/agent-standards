---
name: agentic-engineering
description: 'Work that agents code and a human approves: evals first, unit sizing, tier routing, approval gates. Use when the user says "plan this work for agents". Not for a regression suite, use `ai-regression-testing`.'
metadata:
  version: "1.1.0"
---

# Agentic Engineering

How to run engineering work where agents produce most of the code and a human owns the quality bar.

---

### When not to activate

- Writing the regression suite or sandbox test harness itself, use `ai-regression-testing`
- Writing unit tests for a specific change, use `tdd-workflow` or the language test skill
- Reviewing the code an agent produced, use `code-reviewer`

---

### Plan the work

1. Write a testable done condition before any code is generated.
2. Define a capability eval, expected to fail before the change, and a regression eval, expected to pass before and after. Run both for a baseline, implement, re-run both, and compare the deltas.
3. Size each unit so one agent finishes it in roughly a quarter of an hour, verifiable on its own, with one dominant risk and a clear done condition.
4. Route each unit by the capability tier it demands (small and fast, mid, strongest), named by purpose rather than product, and pick the tier at spawn time. Escalate only after a lower tier fails with a visible reasoning gap, and name the gap.
5. Check the current documentation before implementing against an external API, SDK or library. Without documentation, state the assumption out loud first.

---

### Require explicit approval at each risk boundary

Never infer approval from earlier context: agreement to a design is not agreement to its implementation, and agreement to one step is not agreement to the next. Before any configuration change, infrastructure change or destructive operation, list the worst-case side effects and the rollback procedure, then wait.

---

### Run the work

1. Research what you can answer yourself. Number each question that remains, give your best reasoning for each, and wait rather than picking an interpretation silently.
2. Create no task lists, walkthroughs, summaries, notes or one-shot validation scripts in the repository, and update the document that already owns the subject. The exception is the runtime state in `tasks.md` at the project root and `.agents/tasks.widget.json`: keep them current and never delete or commit them.
3. Prefer the purpose-built tool over the shell, matched by capability rather than name, and keep the shell for tests, builds, installs and version control. An operator who asks for shell-first behaviour overrides this.
4. At around seventy percent context use, compress: summarise finished work, reduce research to findings, split what remains, and push large isolated work to a subagent. Compact after a milestone, never mid-debugging.
5. A subagent reports and the parent decides: validate its output before use, give it the full context it needs, and let it take no irreversible action (push, deploy, delete) without explicit authorisation from the parent or the user.
6. Stop and ask the user on unexpected state, three failed attempts at one approach, a destructive or irreversible next action, or a scope ambiguity where the wrong reading wastes real effort.
7. Record per unit the tier, a token estimate, retries, wall-clock time, and success or failure.
8. Trace code end to end before presenting it, and fix what you find.
9. Spend review on invariants, edge cases, error boundaries, security and authentication assumptions, hidden coupling and rollout risk, not on style a formatter and linter already decide.

---

### Reference files

| Task | Open |
|---|---|
| A planning rule needs its reasoning, its example or the tier table | [planning-the-work.md](references/planning-the-work.md) |
| A rule for running the work needs its reasoning, its example, the tool table or the defect list for the code trace | [running-the-work.md](references/running-the-work.md) |
| Before calling the work done | [checklist.md](references/checklist.md) |
