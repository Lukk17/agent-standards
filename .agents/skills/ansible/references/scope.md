# Scope

Companion reference for the [ansible](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Writing or reviewing a playbook, a role, or a task file.
- Making a task idempotent, or diagnosing one that reports changed on every run.
- Moving secrets into Ansible Vault or into an AWX credential.
- Adding `ansible-lint`, `--check`, or Molecule to CI.
- Pinning collections in `requirements.yml`.
- Targeting more than one operating system from a single role.
- The user says "write an Ansible role for this", "this playbook is not idempotent", "encrypt these variables with Vault", "add Molecule tests to this role" or "why does my shell task always report changed".

---

### When not to activate

- Writing a one-off script for a single host, use `bash` or `powershell`.
- Provisioning cloud infrastructure declaratively rather than configuring it, use `deployment-patterns`.
- Building the container image the service runs in, use `docker-patterns`.
- Wiring health checks, metrics, or the readiness banner into the service itself, use `observability-and-logging`.
- Designing the GitHub Actions workflow that invokes Ansible, use `deployment-patterns`.

---

### Related skills

- `bash` and `powershell` for the scripts a `command` or `win_shell` task ends up invoking.
- `deployment-patterns` for the pipeline that runs Ansible and the approval gate in front of production.
- `docker-patterns` for the container images Ansible deploys.
- `observability-and-logging` for the health and readiness signals a deployed service must expose.
- The `security-auditor` agent before any change that touches credentials, privilege escalation, or a public listener. `application-security-review` covers application code only.
