---
name: automation-inventory
description: 'Audit of every automation (jobs, hooks, CI, MCP servers), each with a live state and proof. Use when the user says "what automations do I have" or "audit our tooling". Not for one CI system, use `github-ops`.'
metadata:
  version: "1.1.0"
---

# Automation Inventory

An audit method for answering what automation exists in a project, what state each piece is in, and which pieces should be kept, merged, cut or fixed next. It produces an evidence table before it produces an opinion, so no recommendation rests on a config file that merely mentions a tool.

---

### When not to activate

- Operating a single CI provider, triaging its runs, finding why one job fails or preparing a release, use `github-ops`
- Designing the deployment pipeline itself rather than surveying what exists, use `deployment-patterns`
- Reviewing the code an automation runs rather than the automation wiring, use `code-reviewer`

---

### Steps

1. Start read-only and stay there until the user asks for fixes, because an audit that repairs things as it goes destroys the evidence of the original state.
2. Inventory every surface before judging any of it: scheduled jobs and timers, git hooks and agent hooks, CI and CD workflows, MCP servers, external connectors and app integrations, wrapper scripts and repository entry points, and notification routes. A partial list makes overlap invisible.
3. Classify each item by live state, not by presence in a config file. Give it exactly one live state (configured, authenticated, verified, stale, missing) and one problem type (active breakage, authentication outage, stale status, overlap, missing capability, or none).
4. Prove every claim with a command and its output, run against the exact thing the claim names. When the tool that would prove it is unavailable, say the claim is unverified and state your confidence.
5. Report one evidence table, each row carrying the automation, where it is defined, its live state, its problem type and the proof. Then give one call per row: keep, merge, cut or fix next. No row ends in "investigate further" without a named next command.
6. Say what is ambiguous: name what you could not determine and what would settle it.

---

### Reference files

| Task | Open |
|---|---|
| A step needs its reasoning or its pass and fail example | [audit-steps.md](references/audit-steps.md) |
| Writing the report: the table columns and a filled example | [evidence-table.md](references/evidence-table.md) |
| Whether a neighbouring skill owns the job | [scope.md](references/scope.md) |
| Before calling the audit done | [checklist.md](references/checklist.md) |
