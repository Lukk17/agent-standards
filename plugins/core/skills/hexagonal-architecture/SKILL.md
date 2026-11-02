---
name: hexagonal-architecture
description: 'Ports and adapters design: use-case boundaries, inbound and outbound ports, dependency inversion, adapters, the composition root, and per-boundary testing in TypeScript, Java, Kotlin and Go. Use when the user says "restructure this around ports and adapters", "my domain imports the ORM", or "swap this payment provider". Not for HTTP contract design, use `api-design`.'
---

# Hexagonal Architecture

Hexagonal architecture (Ports and Adapters) keeps business logic independent from frameworks, transport, and persistence
details. The core app depends on abstract ports, and adapters implement those ports at the edges.

This skill is the architecture authority the `coding-standards` hub defers to for its Architecture section.

Written for TypeScript 5, Java 25, Kotlin 2 and Go 1.27. Check the project's own toolchain file before relying on a
language feature.

---

### When to activate

- Building new features where long-term maintainability and testability matter.
- Refactoring layered or framework-heavy code where domain logic is mixed with I/O concerns.
- Supporting multiple interfaces for the same use case (HTTP, CLI, queue workers, cron jobs).
- Replacing infrastructure (database, external APIs, message bus) without rewriting business rules.
- The user says "restructure this around ports and adapters", "my domain imports the ORM", "test this use case
  without a database", or "swap this payment provider".

Use this skill when the request involves boundaries, domain-centric design, refactoring tightly coupled services, or
decoupling application logic from specific libraries.

---

### When not to activate

- The HTTP or GraphQL contract at the edge: use `api-design`.
- Runtime-specific handler, service, and repository code: use `node-backend-patterns` or `springboot-patterns`.
- Language-neutral service concerns such as idempotency, retries, and outbox: use `backend-patterns`.
- Schema, index, and query work behind the outbound adapter: use `postgres-patterns` or `springboot-patterns`.
- The shared engineering floor of SOLID, naming, and error handling: use `coding-standards`.
- A one-off script or a prototype whose whole lifetime is a week. The indirection costs more than it returns.

---

### Reference map

| Task | Open |
| --- | --- |
| Designing a slice, laying out a module, mapping to Java, Kotlin or Go, migrating a legacy system, or testing per boundary | [references/design-and-migration.md](references/design-and-migration.md) |
| A complete vertical slice in TypeScript, from port to composition root | [references/typescript-example.md](references/typescript-example.md) |

---

### Core Concepts

- Domain model: business rules, entities and value objects, with no framework imports.
- Use cases: orchestrate domain behaviour, take ports through the constructor or arguments, return plain data.
- Inbound ports: what the application can do. Outbound ports: what it needs (repositories, gateways, publishers, clock, UUID), modelled as capabilities, not technologies, and usually declared in the application layer.
- Adapters: HTTP controllers, DB repositories, queue consumers and SDK wrappers that implement ports and own all mapping.
- Composition root: the single place adapters are bound to use cases, with no service locator or hidden singleton.
- Dependencies point inward: adapters to application and domain, application to ports, domain to nothing external.

---

### Rules

1. Model one use case with explicit input and output DTOs, and keep transport details (`req`, GraphQL `context`, job wrappers) outside it.
2. Define outbound ports first, one per side effect.
3. Domain entities never import ORM models, web types or SDK clients, use cases never read `req`, `res` or queue metadata or return raw rows, and adapters never call each other directly.
4. Lay out by feature (`domain`, `application/ports`, `use-cases`, `adapters`, `composition`). Go declares small interfaces in the consuming package.
5. Migrate slice by slice, starting with high-churn, low-blast-radius flows: characterization tests first, a facade over legacy services, wiring centralised early, a reversible toggle per slice, never a big-bang rewrite.
6. Test per boundary: pure domain tests, use cases with fake ports, shared contract suites per outbound port, inbound mapping tests, adapter integration on real infrastructure, end-to-end through the inbound adapter.

---

### Related skills

- `coding-standards` for the shared engineering floor this skill supplies the architecture section of.
- `api-design` for the contract the inbound adapter exposes.
- `backend-patterns` for idempotency, retries, and outbox behaviour inside the application layer.
- `node-backend-patterns`, `springboot-patterns`, `python-patterns`, and `golang-patterns` for the adapter code.
- `tdd-workflow` for the test discipline that makes the boundaries worth having.

---

### Checklist

- Domain and use-case layers import only internal types and ports.
- Every external dependency is represented by an outbound port.
- Validation occurs at boundaries (inbound adapter + use-case invariants).
- Use immutable transformations (return new values/entities instead of mutating shared state).
- Errors are translated across boundaries (infra errors -> application/domain errors).
- Composition root is explicit and easy to audit.
- Use cases are testable with simple in-memory fakes for ports.
- Refactoring starts from one vertical slice with behavior-preserving tests.
- Language/framework specifics stay in adapters, never in domain rules.
