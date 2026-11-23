# Hexagonal Architecture Checklist

Run it before calling a ports-and-adapters design, a refactoring step, or a review of one, done.

- [ ] Domain and use-case layers import only internal types and ports.
- [ ] Every external dependency is represented by an outbound port.
- [ ] Validation occurs at boundaries (inbound adapter + use-case invariants).
- [ ] Use immutable transformations (return new values/entities instead of mutating shared state).
- [ ] Errors are translated across boundaries (infra errors -> application/domain errors).
- [ ] Composition root is explicit and easy to audit.
- [ ] Use cases are testable with simple in-memory fakes for ports.
- [ ] Refactoring starts from one vertical slice with behavior-preserving tests.
- [ ] Language/framework specifics stay in adapters, never in domain rules.
