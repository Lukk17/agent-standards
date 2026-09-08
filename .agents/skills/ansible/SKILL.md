---
name: ansible
description: Ansible standards for role structure, FQCN modules, idempotency, Vault secrets, least-privilege become, block rescue recovery, collection pinning, and the ansible-lint plus Molecule gate. Use when you say "write an Ansible role for this", "this playbook is not idempotent", "encrypt these variables with Vault", "add Molecule tests to this role", or "why does my shell task always report changed". Not for one-off host scripting, use `bash`.
---

# Ansible Standards

How a playbook stays safe to run twice: every task declares the state it wants, secrets never sit in plain text, and
a role proves itself in Molecule before it touches a real host. Ansible's failure mode is a play that appears to
succeed while quietly doing nothing, or doing it again every run.

Baseline: ansible-core current stable, with ansible-lint and Molecule at their current stable releases. Pin the exact
versions in the repository so every contributor and every CI run resolves the same toolchain.

---

### When to activate

- Writing or reviewing a playbook, a role, or a task file.
- Making a task idempotent, or diagnosing one that reports changed on every run.
- Moving secrets into Ansible Vault or into an AWX credential.
- Adding `ansible-lint`, `--check`, or Molecule to CI.
- Pinning collections in `requirements.yml`.
- Targeting more than one operating system from a single role.

---

### When not to activate

- Writing a one-off script for a single host, use `bash` or `powershell`.
- Provisioning cloud infrastructure declaratively rather than configuring it, use `deployment-patterns`.
- Building the container image the service runs in, use `docker-patterns`.
- Wiring health checks, metrics, or the readiness banner into the service itself, use `observability-and-logging`.
- Designing the GitHub Actions workflow that invokes Ansible, use `deployment-patterns`.

---

### Roles, not monolithic playbooks

Every unit of work is a role with `defaults/`, `tasks/`, `handlers/`, and a `meta/main.yml` that names its
dependencies explicitly. A playbook only composes roles against hosts. Use Fully Qualified Collection Names for
every module, so a collection rename or a namespace collision cannot silently change which code runs.

Pass:

```yaml
- name: Ensure nginx is installed
  ansible.builtin.package:
    name: nginx
    state: present
```

Fail:

```yaml
- package: name=nginx state=present
```

Keep configuration data in `host_vars` and `group_vars`, out of the task files that consume it, and keep each task
file focused on one domain of responsibility.

---

### Variables and secrets

Prefix every role variable with the role name so two roles cannot collide in the single flat variable namespace
Ansible actually has. Put defaults in `defaults/main.yml` and override only where a host genuinely differs. Validate
types and required values with `ansible.builtin.assert` at the top of the role, so a missing variable fails on the
first task rather than halfway through a change.

Every secret lives in Ansible Vault or in an AWX credential, never in plain text.

Pass:

```yaml
nginx_tls_key: "{{ vault_nginx_tls_key }}"
```

Fail:

```yaml
nginx_tls_key: "-----BEGIN PRIVATE KEY-----MIIEvQIBADANBg..."
```

---

### Idempotency is the contract

Every task declares a desired state and reports changed only when it actually changed something. Reach for
`ansible.builtin.command` or `ansible.builtin.shell` only when no module covers the job, and give it `creates` or
`removes` so a second run is a no-op.

Pass:

```yaml
- name: Extract the release bundle
  ansible.builtin.command: tar -xzf /tmp/app.tar.gz -C /opt/app
  args:
    creates: /opt/app/VERSION
```

Fail, `changed_when: false` here hides a task that runs every time and really does mutate the host:

```yaml
- name: Extract the release bundle
  ansible.builtin.shell: tar -xzf /tmp/app.tar.gz -C /opt/app
  changed_when: false
```

`changed_when` and `failed_when` exist to describe a command's real semantics, not to paper over a non-idempotent
task. Write task names as a description of the desired state, so `--check` output reads as a plan.

---

### Least privilege on become

Apply `become` on the individual tasks that need root. A playbook-level `become: true` escalates every task,
including the ones that read a file or template a config the service user already owns.

Pass:

```yaml
- name: Install the systemd unit
  ansible.builtin.template:
    src: app.service.j2
    dest: /etc/systemd/system/app.service
  become: true
```

Fail:

```yaml
- hosts: all
  become: true
```

Set `become_user` explicitly when switching to a non-root service account, and quote every variable interpolated
into a shell task so a value containing a space or a semicolon cannot change the command.

---

### Recover deliberately with block, rescue, always

Any task group that mutates system state and may need rolling back is wrapped. `rescue` restores a known-good state
and logs the error, `always` releases locks and removes temp files whether or not the block succeeded.

Pass:

```yaml
- block:
    - name: Deploy application
      ansible.builtin.unarchive:
        src: app.tar.gz
        dest: /opt/app
  rescue:
    - name: Restore previous release
      ansible.builtin.command: /opt/app/bin/rollback.sh
  always:
    - name: Remove the staging directory
      ansible.builtin.file:
        path: /tmp/app-staging
        state: absent
```

Fail:

```yaml
- name: Deploy application
  ansible.builtin.unarchive:
    src: app.tar.gz
    dest: /opt/app
  ignore_errors: true
```

---

### Pin every collection

`requirements.yml` carries an exact version for every collection. A floating version means two runs of the same
commit can execute different module code, which is the hardest class of Ansible bug to reproduce.

Pass, with the exact versions your resolve step produced:

```yaml
collections:
  - name: community.general
    version: "9.5.1"
  - name: amazon.aws
    version: "8.2.0"
```

Fail:

```yaml
collections:
  - name: community.general
```

Install with `ansible-galaxy collection install -r requirements.yml --force` in CI so the pinned set is what runs.

---

### Performance

Enable SSH pipelining and connection reuse once, in `ansible.cfg`, rather than tuning individual plays. Cache facts
for large inventories so every run does not re-gather them.

Pass:

```ini
[ssh_connection]
pipelining = True
ssh_args = -o ControlMaster=auto -o ControlPersist=60s
```

Fail:

```ini
[defaults]
gathering = always
```

Use `async` with `poll: 0` plus `ansible.builtin.async_status` for genuinely long tasks, so the rest of the play is
not blocked waiting on a package install.

---

### Gate every change behind lint, check, and Molecule

Run these in order in CI, before any production execution:

1. `ansible-lint`, zero violations.
2. `ansible-playbook --syntax-check`, zero errors.
3. `ansible-playbook --check --diff` against a staging inventory, review the diff.
4. Molecule, full role execution plus an idempotency run in an isolated container or VM.
5. `verify.yml`, assertions that confirm the expected infrastructure state.
6. Promote. A merge produces a release artifact or a ready-to-run Job Template. Production execution needs an
   explicit approval gate, an AWX approval node or a manually triggered `workflow_dispatch` run.

Pass:

```bash
molecule test --scenario-name default
```

Fail:

```bash
ansible-playbook -i production site.yml
```

The Molecule idempotency step is the one that matters most: it runs the role twice and fails if the second run
reports any change. That is the only mechanical proof the idempotency rule above was actually followed.

---

### Reference files

| Open this | For |
|---|---|
| [references/platform-targets.md](references/platform-targets.md) | Targeting several operating systems, wiring dynamic cloud inventory, or setting up AWX and AAP Job Templates |

---

### Related skills

- `bash` and `powershell` for the scripts a `command` or `win_shell` task ends up invoking.
- `deployment-patterns` for the pipeline that runs Ansible and the approval gate in front of production.
- `docker-patterns` for the container images Ansible deploys.
- `observability-and-logging` for the health and readiness signals a deployed service must expose.
- `security-review` before any change that touches credentials, privilege escalation, or a public listener.

---

### Checklist

- [ ] Every unit of work is a role with `meta/main.yml` and explicit dependencies.
- [ ] Every module call uses its Fully Qualified Collection Name.
- [ ] Role variables are prefixed, defaulted in `defaults/main.yml`, and asserted at role entry.
- [ ] No secret in plain text, everything in Vault or an AWX credential.
- [ ] Every `command` or `shell` task carries `creates` or `removes`.
- [ ] No `changed_when: false` masking a task that really does change the host.
- [ ] `become` is on the tasks that need it, never on the play.
- [ ] State-mutating groups are wrapped in `block` / `rescue` / `always`, no bare `ignore_errors`.
- [ ] Every collection in `requirements.yml` carries an exact version.
- [ ] `ansible-lint`, `--syntax-check`, `--check --diff`, Molecule, and `verify.yml` all pass in CI.
- [ ] Molecule's second run reports zero changes.
- [ ] Production execution sits behind an explicit approval gate.
