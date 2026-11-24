---
name: keycloak-patterns
description: 'Keycloak administration and Keycloak.AuthServices for .NET: realms, flows, MFA. Use when the user says "set up SSO with Keycloak" or "add Keycloak auth to my .NET API". Not for Spring Security, use `springboot-patterns`.'
metadata:
  version: "1.1.0"
---

# Keycloak Patterns

The identity boundary from both sides: the Keycloak server that issues tokens, and the .NET application that consumes them. Written for Keycloak 26 and Keycloak.AuthServices 2, on .NET 8 or newer.

---

### When not to activate

- Spring Security resource-server configuration, use `springboot-patterns`.
- Verifying a JWT inside a Node service, use `node-backend-patterns`.
- The HTTP contract and error bodies the protected endpoints expose, use `api-design`.

---

### Rules

1. Decide first whether a token is minted wrong, which is the server side, or validated wrong, which is the client side.
2. The master realm administers Keycloak only: each application and environment gets its own realm, with an exactly matching client ID.
3. Roles go to groups, never to users directly, composites only where one role implies another. A .NET policy names the role, never a raw claim.
4. Never edit a built-in flow: copy it, change the copy, and bind the copy.
5. Keep `verify-token-audience` on, and set `KC_HOSTNAME` and TLS so the issuer is the public URL.
6. No client secret in a committed `appsettings.json`, server configuration through the environment, never the command line, and a realm export treated as a secret.
7. Pin the image to a minor tag, never `latest`, build once, run `start --optimized` on PostgreSQL, and pin NuGet packages too.

---

### Which reference to open for which task

| Both sides | Open |
| --- | --- |
| The reasoning behind a rule above, and the version notes | [boundary-rules.md](references/boundary-rules.md) |
| Before calling a change or its review done | [checklist.md](references/checklist.md) |

| Server side | Open |
| --- | --- |
| Dev mode, production start, object model, CLI | [administration.md](references/administration.md) |
| Realms, users, groups, attributes, sessions | [realm-management.md](references/realm-management.md) |
| OIDC and SAML clients, scopes, mappers, service accounts | [client-configuration.md](references/client-configuration.md) |
| Authentication flows, MFA, brokering, social login | [authentication-sso.md](references/authentication-sso.md) |
| Roles, UMA authorization, policies | [authorization-rbac.md](references/authorization-rbac.md) |
| LDAP and Active Directory, sync, mappers | [user-federation.md](references/user-federation.md) |
| Password policy, brute force, TLS, audit | [security-hardening.md](references/security-hardening.md) |
| Clustering, database, caching, backup | [ha-scalability.md](references/ha-scalability.md) |
| Login, token, LDAP sync or session failures | [administration-troubleshooting.md](references/administration-troubleshooting.md) |
| Validating a token on a platform other than .NET | [token-validation.md](references/token-validation.md) |

| .NET side | Open |
| --- | --- |
| Packages, minimal setup, the configuration section | [dotnet-auth-services.md](references/dotnet-auth-services.md) |
| The smallest working snippet of one .NET feature | [dotnet-integration-examples.md](references/dotnet-integration-examples.md) |
| JWT Bearer, OIDC web apps, the audience mapper | [authentication.md](references/authentication.md) |
| RBAC, role claims, token introspection | [authorization.md](references/authorization.md) |
| Authorization Server, protected resources | [resource-protection.md](references/resource-protection.md) |
| Admin REST API, Kiota clients | [admin-sdk.md](references/admin-sdk.md) |
| UMA Protection API | [protection-api.md](references/protection-api.md) |
| Organization multi-tenancy and membership | [organization-authorization.md](references/organization-authorization.md) |
| .NET Aspire, templates, OpenTelemetry | [devex.md](references/devex.md) |
| Every configuration option and the adapter file | [configuration.md](references/configuration.md) |
| Recipes, failures, debugging | [dotnet-troubleshooting.md](references/dotnet-troubleshooting.md) |
