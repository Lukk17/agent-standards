---
name: ansible
description: 'Ansible standards for role structure, FQCN modules, idempotency, Vault secrets, least-privilege become, collection pinning and the ansible-lint plus Molecule gate. Use when the user says "write an Ansible role for this", "this playbook is not idempotent", "encrypt these variables with Vault" or "add Molecule tests to this role". Not for one-off host scripting, use `bash`.'
---

# Ansible Standards

How a playbook stays safe to run twice: every task declares the state it wants, secrets never sit in plain text, and
a role proves itself in Molecule before it touches a real host. Ansible's failure mode is a play that appears to
succeed while quietly doing nothing, or doing it again every run.

Written for ansible-core 2, with ansible-lint and Molecule. Pin the exact versions in the repository so every contributor and every CI run resolves the same toolchain.

---

### When to activate

- Writing or reviewing a playbook, a role, or a task file.
- Making a task idempotent, or diagnosing one that reports changed on every run.
- Moving secrets into Ansible Vault or into an AWX credential.
- Adding `ansible-lint`, `--check`, or Molecule to CI.
- Pinning collections in `requirements.yml`.
- Targeting more than one operating system from a single role.
- The user says "why does my shell task always report changed".

---

### When not to activate

- Writing a one-off script for a single host, use `bash` or `powershell`.
- Provisioning cloud infrastructure declaratively rather than configuring it, use `deployment-patterns`.
- Building the container image the service runs in, use `docker-patterns`.
- Wiring health checks, metrics, or the readiness banner into the service itself, use `observability-and-logging`.
- Designing the GitHub Actions workflow that invokes Ansible, use `deployment-patterns`.

---

### Reference files

| Open this | For |
|---|---|
| [references/role-examples.md](references/role-examples.md) | Pass and fail YAML, INI and commands for every rule below |
| [references/platform-targets.md](references/platform-targets.md) | Targeting several operating systems, wiring dynamic cloud inventory, or setting up AWX and AAP Job Templates |

---

### Rules

1. Every unit of work is a role with `defaults/`, `tasks/`, `handlers/` and a `meta/main.yml` naming its dependencies. A playbook only composes roles against hosts.
2. Call every module by its Fully Qualified Collection Name, such as `ansible.builtin.apt`.
3. Keep configuration in `host_vars` and `group_vars`, and each task file on one domain of responsibility.
4. Prefix every role variable with the role name, default it in `defaults/main.yml`, and validate it with `ansible.builtin.assert` at the top of the role.
5. Every secret lives in Ansible Vault or an AWX credential, never in plain text.
6. Every task declares a desired state and reports changed only when it changed something. Use `command` or `shell` only when no module covers the job, with `creates` or `removes`, or `changed_when: true` when it runs only from a `rescue`. Never use `changed_when: false` or `failed_when` to hide a non-idempotent task.
7. Name tasks as the desired state, so `--check` output reads as a plan.
8. Put `become` on the tasks that need root, never on the play. Set `become_user` explicitly for a service account, and quote every variable interpolated into a shell task.
9. Wrap state-mutating groups in `block`, with `rescue` restoring a known-good state and logging the error, and `always` releasing locks and temp files. Never a bare `ignore_errors`.
10. Pin every collection in `requirements.yml` to an exact version, and install in CI with `ansible-galaxy collection install -r requirements.yml --force`.
11. Enable SSH pipelining and connection reuse once in `ansible.cfg`, cache facts for large inventories, and run long tasks with `async`, `poll: 0` and `ansible.builtin.async_status`.
12. Gate every change in CI, in order: `ansible-lint` with zero violations, `--syntax-check`, `--check --diff` against staging with the diff reviewed, Molecule with its idempotency run, `verify.yml`, then promote.

---

### Production needs approval

Production execution needs an explicit approval gate, an AWX approval node or a manually triggered `workflow_dispatch`
run. Never run a playbook against production straight from a workstation or an unreviewed change.

---

### Related skills

- `bash` and `powershell` for the scripts a `command` or `win_shell` task ends up invoking.
- `deployment-patterns` for the pipeline that runs Ansible and the approval gate in front of production.
- `docker-patterns` for the container images Ansible deploys.
- `observability-and-logging` for the health and readiness signals a deployed service must expose.
- The `security-auditor` agent before any change that touches credentials, privilege escalation, or a public listener. `security-review` covers application code only.

---

### Checklist

- [ ] Every unit of work is a role with `meta/main.yml` and explicit dependencies.
- [ ] Every module call uses its Fully Qualified Collection Name.
- [ ] Role variables are prefixed, defaulted in `defaults/main.yml`, and asserted at role entry.
- [ ] No secret in plain text, everything in Vault or an AWX credential.
- [ ] Every `command` or `shell` task carries `creates` or `removes`, or runs only from a `rescue` with
  `changed_when: true`.
- [ ] No `changed_when: false` masking a task that really does change the host.
- [ ] `become` is on the tasks that need it, never on the play.
- [ ] State-mutating groups are wrapped in `block` / `rescue` / `always`, no bare `ignore_errors`.
- [ ] Every collection in `requirements.yml` carries an exact version.
- [ ] `ansible-lint`, `--syntax-check`, `--check --diff`, Molecule, and `verify.yml` all pass in CI.
- [ ] Molecule's second run reports zero changes.
- [ ] Production execution sits behind an explicit approval gate.
