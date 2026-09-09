---
name: hexagonal-architecture
description: Ports and adapters design covering domain and use-case boundaries, inbound and outbound ports, dependency inversion, adapters, the composition root, and per-boundary testing in TypeScript, Java, Kotlin and Go. Use when you say "restructure this around ports and adapters", "my domain imports the ORM", "test this use case without a database", or "swap this payment provider". Not for HTTP contract design, use `api-design`.
---

# Hexagonal Architecture

Hexagonal architecture (Ports and Adapters) keeps business logic independent from frameworks, transport, and persistence
details. The core app depends on abstract ports, and adapters implement those ports at the edges.

This skill is the architecture authority the `coding-standards` hub defers to for its Architecture section.

Language baselines the examples assume, current as of September 2026: TypeScript 5 on Node.js 24 LTS, Java 21 LTS,
Kotlin 2.2, and Go 1.25.

---

### When to activate

- Building new features where long-term maintainability and testability matter.
- Refactoring layered or framework-heavy code where domain logic is mixed with I/O concerns.
- Supporting multiple interfaces for the same use case (HTTP, CLI, queue workers, cron jobs).
- Replacing infrastructure (database, external APIs, message bus) without rewriting business rules.

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
| A complete vertical slice in TypeScript, from port to composition root | [references/typescript-example.md](references/typescript-example.md) |

---

### Core Concepts

- Domain model: Business rules and entities/value objects. No framework imports.
- Use cases (application layer): Orchestrate domain behavior and workflow steps.
- Inbound ports: Contracts describing what the application can do (commands/queries/use-case interfaces).
- Outbound ports: Contracts for dependencies the application needs (repositories, gateways, event publishers, clock,
  UUID, etc.).
- Adapters: Infrastructure and delivery implementations of ports (HTTP controllers, DB repositories, queue consumers,
  SDK wrappers).
- Composition root: Single wiring location where concrete adapters are bound to use cases.

Outbound port interfaces usually live in the application layer (or in domain only when the abstraction is truly
domain-level), while infrastructure adapters implement them.

Dependency direction is always inward:

- Adapters -> application/domain
- Application -> port interfaces (inbound/outbound contracts)
- Domain -> domain-only abstractions (no framework or infrastructure dependencies)
- Domain -> nothing external

---

### How It Works

#### Step 1: Model a use case boundary

Define a single use case with a clear input and output DTO. Keep transport details (Express `req`, GraphQL `context`,
job payload wrappers) outside this boundary.

#### Step 2: Define outbound ports first

Identify every side effect as a port:

- persistence (`UserRepositoryPort`)
- external calls (`BillingGatewayPort`)
- cross-cutting (`LoggerPort`, `ClockPort`)

Ports should model capabilities, not technologies.

#### Step 3: Implement the use case with pure orchestration

Use case class/function receives ports via constructor/arguments. It validates application-level invariants, coordinates
domain rules, and returns plain data structures.

#### Step 4: Build adapters at the edge

- Inbound adapter converts protocol input to use-case input.
- Outbound adapter maps app contracts to concrete APIs/ORM/query builders.
- Mapping stays in adapters, not inside use cases.

#### Step 5: Wire everything in a composition root

Instantiate adapters, then inject them into use cases. Keep this wiring centralized to avoid hidden service-locator
behavior.

#### Step 6: Test per boundary

- Unit test use cases with fake ports.
- Integration test adapters with real infra dependencies.
- E2E test user-facing flows through inbound adapters.

---

### Architecture Diagram

```mermaid
flowchart LR
  Client["Client (HTTP/CLI/Worker)"] --> InboundAdapter["Inbound Adapter"]
  InboundAdapter -->|"calls"| UseCase["UseCase (Application Layer)"]
  UseCase -->|"uses"| OutboundPort["OutboundPort (Interface)"]
  OutboundAdapter["Outbound Adapter"] -->|"implements"| OutboundPort
  OutboundAdapter --> ExternalSystem["DB/API/Queue"]
  UseCase --> DomainModel["DomainModel"]
```

---

### Suggested Module Layout

Use feature-first organization with explicit boundaries:

```text
src/
  features/
    orders/
      domain/
        Order.ts
        OrderPolicy.ts
      application/
        ports/
          inbound/
            CreateOrder.ts
          outbound/
            OrderRepositoryPort.ts
            PaymentGatewayPort.ts
        use-cases/
          CreateOrderUseCase.ts
      adapters/
        inbound/
          http/
            createOrderRoute.ts
        outbound/
          postgres/
            PostgresOrderRepository.ts
          stripe/
            StripePaymentGateway.ts
      composition/
        ordersContainer.ts
```

---

### Multi-Language Mapping

Use the same boundary rules across ecosystems. Only the syntax and the wiring style change.

- TypeScript/JavaScript
  - Ports: `application/ports/*` as interfaces/types.
  - Use cases: classes/functions with constructor/argument injection.
  - Adapters: `adapters/inbound/*`, `adapters/outbound/*`.
  - Composition: explicit factory/container module (no hidden globals).
- Java
  - Packages: `domain`, `application.port.in`, `application.port.out`, `application.usecase`, `adapter.in`,
    `adapter.out`.
  - Ports: interfaces in `application.port.*`.
  - Use cases: plain classes (Spring `@Service` is optional, not required).
  - Composition: Spring config or a manual wiring class, keeping wiring out of domain and use-case classes.
- Kotlin
  - Modules/packages mirror the Java split (`domain`, `application.port`, `application.usecase`, `adapter`).
  - Ports: Kotlin interfaces.
  - Use cases: classes with constructor injection (Koin/Dagger/Spring/manual).
  - Composition: module definitions or dedicated composition functions, never a service locator.
- Go
  - Packages: `internal/<feature>/domain`, `application`, `ports`, `adapters/inbound`, `adapters/outbound`.
  - Ports: small interfaces owned by the consuming application package.
  - Use cases: structs with interface fields plus explicit `New...` constructors.
  - Composition: wire in `cmd/<app>/main.go` (or dedicated wiring package), keep constructors explicit.

---

### Anti-Patterns to Avoid

- Domain entities importing ORM models, web framework types, or SDK clients.
- Use cases reading directly from `req`, `res`, or queue metadata.
- Returning database rows directly from use cases without domain/application mapping.
- Letting adapters call each other directly instead of flowing through use-case ports.
- Spreading dependency wiring across many files with hidden global singletons.

---

### Migration Playbook

1. Pick one vertical slice (single endpoint/job) with frequent change pain.
2. Extract a use-case boundary with explicit input/output types.
3. Introduce outbound ports around existing infrastructure calls.
4. Move orchestration logic from controllers/services into the use case.
5. Keep old adapters, but make them delegate to the new use case.
6. Add tests around the new boundary (unit + adapter integration).
7. Repeat slice by slice, and avoid full rewrites.

#### Refactoring Existing Systems

- Strangler approach: keep current endpoints, route one use case at a time through new ports/adapters.
- No big-bang rewrites: migrate per feature slice and preserve behavior with characterization tests.
- Facade first: wrap legacy services behind outbound ports before replacing internals.
- Composition freeze: centralize wiring early so new dependencies do not leak into domain/use-case layers.
- Slice selection rule: prioritize high-churn, low-blast-radius flows first.
- Rollback path: keep a reversible toggle or route switch per migrated slice until production behavior is verified.

---

### Testing Guidance (Same Hexagonal Boundaries)

- Domain tests: test entities/value objects as pure business rules (no mocks, no framework setup).
- Use-case unit tests: test orchestration with fakes or stubs for outbound ports, asserting business outcomes and port
  interactions.
- Outbound adapter contract tests: define shared contract suites at port level and run them against each adapter
  implementation.
- Inbound adapter tests: verify protocol mapping (HTTP/CLI/queue payload to use-case input and output/error mapping back
  to protocol).
- Adapter integration tests: run against real infrastructure (DB/API/queue) for serialization, schema/query behavior,
  retries, and timeouts.
- End-to-end tests: cover critical user journeys through inbound adapter -> use case -> outbound adapter.
- Refactor safety: add characterization tests before extraction, and keep them until the new boundary behavior is
  equivalent.

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
