---
name: keycloak-patterns
description: 'Keycloak server administration and the Keycloak.AuthServices .NET client: realms, clients, flows and MFA, RBAC and UMA, LDAP federation and hardening, plus JWT Bearer and OIDC wiring and the Admin SDKs. Use when the user says "set up SSO with Keycloak", "enable MFA for admins" or "add Keycloak auth to my .NET API". Not for Spring Security, use `springboot-patterns`.'
---

# Keycloak Patterns

The identity boundary from both sides: the Keycloak server that issues tokens, and the .NET application that consumes
them. The hub holds the rules for both sides, and each reference holds the depth for one.

---

### Versions

Written for Keycloak 26 and Keycloak.AuthServices 2, on .NET 8 or newer. Two things follow from that pairing and are easy to get wrong:

- Keycloak 26 renamed the bootstrap admin variables to `KC_BOOTSTRAP_ADMIN_USERNAME` and
  `KC_BOOTSTRAP_ADMIN_PASSWORD`. The older `KEYCLOAK_ADMIN` pair no longer works.
- A .NET application binds the `Keycloak` configuration section in the kebab-case adapter format, so `auth-server-url`
  and `verify-token-audience` are keys, not properties invented locally.

---

### When to activate

- Standing up a Keycloak instance, or moving one from development mode to production.
- Creating a realm, a client, a role model, or an authentication flow, including MFA and identity brokering.
- Federating users from LDAP or Active Directory.
- Adding JWT Bearer or OIDC authentication to an ASP.NET Core API or web application.
- Enforcing realm or client roles through an authorization policy, or protecting a resource with UMA.
- Calling the Keycloak Admin REST API or Protection API from C#.
- Diagnosing a login failure, a rejected token, an audience mismatch, or a session that ends too soon.
- The user says "create a realm and a confidential client", "connect Keycloak to Active Directory", "why does my token fail audience validation", "require a realm role on this endpoint", "call the Keycloak Admin API from C#" or "protect this resource with UMA".

---

### When not to activate

- Spring Security resource-server configuration. Use `springboot-patterns`.
- Verifying a JWT inside a Node service. Use `node-backend-patterns`.
- The HTTP contract and error bodies the protected endpoints expose. Use `api-design`.
- Threat modelling the wider application. Use the `security-auditor` agent.
- Running the Keycloak container inside a local stack. Use `docker-patterns`.
- Pinning the package versions across a multi-project solution. Use `build-dependency-management`.

---

### Rules

Reasoning per rule: [references/boundary-rules.md](references/boundary-rules.md).

1. Decide first whether a token is minted wrong (server: realm, client, flow, mappers, roles, issuer) or validated wrong (client: audience, policy, claims, token cache, SDK call).
2. The master realm administers Keycloak only: each application and environment gets its own realm, with an exactly matching client ID.
3. Roles go to groups, never to users directly, composites only where one role implies another. A .NET policy names the role, never a raw claim.
4. Never edit a built-in flow: copy the Browser flow, add OTP or WebAuthn, set it Required or Conditional on a group, bind the copy.
5. Keep `verify-token-audience` on, and set `KC_HOSTNAME` and TLS so the issuer is the public URL.
6. No client secret in a committed `appsettings.json`, server configuration through the environment, never the command line, and a realm export treated as a secret.
7. Pin the image to a minor tag, never `latest`, build once with `bin/kc.sh build`, run `start --optimized` on PostgreSQL, and pin NuGet packages too.

---

### Which reference to open for which task

Open the table for your side of the boundary.

Server side:

| Task | Open |
| --- | --- |
| Dev mode, optimized production start, object model, SSO client, MFA, LDAP, CLI, defaults | [references/administration.md](references/administration.md) |
| Realms, users, groups, attributes, sessions | [references/realm-management.md](references/realm-management.md) |
| OIDC and SAML clients, scopes, mappers, service accounts | [references/client-configuration.md](references/client-configuration.md) |
| Authentication flows, MFA, identity brokering, social login | [references/authentication-sso.md](references/authentication-sso.md) |
| Roles, UMA fine-grained authorization, policies | [references/authorization-rbac.md](references/authorization-rbac.md) |
| LDAP and Active Directory integration, sync, mappers | [references/user-federation.md](references/user-federation.md) |
| Password policy, brute force, TLS, audit, production checks | [references/security-hardening.md](references/security-hardening.md) |
| Clustering, database tuning, caching, monitoring, backup | [references/ha-scalability.md](references/ha-scalability.md) |
| Login failures, token issues, LDAP sync, session problems | [references/administration-troubleshooting.md](references/administration-troubleshooting.md) |
| Integration examples, token validation on any platform | [references/integration-examples.md](references/integration-examples.md) |

.NET side:

| Task | Open |
| --- | --- |
| Packages, minimal Web API setup, the configuration section, quick starts | [references/dotnet-auth-services.md](references/dotnet-auth-services.md) |
| JWT Bearer and OIDC web app auth, RFC 8414 discovery, the audience mapper | [references/authentication.md](references/authentication.md) |
| RBAC, role claims transformation, token introspection | [references/authorization.md](references/authorization.md) |
| Authorization Server, protected resources, policy builder, parameter resolvers | [references/resource-protection.md](references/resource-protection.md) |
| Admin REST API, hand-written and Kiota clients, token management | [references/admin-sdk.md](references/admin-sdk.md) |
| UMA Protection API, resource and permission management | [references/protection-api.md](references/protection-api.md) |
| Organization multi-tenancy and membership requirements | [references/organization-authorization.md](references/organization-authorization.md) |
| .NET Aspire, project templates, OpenTelemetry | [references/devex.md](references/devex.md) |
| Every configuration option, naming conventions, adapter file | [references/configuration.md](references/configuration.md) |
| Recipes, failures, debugging | [references/dotnet-troubleshooting.md](references/dotnet-troubleshooting.md) |

---

### Related skills

- `springboot-patterns` and `node-backend-patterns` for validating Keycloak tokens outside .NET.
- `api-design` for the status codes and problem bodies an authorization failure should return.
- The `security-auditor` agent for threat modelling around the identity boundary.
- `docker-patterns` for running the Keycloak container safely in a local stack.
- `build-dependency-management` for pinning the image tag and the package versions.
- `observability-and-logging` for what the OpenTelemetry instrumentation should feed into.

---

### Checklist

- [ ] The container image is pinned to a minor version tag, and the server runs `start --optimized` against PostgreSQL.
- [ ] Bootstrap admin credentials are replaced by a real admin account and removed.
- [ ] Applications run against their own realm, never master, and every client has exact redirect URIs.
- [ ] Every client, confidential or public, requires PKCE, and MFA is enforced for administrative accounts through a
      copied flow.
- [ ] Roles reach users through groups, and policies name realm or client roles rather than raw claims.
- [ ] `KC_HOSTNAME` and TLS are configured so the issuer matches the public URL.
- [ ] `verify-token-audience` is on and `ssl-required` is `external` or `all` outside local development.
- [ ] Client secrets and realm exports are handled as secrets, never committed.
- [ ] Brute-force protection and event logging are enabled, exported, and visible in traces.
