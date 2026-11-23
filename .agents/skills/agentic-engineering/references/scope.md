# Scope

Companion reference for the [agentic-engineering](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Planning a piece of work that will be handed to one or more agents
- Deciding how much capability a given unit of work needs before spending it
- Splitting a large change into units an agent can finish and verify
- Setting up the measurement that will say whether the work succeeded
- Coordinating a parent agent and its subagents on one task
- Deciding whether to continue a session, start a fresh one, or compact
- The user says "plan this work for agents", "which tier should run this", "split this into agent-sized units" or "set up evals before we start"

It covers what to define before execution starts, how to size and route the units of work, and which moments require a human to say yes before anything proceeds: eval-first execution, agent-sized units, capability-tier routing, approval gates, context budgets and subagents.

---

### When not to activate

- Writing the regression suite or sandbox test harness itself, use `ai-regression-testing`
- Writing unit tests for a specific change, use `tdd-workflow` or the language test skill
- Reviewing the code an agent produced, use `code-reviewer`
- Deciding what the code should look like, use `coding-standards`
- Recording the architectural decision that came out of the work, use `architecture-decision-records`
- Surveying which automations already exist in the project, use `automation-inventory`

---

### Related skills

- `ai-regression-testing` owns the regression harness, sandbox-mode API testing and automated bug-check workflows
- `code-reviewer` owns the structured review pass over what an agent produced
- `coding-standards` owns what the resulting code should look like
- `tdd-workflow` owns the red-green-refactor loop inside a single unit
- `project-tracking` owns turning units of work into tracked items with acceptance criteria
- `architecture-decision-records` owns capturing a design decision the work produced
