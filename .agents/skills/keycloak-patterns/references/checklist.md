# Keycloak Patterns Checklist

Run it before calling a Keycloak change on either side of the boundary, or a review of one, done. The checklists for one side sit at the end of [administration.md](administration.md), [security-hardening.md](security-hardening.md) and [dotnet-auth-services.md](dotnet-auth-services.md).

- [ ] The container image is pinned to a minor version tag, and the server runs `start --optimized` against PostgreSQL.
- [ ] Bootstrap admin credentials are replaced by a real admin account and removed.
- [ ] Applications run against their own realm, never master, and every client has exact redirect URIs.
- [ ] Every client, confidential or public, requires PKCE, and MFA is enforced for administrative accounts through a copied flow.
- [ ] Roles reach users through groups, and policies name realm or client roles rather than raw claims.
- [ ] `KC_HOSTNAME` and TLS are configured so the issuer matches the public URL.
- [ ] `verify-token-audience` is on and `ssl-required` is `external` or `all` outside local development.
- [ ] Client secrets and realm exports are handled as secrets, never committed.
- [ ] Brute-force protection and event logging are enabled, exported, and visible in traces.
