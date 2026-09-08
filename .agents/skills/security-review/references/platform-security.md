# Platform security requirements

The controls that sit around the application code rather than inside a single handler: how tokens are issued and
validated, how services authenticate to each other, what headers every response carries, and what the pipeline and the
data lifecycle owe. Depth behind [SKILL.md](../SKILL.md).

---

### OAuth 2.1 and PKCE

- PKCE is mandatory on every authorization code flow, with the `S256` code challenge method.
- The implicit grant is removed in OAuth 2.1. Use authorization code plus PKCE instead.
- Resource owner password credentials is prohibited with no exceptions: it hands the client the user's password and
  defeats every second factor.
- Rotate refresh tokens. Issue a new one on every use and invalidate the old one immediately, so a stolen token is
  detectable as a reuse.
- Access token lifetime caps at 15 minutes.

---

### JWT validation

A token is only as trustworthy as the claims you actually check. Validate all four of these on every request, and pin
the algorithm explicitly.

- `alg`: reject `none`, and configure an explicit algorithm allowlist rather than accepting whatever the token declares.
- `exp`: the token must not be expired.
- `iss`: must equal the expected issuer exactly.
- `aud`: must equal the expected audience.

```python
import jwt

def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        options={"require": ["exp", "iss", "aud"]},
        audience="my-api",
        issuer="https://auth.example.com",
    )
```

Passing a wildcard or the token's own `alg` value into `algorithms` is the algorithm-confusion vulnerability: an
attacker re-signs the token with the public key as an HMAC secret and the library accepts it.

---

### Service-to-service mTLS

Internal traffic gets mutual TLS, so a service proves its identity rather than inheriting trust from being inside the
network.

- Both client and server present certificates.
- Issue internal certificates from a private CA, not the public one.
- Keep certificate lifetimes short, under 24 hours, with automated issuance through cert-manager or a Vault PKI backend.

---

### Required response headers

Every response from an application serving a browser carries these.

```http
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-{random}'; frame-ancestors 'none'
Permissions-Policy: camera=(), microphone=(), geolocation=()
Referrer-Policy: strict-origin-when-cross-origin
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
```

---

### Zero trust

- Never trust, always verify. No implicit trust from network location.
- Authenticate and authorize every request, including between internal services.
- Default-deny network policies, with explicit allow rules for the paths that must exist.
- Short-lived credentials, rotated automatically.
- Least privilege for every service account.

---

### Supply chain

- Generate an SBOM for every release, in CycloneDX or SPDX format.
- Sign container images with cosign on every production push.
- Pin every dependency to an exact version in a committed lock file. Unpinned ranges are prohibited in production.
- Block CI on critical and high CVEs that have a fix available, using Trivy, Grype, or the language's own audit command.

The container-side mechanics, base image choice, image scanning and signing in the build pipeline, belong to the
`docker-patterns` skill.

---

### Audit logging

Every security-relevant event produces an immutable log entry carrying:

- `timestamp`, UTC ISO 8601
- `actor`, user id or service account
- `action`, what was done
- `resource`, what it was done to
- `outcome`, success or failure
- `ip_address` and `user_agent` for user-initiated actions

Write to an append-only sink in a separate account, so an attacker who compromises the application cannot rewrite the
record of it. Retain for at least 12 months, and never expose raw audit logs to end users.

---

### Privacy by design

- Data minimisation: collect only what the feature strictly needs.
- Legal basis: document the basis (consent, legitimate interest, contract) for each category of personal data.
- Right to erasure: implement it, and complete within 30 days of a request.
- Data protection impact assessment: required before shipping a feature that processes sensitive personal data at scale.
- Pseudonymisation outside production: never load real personal data into a development or staging environment.

---

### Encryption at rest

- Field-level symmetric encryption: AES-256-GCM.
- Key wrapping: RSA-4096 or ECDSA P-384.
- Manage keys in a KMS or HSM. A master key never lives in application config.
- Rotate encryption keys annually, and immediately on suspected compromise.

---

### SAST and DAST

- Static analysis on every pull request: Semgrep, SonarQube, or Bandit for Python.
- Dynamic analysis weekly and before every major release, with OWASP ZAP against a staging environment.
- Dependency scanning on every pull request, with the language's audit command plus a filesystem scanner.

---

### Reading

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Security in Next.js Server Components and Actions](https://nextjs.org/blog/security-nextjs-server-components-actions)
- [Web Security Academy](https://portswigger.net/web-security)
