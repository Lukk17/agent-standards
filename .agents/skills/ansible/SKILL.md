---
name: ansible
description: 'Ansible roles, FQCN modules, idempotency, Vault secrets and the ansible-lint plus Molecule gate. Use when the user says "write an Ansible role" or "this playbook is not idempotent". Not for one-off scripts, use `bash`.'
metadata:
  version: "1.1.0"
---

# Ansible Standards

How a playbook stays safe to run twice: every task declares the state it wants, secrets never sit in plain text, and a role proves itself in Molecule before it touches a real host. Ansible's failure mode is a play that appears to succeed while quietly doing nothing, or doing it again every run.

Written for ansible-core 2, with ansible-lint and Molecule. Pin the exact versions in the repository so every contributor and every CI run resolves the same toolchain.

---

### When not to activate

- Writing a one-off script for a single host, use `bash` or `powershell`.
- Provisioning cloud infrastructure declaratively rather than configuring it, or designing the GitHub Actions workflow that invokes Ansible, use `deployment-patterns`.
- Building the container image the service runs in, use `docker-patterns`.

---

### Reference files

| Open this | For |
|---|---|
| [role-examples.md](references/role-examples.md) | Pass and fail YAML, INI and commands for every rule below |
| [platform-targets.md](references/platform-targets.md) | Targeting several operating systems, or wiring dynamic cloud inventory |
| [awx.md](references/awx.md) | Setting up AWX or Ansible Automation Platform: Job Templates, surveys, credentials, approval nodes |
| [scope.md](references/scope.md) | Whether a neighbouring skill owns the job |
| [checklist.md](references/checklist.md) | Before calling a role or playbook change done |

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
10. Pin every collection in `requirements.yml` to an exact version, and install the pinned set in CI.
11. Enable SSH pipelining and connection reuse once in `ansible.cfg`, cache facts for large inventories, and run long tasks asynchronously.
12. Gate every change in CI, in order: `ansible-lint` with zero violations, `--syntax-check`, `--check --diff` against staging with the diff reviewed, Molecule with its idempotency run, `verify.yml`, then promote.

---

### Production needs approval

Production execution needs an explicit approval gate, an AWX approval node or a manually triggered pipeline run. Never run a playbook against production straight from a workstation or an unreviewed change.
