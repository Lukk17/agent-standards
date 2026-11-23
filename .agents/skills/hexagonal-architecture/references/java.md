# Hexagonal Architecture in Java

How the ports-and-adapters boundaries map onto Java. The boundary rules are the same in every language, and only the syntax and the wiring style change. Open it when the code in front of you is Java. The method itself is in [design-and-migration.md](design-and-migration.md).

---

### Mapping

- Packages: `domain`, `application.port.in`, `application.port.out`, `application.usecase`, `adapter.in`,
  `adapter.out`.
- Ports: interfaces in `application.port.*`.
- Use cases: plain classes (Spring `@Service` is optional, not required).
- Composition: Spring config or a manual wiring class, keeping wiring out of domain and use-case classes.
