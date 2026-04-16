# Universal Coding Standards

Applies to all languages and frameworks. Language-specific standards files do not repeat these rules.

---

## Design Principles

Follow KISS, SOLID, and DRY in every implementation.

Never implement a "quick fix" or patch that relies on hardcoded values or bypasses architectural standards. If a fix requires configuration, implement the full configuration layer immediately. Temporary code is forbidden.

Ensure solutions are long-term, not duct-tape fixes.

---

## Clean Code

### Naming
- Variable and method names must be descriptive (e.g., `calculateTotalRevenue`, not `calc`).
- Boolean variables must start with `is`, `has`, or `can`.
- Never use magic numbers; extract them to properly named constants or application properties.

### Comments
- Comments are allowed only where logic is genuinely non-obvious and cannot be made self-explanatory by extraction or renaming.
- Do not add comments that merely restate what the code does.
- Do not add docstrings or documentation to code you did not change.

### Structure
- Public methods must be concise; extract complex logic into private helpers.
- Avoid deep nesting (arrow code); use guard clauses and early returns.
- Never use fully qualified names; use imports.

---

## Error Handling

- Use global exception handlers instead of local try-catch blocks scattered across methods.
- Extract complicated error handling logic to separate, named methods.
- Implement fail-fast validation at method entry points for external inputs.
- Only validate at system boundaries (user input, external APIs). Do not add validation for scenarios that cannot happen.

---

## Security (OWASP Top 10)

- Validate and sanitize all user input at system boundaries.
- Never store secrets (API keys, passwords, tokens) in source code or committed files.
- Prevent injection vulnerabilities: SQL injection, command injection, XSS.
- Use parameterized queries for all database interactions.
- Apply principle of least privilege for all service accounts and roles.
- Use only trusted dependencies; audit third-party packages before adding them.

---

## General Constraints

- Do not add features, refactor code, or make improvements beyond what was explicitly requested.
- Do not add error handling for scenarios that cannot occur.
- Do not create helpers, utilities, or abstractions for one-time operations.
- Do not design for hypothetical future requirements (YAGNI).
- Extract configuration to environment variables or config files; never hardcode environment-specific values.
