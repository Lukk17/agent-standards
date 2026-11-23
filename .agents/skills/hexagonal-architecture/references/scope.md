# Scope

Companion reference for the [hexagonal-architecture](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Building new features where long-term maintainability and testability matter.
- Refactoring layered or framework-heavy code where domain logic is mixed with I/O concerns.
- Supporting multiple interfaces for the same use case (HTTP, CLI, queue workers, cron jobs).
- Replacing infrastructure (database, external APIs, message bus) without rewriting business rules.
- The user says "restructure this around ports and adapters", "my domain imports the ORM", "test this use case without a database", or "swap this payment provider".

Use this skill when the request involves boundaries, domain-centric design, refactoring tightly coupled services, or decoupling application logic from specific libraries.

---

### When not to activate

- The HTTP or GraphQL contract at the edge: use `api-design`.
- Runtime-specific handler, service, and repository code: use `node-backend-patterns` or `springboot-patterns`.
- Language-neutral service concerns such as idempotency, retries, and outbox: use `backend-patterns`.
- Schema, index, and query work behind the outbound adapter: use `postgres-patterns` or `springboot-patterns`.
- The shared engineering floor of SOLID, naming, and error handling: use `coding-standards`.
- A one-off script or a prototype whose whole lifetime is a week. The indirection costs more than it returns.

---

### Related skills

- `coding-standards` for the shared engineering floor this skill supplies the architecture section of.
- `api-design` for the contract the inbound adapter exposes.
- `backend-patterns` for idempotency, retries, and outbox behaviour inside the application layer.
- `node-backend-patterns`, `springboot-patterns`, `python-patterns`, and `golang-patterns` for the adapter code.
- `tdd-workflow` for the test discipline that makes the boundaries worth having.
- `node-backend-patterns` for the Express or Next.js inbound adapter around the use case.
- `react-patterns` when a similar boundary is wanted on the client.
