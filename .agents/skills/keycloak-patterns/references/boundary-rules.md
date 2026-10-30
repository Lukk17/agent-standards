# Boundary Rules

Contents:

- [Decide which side of the boundary the task is on](#decide-which-side-of-the-boundary-the-task-is-on)
- [One realm per application and environment](#one-realm-per-application-and-environment)
- [Assign roles to groups, never directly to users](#assign-roles-to-groups-never-directly-to-users)
- [Never edit a built-in authentication flow in place](#never-edit-a-built-in-authentication-flow-in-place)
- [Verify the audience, and keep the issuer public](#verify-the-audience-and-keep-the-issuer-public)
- [Keep every secret out of the repository and out of the process list](#keep-every-secret-out-of-the-repository-and-out-of-the-process-list)
- [Pin the version on both sides](#pin-the-version-on-both-sides)

Companion reference for the [keycloak-patterns](../SKILL.md) skill. Load it for the reasoning behind the rules that hold on both sides of the identity boundary: which side owns a problem, realms, roles through groups, copied flows, audience and issuer, secrets, and version pinning.

---

### Decide which side of the boundary the task is on

Most confusion here comes from fixing the wrong side. A token that is rejected is either minted wrong or validated
wrong, and the two have different owners. Establish which before touching anything.

```text
Server side: the realm, the client registration, the flow, the mappers, the roles, the issuer URL.
Client side: the audience check, the policy, the claims transformation, the token cache, the SDK call.
```

The two reference tables in the skill split along exactly that line.

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

A Keycloak image tagged `latest` silently upgrades across a major version and can change flow defaults, admin console behaviour, and the database schema in one `docker pull`. Pin a minor version tag and move it deliberately, build once with `bin/kc.sh build`, and start with `start --optimized` against PostgreSQL. Pin the NuGet package versions the same way.
