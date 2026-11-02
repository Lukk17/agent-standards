# Running the Work

Contents:

- [Require explicit approval at each risk boundary](#require-explicit-approval-at-each-risk-boundary)
- [Answer your own questions, then number what remains](#answer-your-own-questions-then-number-what-remains)
- [Do not leave process files behind](#do-not-leave-process-files-behind)
- [Prefer the purpose-built tool over the shell](#prefer-the-purpose-built-tool-over-the-shell)
- [Budget the context window](#budget-the-context-window)
- [Parent validates, subagent reports](#parent-validates-subagent-reports)
- [Escalate instead of brute-forcing](#escalate-instead-of-brute-forcing)
- [Track the cost of each unit](#track-the-cost-of-each-unit)
- [Check the code before presenting it](#check-the-code-before-presenting-it)
- [Review what agents get wrong, not what linters catch](#review-what-agents-get-wrong-not-what-linters-catch)

Companion reference for the [agentic-engineering](../SKILL.md) skill. Load it for the reasoning and the pass and fail examples behind the execution rules: approval at risk boundaries, open questions, process files, tool choice, context budget, subagent validation, escalation, cost tracking, self-checking code, and review focus.

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

One exception: `tasks.md` at the project root and `.agents/tasks.widget.json` are runtime state, not process files. The task-list hook keeps them, git-ignored, and the model updates `tasks.md` as work moves. Keep them current and never delete or commit them.

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
