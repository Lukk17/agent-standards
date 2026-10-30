# Role Rules in Depth

Contents:

- [Roles, not monolithic playbooks](#roles-not-monolithic-playbooks)
- [Variables and secrets](#variables-and-secrets)
- [Idempotency is the contract](#idempotency-is-the-contract)
- [Least privilege on become](#least-privilege-on-become)
- [Recover deliberately with block, rescue, always](#recover-deliberately-with-block-rescue-always)
- [Pin every collection](#pin-every-collection)
- [Performance](#performance)
- [Gate every change behind lint, check, and Molecule](#gate-every-change-behind-lint-check-and-molecule)

Companion reference for the [ansible](../SKILL.md) skill. Load it for the pass and fail YAML, INI and commands behind each rule: role layout and FQCN, variables and Vault, idempotency, become, block and rescue, collection pinning, performance, and the CI gate.

---

### Roles, not monolithic playbooks

Every unit of work is a role with `defaults/`, `tasks/`, `handlers/`, and a `meta/main.yml` that names its
dependencies explicitly. A playbook only composes roles against hosts. Use Fully Qualified Collection Names for
every module, so a collection rename or a namespace collision cannot silently change which code runs.

Pass:

```yaml
- name: Ensure nginx is installed
  ansible.builtin.apt:
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
`removes` so a second run is a no-op. A command that runs only from a `rescue` has no such marker, so it states its
real result with `changed_when: true` instead.

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
      changed_when: true
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
