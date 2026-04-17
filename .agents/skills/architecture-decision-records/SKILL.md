---
name: architecture-decision-records
description: Capture architectural decisions made during Claude Code sessions as structured ADRs. Auto-detects decision moments, records context, alternatives considered, and rationale. Maintains an ADR log so future developers understand why the codebase is shaped the way it is.
origin: ECC
---

# Architecture Decision Records

Capture architectural decisions as they happen during coding sessions. Instead of decisions living only in Slack threads, PR comments, or someone's memory, this skill produces structured ADR documents that live alongside the code.

## When to Activate

- User explicitly says "let's record this decision" or "ADR this"
- User chooses between significant alternatives (framework, library, pattern, database, API design)
- User says "we decided to..." or "the reason we're doing X instead of Y is..."
- User asks "why did we choose X?" (read existing ADRs)
- During planning phases when architectural trade-offs are discussed

## ADR Format

Use the lightweight ADR format proposed by Michael Nygard, adapted for AI-assisted development:

```markdown
# ADR-NNNN: [Decision Title]

**Date**: YYYY-MM-DD
**Status**: proposed | accepted | deprecated | superseded by ADR-NNNN
**Deciders**: [who was involved]

## Context

What is the issue that we're seeing that is motivating this decision or change?

[2-5 sentences describing the situation, constraints, and forces at play]

## Decision

What is the change that we're proposing and/or doing?

[1-3 sentences stating the decision clearly]

## Alternatives Considered

### Alternative 1: [Name]
- **Pros**: [benefits]
- **Cons**: [drawbacks]
- **Why not**: [specific reason this was rejected]

### Alternative 2: [Name]
- **Pros**: [benefits]
- **Cons**: [drawbacks]
- **Why not**: [specific reason this was rejected]

## Consequences

What becomes easier or more difficult to do because of this change?

### Positive
- [benefit 1]
- [benefit 2]

### Negative
- [trade-off 1]
- [trade-off 2]

### Risks
- [risk and mitigation]
```

## Workflow

### Capturing a New ADR

When a decision moment is detected:

1. **Initialize (first time only)** — if `docs/adr/` does not exist, ask the user for confirmation before creating the directory, a `README.md` seeded with the index table header (see ADR Index Format below), and a blank `template.md` for manual use. Do not create files without explicit consent.
2. **Identify the decision** — extract the core architectural choice being made
3. **Gather context** — what problem prompted this? What constraints exist?
4. **Document alternatives** — what other options were considered? Why were they rejected?
5. **State consequences** — what are the trade-offs? What becomes easier/harder?
6. **Assign a number** — scan existing ADRs in `docs/adr/` and increment
7. **Confirm and write** — present the draft ADR to the user for review. Only write to `docs/adr/NNNN-decision-title.md` after explicit approval. If the user declines, discard the draft without writing any files.
8. **Update the index** — append to `docs/adr/README.md`

### Reading Existing ADRs

When a user asks "why did we choose X?":

1. Check if `docs/adr/` exists — if not, respond: "No ADRs found in this project. Would you like to start recording architectural decisions?"
2. If it exists, scan `docs/adr/README.md` index for relevant entries
3. Read matching ADR files and present the Context and Decision sections
4. If no match is found, respond: "No ADR found for that decision. Would you like to record one now?"

### ADR Directory Structure

```
docs/
└── adr/
    ├── README.md              ← index of all ADRs
    ├── 0001-use-nextjs.md
    ├── 0002-postgres-over-mongo.md
    ├── 0003-rest-over-graphql.md
    └── template.md            ← blank template for manual use
```

### ADR Index Format

```markdown
# Architecture Decision Records

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [0001](0001-use-nextjs.md) | Use Next.js as frontend framework | accepted | 2026-01-15 |
| [0002](0002-postgres-over-mongo.md) | PostgreSQL over MongoDB for primary datastore | accepted | 2026-01-20 |
| [0003](0003-rest-over-graphql.md) | REST API over GraphQL | accepted | 2026-02-01 |
```

## Decision Detection Signals

Watch for these patterns in conversation that indicate an architectural decision:

**Explicit signals**
- "Let's go with X"
- "We should use X instead of Y"
- "The trade-off is worth it because..."
- "Record this as an ADR"

**Implicit signals** (suggest recording an ADR — do not auto-create without user confirmation)
- Comparing two frameworks or libraries and reaching a conclusion
- Making a database schema design choice with stated rationale
- Choosing between architectural patterns (monolith vs microservices, REST vs GraphQL)
- Deciding on authentication/authorization strategy
- Selecting deployment infrastructure after evaluating alternatives

## What Makes a Good ADR

### Do
- **Be specific** — "Use Prisma ORM" not "use an ORM"
- **Record the why** — the rationale matters more than the what
- **Include rejected alternatives** — future developers need to know what was considered
- **State consequences honestly** — every decision has trade-offs
- **Keep it short** — an ADR should be readable in 2 minutes
- **Use present tense** — "We use X" not "We will use X"

### Don't
- Record trivial decisions — variable naming or formatting choices don't need ADRs
- Write essays — if the context section exceeds 10 lines, it's too long
- Omit alternatives — "we just picked it" is not a valid rationale
- Backfill without marking it — if recording a past decision, note the original date
- Let ADRs go stale — superseded decisions should reference their replacement

## ADR Lifecycle

```
proposed → accepted → [deprecated | superseded by ADR-NNNN]
```

- **proposed**: decision is under discussion, not yet committed
- **accepted**: decision is in effect and being followed
- **deprecated**: decision is no longer relevant (e.g., feature removed)
- **superseded**: a newer ADR replaces this one (always link the replacement)

## Categories of Decisions Worth Recording

| Category | Examples |
|----------|---------|
| **Technology choices** | Framework, language, database, cloud provider |
| **Architecture patterns** | Monolith vs microservices, event-driven, CQRS |
| **API design** | REST vs GraphQL, versioning strategy, auth mechanism |
| **Data modeling** | Schema design, normalization decisions, caching strategy |
| **Infrastructure** | Deployment model, CI/CD pipeline, monitoring stack |
| **Security** | Auth strategy, encryption approach, secret management |
| **Testing** | Test framework, coverage targets, E2E vs integration balance |
| **Process** | Branching strategy, review process, release cadence |

## Integration with Other Skills

- **Planner agent**: when the planner proposes architecture changes, suggest creating an ADR
- **Code reviewer agent**: flag PRs that introduce architectural changes without a corresponding ADR

---

## Implementation Plan Standards

### Plan Structure

Every implementation plan must open with a section listing **all applicable coding rules** that govern the work:

```markdown
## Applicable Rules
- Java: `@Slf4j` mandatory; no `LoggerFactory.getLogger(...)`
- REST: RFC 7807 error envelope
- DB migrations: explicit constraint naming (`ck_`, `uq_`, `fk_`, `ix_`)
- Security: Argon2id for password hashing
```

This prevents rule violations discovered late in review.

### Mandatory Verification Section

Every plan must include a verification section **before** implementation begins:

```markdown
## Verification Checklist
- [ ] File-by-file comparison against existing code
- [ ] Each change checked against applicable coding rules
- [ ] Vulnerability assessment (SQL injection, SSRF, XSS, secrets exposure)
- [ ] PR simulation: would this pass review?
- [ ] No regressions in adjacent functionality
```

### Rollback Plan (Required)

Every plan that touches production systems must include:

```markdown
## Rollback Plan
**Trigger condition:** Error rate > 1% within 5 minutes of deployment, or health check failure
**Rollback steps:**
1. Trigger automated pipeline rollback job
2. If pipeline unavailable: `kubectl rollout undo deployment/my-app`
3. Notify on-call channel with incident ticket
**Owner:** Platform team on-call
```

### Dependency Analysis

Before breaking work into steps, analyse dependencies:

```markdown
## Dependency Analysis
**Affected components:** auth-service, user-api, frontend login flow
**Blast radius:** All users on login path; ~2,000 req/min
**Change order:** DB migration → service deploy → frontend deploy
**Rollback order:** Frontend revert → service revert → DB migration down
```

Blast radius determines review strictness and deployment window requirements.

### Risk Assessment

Every plan that changes > 3 files or touches a shared service must include a risk table:

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| DB migration timeout on large table | Medium | High | Run during low-traffic window; add `LOCK TIMEOUT` |
| Config mismatch between envs | Low | Medium | Use environment parity check in CI |
| N+1 introduced in new query | Low | Low | Add query count assertion in integration test |

### Phased Delivery Rule

Split into phases when **any** of these conditions hold:
- > **5 files** changed, OR
- > **1 service** affected, OR
- The change cannot be deployed atomically (requires migration + code deploy)

Each phase must be independently deployable and not break production in isolation.

### Performance Impact

For plans that touch **hot paths** (endpoints with > 1,000 req/min or latency-sensitive flows):

```markdown
## Performance Impact
**Affected path:** POST /api/orders (avg 3,200 req/min)
**Estimated latency change:** +2ms (additional DB lookup per request)
**Mitigation:** Cache lookup result in Redis for 60s — reduces additional latency to < 0.5ms p99
**Load test:** k6 script in `tests/load/order-flow.js` must pass p99 ≤ 50ms before production deploy
```
