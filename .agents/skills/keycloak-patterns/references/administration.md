# Keycloak Administration

Operating and configuring a Keycloak server: realms, clients, flows, federation, and the hardening a production
deployment needs. This is the server side of the identity boundary, not the application code that validates its tokens.

Baseline version, current as of September 2026: Keycloak 26.

---

### When to activate

- Standing up a Keycloak instance, or moving one from development mode to production.
- Creating a realm, a client, or a role model for an application.
- Configuring an authentication flow, MFA, identity brokering, or social login.
- Federating users from LDAP or Active Directory.
- Diagnosing a login failure, a token rejection, or a session that ends too soon.

---

### When not to activate

- Integrating the .NET Keycloak.AuthServices library: see [dotnet-auth-services.md](dotnet-auth-services.md).
- Verifying a JWT inside a Node service: use `node-backend-patterns`.
- Spring Security resource-server configuration: use `springboot-patterns`.
- Designing the API contract the tokens protect: use `api-design`.
- Threat modelling the wider application: use `security-review`.

---

### Reference map

| Task | Open |
| --- | --- |
| Realms, users, groups, attributes, sessions | [realm-management.md](realm-management.md) |
| OIDC and SAML clients, scopes, mappers, service accounts | [client-configuration.md](client-configuration.md) |
| Auth flows, MFA, identity brokering, social login | [authentication-sso.md](authentication-sso.md) |
| Roles, UMA fine-grained authorization, policies | [authorization-rbac.md](authorization-rbac.md) |
| LDAP and AD integration, sync, mappers | [user-federation.md](user-federation.md) |
| Password policy, brute force, TLS, audit, production checklist | [security-hardening.md](security-hardening.md) |
| Clustering, database tuning, caching, monitoring, backup | [ha-scalability.md](ha-scalability.md) |
| Login failures, token issues, LDAP sync, session problems | [administration-troubleshooting.md](administration-troubleshooting.md) |
| .NET, Spring Boot, and Node.js integration examples | [integration-examples.md](integration-examples.md) |

---

### Start development mode with a pinned image

```bash
docker run -d --name keycloak -p 8080:8080 -e KC_BOOTSTRAP_ADMIN_USERNAME=admin -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin quay.io/keycloak/keycloak:26.0 start-dev
```

Pass: a pinned major tag such as `26.0`, so a rebuild six months from now produces the same server.

Fail: `quay.io/keycloak/keycloak:latest`, which silently upgrades across a major version and can change flow defaults,
admin console behaviour, and database schema in one `docker pull`.

`KC_BOOTSTRAP_ADMIN_USERNAME` and `KC_BOOTSTRAP_ADMIN_PASSWORD` create the temporary bootstrap admin. The older
`KEYCLOAK_ADMIN` and `KEYCLOAK_ADMIN_PASSWORD` names were replaced in Keycloak 26. Create a real admin account and
remove the bootstrap credentials before the instance is reachable by anyone else.

---

### Build once, then start optimized in production

Build the server against the database you will actually run, so startup does no augmentation work:

```bash
bin/kc.sh build --db=postgres
```

Supply the runtime configuration through the environment rather than the command line, so nothing lands in a process
listing:

```bash
export KC_DB=postgres KC_DB_URL=jdbc:postgresql://localhost/keycloak KC_DB_USERNAME=keycloak KC_HOSTNAME=keycloak.example.com
```

Start with the prebuilt configuration:

```bash
bin/kc.sh start --optimized
```

Before the first real login: set a strong admin password, configure `KC_HOSTNAME`, terminate TLS in front of or inside
Keycloak, point it at PostgreSQL rather than the embedded database, and configure SMTP so verification and reset emails
work.

---

### Understand the object model before configuring it

| Concept | What it is |
| --- | --- |
| Realm | Tenant boundary. Master is for administering Keycloak, never for applications |
| Client | An application registration. OIDC or SAML, confidential (server) or public (SPA and mobile) |
| User and group | An identity with credentials. Groups exist to carry role assignments, not permissions |
| Realm role | A permission that spans every client in the realm |
| Client role | A permission scoped to one client |
| Composite role | A role that includes other roles |

Assign roles to groups and put users in groups. Assigning roles directly to users produces a permission model nobody
can audit a year later.

---

### Configure a client for SSO

1. Create an OIDC client whose client ID matches what the application sends.
2. Set exact redirect URIs. A wildcard such as `https://app.example.com/*` lets any path on the host receive the code.
3. Turn client authentication on for a server-side application, off for a public client, and require PKCE either way.
4. Give the application the discovery document at
   `{AuthServerUrl}/realms/{realm}/.well-known/openid-configuration` rather than hand-copied endpoint URLs.

Fail: a public client with no PKCE, where an intercepted authorization code can be exchanged by anyone who has it.

---

### Add MFA through a copied flow, never the built-in one

1. Authentication, then Flows, then duplicate the Browser flow.
2. Add an OTP or WebAuthn authenticator to the copy.
3. Set it Required, or Conditional on a group or role so administrators get it first.
4. Bind the copy to the realm as the browser flow.

Editing the built-in flow in place leaves no clean way back when the change locks everyone out, including you.

---

### Connect LDAP or Active Directory

1. User Federation, then add an LDAP provider.
2. Configure the URL, the bind DN, and a search base such as `ou=users,dc=example,dc=com`.
3. Map the attributes you need, including the ones roles depend on.
4. Test the connection, then run a sync, then check a real user before enabling it broadly.

Choose the edit mode deliberately. `READ_ONLY` keeps the directory authoritative, `WRITEABLE` lets Keycloak write back,
and picking the wrong one is discovered when a password reset fails.

---

### Administer from the CLI for anything repeatable

Authenticate the admin CLI once per session:

```bash
bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user admin
```

Create a realm:

```bash
bin/kcadm.sh create realms -s realm=my-realm -s enabled=true
```

Create a user:

```bash
bin/kcadm.sh create users -r my-realm -s username=john -s enabled=true
```

Set that user's password:

```bash
bin/kcadm.sh set-password -r my-realm --username john --new-password secret
```

Export a realm for backup or promotion between environments:

```bash
bin/kc.sh export --dir /backup --realm my-realm
```

Import it on the target:

```bash
bin/kc.sh import --dir /backup
```

An export contains client secrets. Treat the directory as a secret, not as a configuration artifact to commit.

---

### Production defaults worth setting on day one

- One realm per application and environment. Never run an application against the master realm.
- Access tokens live 5 to 15 minutes. Refresh token lifetime follows the session policy, not habit.
- Brute-force detection enabled, with a lockout that a support process can actually undo.
- MFA required for every account with realm-management roles.
- Event logging on, with login and admin events shipped off the box before they rotate.
- TLS everywhere, and `KC_HOSTNAME` set so issued tokens carry the public issuer rather than an internal address.

---

### Where to go next

- [dotnet-auth-services.md](dotnet-auth-services.md) for the .NET client library that consumes this server.
- `springboot-patterns` and `node-backend-patterns` for validating the tokens Keycloak issues.
- `api-design` for the status codes and error bodies an authorization failure should produce.
- `security-review` for threat modelling around the identity boundary.
- `docker-patterns` for running the container safely in a local stack.

---

### Checklist

- [ ] The container image is pinned to a major version, never `latest`.
- [ ] Bootstrap admin credentials are replaced by a real admin account and removed.
- [ ] Applications run against their own realm, not master.
- [ ] Every client has exact redirect URIs and no wildcard.
- [ ] Public clients require PKCE.
- [ ] MFA is enforced for administrative accounts.
- [ ] Brute-force protection and event logging are enabled and exported.
- [ ] `KC_HOSTNAME` and TLS are configured so the issuer matches the public URL.
- [ ] The server runs `start --optimized` against PostgreSQL, not development mode.
- [ ] Realm exports are handled as secrets.
