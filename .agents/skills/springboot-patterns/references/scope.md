# Scope

Companion reference for the [springboot-patterns](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Building or restructuring a REST API on Spring MVC: layering, validation, errors, pagination, OpenAPI and outbound calls.
- The user says "structure this Spring Boot API", "add JWT auth to this endpoint", "why does this query run two hundred times", "write a @WebMvcTest for this controller", or "verify this before I open the PR".
- Caching, asynchronous work, events, authentication, authorization, CORS, headers or rate limiting.
- Entities, queries, fetch strategy, an N+1 query, or connection pool sizing.
- Tests, slices, Testcontainers, the coverage gate, and the pipeline before a merge or deploy.

---

### When not to activate

- Java language style, naming, immutability, and `Optional`, use `java-coding-standards`.
- Ports and adapters layering across the whole service, use `hexagonal-architecture`.
- Log format, metrics, tracing, and the startup readiness banner, use `observability-and-logging`.
- Schema change and rollout mechanics, use `database-migrations`.
- PostgreSQL query planning and index internals, use `postgres-patterns`.
- Language-neutral security review checklists, use `application-security-review`. Threat modelling goes to the `security-auditor` agent.
- Configuring Keycloak itself as the identity provider, use `keycloak-patterns`.
- Version catalogs, BOM imports, and dependency admission, use `build-dependency-management`.

---

### Related skills

| Skill | What it owns |
| --- | --- |
| `java-coding-standards` | Java naming, records, immutability, exceptions, and logging style. |
| `coding-standards` | The cross-language engineering floor these patterns sit on. |
| `hexagonal-architecture` | Ports and adapters layering, when the project has chosen it over layered packages. |
| `api-design` | Resource naming, status codes, and versioning policy above the framework. |
| `database-migrations` | Migration authoring, rollback, and zero-downtime schema change. |
| `postgres-patterns` | PostgreSQL-specific indexing and query planning. |
| `observability-and-logging` | Log format, metrics, tracing, health, and the startup banner. |
| `build-dependency-management` | Version catalogs, BOM imports, and where the plugin versions live. |
| `keycloak-patterns` | Configuring Keycloak as the identity provider behind these flows. |
| `code-reviewer` | Reviewing a Spring Boot diff against all of the above. |
