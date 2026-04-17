---
name: agentic-engineering
description: Operate as an agentic engineer using eval-first execution, decomposition, and cost-aware model routing.
origin: ECC
---

# Agentic Engineering

Use this skill for engineering workflows where AI agents perform most implementation work and humans enforce quality and risk controls.

## Operating Principles

1. Define completion criteria before execution.
2. Decompose work into agent-sized units.
3. Route model tiers by task complexity.
4. Measure with evals and regression checks.

## Eval-First Loop

1. Define capability eval and regression eval.
2. Run baseline and capture failure signatures.
3. Execute implementation.
4. Re-run evals and compare deltas.

## Task Decomposition

Apply the 15-minute unit rule:
- each unit should be independently verifiable
- each unit should have a single dominant risk
- each unit should expose a clear done condition

## Model Routing

- Haiku: classification, boilerplate transforms, narrow edits
- Sonnet: implementation and refactors
- Opus: architecture, root-cause analysis, multi-file invariants

## Session Strategy

- Continue session for closely-coupled units.
- Start fresh session after major phase transitions.
- Compact after milestone completion, not during active debugging.

## Review Focus for AI-Generated Code

Prioritize:
- invariants and edge cases
- error boundaries
- security and auth assumptions
- hidden coupling and rollout risk

Do not waste review cycles on style-only disagreements when automated format/lint already enforce style.

## Cost Discipline

Track per task:
- model
- token estimate
- retries
- wall-clock time
- success/failure

Escalate model tier only when lower tier fails with a clear reasoning gap.

---

## Workflow Discipline

### Anti-Hallucination Protocol

Before implementing **any non-trivial integration, external API, or library usage**:
1. Run a web search or consult official documentation to verify current API signatures
2. Never assume an API or library works based on training data alone — SDKs change
3. If documentation is unavailable or unclear, state the assumption explicitly before writing code

### Approval Protocol

- Require **explicit user approval** before starting any implementation step
- Never infer approval from context (e.g., a previous "yes" to a design does not approve the implementation)
- If a step was not explicitly covered in the original request, pause and confirm scope before proceeding

### Side-Effect Disclosure

Before proposing any configuration change, infrastructure modification, or destructive operation:
- List the **worst-case side effects** (data loss, downtime, permission escalation, irreversibility)
- State the rollback procedure
- Only proceed after user acknowledgement

### Question Protocol

When you have open questions before writing code:
1. Number every open question
2. Answer each one with your best reasoning
3. Only begin writing code after all questions are resolved
4. Do not ask the user questions you can answer yourself through research

### File Creation Constraints

Do **not** create any of the following ephemeral files:
- `Task.md`, `Walkthrough.md`, `Summary.md`, `Notes.md`
- Validation scripts used once and discarded
- Temporary documentation files describing what you just did

These add noise to the repository. If persistent documentation is needed, update the relevant `SKILL.md`, `README.md`, or `AGENTS.md` instead.

---

## Tool Use Hierarchy

Always prefer the dedicated tool over a shell command:

| Operation | Use this | Not this |
|---|---|---|
| Read a file | `Read` tool | `cat`, `head`, `tail` |
| Edit a file | `Edit` tool | `sed`, `awk`, heredoc |
| Create a file | `Write` tool | `echo >`, `tee` |
| Find files | `Glob` tool | `find`, `ls` |
| Search content | `Grep` tool | `grep`, `rg` |
| Everything else | `Bash` | — |

Reserve `Bash` exclusively for operations that have no dedicated tool equivalent (running tests, installing packages, git commands).

---

## Context Window Management

### 70% Utilisation Threshold

When context utilisation reaches **70%**:
1. Summarise completed work in a brief status note
2. Compress prior research into key findings only
3. Split the remaining work into clearly scoped sub-tasks
4. Use sub-agents for large isolated tasks to protect the main context

### Large Task Decomposition

Break any task > ~15 minutes of work into units of:
- One logical change per unit
- Independently verifiable (can be tested in isolation)
- Clear input and output

---

## Multi-Agent Coordination

### Parent Agent Responsibilities

- Validate sub-agent output **before** incorporating it into the main task
- Do not pass partial or unvalidated results to the next step
- If a sub-agent's output is unexpected, investigate before proceeding — do not assume correctness

### Sub-Agent Constraints

- Sub-agents must **not** take irreversible actions (push to remote, deploy, delete files) without explicit parent or user authorisation
- Every sub-agent receives the **full context** needed for its task — do not rely on implicit shared state
- Sub-agents report back; parent agents decide

---

## Escalation Policy

Stop and ask the user when **any** of the following occur:

1. You encounter unexpected state (files that should not exist, branches, config mismatch)
2. You have made **3 failed attempts** at the same approach
3. The next required action is **destructive** or **irreversible**
4. The scope of the request is ambiguous and the wrong interpretation would waste significant effort

Do not brute-force past blockers. Pause, diagnose, and escalate.

---

## Output Formatting

- Use **code blocks** (triple backtick with language) for all code, commands, and file paths
- Use **numbered lists** for sequential steps
- Use **bullet lists** for unordered items
- **Never** use filler phrases: "Certainly!", "Great question!", "Of course!", "Sure thing!"
- Lead with the answer or action — not the reasoning
- If you can say it in one sentence, do not use three

### Mental Compiler Check

Before presenting any code:
1. Trace the logic end-to-end in your head
2. Check for: type errors, null/undefined dereferences, off-by-one errors, missing awaits, unclosed resources
3. If you find an error, fix it before outputting — do not output code you know is wrong

```typescript
// Mental check example:
async function getUser(id: string) {
  const user = await db.findById(id)
  // ✓ null-check: what if user is null?
  return user.name  // FAIL: potential null dereference
}

// After check:
async function getUser(id: string) {
  const user = await db.findById(id)
  if (!user) throw new Error(`User ${id} not found`)
  return user.name  // PASS
}
```
