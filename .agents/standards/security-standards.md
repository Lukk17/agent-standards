### Security Coding Standards and Best Practices

---

#### 1. Authentication and Identity (OAuth2 & OIDC)
- Adopt OAuth 2.1 standard across all new implementations.
- Strictly forbid the Implicit Grant type and the Resource Owner Password Credentials Grant type.
- Mandate the Authorization Code Grant flow with Proof Key for Code Exchange (PKCE) for all clients, including single-page applications and mobile apps.
- Use OpenID Connect (OIDC) when identity verification is required, utilizing the ID Token for identity assertions and the Access Token solely for API authorization.
- Implement short-lived Access Tokens (e.g., 15 minutes) coupled with securely stored Refresh Tokens.
- Implement Refresh Token Rotation to detect and prevent token theft.

---

#### 2. Session and Token Management
- Never store JWTs or sensitive session identifiers in HTML5 LocalStorage or SessionStorage to mitigate Cross-Site Scripting (XSS) extraction.
- For web applications, transport and store tokens exclusively using secure cookies with HttpOnly, Secure, and SameSite=Strict attributes.
- Always enforce signature validation on JWTs.
- Explicitly reject JWTs with the "none" algorithm header.
- Validate all standard JWT claims upon receipt: expiration (exp), issuer (iss), and audience (aud).

---

#### 3. API Security and Communication
- Mandate Transport Layer Security (TLS) 1.2 or 1.3 for all endpoints. Drop all unencrypted HTTP traffic immediately at the load balancer or API gateway.
- Implement strict Cross-Origin Resource Sharing (CORS) policies. Never use the wildcard character for the Access-Control-Allow-Origin header on endpoints that require authentication.
- Enforce API rate limiting and throttling based on IP address and user ID to prevent brute-force and denial-of-service attacks.
- Return generic error messages to clients. Never expose stack traces, database schema details, or internal server state in API responses.

---

#### 4. OWASP Top 10 Mitigation
- Defend against SQL Injection by strictly using parameterized queries, prepared statements, or modern Object-Relational Mapping (ORM) frameworks. Never concatenate user input directly into SQL strings.
- Defend against Cross-Site Scripting (XSS) by enforcing context-aware output encoding. 
- Implement Content Security Policy (CSP) headers to restrict the domains from which executable scripts can be loaded.
- Defend against Cross-Site Request Forgery (CSRF) by using anti-CSRF tokens for state-changing operations, or rely on the SameSite cookie attribute.
- Implement strict input validation on the server side using an allow-list approach. Do not rely exclusively on client-side validation.
- Validate all uploaded file types by checking their actual binary signature (magic numbers), not just the file extension.

---

#### 5. Data Protection and Cryptography
- Hash all user passwords using Argon2id or bcrypt with an appropriate work factor. Never use MD5, SHA-1, or plain SHA-256 for password storage.
- Encrypt highly sensitive data at rest (such as PII, financial data, or health records) using AES-256-GCM.
- Utilize a dedicated Key Management Service (KMS) or hardware security module (HSM) to store cryptographic keys. Never hardcode keys in the source code or store them in plaintext configuration files.
- Mask or redact all sensitive data, security tokens, and passwords before writing objects to application logs.

---

#### 6. CI/CD and Secure Development Lifecycle
- Integrate Software Composition Analysis (SCA) tools into the build pipeline to automatically detect and block deployments containing third-party dependencies with known Common Vulnerabilities and Exposures (CVEs).
- Run Static Application Security Testing (SAST) on every pull request to identify hardcoded secrets, injection flaws, and insecure configurations before merging code.
- Store all deployment secrets, database credentials, and API keys in secure vaults (e.g., HashiCorp Vault, AWS Secrets Manager) and inject them at runtime.