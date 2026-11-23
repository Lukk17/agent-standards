# Scope

Companion reference for the [application-security-review](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Adding or changing authentication, session handling, or authorization.
- Creating an API endpoint, especially one that accepts a body or a file.
- Handling secrets, tokens, or credentials in code or configuration.
- Implementing payments, or storing and transmitting personal data.
- Integrating a third-party API that holds or returns sensitive data.
- Reviewing a change that touches any of the above, as the security pillar of `code-reviewer`.
- The user says "add login to this app", "review this endpoint before it ships", "we are taking payments now", "is this file upload safe", or "check this for injection".
- Hardening cloud IAM, network rules, pipeline scanning, or a CDN, through [cloud-infrastructure-security.md](cloud-infrastructure-security.md).

---

### When not to activate

- A full multi-pillar review of a change. Use `code-reviewer`, which pulls this skill in for the security pillar.
- Threat modelling, attack trees, or a formal assessment. Escalate to the `security-auditor` agent.
- Pipeline OIDC, job permissions, and action pinning. Use `deployment-patterns`.
- Container image hardening, base image choice, SBOM generation, and image scanning. Use `docker-patterns`.
- Spring Security wiring specifically. Use `springboot-patterns`.
- Writing the tests that prove a control works. Use `tdd-workflow`.

---

### Related skills

- `code-reviewer` is the parent review, and its security findings escalate to the `security-auditor` agent.
- `api-design` owns the contract and error shape validation asserts against, `observability-and-logging` the log structure redaction applies to, and `tdd-workflow` the discipline behind the control tests.
