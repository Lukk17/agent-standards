# Multi-OS targets, dynamic inventory, and AWX / AAP

Everything that varies by where a play runs rather than by how it is written. The rules that always apply live in
[SKILL.md](../SKILL.md).

---

### Multi-OS provisioning architecture

Route on gathered facts, never on a hostname convention. `ansible_os_family` groups Debian with Ubuntu and RedHat
with Fedora and Rocky, `ansible_distribution` separates them when the difference matters.

```yaml
- name: Load OS-specific package names
  ansible.builtin.include_vars: "{{ ansible_os_family | lower }}.yml"

- name: Include OS-specific tasks
  ansible.builtin.include_tasks: "install_{{ ansible_os_family | lower }}.yml"
```

Abstract every system package name into those OS-specific variable files. A package name hardcoded in a task file is
the single thing that breaks a role the first time it meets a second distribution.

Invoke the exact package manager module for the target, never the generic `package` module when a specific one
exists, because only the specific module exposes that manager's own options:

| Target | Module | Reference |
|---|---|---|
| Debian, Ubuntu | `ansible.builtin.apt` | https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/apt_module.html |
| Arch Linux | `community.general.pacman` | https://docs.ansible.com/projects/ansible/latest/collections/community/general/pacman_module.html |
| Fedora, RHEL | `ansible.builtin.dnf` | https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/dnf_module.html |
| Windows | `chocolatey.chocolatey.win_chocolatey` | https://docs.ansible.com/projects/ansible/latest/collections/chocolatey/chocolatey/win_chocolatey_module.html |
| macOS | `community.general.homebrew` | https://docs.ansible.com/projects/ansible/latest/collections/community/general/homebrew_module.html |

On Windows use `chocolatey.chocolatey.win_chocolatey`, not `ansible.windows.win_chocolatey`. The Chocolatey-owned
collection is the maintained one.

---

### Dynamic inventory

Use the official cloud inventory plugins, not the deprecated inventory scripts:

- AWS: `amazon.aws.aws_ec2`
- GCP: `google.cloud.gcp_compute`
- Azure: `azure.azcollection.azure_rm`

Commit the plugin configuration as YAML under `inventory/` so the grouping logic is reviewable and reproducible.

```yaml
plugin: amazon.aws.aws_ec2
regions:
  - eu-west-1
filters:
  tag:env: production
keyed_groups:
  - key: tags.role
    prefix: role
```

`filters` narrows what the plugin returns, `keyed_groups` builds logical groups out of tags. Between them there is
no reason left to hardcode an IP address anywhere in the repository.

---

### AWX and Ansible Automation Platform

Define automation as reusable Job Templates. Ad-hoc playbook runs against production leave no audit trail and no
approval record, which is the whole reason the platform exists.

- Use Survey Variables for operator-supplied runtime parameters, with allowed values and a default on each.
- Use Credentials objects for every secret. A secret passed as an extra variable is stored in the job's own record
  and shows up in the job output.
- Name Job Templates `[Environment] Role/Action Description`, for example `[Prod] Deploy Web Application`, so the
  environment is visible in every list, notification, and audit line without opening the template.
- Gate production execution behind an approval node in a Workflow Job Template. Merging to the main branch produces a
  ready-to-run template, it does not run it.
