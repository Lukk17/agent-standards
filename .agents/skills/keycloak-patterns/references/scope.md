# Scope

Companion reference for the [keycloak-patterns](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Standing up a Keycloak instance, or moving one from development mode to production.
- Creating a realm, a client, a role model, or an authentication flow, including MFA and identity brokering.
- Federating users from LDAP or Active Directory.
- Adding JWT Bearer or OIDC authentication to an ASP.NET Core API or web application.
- Enforcing realm or client roles through an authorization policy, or protecting a resource with UMA.
- Calling the Keycloak Admin REST API or Protection API from C#.
- Diagnosing a login failure, a rejected token, an audience mismatch, or a short session.
- The user says "set up SSO with Keycloak", "enable MFA for admins", "add Keycloak auth to my .NET API", "create a realm and a confidential client", "connect Keycloak to Active Directory", "why does my token fail audience validation", "require a realm role on this endpoint", "call the Keycloak Admin API from C#" or "protect this resource with UMA".

---

### When not to activate

- Spring Security resource-server configuration. Use `springboot-patterns`.
- Verifying a JWT inside a Node service. Use `node-backend-patterns`.
- The HTTP contract and error bodies the protected endpoints expose. Use `api-design`.
- Threat modelling the wider application. Use the `security-auditor` agent.
- Running the Keycloak container inside a local stack. Use `docker-patterns`.
- Pinning the package versions across a multi-project solution. Use `build-dependency-management`.

---

### Related skills

- `springboot-patterns` and `node-backend-patterns` for validating Keycloak tokens outside .NET.
- `api-design` for the status codes and problem bodies an authorization failure should return.
- The `security-auditor` agent for threat modelling around the identity boundary.
- `docker-patterns` for running the Keycloak container safely in a local stack.
- `build-dependency-management` for pinning the image tag and the package versions.
- `observability-and-logging` for what the OpenTelemetry instrumentation should feed into.
