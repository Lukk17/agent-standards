---
name: ansible
description: Ansible role structure, idempotency, vault, molecule testing, and CI standards for infrastructure automation playbooks.
origin: project-standards
---

# Ansible Standards

## Core Execution Directives

- Treat all LLM generated Ansible modules, collections, and parameters as potentially hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every Ansible task generation.
- Append a Zero-Trust directive demanding mandatory web searches for current Ansible module documentation and live configuration schemas.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official Ansible documentation cannot be retrieved via live search.
- Require exact confidence percentage scores for every module parameter and configuration detail provided.
- Mandate that the agent provides direct, working links to the official Ansible documentation used to ground the code.

---

## Playbook and Role Architecture

- Structure all code into Ansible Roles instead of monolithic playbooks.
- Require the agent to generate `meta/main.yml` for every role with explicitly defined dependencies.
- Use Fully Qualified Collection Names (FQCN) for all modules.
- Separate configuration data from execution logic using `host_vars` and `group_vars`.
- Keep task files concise and focused on a single domain of responsibility.

---

## Variable and Secret Management

- Never hardcode secrets, passwords, API keys, or tokens in plain text.
- Require the agent to use Ansible Vault for all sensitive variables.
- Prefix all role variables with the role name to prevent namespace collisions.
- Define default variables in `defaults/main.yml` and override only when necessary.
- Validate variable types and constraints at the beginning of roles using the `assert` module.

---

## State and Idempotency

- Ensure every generated task is strictly idempotent.
- Restrict the use of the `command` or `shell` modules strictly to scenarios where no dedicated module exists.
- When `shell` or `command` modules must be used, require `creates` or `removes` parameters to guarantee idempotency.
- Do not use the `changed_when` and `failed_when` parameters to artificially mask non-idempotent behavior.

---

## Security Standards

- Execute tasks with the least privilege required.
- Apply `become` explicitly only on tasks that require root privileges.
- Do not apply `become` at the playbook level unless completely unavoidable.
- Explicitly define `become_user` when switching to non-root system accounts.
- Defend against injection attacks by enforcing parameterized inputs and quoting variables properly when passed to shell tasks.

---

## Linting and Validation

- Mandate the use of `ansible-lint` for all generated code to ensure compliance.
- Require strict adherence to YAML formatting standards.
- Generate Molecule test scenarios for testing role execution.
- Require `verify.yml` playbooks to confirm infrastructure state post-execution.

---

## Git and Version Control

- Configure central standards repositories as read-only.
- Use `git checkout remote/master -- path/to/files` to extract specific Ansible AI configuration files into projects.
- Document all required external collections in `requirements.yml`.
- Write task names as clear, human-readable descriptions of the desired state.

---

## Multi-OS Provisioning Architecture

- Use the `ansible_os_family` or `ansible_distribution` gathered facts to dynamically route execution to OS-specific task files.
- Abstract all system packages into OS-specific variable files loaded via the `include_vars` module. Never hardcode package names directly in task files.
- Explicitly invoke the exact package manager module for the target OS:
  - **Debian/Ubuntu**: Use `ansible.builtin.apt`
    - Ref: https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/apt_module.html
  - **Arch Linux**: Use `community.general.pacman`
    - Ref: https://docs.ansible.com/projects/ansible/latest/collections/community/general/pacman_module.html
  - **Fedora/RHEL**: Use `ansible.builtin.dnf`
    - Ref: https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/dnf_module.html
  - **Windows**: Use `chocolatey.chocolatey.win_chocolatey`. Do not use `ansible.windows.win_chocolatey`.
    - Ref: https://docs.ansible.com/projects/ansible/latest/collections/chocolatey/chocolatey/win_chocolatey_module.html
  - **macOS**: Use `community.general.homebrew`
    - Ref: https://docs.ansible.com/projects/ansible/latest/collections/community/general/homebrew_module.html

---

## Error Recovery

Use `block` / `rescue` / `always` for any task group that modifies system state and may need rollback:

```yaml
- block:
    - name: Deploy application
      # ... tasks
  rescue:
    - name: Rollback on failure
      # ... rollback tasks
  always:
    - name: Send notification
      # ... notification tasks
```

- The `rescue` block must restore the system to a known-good state and log the failure with the error message.
- The `always` block must run cleanup tasks (remove temp files, release locks) regardless of success or failure.

---

## Performance Optimisation

- Enable SSH pipelining in `ansible.cfg` (`pipelining = True`) to reduce SSH connection overhead for multi-task playbooks.
- Enable ControlPersist via SSH multiplexing in `ansible.cfg` to reuse SSH connections:

```ini
[ssh_connection]
pipelining = True
ssh_args = -o ControlMaster=auto -o ControlPersist=60s
```

- Use `async` with `poll: 0` for long-running tasks (package installs, service restarts), then use `async_status` to wait for completion, allowing other tasks to run in parallel.
- Enable fact caching (`fact_caching = jsonfile`) for large inventories to avoid re-gathering facts on every run.

---

## Dynamic Inventory

- Use the official cloud provider inventory plugins (not deprecated scripts) for dynamic inventory:
  - **AWS**: `amazon.aws.aws_ec2`
  - **GCP**: `google.cloud.gcp_compute`
  - **Azure**: `azure.azcollection.azure_rm`
- Store inventory plugin configuration in the `inventory/` directory as YAML files committed to the repository.
- Filter dynamic inventory using `filters` and `keyed_groups` to create logical host groups without hardcoding IPs.

---

## AWX / Ansible Automation Platform (AAP)

- Define all automation as reusable Job Templates in AWX/AAP; do not run ad-hoc playbooks against production.
- Use **Survey Variables** in Job Templates for operator-supplied runtime parameters; define allowed values and defaults.
- Use **Credentials** objects in AWX/AAP for all secrets; never pass secrets as extra variables.
- Name Job Templates using the convention: `[Environment] Role/Action Description` (e.g., `[Prod] Deploy Web Application`).

---

## Collection Dependency Pinning

- Pin all Ansible Galaxy collections to exact versions in `requirements.yml`:

```yaml
collections:
  - name: community.general
    version: "9.x.x"
  - name: amazon.aws
    version: "8.x.x"
```

- Run `ansible-galaxy collection install -r requirements.yml --force` in CI to ensure reproducible collection installs.
- Never use `version: "*"` or omit the version field in `requirements.yml`.

---

## Testing Pipeline Stages

Run automation through the following gate sequence in CI before any production execution:

1. **Lint**: `ansible-lint` — zero violations.
2. **Syntax check**: `ansible-playbook --syntax-check` — zero errors.
3. **Dry run**: `ansible-playbook --check --diff` against a staging inventory — review diff output.
4. **Molecule test**: Full role execution + idempotency check in an isolated container/VM.
5. **Verify**: Run `verify.yml` assertions to confirm the expected infrastructure state.
6. **Promote**: Merge to main triggers execution against production inventory.
