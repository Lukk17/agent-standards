### AI Ansible Development Standards

---

### Core Execution Directives

- Treat all LLM generated Ansible modules, collections, and parameters as potentially hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every Ansible task generation.
- Append a Zero-Trust directive demanding mandatory web searches for current Ansible module documentation and live configuration schemas.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official Ansible documentation cannot be retrieved via live search.
- Require exact confidence percentage scores for every module parameter and configuration detail provided.
- Mandate that the agent provides direct, working links to the official Ansible documentation used to ground the code.

---

### Playbook and Role Architecture

- Structure all code into Ansible Roles instead of monolithic playbooks.
- Require the agent to generate meta/main.yml for every role with explicitly defined dependencies.
- Use Fully Qualified Collection Names for all modules.
- Separate configuration data from execution logic using host_vars and group_vars.
- Keep tasks files concise and focused on a single domain of responsibility.

---

### Variable and Secret Management

- Never hardcode secrets, passwords, API keys, or tokens in plain text.
- Require the agent to use Ansible Vault for all sensitive variables.
- Prefix all role variables with the role name to prevent namespace collisions.
- Define default variables in defaults/main.yml and override only when necessary.
- Validate variable types and constraints at the beginning of roles using the assert module.

---

### State and Idempotency

- Ensure every generated task is strictly idempotent.
- Restrict the use of the command or shell modules strictly to scenarios where no dedicated module exists.
- When shell or command modules must be used, require creates or removes parameters to guarantee idempotency.
- Do not use the changed_when and failed_when parameters to artificially mask non-idempotent behavior.

---

### Security Standards

- Execute tasks with the least privilege required.
- Apply become explicitly only on tasks that require root privileges.
- Do not apply become at the playbook level unless completely unavoidable.
- Explicitly define become_user when switching to non-root system accounts.
- Defend against injection attacks by enforcing parameterized inputs and quoting variables properly when passed to shell tasks.

---

### Linting and Validation

- Mandate the use of ansible-lint for all generated code to ensure compliance.
- Require strict adherence to YAML formatting standards.
- Generate Molecule test scenarios for testing role execution.
- Require verify.yml playbooks to confirm infrastructure state post-execution.

---

### Git and Version Control

- Configure central standards repositories as read-only.
- Use git checkout remote/master -- path/to/files to extract specific Ansible AI configuration files into projects.
- Document all required external collections in requirements.yml.
- Write task names as clear, human readable descriptions of the desired state.

---

### Multi-OS Provisioning Architecture

- Use the ansible_os_family or ansible_distribution gathered facts to dynamically route execution to OS-specific task files. [Confidence: 100%]
- Abstract all system packages into OS-specific variable files loaded via the include_vars module. Never hardcode package names directly in task files. [Confidence: 100%]
- Explicitly invoke the exact package manager module for the target OS:
  - Debian/Ubuntu: Use ansible.builtin.apt. [Confidence: 100%]
    - Link: https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/apt_module.html
    - Quote: "of"
  - Arch Linux: Use community.general.pacman. [Confidence: 100%]
    - Link: https://docs.ansible.com/projects/ansible/latest/collections/community/general/pacman_module.html
    - Quote: "(stable)"
  - Fedora/RHEL: Use ansible.builtin.dnf. [Confidence: 100%]
    - Link: https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/dnf_module.html
    - Quote: "of"
  - Windows: Use chocolatey.chocolatey.win_chocolatey. Do not use ansible.windows.win_chocolatey. [Confidence: 100%]
    - Link: https://docs.ansible.com/projects/ansible/latest/collections/chocolatey/chocolatey/win_chocolatey_module.html
    - Quote: "(stable)"
  - macOS: Use community.general.homebrew. [Confidence: 100%]
    - Link: https://docs.ansible.com/projects/ansible/latest/collections/community/general/homebrew_module.html
    - Quote: "(stable)"