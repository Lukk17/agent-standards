# Scope

Companion reference for the [api-design](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Designing a new endpoint or reviewing an existing API contract.
- Choosing a status code, an error body, or a response envelope.
- Adding pagination, filtering, or sorting to a collection endpoint.
- Planning a versioning or deprecation path for a public or partner API.
- Deciding what an endpoint must accept to be safe to retry.
- The user says "design this endpoint", "what status code should this return", "review our API contract", "add cursor pagination to this list", or "how do we deprecate v1".

---

### When not to activate

- Service structure, layering, or data access behind the endpoint: use `backend-patterns`.
- Node, Express, or Next.js implementation of a handler: use `node-backend-patterns`.
- Spring Boot controllers and their error handling: use `springboot-patterns`.
- Authentication mechanics and token verification: use `application-security-review`. Threat modelling: use the `security-auditor`
  agent.
- SOAP and WSDL contracts: use `soap-webservices`.
- Writing the reference documentation for a finished contract: use `markdown-writer`.

---

### Related skills

- `backend-patterns` for idempotency storage, retries, and readiness behind the contract.
- `node-backend-patterns` and `springboot-patterns` for handler-level implementations.
- `hexagonal-architecture` for keeping transport concerns out of the domain.
- `application-security-review` before exposing an endpoint that touches credentials, payments, or personal data.
- `soap-webservices` when the contract is WSDL rather than HTTP and JSON.
- `observability-and-logging` for correlating a request identifier across services.
- `database-migrations` when a breaking version change reaches the stored shape as well as the wire shape.
- `deployment-patterns` for running two API versions side by side during the overlap.
- `postgres-patterns` for the indexes a sort or filter parameter needs.
- `backend-patterns` for the language-neutral cursor rules.
- `node-backend-patterns` for resolver and data-loader wiring in a Node service, and the service structure around a Next.js handler.
- `application-security-review` before exposing a GraphQL endpoint to the public internet.
- `python-patterns` and `golang-patterns` for the service structure around a Django REST or Go handler.
- `springboot-patterns` for the Java and Spring Boot equivalent of the handler examples.
