# Hexagonal Architecture in Kotlin

How the ports-and-adapters boundaries map onto Kotlin. The boundary rules are the same in every language, and only the syntax and the wiring style change. Open it when the code in front of you is Kotlin. The method itself is in [design-and-migration.md](design-and-migration.md).

---

### Mapping

- Modules/packages mirror the Java split (`domain`, `application.port`, `application.usecase`, `adapter`).
- Ports: Kotlin interfaces.
- Use cases: classes with constructor injection (Koin/Dagger/Spring/manual).
- Composition: module definitions or dedicated composition functions, never a service locator.
