# Implementation Plan Standards

Rules for creating and executing implementation plans.

---

## Plan Structure

Every implementation plan must:

1. Start by listing all applicable coding rules for the target language(s) — copy them from the relevant standards files so they are visible and enforced during implementation.
2. Present a clear step-by-step breakdown: requirements → structure → execution flow → standards to apply.
3. Override any previous plan entirely; never merge new steps into an existing plan.
4. Include a mandatory verification section (see below).

Validation steps in the plan are for the AI agent only — do not list manual steps for the user to perform.

---

## Approval Gate

Implementation must not begin until the user explicitly approves the plan. Answering user questions and receiving a new approval is required before proceeding if questions are asked after the plan is presented.

---

## Mandatory Verification Section

Every plan must end with a verification phase. Upon completion of implementation, the agent must execute all of the following and report results in the chat:

### 1. File-by-File Comparison
Systematically review every modified or newly created file against the original implementation plan. Confirm that every planned change exists and no unplanned changes were made.

### 2. Rule Compliance Check
For each file, verify line-by-line that all changes adhere to the applicable language standards and universal coding standards. Report pass/fail per rule per file.

### 3. Vulnerability Assessment
Identify any security risks, logical inconsistencies, or weak spots introduced by the changes.

### 4. Pull Request Simulation
Conduct a senior-level PR review of the entire changeset: correctness, naming, structure, edge cases, and standards compliance.

---

## Verification Output Format

Report the verification in the chat using this structure:

```
## Change Review

### <filename>
- [ ] Rule: <rule name> — <Passed / Failed: reason>
- [ ] Rule: <rule name> — <Passed / Failed: reason>

### Holistic Review
- Does this meet the requirement? <answer>
- Are there any quick fixes or architectural deviations? <answer>
- Security risks identified: <list or "None">
```

---

## Reporting Errors

Report all errors, deviations, and suboptimal implementations directly in the chat, structured by filename with specific details on what is wrong and why it fails the plan or standards.

---

## Rollback Plan

Every plan that modifies existing behaviour must include a rollback section:

1. **Rollback trigger**: define the condition that requires rollback (e.g., health check failure, error rate spike).
2. **Rollback steps**: exact, ordered steps to revert the change (migration rollback script, previous image tag, feature flag toggle).
3. **Rollback owner**: identify who executes the rollback (automated pipeline or manual operator step).

If a change is irreversible (e.g., a destructive database migration), state this explicitly and require explicit user acknowledgement before proceeding.

---

## Dependency Analysis

Before writing the step-by-step breakdown, identify:

- **Affected components**: every file, service, schema, or config that must change together.
- **Blast radius**: list downstream consumers that could be broken by the change.
- **Change order**: if components must be updated in a specific sequence, state the sequence and the reason.

---

## Risk Assessment

Include a risk table for every non-trivial plan:

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| \<description\> | Low / Med / High | Low / Med / High | \<action\> |

Risks that are High × High must be resolved before implementation begins.

---

## Phased Delivery

For large changes (more than 5 files or more than one service):

- Break the plan into phases, each independently deployable and testable.
- Each phase must leave the system in a valid, working state.
- State the definition of "done" for each phase before starting it.

---

## Performance Impact Assessment

For any change that touches a hot path, database query, or external API call, include:

- Expected change in latency (p50 / p99 estimate).
- Whether a load test or benchmark is required before merging.
- Any caching, indexing, or batching changes needed alongside the feature change.
