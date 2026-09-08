---
name: agentic-engineering
description: 'Running engineering work where agents write most of the code and a human holds the quality bar: eval-first execution, agent-sized decomposition, capability-tier routing, approval and escalation, context budgeting, and multi-agent coordination. Use when you say "plan this work for agents", "which tier should run this", "split this into agent-sized units", or "set up evals before we start". Not for building the regression suite itself, use `ai-regression-testing`.'
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

---

### When not to activate

- Writing the regression suite or sandbox test harness itself, use `ai-regression-testing`
- Writing unit tests for a specific change, use `tdd-workflow` or the language test skill
- Reviewing the code an agent produced, use `code-reviewer`
- Deciding what the code should look like, use `coding-standards`
- Recording the architectural decision that came out of the work, use `architecture-decision-records`
- Surveying which automations already exist in the project, use `automation-inventory`

---

### Define completion before execution

Write the done condition before any code is generated. An agent given a goal but no completion test explores widely
and retries, which burns time and produces work nobody asked for.

Pass:

```text
Done when POST /orders rejects a negative quantity with 422 and the existing order tests still pass.
```

Fail:

```text
Done when the order endpoint handles bad input properly.
```

---

### Run a capability eval and a regression eval

Two different measurements answer two different questions. A capability eval asks whether the new behaviour now
works, and it is expected to fail before the change. A regression eval asks whether anything that already worked
stopped working, and it is expected to pass before and after. Running only the first ships breakage. Running only the
second ships nothing.

Take a rate limiter added to a login endpoint.

Capability eval, expected to fail at baseline and pass afterwards:

```text
Send 11 login attempts for one account in 60 seconds. Expect the 11th to return 429 with a Retry-After header.
```

Regression eval, expected to pass at baseline and still pass afterwards:

```text
Send 1 valid login. Expect 200 and a session cookie. Send 1 wrong password. Expect 401 and no cookie.
```

The loop is: define both, run both to capture the baseline and the failure signature, implement, re-run both, and
compare the deltas rather than reading the final run alone.

Fail:

```text
Wrote the rate limiter, ran the full suite once at the end, it was green, shipped.
```

---

### Size units so one agent can finish and verify one

Aim at a unit an agent can complete in roughly a quarter of an hour of work. Each unit is independently verifiable,
carries a single dominant risk, and exposes a clear done condition. A unit with two risks fails in a way that takes
longer to diagnose than the unit took to write.

Pass:

```text
Unit 1: add the migration adding orders.cancelled_at, nullable, with a down migration. Risk: migration lock time.
Unit 2: expose cancelled_at on the order response DTO. Risk: contract change for existing clients.
```

Fail:

```text
Unit 1: add order cancellation end to end, migration through UI.
```

---

### Route by capability tier, not by habit

Match the strength of the model to what the unit actually demands, and describe the tier by what it is for rather
than by a product name, because names change and a skill that hardcodes them goes stale.

| Tier | Use it for | Signal you picked wrong |
|---|---|---|
| Small and fast | Lookups, classification, mechanical transforms, narrow single-file edits | It gets the answer right but you did not need it that fast |
| Mid capability | Bounded implementation, refactors inside known boundaries, test writing | It loops on the same failure without new reasoning |
| Strongest available | Architecture, root-cause analysis, cross-file invariants, final review | You are paying design rates for a rename |

Escalate a tier only after the lower tier fails with a visible reasoning gap, and say what the gap was. Escalating on
the first error teaches you nothing about whether the task was actually hard.

Pass:

```text
Small tier rewrote the 40 import paths. Mid tier implemented the handler. Strongest tier reviewed the transaction boundary.
```

Fail:

```text
Used the strongest tier for everything because it is the safest choice.
```

---

### Verify external interfaces before using them

Before implementing against an external API, SDK or library, check the current documentation. Training data goes
stale and an invented method signature costs more to debug than it costs to look up. When documentation is
unavailable, state the assumption out loud before writing code against it.

Pass:

```text
Checked the current SDK reference: the client takes a config object, not positional args, since v4. Implementing that.
```

Fail:

```text
The client constructor takes the API key as the first argument.
```

---

### Require explicit approval at each risk boundary

Never infer approval from earlier context. Agreement to a design is not agreement to its implementation, and
agreement to one step is not agreement to the next. Before any configuration change, infrastructure change or
destructive operation, list the worst-case side effects and the rollback procedure, then wait.

Pass:

```text
Next step drops the legacy index. Worst case: 40s table lock on a 12M row table. Rollback: recreate from the DDL below. Proceed?
```

Fail:

```text
You approved the migration plan, so I also applied it to staging.
```

---

### Answer your own questions, then number what remains

Research anything you can determine yourself before asking. For what genuinely remains open, number each question,
give your best reasoning for each, and wait rather than picking an interpretation silently. An ambiguous request
resolved by guessing costs more than the round trip.

Pass:

```text
1. Should cancelled orders stay in the list endpoint? My reading: yes, with a status filter. Confirm?
2. Retention for cancelled rows? No policy found in the repo. Need your answer.
```

Fail:

```text
The requirements were unclear so I picked the interpretation that seemed most likely and built it.
```

---

### Do not leave process files behind

Do not create task lists, walkthroughs, summaries, notes files or one-shot validation scripts in the repository.
They read as project documentation to the next person and are wrong within a week. Where something is genuinely
worth keeping, update the document that already owns that subject.

Pass:

```text
Updated the existing README section on the new flag. No new files.
```

Fail:

```text
Added IMPLEMENTATION_SUMMARY.md, Walkthrough.md and check_migration.py at the repo root.
```

---

### Prefer the purpose-built tool over the shell

Every agent runtime exposes some set of purpose-built tools alongside a general shell. Reach for the specific one
first: the file reader for reading, the editor for modifying, the file writer for creating, the file-pattern search
for locating files, the content search for locating text. Reserve the shell for work with no dedicated equivalent,
such as running tests, invoking the build, installing packages, or version control. Tool names differ between
runtimes, so match the capability rather than a name from another tool's documentation.

| Operation | Reach for | Rather than |
|---|---|---|
| Read a file | The file reader | `cat`, `head`, `tail` |
| Modify a file | The editor | `sed`, `awk`, a heredoc rewrite |
| Create a file | The file writer | `echo >`, `tee` |
| Find files by name | The file-pattern search | `find`, `ls` |
| Find text in files | The content search | `grep`, `rg` |
| Run tests, build, install, version control | The shell | no dedicated equivalent exists |

A runtime whose operator has explicitly asked for shell-first behaviour overrides this table. Follow the operator.

---

### Budget the context window

At around seventy percent utilisation, stop adding and start compressing: summarise what is finished, reduce prior
research to its findings, split what remains into scoped sub-tasks, and push large isolated work to a subagent so the
main thread keeps room to reason. Compact after a milestone, never in the middle of active debugging, because the
detail you drop is the detail the diagnosis needs.

Pass:

```text
Phase 1 done and committed. Compacting to the summary, then starting phase 2 in a fresh session.
```

Fail:

```text
Context is nearly full and the bug is half diagnosed. Compacting now.
```

---

### Parent validates, subagent reports

A subagent reports and the parent decides. Validate a subagent's output before folding it into the main task, and
investigate anything unexpected rather than assuming it is correct. Give each subagent the full context its task
needs, because implicit shared state does not cross the boundary. A subagent takes no irreversible action, including
pushing, deploying or deleting, without explicit authorisation from the parent or the user.

Pass:

```text
Subagent reported the migration applied. Checked the schema myself before running the dependent unit.
```

Fail:

```text
Subagent said it was done, so I moved on and started the next unit against its output.
```

---

### Escalate instead of brute-forcing

Stop and ask the user on any of: unexpected state such as files, branches or config that should not exist, three
failed attempts at the same approach, a next action that is destructive or irreversible, or a scope ambiguity where
the wrong reading would waste real effort.

Pass:

```text
Third failure on the same import resolution. Stopping. The tsconfig paths and the bundler alias disagree. Which is authoritative?
```

Fail:

```text
Attempt 7 at the same fix with a slightly different regex.
```

---

### Track the cost of each unit

Record per unit: the tier used, a token estimate, retries, wall-clock time, and success or failure. Without the
record there is no evidence about which tier was actually needed, and routing stays a matter of taste.

---

### Check the code before presenting it

Trace the logic end to end before output. Look for type errors, null dereferences, off-by-one boundaries, missing
awaits and unclosed resources. Fix what you find rather than shipping code you already know is wrong.

Pass:

```typescript
async function getUser(id: string) {
  const user = await db.findById(id)
  if (!user) throw new Error(`User ${id} not found`)
  return user.name
}
```

Fail:

```typescript
async function getUser(id: string) {
  const user = await db.findById(id)
  return user.name
}
```

---

### Review what agents get wrong, not what linters catch

Spend review attention on invariants and edge cases, error boundaries, security and authentication assumptions,
hidden coupling, and rollout risk. Do not spend review cycles on style where an automated formatter and linter
already decide the answer.

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
