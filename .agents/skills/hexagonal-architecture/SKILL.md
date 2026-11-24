---
name: hexagonal-architecture
description: 'Ports and adapters design: use cases, ports, adapters, the composition root. Use when the user says "restructure this around ports and adapters" or "my domain imports the ORM". Not for HTTP contracts, use `api-design`.'
metadata:
  version: "1.1.0"
---

# Hexagonal Architecture

Hexagonal architecture (Ports and Adapters) keeps business logic independent from frameworks, transport, and persistence details. The core app depends on abstract ports, and adapters implement those ports at the edges.

This skill is the architecture authority the `coding-standards` hub defers to for its Architecture section.

Written for TypeScript 5, Java 25, Kotlin 2 and Go 1.27. Check the project's own toolchain file before relying on a language feature.

---

### When not to activate

- The HTTP or GraphQL contract at the edge, use `api-design`.
- Runtime-specific handler, service, and repository code, use `node-backend-patterns` or `springboot-patterns`.
- Language-neutral service concerns such as idempotency, retries, and outbox, use `backend-patterns`.

---

### Reference map

| Task | Open |
| --- | --- |
| Designing a slice, laying out a module, the anti-patterns, migrating a legacy system, or testing per boundary | [design-and-migration.md](references/design-and-migration.md) |
| The code is TypeScript or JavaScript: the layer mapping and a complete vertical slice, from port to composition root | [typescript.md](references/typescript.md) |
| The code is Java: packages, ports, use cases and wiring | [java.md](references/java.md) |
| The code is Kotlin: packages, ports, use cases and wiring | [kotlin.md](references/kotlin.md) |
| The code is Go: packages, where the interfaces are declared, constructors and wiring | [go.md](references/go.md) |
| Before calling a design, a refactoring step or its review done | [checklist.md](references/checklist.md) |

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
4. Lay out by feature (`domain`, `application/ports`, `use-cases`, `adapters`, `composition`), mapped onto each language as its reference shows.
5. Migrate slice by slice, starting with high-churn, low-blast-radius flows: characterization tests first, a facade over legacy services, wiring centralised early, a reversible toggle per slice, never a big-bang rewrite.
6. Test per boundary: pure domain tests, use cases with fake ports, shared contract suites per outbound port, inbound mapping tests, adapter integration on real infrastructure, end-to-end through the inbound adapter.
