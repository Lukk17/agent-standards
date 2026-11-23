# Replicas, alerts, backups and erasure

Open this for the reasoning behind the replica routing, monitoring threshold, backup and erasure rules in [SKILL.md](../SKILL.md). Server settings are in [server-settings.md](server-settings.md), and the EXPLAIN ANALYZE examples in [explain-analyze.md](explain-analyze.md).

---

### Route reads to replicas, except read-your-own-writes

- Writes go to the primary.
- Reads that tolerate eventual consistency go to a replica.
- A read in the same request as a preceding write goes to the primary, or the user sees their own change missing.

Alert on these before a user reports them:

| Metric | Alert threshold |
| --- | --- |
| Query duration | over 500ms |
| Connection pool utilization | over 80% for more than 30s |
| Replication lag | over 30s |
| Disk usage | over 80% |

---

### Back up on a schedule you have actually tested

- Daily full backup plus continuous WAL archiving.
- Backups stored in a separate cloud account from the application.
- AES-256 encryption at rest.
- Quarterly restore drills that measure the real recovery time, not the intended one.
- RTO and RPO written in the runbook, next to the measured numbers from the last drill.

A backup nobody has restored is a hypothesis.

---

### Erase personal data within the legal window

GDPR requires an answer to an erasure request without undue delay and within one month of receipt, extendable by two
further months for complex or numerous requests (Article 12(3)). Two workable shapes:

1. Soft delete then purge: set `deleted_at`, exclude the row everywhere, delete it for real after the window.
2. Pseudonymize in place: overwrite the identifying columns with a non-reversible value, keeping the row for referential
   integrity and aggregates.

Never hard-delete before checking cascade behaviour and audit-log retention, because a `DELETE` that cascades into an
audit trail destroys the evidence that the erasure was lawful.
