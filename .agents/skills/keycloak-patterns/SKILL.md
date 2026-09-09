---
name: keycloak-patterns
description: "Keycloak server administration and the Keycloak.AuthServices .NET client, covering realms and clients, authentication flows and MFA, RBAC and UMA authorization, LDAP federation, hardening and clustering, plus JWT Bearer and OIDC wiring, role policies, resource protection, and the Admin and Protection API SDKs. Use when you say \"set up SSO with Keycloak\", \"create a realm and a confidential client\", \"enable MFA for admins\", \"connect Keycloak to Active Directory\", \"why does my token fail audience validation\", \"add Keycloak auth to my .NET API\", \"require a realm role on this endpoint\", \"call the Keycloak Admin API from C#\", or \"protect this resource with UMA\". Not for Spring Security resource-server configuration, use `springboot-patterns`."
---

# Keycloak Patterns

The identity boundary from both sides: the Keycloak server that issues tokens, and the .NET application that consumes
them. The hub carries the rules that hold on both sides, and each reference carries the depth for one of them.

---

### Baseline

Current as of September 2026: Keycloak 26, and Keycloak.AuthServices 2.x on .NET 8 or newer. Two things follow from
that pairing and are easy to get wrong:

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

---

### When not to activate

- Spring Security resource-server configuration. Use `springboot-patterns`.
- Verifying a JWT inside a Node service. Use `node-backend-patterns`.
- The HTTP contract and error bodies the protected endpoints expose. Use `api-design`.
- Threat modelling the wider application. Use `security-review`.
- Running the Keycloak container inside a local stack. Use `docker-patterns`.
- Pinning the package versions across a multi-project solution. Use `build-dependency-management`.

---

### Decide which side of the boundary the task is on

Most confusion here comes from fixing the wrong side. A token that is rejected is either minted wrong or validated
wrong, and the two have different owners. Establish which before touching anything.

```text
Server side: the realm, the client registration, the flow, the mappers, the roles, the issuer URL.
Client side: the audience check, the policy, the claims transformation, the token cache, the SDK call.
```

The reference map below splits along exactly that line.

---

### One realm per application and environment

The master realm exists to administer Keycloak and nothing else. Running an application against it means an
application compromise is an administrative compromise. Each application and each environment gets its own realm, and
the client ID the application sends has to match the registration exactly.

---

### Assign roles to groups, never directly to users

Direct role assignment produces a permission model nobody can audit a year later. Put users in groups, attach roles to
groups, and use composite roles when a role genuinely implies others. On the .NET side, name the realm or client role
in an authorization policy rather than reading a raw claim, so the check survives a claims-mapping change.

---

### Never edit a built-in authentication flow in place

Duplicate the Browser flow, add the OTP or WebAuthn authenticator to the copy, set it Required or Conditional on a
group, and bind the copy to the realm. Editing the built-in flow leaves no clean way back when the change locks
everyone out, including you.

---

### Verify the audience, and keep the issuer public

`verify-token-audience` on means a token minted for another client is rejected rather than accepted by coincidence.
It only works when the server issues the audience it claims to, which is what `KC_HOSTNAME` and TLS termination are
for: an issuer pointing at an internal address produces tokens that fail validation everywhere the public URL is
expected.

---

### Keep every secret out of the repository and out of the process list

A client secret belongs in configuration or a secret store, never in a committed `appsettings.json`. Supply server
runtime configuration through the environment rather than the command line, so nothing lands in a process listing. A
realm export contains client secrets, so treat the export directory as a secret rather than as a configuration
artifact to commit.

---

### Pin the version on both sides

A Keycloak image tagged `latest` silently upgrades across a major version and can change flow defaults, admin console
behaviour, and the database schema in one `docker pull`. Pin a major tag such as `26.0`, build once with
`bin/kc.sh build`, and start with `start --optimized` against PostgreSQL. Pin the NuGet package versions the same way.

---

### Which reference to open for which task

Each entry below carries its own reference map, so open the entry for your side of the boundary and let it route you.

| Task | Reference |
| --- | --- |
| Server administration: realms, clients, flows and MFA, RBAC, LDAP, hardening, clustering, server-side failures | [references/administration.md](references/administration.md) |
| The .NET client library: JWT Bearer and OIDC setup, role policies, resource protection, Admin and Protection SDKs | [references/dotnet-auth-services.md](references/dotnet-auth-services.md) |

---

### Related skills

- `springboot-patterns` and `node-backend-patterns` for validating Keycloak tokens outside .NET.
- `api-design` for the status codes and problem bodies an authorization failure should return.
- `security-review` for threat modelling around the identity boundary.
- `docker-patterns` for running the Keycloak container safely in a local stack.
- `build-dependency-management` for pinning the image tag and the package versions.
- `observability-and-logging` for what the OpenTelemetry instrumentation should feed into.

---

### Checklist

- [ ] The container image is pinned to a major version, and the server runs `start --optimized` against PostgreSQL.
- [ ] Bootstrap admin credentials are replaced by a real admin account and removed.
- [ ] Applications run against their own realm, never master, and every client has exact redirect URIs.
- [ ] Public clients require PKCE, and MFA is enforced for administrative accounts through a copied flow.
- [ ] Roles reach users through groups, and policies name realm or client roles rather than raw claims.
- [ ] `KC_HOSTNAME` and TLS are configured so the issuer matches the public URL.
- [ ] `verify-token-audience` is on and `ssl-required` is `external` or `all` outside local development.
- [ ] Client secrets and realm exports are handled as secrets, never committed.
- [ ] Brute-force protection and event logging are enabled, exported, and visible in traces.
