# Hexagonal Architecture in Go

How the ports-and-adapters boundaries map onto Go. The boundary rules are the same in every language, and only the syntax and the wiring style change. Open it when the code in front of you is Go. The method itself is in [design-and-migration.md](design-and-migration.md).

---

### Mapping

- Packages: `internal/<feature>/domain`, `application`, `adapters/inbound`, `adapters/outbound`.
- Ports: small interfaces declared in the consuming `application` package, not in a separate `ports` package.
- Use cases: structs with interface fields plus explicit `New...` constructors.
- Composition: wire in `cmd/<app>/main.go` (or dedicated wiring package), keep constructors explicit.
