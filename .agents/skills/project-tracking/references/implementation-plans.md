# Implementation Plan Standards

What a plan has to contain before implementation starts on it. Load this file when writing or reviewing a plan for a
change that touches more than one file, more than one service, or anything running in production.

---

### Applicable rules come first

Open every plan with the coding rules that govern the work, taken from the project's own standards rather than
recalled from memory. Naming them up front is what stops a rule violation being discovered in review, after the code
is written.

```markdown
## Applicable Rules

- Java: constructor injection, no field injection
- REST: RFC 7807 error envelope
- DB migrations: explicit constraint naming (ck_, uq_, fk_, ix_)
- Security: Argon2id for password hashing
```

---

### Verification section before implementation

State how the finished work will be checked before any of it is written, so the check is a target rather than a
retrospective justification.

```markdown
## Verification Checklist

- [ ] File-by-file comparison against existing code
- [ ] Each change checked against the applicable rules above
- [ ] Vulnerability pass: injection, SSRF, XSS, secret exposure
- [ ] Review simulation: would this pass a senior review
- [ ] No regression in adjacent functionality
```

---

### Rollback plan for anything touching production

Every plan that reaches a production system carries a rollback plan with a trigger condition somebody can observe, an
ordered set of steps, and a named owner.

```markdown
## Rollback Plan

Trigger: error rate above 1 percent within 5 minutes of deploy, or a failing health check
Steps:
1. Run the automated pipeline rollback job
2. If the pipeline is unavailable, roll the deployment back directly
3. Notify the on-call channel with the incident reference
Owner: platform on-call
```

---

### Dependency analysis before splitting into steps

Work out what the change touches and how far the effect reaches before deciding on an order. Blast radius sets how
strict the review has to be and which deployment window the change belongs in.

```markdown
## Dependency Analysis

Affected components: auth-service, user-api, frontend login flow
Blast radius: every user on the login path, roughly 2,000 requests per minute
Change order: database migration, then service deploy, then frontend deploy
Rollback order: frontend revert, then service revert, then migration down
```

---

### Risk table for a change over three files or on a shared service

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Migration times out on a large table | Medium | High | Run in a low-traffic window with a lock timeout |
| Configuration differs between environments | Low | Medium | Environment parity check in CI |
| N+1 introduced in the new query | Low | Low | Query-count assertion in an integration test |

---

### Phase the delivery when any threshold is crossed

Split into phases when more than five files change, when more than one service is affected, or when the change cannot
deploy atomically because it needs a migration and a code deploy together. Each phase has to be independently
deployable and has to leave production working on its own.

---

### Performance impact for a hot path

For an endpoint above roughly a thousand requests per minute, or any latency-sensitive flow, state the expected
change and how it will be measured before the change ships.

```markdown
## Performance Impact

Affected path: POST /api/orders, averaging 3,200 requests per minute
Estimated latency change: plus 2ms from one additional database lookup per request
Mitigation: cache the lookup for 60 seconds, which brings the additional latency under 0.5ms at p99
Load test: the k6 script at tests/load/order-flow.js must pass p99 at or under 50ms before the production deploy
```
