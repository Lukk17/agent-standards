---
name: agentic-engineering
description: 'Running engineering work where agents write most of the code and a human holds the quality bar: eval-first execution, agent-sized units, capability-tier routing, approval gates, context budgets and subagents. Use when the user says "plan this work for agents", "which tier should run this" or "split this into agent-sized units". Not for the regression suite itself, use `ai-regression-testing`.'
---

# Agentic Engineering

How to run engineering work where agents produce most of the code and a human owns the quality bar. It covers what
to define before execution starts, how to size and route the units of work, and which moments require a human to say
yes before anything proceeds.

---

### When to activate

- Planning a piece of work that will be handed to one or more agents
- Deciding how much capability a given unit of work needs before spending it
- Splitting a large change into units an agent can finish and verify
- Setting up the measurement that will say whether the work succeeded
- Coordinating a parent agent and its subagents on one task
- Deciding whether to continue a session, start a fresh one, or compact
- The user says "set up evals before we start"

---

### When not to activate

- Writing the regression suite or sandbox test harness itself, use `ai-regression-testing`
- Writing unit tests for a specific change, use `tdd-workflow` or the language test skill
- Reviewing the code an agent produced, use `code-reviewer`
- Deciding what the code should look like, use `coding-standards`
- Recording the architectural decision that came out of the work, use `architecture-decision-records`
- Surveying which automations already exist in the project, use `automation-inventory`

---

### Reference files

| Task | Open |
|---|---|
| The done condition, capability and regression evals, unit sizing, the tier table, external interfaces, with examples | [references/planning-the-work.md](references/planning-the-work.md) |
| Approval, questions, process files, the tool table, context budget, subagents, escalation, cost, code checks, review | [references/running-the-work.md](references/running-the-work.md) |

---

### Plan the work

1. Write a testable done condition before any code is generated, such as "POST /orders rejects a negative quantity with 422 and the existing order tests still pass".
2. Define a capability eval, expected to fail before the change, and a regression eval, expected to pass before and after. Run both for a baseline, implement, re-run both, and compare the deltas.
3. Size each unit so one agent finishes it in roughly a quarter of an hour, verifiable on its own, with one dominant risk and a clear done condition.
4. Route each unit by the capability tier it demands (small and fast, mid, strongest), named by purpose rather than product. Pick the tier at spawn time, because a subagent definition never pins a model. Escalate only after a lower tier fails with a visible reasoning gap, and name the gap.
5. Check the current documentation before implementing against an external API, SDK or library. Without documentation, state the assumption out loud first.

---

### Require explicit approval at each risk boundary

Never infer approval from earlier context. Agreement to a design is not agreement to its implementation, and
agreement to one step is not agreement to the next. Before any configuration change, infrastructure change or
destructive operation, list the worst-case side effects and the rollback procedure, then wait.

---

### Run the work

1. Research what you can answer yourself. Number each question that remains, give your best reasoning for each, and wait rather than picking an interpretation silently.
2. Create no task lists, walkthroughs, summaries, notes or one-shot validation scripts in the repository. Update the document that already owns the subject. The exception is `tasks.md` at the project root and `.agents/tasks.widget.json`, runtime state the task-list hook keeps git-ignored: keep them current and never delete or commit them.
3. Prefer the purpose-built tool (file reader, editor, writer, file-pattern and content search) over the shell, matched by capability rather than name. Keep the shell for tests, builds, installs and version control. An operator who asks for shell-first behaviour overrides this.
4. At around seventy percent context use, compress: summarise finished work, reduce research to findings, split what remains, and push large isolated work to a subagent. Compact after a milestone, never mid-debugging.
5. A subagent reports and the parent decides: validate its output before use, give it the full context it needs, and let it take no irreversible action (push, deploy, delete) without explicit authorisation from the parent or the user.
6. Stop and ask the user on unexpected state, three failed attempts at one approach, a destructive or irreversible next action, or a scope ambiguity where the wrong reading wastes real effort.
7. Record per unit the tier, a token estimate, retries, wall-clock time, and success or failure.
8. Trace code end to end before presenting it, looking for type errors, null dereferences, off-by-one boundaries, missing awaits and unclosed resources, and fix what you find.
9. Spend review on invariants, edge cases, error boundaries, security and authentication assumptions, hidden coupling and rollout risk, not on style a formatter and linter already decide.

---

### Related skills

- `ai-regression-testing` owns the regression harness, sandbox-mode API testing and automated bug-check workflows
- `code-reviewer` owns the structured review pass over what an agent produced
- `coding-standards` owns what the resulting code should look like
- `tdd-workflow` owns the red-green-refactor loop inside a single unit
- `project-tracking` owns turning units of work into tracked items with acceptance criteria
- `architecture-decision-records` owns capturing a design decision the work produced

---

### Checklist

- [ ] A done condition exists and is testable before execution starts
- [ ] A capability eval and a regression eval are both defined, with baselines captured
- [ ] Units are independently verifiable and carry one dominant risk each
- [ ] Each unit is routed to a tier justified by what it demands
- [ ] External interfaces were checked against current documentation
- [ ] Every risk boundary got explicit approval, with side effects and rollback stated
- [ ] Open questions were numbered and answered rather than guessed
- [ ] No process or summary files were left in the repository
- [ ] Subagent output was validated before use
- [ ] Cost and outcome recorded per unit
