# Security Coding Standards and Best Practices

---

## 1. Authentication and Identity (OAuth2 & OIDC)

- Adopt OAuth 2.1 standard across all new implementations.
- Strictly forbid the Implicit Grant type and the Resource Owner Password Credentials Grant type.
- Mandate the Authorization Code Grant flow with Proof Key for Code Exchange (PKCE) for all clients, including single-page applications and mobile apps.
- Use OpenID Connect (OIDC) when identity verification is required, utilizing the ID Token for identity assertions and the Access Token solely for API authorization.
- Implement short-lived Access Tokens (e.g., 15 minutes) coupled with securely stored Refresh Tokens.
- Implement Refresh Token Rotation to detect and prevent token theft.

---

## 2. Session and Token Management

- Never store JWTs or sensitive session identifiers in HTML5 LocalStorage or SessionStorage to mitigate Cross-Site Scripting (XSS) extraction.
- For web applications, transport and store tokens exclusively using secure cookies with HttpOnly, Secure, and SameSite=Strict attributes.
- Always enforce signature validation on JWTs.
- Explicitly reject JWTs with the "none" algorithm header.
- Validate all standard JWT claims upon receipt: expiration (exp), issuer (iss), and audience (aud).

---

## 3. API Security and Communication

- Mandate Transport Layer Security (TLS) 1.2 or 1.3 for all endpoints. Drop all unencrypted HTTP traffic immediately at the load balancer or API gateway.
- Implement strict Cross-Origin Resource Sharing (CORS) policies. Never use the wildcard character for the Access-Control-Allow-Origin header on endpoints that require authentication.
- Enforce API rate limiting and throttling based on IP address and user ID to prevent brute-force and denial-of-service attacks.
- Return generic error messages to clients. Never expose stack traces, database schema details, or internal server state in API responses.
- Enforce mTLS (mutual TLS) for all service-to-service communication inside a private network perimeter; do not rely on network isolation alone.

---

## 4. OWASP Top 10 Mitigation

- Defend against SQL Injection by strictly using parameterized queries, prepared statements, or modern Object-Relational Mapping (ORM) frameworks. Never concatenate user input directly into SQL strings.
- Defend against Cross-Site Scripting (XSS) by enforcing context-aware output encoding.
- Implement Content Security Policy (CSP) headers to restrict the domains from which executable scripts can be loaded.
- Defend against Cross-Site Request Forgery (CSRF) by using anti-CSRF tokens for state-changing operations, or rely on the SameSite cookie attribute.
- Implement strict input validation on the server side using an allow-list approach. Do not rely exclusively on client-side validation.
- Validate all uploaded file types by checking their actual binary signature (magic numbers), not just the file extension.

---

## 5. Security Response Headers

Every HTTP response from a web-facing service must include the following headers:

| Header | Required Value |
|---|---|
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` |
| `Content-Security-Policy` | Explicitly allowlisted sources; no `unsafe-inline` or `unsafe-eval` |
| `X-Frame-Options` | `DENY` (or `SAMEORIGIN` if framing is required) |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | Disable unused browser features (camera, microphone, geolocation) |

---

## 6. Data Protection and Cryptography

- Hash all user passwords using Argon2id or bcrypt with an appropriate work factor. Never use MD5, SHA-1, or plain SHA-256 for password storage.
- Encrypt highly sensitive data at rest (such as PII, financial data, or health records) using AES-256-GCM.
- Utilize a dedicated Key Management Service (KMS) or hardware security module (HSM) to store cryptographic keys. Never hardcode keys in the source code or store them in plaintext configuration files.
- Mask or redact all sensitive data, security tokens, and passwords before writing objects to application logs.

---

## 7. Audit Logging

- Every security-relevant event must produce an immutable audit log entry: authentication attempts (success and failure), authorization decisions, privilege escalation, data access for sensitive records, and configuration changes.
- Audit log entries must include: timestamp (UTC), actor identity, action performed, target resource, source IP, and outcome (success/failure).
- Audit logs must be written to a separate, write-only log sink that application code cannot modify or delete.
- Retain audit logs for a minimum of 12 months (or as required by applicable compliance frameworks).

---

## 8. Zero Trust Architecture

- Apply the principle "never trust, always verify" regardless of network location. Authenticate and authorize every request explicitly, even between internal services.
- Segment services with network policies (Kubernetes NetworkPolicy, cloud security groups) so that a compromised service cannot reach unrelated services.
- Enforce least-privilege access for every identity: human users, service accounts, CI/CD pipelines, and automated agents.
- Treat all tokens, credentials, and certificates as short-lived; rotate them automatically before expiry rather than on breach detection.

---

## 9. Supply Chain Security

- Generate a Software Bill of Materials (SBOM) in CycloneDX or SPDX format for every release artefact and store it as a build artifact.
- Sign all published container images using Sigstore cosign. Verify signatures in deployment pipelines before pulling an image.
- Pin all third-party dependencies to exact versions and commit lock files. Never use unversioned or `latest` dependency references in production.
- Block deployment of any artefact containing a third-party dependency with a CRITICAL or HIGH CVE that has an available fix.

---

## 10. Secret Scanning

- Run secret scanning (gitleaks or truffleHog) as a pre-commit hook and as a CI pipeline step on every PR.
- If a secret is detected in any commit — even a commit that is later amended or rebased — treat the secret as compromised and rotate it immediately.
- Configure the repository to block pushes containing high-entropy strings matching known secret patterns.
- Store all secrets in a vault (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault); inject them at runtime via environment variables or mounted secret files — never bake them into images or config files.

---

## 11. CI/CD and Secure Development Lifecycle

- Integrate Software Composition Analysis (SCA) tools into the build pipeline to automatically detect and block deployments containing third-party dependencies with known Common Vulnerabilities and Exposures (CVEs).
- Run Static Application Security Testing (SAST) on every pull request to identify hardcoded secrets, injection flaws, and insecure configurations before merging code.
- Run Dynamic Application Security Testing (DAST) against a deployed staging environment on every release candidate using OWASP ZAP or equivalent.
- Store all deployment secrets, database credentials, and API keys in secure vaults and inject them at runtime.
- Enforce branch protection: no direct push to the main branch; all changes require a reviewed and CI-passing PR.

---

## 12. Privacy by Design

- Collect only the minimum personal data required to fulfil the stated purpose (data minimisation principle).
- Document the legal basis for every category of personal data processed.
- Implement the right to erasure: personal data must be fully deletable on request without leaving ghost records in backups or logs.
- Pseudonymise or anonymise personal data in non-production environments (development, staging, testing).
- Conduct a Data Protection Impact Assessment (DPIA) before implementing any feature that processes sensitive personal data at scale.