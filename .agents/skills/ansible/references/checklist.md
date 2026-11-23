# Ansible Checklist

Run it before calling a role or playbook change done.

- [ ] Every unit of work is a role with `meta/main.yml` and explicit dependencies.
- [ ] Every module call uses its Fully Qualified Collection Name.
- [ ] Role variables are prefixed, defaulted in `defaults/main.yml`, and asserted at role entry.
- [ ] No secret in plain text, everything in Vault or an AWX credential.
- [ ] Every `command` or `shell` task carries `creates` or `removes`, or runs only from a `rescue` with `changed_when: true`.
- [ ] No `changed_when: false` masking a task that really does change the host.
- [ ] `become` is on the tasks that need it, never on the play.
- [ ] State-mutating groups are wrapped in `block` / `rescue` / `always`, no bare `ignore_errors`.
- [ ] Every collection in `requirements.yml` carries an exact version.
- [ ] `ansible-lint`, `--syntax-check`, `--check --diff`, Molecule, and `verify.yml` all pass in CI.
- [ ] Molecule's second run reports zero changes.
- [ ] Production execution sits behind an explicit approval gate.
